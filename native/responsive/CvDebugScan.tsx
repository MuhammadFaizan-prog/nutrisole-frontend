// G9 Stage J5-J8 (cv-gauntlet-device): phone-test layer for the Scan screen. Loaded ONLY when CV_DEBUG_PIPELINE is true
// (native/src/cv/device/flags.ts, default false; the QA APK swaps in flags.qa.ts at bundle time). With the flag off this module is
// never required, so no camera permission is requested and no native camera / inference module is touched.
// J8 (default) LIVE mode: VisionCamera frame output -> GPU resizer in the frame worklet (480 letterbox inner size, RGB uint8) ->
//   RN thread, ONE inference in flight, adaptive 3-8 updates/s, frames dropped never queued -> G3 (ORT, its own native thread) ->
//   class-agnostic grouping -> IoU tracker -> label only when the UNCHANGED wide policy (DEFAULT_ID: 3 frames, score >= 0.5) passes
//   on 3 successive live frames of that track. Tap a tracked item -> ONE high-res photo -> H2 close-up -> FROZEN_VERIFY P-a ->
//   "<name>. Not graded" / "Unable to identify". Guidance hints (Move closer / Hold steady / Improve lighting) are UI only.
// J9: the FROZEN G3 scene guard (sceneGuard / DEFAULT_SCENE_GUARD, minAreaFrac 0.01, rule 2 off) runs on every path (live frames,
//   close-up photo, tap-3 stills) via device/guard.ts before grouping / tracking / tapping. Below it: no box, no label, not tappable,
//   never confirmed, no tracker hit; one rate-limited "Move closer" chip instead; suppressions logged as "NSCV suppressed".
// J7 tap -> 3-photo burst stays as an OPTIONAL fallback mode (toggle), never the default. Grades stay blocked; no model score is ever shown.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AppState, Linking, NativeModules, Pressable, StyleSheet, Text, View } from 'react-native';
import { Camera, useCameraDevice, useCameraPermission, usePhotoOutput, useFrameOutput } from 'react-native-vision-camera';
import { createResizer, isResizerAvailable } from 'react-native-vision-camera-resizer';
import { createSynchronizable, scheduleOnRN } from 'react-native-worklets';
import { InferenceSession, Tensor } from 'onnxruntime-react-native';
import { permissionView } from '../src/cv/device/permissions.ts';
import { rawToRgb, detectorInput, cropRgb, type PixelFormat } from '../src/cv/device/pixels.ts';
import { runDebugPipeline, runCloseupFromTrack, BURST, labelOf, DET_DECODE_FLOOR, type UprightStill } from '../src/cv/device/debugPipeline.ts';
import { guardFrame, closerCandidates, createCloserHint, type Suppressed } from '../src/cv/device/guard.ts';
import { overlayBoxes, type OverlayBox } from '../src/cv/device/overlay.ts';
import { resolveDebugModels, MODELS_NOT_LOADED, type ModelNative } from '../src/cv/device/modelSource.ts';
import { checkModelIO, MODEL_IO, identityCrop, type RuntimeMeta } from '../src/cv/pipeline/camera.ts';
import { decodeRawWithNms } from '../src/cv/pipeline/postprocess.ts';
import { detectorToFrame } from '../src/cv/pipeline/closeup.ts';
import { nscv, setCvDebug, nscvResultLine } from '../src/cv/debug.ts';
import { inferenceBadge, createLatencyRecorder, createLagSampler } from '../src/cv/device/instrument.ts';
import { nutritionForCv } from '../src/cv/data/nutrition.ts';
import { stillBoxToView } from '../src/cv/device/orientation.ts';
import {
  gateVerdict, createThrottler, liveResizeDims, rotateRgb, unpackResized, mergeAgnostic, LiveTracker, trackWide, guidanceHints, qualityMetrics,
  boxSide, meanRgb, colourCheck, lifeReduce, LIFE_INITIAL, cameraActive, frameProcessorActive, effectiveMode, DEFAULT_SCAN_MODE, createPerfMeter, perfLine,
  type GateState, type LiveTrackView, type Hint, type ScanMode, type CamOrientation, type PerfSnapshot,
} from '../src/cv/device/live.ts';
import { diagRecord, diagLine, shouldSave, toBase64, suppressedRecord, suppressedLine, createSuppressedLogger } from '../src/cv/device/diag.ts';
import { DEFAULT_SCENE_GUARD } from '../src/cv/pipeline/postprocess.ts';
import { h2Input } from '../src/cv/pipeline/camera.ts';
import { asProbs } from '../src/cv/device/pixels.ts';
import { h2Top3 } from '../src/cv/device/debugPipeline.ts';
import { nscvSink, jsHeapMb, type NsCvNative } from '../src/cv/device/nativeCv.ts';
import CvPerfOverlay from './CvPerfOverlay';

const MAX_SIDE = 1280;   // upright still is downscaled to this longest side before inference (crop still >> 224 px)
type Sessions = { h2: InferenceSession; g3_det: InferenceSession };
type LiveFrame = { rgb: Uint8Array; w: number; h: number; frameW: number; frameH: number; t: number };
type ShownTrack = LiveTrackView & { hints: Hint[] };
const NC = 12; const N_ANCHORS = 4725;
const nativeCv = NativeModules.NsModelAssets as (ModelNative & NsCvNative) | undefined;

// J8 model reuse: ONE pair of ORT sessions per app process, shared by every mount of the debug layer (never reloaded per frame).
let SESSIONS: Promise<Sessions | { error: string; message: string }> | null = null;
function loadSessionsOnce(): Promise<Sessions | { error: string; message: string }> {
  if (SESSIONS) return SESSIONS;
  SESSIONS = (async () => {
    try {
      // J7: bundled QA-APK assets first, hash-verified adb push second; both sha256-checked against models.ts. No mock fallback.
      const src = await resolveDebugModels(NativeModules.NsModelAssets as ModelNative | undefined);
      src.lines.forEach((l) => nscv(l));
      if (!src.ok) { nscv(`NSCV event=models_not_loaded ${src.message.slice(0, 200)}`); SESSIONS = null; return { error: 'models not loaded', message: src.message }; }
      const t0 = Date.now(); const h2 = await InferenceSession.create(src.paths.h2); const t1 = Date.now();
      const g3 = await InferenceSession.create(src.paths.g3_det); const t2 = Date.now();
      nscv(`NSCV stage=init model=h2 ms=${t1 - t0}`); nscv(`NSCV stage=init model=g3_det ms=${t2 - t1}`);
      nscv(`NSCV model h2 inputs=${h2.inputNames.join('|')} outputs=${h2.outputNames.join('|')} io=${JSON.stringify(checkModelIO('h2', meta(h2)).filter((e) => !/rank|dim/.test(e)))}`);
      nscv(`NSCV model g3_det inputs=${g3.inputNames.join('|')} outputs=${g3.outputNames.join('|')}`);
      return { h2, g3_det: g3 };
    } catch (e) {
      nscv(`NSCV event=model_load_failed error=${String(e).slice(0, 160)}`); SESSIONS = null;
      return { error: 'models not loaded', message: `${MODELS_NOT_LOADED}: ONNX session failed (${String(e).slice(0, 80)}). See P1 guide.` };
    }
  })();
  return SESSIONS;
}
function meta(s: InferenceSession): RuntimeMeta {
  return { inputs: s.inputNames.map((n) => ({ name: n, shape: [] })), outputs: s.outputNames.map((n) => ({ name: n, shape: [] })) };
}

export default function CvDebugScan({ width, height, back }: { width: number; height: number; back: () => void }) {
  const { status, canRequestPermission, requestPermission } = useCameraPermission() as any;
  const device = useCameraDevice('back');
  const photoOutput = usePhotoOutput();
  const sessions = useRef<Sessions | null>(null);
  const [state, setState] = useState('Loading models…');
  const [title, setTitle] = useState<string | null>(null);
  const [boxes, setBoxes] = useState<OverlayBox[]>([]);
  const busy = useRef(false);
  const [fromPipeline, setFromPipeline] = useState(false);
  const [badgeReason, setBadgeReason] = useState('loading models');
  const [domainLine, setDomainLine] = useState<string | null>(null);
  const [banner, setBanner] = useState<string | null>(null);
  const lat = useRef(createLatencyRecorder(() => Date.now()));
  const pv = permissionView(true, status, !!canRequestPermission);
  // ---- J8 lifecycle + mode
  const [life, setLife] = useState(LIFE_INITIAL);
  const liveSupported = useMemo(() => { try { return isResizerAvailable(); } catch { return false; } }, []);
  const [pref, setPref] = useState<ScanMode>(DEFAULT_SCAN_MODE);
  const mode = effectiveMode(pref, liveSupported);
  const [tracks, setTracks] = useState<ShownTrack[]>([]);
  const [liveBuf, setLiveBuf] = useState<{ w: number; h: number } | null>(null);
  const [perf, setPerf] = useState<PerfSnapshot | null>(null);
  const tracker = useRef(new LiveTracker());
  // ---- J9 frozen scene guard: one discreet "Move closer" hint for the whole screen + separate suppressed-detection log
  const [closer, setCloser] = useState(false);
  const closerHint = useRef(createCloserHint());
  const suppLog = useRef(createSuppressedLogger());
  const lastSuppressed = useRef<Suppressed[]>([]);
  const droppedSeen = useRef(0);
  const clearLive = () => { tracker.current.reset(); setTracks([]); closerHint.current.reset(); setCloser(false); lastSuppressed.current = []; };
  const throttler = useRef(createThrottler());
  const meter = useRef(createPerfMeter(() => Date.now()));
  const lastLive = useRef<LiveFrame | null>(null);
  const thermal = useRef(-1);
  const shownLog = useRef(new Map<number, string>());
  const saves = useRef<number[]>([]);
  const gate = useMemo(() => createSynchronizable<GateState & { enabled: boolean; fw: number; fh: number }>({ busy: false, nextDueMs: 0, enabled: false, fw: 0, fh: 0 }), []);
  const counters = useMemo(() => createSynchronizable({ frames: 0, skipBusy: 0, skipInterval: 0 }), []);
  const [resizer, setResizer] = useState<any>(null);
  const resizerDims = useRef<string>('');

  useEffect(() => { setCvDebug(true, nscvSink(nativeCv)); }, []);
  useEffect(() => {   // J6: UI responsiveness hook (JS event-loop lag), logged every 10 s
    const lag = createLagSampler(() => Date.now(), 100); const a = setInterval(lag.tick, 100); const b = setInterval(() => nscv(lag.line()), 10000);
    return () => { clearInterval(a); clearInterval(b); };
  }, []);
  useEffect(() => { if (pv.action === 'request') requestPermission(); }, [pv.action, requestPermission]);
  useEffect(() => { if (status === 'authorized' || status === 'denied') setLife((s) => lifeReduce(s, { type: 'permission', granted: status === 'authorized' })); }, [status]);
  useEffect(() => {   // J8: pause on background, resume on foreground; tracks are reset so no stale label survives a pause
    const sub = AppState.addEventListener('change', (s) => {
      const active = s === 'active'; setLife((l) => lifeReduce(l, { type: 'app_state', active }));
      if (!active) clearLive();
      nscv(`NSCV event=app_state state=${s}`);
    });
    return () => { sub.remove(); setLife((l) => lifeReduce(l, { type: 'unmount' })); tracker.current.reset(); };
  }, []);
  useEffect(() => {
    let live = true;
    loadSessionsOnce().then((r) => {
      if (!live) return;
      if ('error' in r) { setBadgeReason('models not loaded'); setState(r.message); setLife((s) => lifeReduce(s, { type: 'models', ok: false })); return; }
      sessions.current = r; setLife((s) => lifeReduce(s, { type: 'models', ok: true }));
      setState(mode.mode === 'live' ? 'Point at an item' : 'Tap an item'); setBadgeReason(mode.mode === 'live' ? 'models loaded, live' : 'models loaded, tap an item');
      nscv(`NSCV event=mode mode=${mode.mode} live_supported=${liveSupported ? 1 : 0}${mode.note ? ' note=no_gpu_resizer' : ''}`);
    });
    return () => { live = false; };
  }, []);   // eslint-disable-line react-hooks/exhaustive-deps

  const fpActive = frameProcessorActive(life, mode.mode);
  useEffect(() => { gate.setBlocking((g) => ({ ...g, enabled: fpActive, busy: false })); if (!fpActive) clearLive(); }, [fpActive, gate]);   // eslint-disable-line react-hooks/exhaustive-deps

  // ---- J8 perf + runtime stats every 5 s (screen + logcat). Numbers only from this device.
  const lastCounters = useRef({ frames: 0, skipBusy: 0, skipInterval: 0 });
  useEffect(() => {
    if (!fpActive) return;
    const id = setInterval(async () => {
      const c = counters.getDirty(); const p = lastCounters.current;
      meter.current.frame(c.frames - p.frames); meter.current.skipped(c.skipBusy - p.skipBusy, c.skipInterval - p.skipInterval); lastCounters.current = { ...c };
      let nativeHeap: number | null = null;
      try { const s = await nativeCv?.runtimeStats?.(); if (s) { thermal.current = s.thermal; nativeHeap = Math.round(s.nativeHeapMb * 10) / 10; } } catch { /* optional */ }
      const snap = meter.current.snapshot(throttler.current.intervalMs, thermal.current, jsHeapMb(), nativeHeap);
      setPerf(snap); nscv(perfLine(snap));
    }, 5000);
    return () => clearInterval(id);
  }, [fpActive, counters]);

  // ---- J8 resizer: created from the first frame's size (sensor orientation, letterbox inner size), reused afterwards
  const onMeta = useCallback(async (fw: number, fh: number, orientation: string, pixelFormat: string) => {
    const d = liveResizeDims(fw, fh); const key = `${d.w}x${d.h}`;
    if (resizerDims.current === key) return; resizerDims.current = key;
    nscv(`NSCV live frame=${fw}x${fh} orientation=${orientation} pixel_format=${pixelFormat} resize=${key}`);
    try { const r = await createResizer({ width: d.w, height: d.h, channelOrder: 'rgb', dataType: 'uint8', scaleMode: 'stretch', pixelLayout: 'interleaved' }); setResizer(r); }
    catch (e) { nscv(`NSCV event=resizer_failed error=${String(e).slice(0, 160)}`); setPref('tap3'); setBanner('Live mode could not start on this device; using tap-to-analyze.'); }
  }, []);
  const onMetaRef = useRef(onMeta); onMetaRef.current = onMeta;
  const onMetaStable = useCallback((fw: number, fh: number, o: string, pf: string) => { onMetaRef.current(fw, fh, o, pf); }, []);

  // ---- J8 RN-thread live step: one frame in, overlay out, gate released
  const onLiveFrame = useCallback(async (buf: ArrayBuffer, bw: number, bh: number, orientation: CamOrientation, mirrored: boolean, fw: number, fh: number, tFrame: number) => {
    const S = sessions.current; const t0 = Date.now();
    if (!S) { gate.setBlocking((g) => ({ ...g, busy: false })); return; }
    try {
      const packed = unpackResized(buf, bw, bh);
      const up = rotateRgb(packed.rgb, bw, bh, orientation, mirrored);
      const swap = orientation === 'left' || orientation === 'right'; const frameUpW = swap ? fh : fw; const frameUpH = swap ? fw : fh;
      const x = detectorInput(up.rgb, up.w, up.h);
      const ti = Date.now(); const r = await S.g3_det.run({ [S.g3_det.inputNames[0]]: new Tensor('float32', x, MODEL_IO.g3_det.inputs[0].shape as number[]) });
      const inferMs = Date.now() - ti; const out = r[S.g3_det.outputNames[0]].data as Float32Array;
      const raw = decodeRawWithNms(out, NC, N_ANCHORS, DET_DECODE_FLOOR).map((d) => ({ ...d, box: detectorToFrame(d.box, up.w, up.h) }));
      // J9: frozen 1 % scene guard, area in the upright camera frame (letterbox undone; the buffer is a uniform scale of the frame).
      // Suppressed boxes never reach mergeAgnostic / the tracker as hits; a track they overlap is dropped at once (no stale box).
      const g = guardFrame(raw, up.w, up.h);
      const views = tracker.current.update(mergeAgnostic(g.kept), t0, g.suppressed.map((d) => d.box));
      lastSuppressed.current = g.suppressed;
      const closerOn = closerHint.current.update(closerCandidates(g.suppressed).length, g.kept.length, t0); setCloser(closerOn);
      const due = suppLog.current.feed(t0, g.suppressed.length);
      if (due) {
        const dropped = tracker.current.droppedBySuppression - droppedSeen.current; droppedSeen.current = tracker.current.droppedBySuppression;
        const srec = suppressedRecord({ path: 'live', tMs: t0, frame: [up.w, up.h], params: g.params, decodeFloor: DET_DECODE_FLOOR, nIn: raw.length, suppressed: g.suppressed,
          framesSinceLast: due.framesSinceLast, suppressedSinceLast: due.suppressedSinceLast, droppedTracks: dropped, hintVisible: closerOn });
        nscv(suppressedLine(srec)); nativeCv?.appendDiag?.(JSON.stringify(srec)).catch(() => undefined);
      }
      const scale = frameUpW / up.w;   // live buffer px -> full frame-output px (the "source pixels" of the size hint)
      const shown: ShownTrack[] = views.map((v) => {
        const q = qualityMetrics(up.rgb, up.w, up.h, v.box, scale);
        const t = tracker.current.tracks.find((k) => k.id === v.id); const jit = t?.jitter.length ? t.jitter[t.jitter.length - 1] : undefined;
        return { ...v, hints: guidanceHints({ sidePx: q.sidePx, blurVar: q.blurVar, meanV: q.meanV, jitterIou: jit, touchesEdge: q.touchesEdge }) };
      });
      lastLive.current = { rgb: up.rgb, w: up.w, h: up.h, frameW: frameUpW, frameH: frameUpH, t: t0 };
      setLiveBuf({ w: up.w, h: up.h }); setTracks(shown); setFromPipeline(true);
      if (!banner && shown.length) setBadgeReason('live');
      const now = Date.now(); meter.current.detection(inferMs, now - tFrame);
      lat.current.record('live_g3_infer', inferMs);
      // per-decision diagnostics: whenever a track's shown label / state changes (rate-bounded by the track count)
      for (const v of shown) {
        const sig = `${v.state}:${v.label ?? '-'}:${v.hints.map((h) => h.code).join(',')}`;
        if (shownLog.current.get(v.id) === sig) continue; shownLog.current.set(v.id, sig);
        const t = tracker.current.tracks.find((k) => k.id === v.id); const last = t?.obs.filter(Boolean).slice(-1)[0] ?? null;
        let h2t: { classId: number; p: number }[] | null = null;
        if (v.label && t) {   // report-only: H2 top-3 on the PREVIEW-resolution crop when a label first appears (never used for the label)
          const c = identityCrop(v.box, up.w, up.h); const cr = cropRgb(up.rgb, up.w, up.h, c);
          const hr = await S.h2.run({ [S.h2.inputNames[0]]: new Tensor('float32', h2Input(cr.rgb, cr.w, cr.h), [1, 3, 224, 224]) });
          h2t = h2Top3(asProbs(hr[S.h2.outputNames[0]].data as Float32Array));
        }
        const rec = diagRecord({ path: 'live', tMs: now, trackId: v.id, g3: last ? { classId: last.classId, score: last.score } : null, competing: v.competing, wide: t?.wide ?? null,
          h2Top3: h2t, verify: null, box: v.box, frame: [up.w, up.h], crop: null, quality: qualityMetrics(up.rgb, up.w, up.h, v.box, scale), hints: v.hints, shownLabel: v.label });
        nscv(diagLine({ ...rec, h2_crop_source: h2t ? 'preview_480_report_only' : null }));
        nativeCv?.appendDiag?.(JSON.stringify(rec)).catch(() => undefined);
        if (shouldSave(rec, recentSaves())) saveDiag(`live_t${v.id}_${now}`, up.rgb, up.w, up.h, v.box);
      }
      for (const id of [...shownLog.current.keys()]) if (!shown.some((v) => v.id === id)) shownLog.current.delete(id);
      gate.setBlocking((g) => ({ ...g, ...throttler.current.onResult(Date.now(), Date.now() - t0, thermal.current) }));
    } catch (e) {
      nscv(`NSCV event=live_error error=${String(e).slice(0, 160)}`); meter.current.dropped();
      gate.setBlocking((g) => ({ ...g, ...throttler.current.onError(Date.now()) }));
    }
  }, [gate, banner]);   // eslint-disable-line react-hooks/exhaustive-deps
  const onLiveRef = useRef(onLiveFrame); onLiveRef.current = onLiveFrame;
  const onLiveStable = useCallback((...a: Parameters<typeof onLiveFrame>) => { onLiveRef.current(...a); }, []);

  /** J9: suppressed detections of a tap path (close-up photo / tap-3 stills), logged separately from the decision record. */
  function logGuard(path: 'closeup' | 'tap3', w: number, h: number, gd: { suppressed: Suppressed[][]; nIn: number[]; tooSmallAtTap: boolean }) {
    gd.suppressed.forEach((s, i) => {
      if (!s.length) return;
      const rec = { ...suppressedRecord({ path, tMs: Date.now(), frame: [w, h], params: DEFAULT_SCENE_GUARD, decodeFloor: DET_DECODE_FLOOR, nIn: gd.nIn[i] ?? s.length, suppressed: s }), still: i, too_small_at_tap: gd.tooSmallAtTap };
      nscv(suppressedLine(rec)); nativeCv?.appendDiag?.(JSON.stringify(rec)).catch(() => undefined);
    });
  }
  function recentSaves() { const t = Date.now(); saves.current = saves.current.filter((s) => t - s < 60000); return saves.current.length; }
  function saveDiag(name: string, rgb: Uint8Array, w: number, h: number, box: [number, number, number, number] | null) {
    if (!nativeCv?.saveRgbJpeg) return; saves.current.push(Date.now());
    nativeCv.saveRgbJpeg(`${name}_frame`, toBase64(rgb), w, h).then((p) => nscv(`NSCV diag_saved ${p}`)).catch(() => undefined);
    if (box) { const c = cropRgb(rgb, w, h, identityCrop(box, w, h)); nativeCv.saveRgbJpeg(`${name}_crop`, toBase64(c.rgb), c.w, c.h).catch(() => undefined); }
  }

  // ---- J8 frame worklet: counts frames, drops while busy / before the interval, resizes ONE frame per inference on the GPU
  const frameOutput = useFrameOutput({
    pixelFormat: 'yuv', dropFramesWhileBusy: true,
    onFrame: useMemo(() => (frame: any) => {
      'worklet';
      const c = counters.getDirty(); const g = gate.getDirty(); const now = Date.now();
      const v = g.enabled ? gateVerdict(g, now) : 'skip_busy';
      counters.setBlocking({ frames: c.frames + 1, skipBusy: c.skipBusy + (v === 'skip_busy' ? 1 : 0), skipInterval: c.skipInterval + (v === 'skip_interval' ? 1 : 0) });
      if (g.fw !== frame.width || g.fh !== frame.height) {
        gate.setBlocking({ ...g, fw: frame.width, fh: frame.height });
        scheduleOnRN(onMetaStable, frame.width, frame.height, frame.orientation, frame.pixelFormat);
      }
      if (v === 'send' && resizer != null) {
        gate.setBlocking({ ...gate.getDirty(), busy: true });
        const r = resizer.resize(frame);
        const buf = r.getPixelBuffer().slice(0);
        const rw = r.width; const rh = r.height; r.dispose();
        scheduleOnRN(onLiveStable, buf, rw, rh, frame.orientation, frame.isMirrored, frame.width, frame.height, now);
      }
      frame.dispose();
    }, [resizer, gate, counters, onMetaStable, onLiveStable]),
  });

  async function grabUpright(): Promise<UprightStill> {
    const photo = await (photoOutput as any).capturePhoto({}, {});
    try {
      let img = await photo.toImageAsync();   // applies orientation + mirroring
      const s = Math.min(1, MAX_SIDE / Math.max(img.width, img.height));
      if (s < 1) img = await img.resizeAsync(Math.round(img.width * s), Math.round(img.height * s));
      const raw = await img.toRawPixelDataAsync(false);
      nscv(`NSCV photo raw=${photo.width}x${photo.height} orientation=${photo.orientation} mirror=${photo.isMirrored ? 1 : 0} upright=${raw.width}x${raw.height} fmt=${raw.pixelFormat}`);
      return { rgb: rawToRgb(raw.buffer, raw.width, raw.height, raw.pixelFormat as PixelFormat), w: raw.width, h: raw.height };
    } finally { photo.dispose?.(); }
  }
  const infer = (S: Sessions) => async (m: 'h2' | 'g3_det', input: Float32Array, dims: number[]) => {
    const sess = S[m]; const feeds = { [sess.inputNames[0]]: new Tensor('float32', input, dims) };
    const end = lat.current.start(`infer_${m}`); const r = await sess.run(feeds); end(); return r[sess.outputNames[0]].data as Float32Array;
  };

  // ---- J8 close-up: tap a tracked item -> one high-res photo -> H2 -> FROZEN_VERIFY (unchanged)
  async function onTapLive(x: number, y: number) {
    if (busy.current || !sessions.current || !liveBuf) return;
    const hit = tracks.map((t) => ({ t, v: stillBoxToView(t.box, [liveBuf.w, liveBuf.h], [width, height]) }))
      .filter(({ v }) => x >= v.left && x <= v.left + v.width && y >= v.top && y <= v.top + v.height)
      .sort((a, b) => a.v.width * a.v.height - b.v.width * b.v.height)[0];
    if (!hit) {   // J9: a below-1 % detection is not tappable: no close-up, no label, just the hint
      const tiny = lastSuppressed.current.find((d) => { const v = stillBoxToView(d.box, [liveBuf.w, liveBuf.h], [width, height]); return x >= v.left && x <= v.left + v.width && y >= v.top && y <= v.top + v.height; });
      if (tiny) { setTitle(null); setBanner('Move closer'); nscv(`NSCV event=tap_on_suppressed area_frac=${tiny.areaFrac.toFixed(5)} min_area_frac=${DEFAULT_SCENE_GUARD.minAreaFrac}`); return; }
    }
    const trk = hit ? tracker.current.tracks.find((k) => k.id === hit.t.id) : undefined;
    const wide = trk ? trackWide(trk.obs) : { status: 'unable' as const, reason: 'nothing_detected_at_tap' };
    busy.current = true; setTitle(null); setDomainLine(null); setState('Close-up check… hold still');
    const endTap = lat.current.start('tap_to_result');
    try {
      const still = await grabUpright();
      const S = sessions.current;
      const out = await runCloseupFromTrack(still, [x, y], [width, height], wide, infer(S));
      out.logLines.forEach((l) => nscv(l));
      const live = lastLive.current; const frameSide = hit && live ? boxSide(hit.t.box) * (live.frameW / live.w) : 0;
      const hints = guidanceHints({ sidePx: hit ? frameSide : 0, closeupCropSidePx: out.closeup?.cropSidePx });
      if (out.plan) nscv(`NSCV map tap=${x.toFixed(1)},${y.toFixed(1)} view=${width}x${height} still=${still.w}x${still.h} crop=${out.plan.crop.x},${out.plan.crop.y},${out.plan.crop.w},${out.plan.crop.h} src=${out.plan.source} rot=0 mirror=0`);
      nscv(nscvResultLine(out.display));
      if (out.displayErrors.length) { nscv(`NSCV event=display_refused errors=${out.displayErrors.join('|')}`); setTitle('Unable to identify'); }
      else { setTitle(out.display.state === 'unknown' && (out.guard.tooSmallAtTap || hints.some((h) => h.code === 'move_closer')) ? 'Unable to identify — move closer' : out.display.title); setFromPipeline(true); }
      setBanner(hints.length ? hints.map((h) => h.text).join(' · ') : out.guard.tooSmallAtTap ? 'Move closer' : null);
      logGuard('closeup', still.w, still.h, out.guard);
      const nut = nutritionForCv(out.domain.cvClass);
      setDomainLine(out.domain.domainId ? `domain=${out.domain.domainId} · nutrition ${nut ? 'USDA FDC per 100 g' : 'n/a'} · price: no verified source loaded` : null);
      nscv(`NSCV domain cv=${out.domain.cvClass ?? '-'} domain=${out.domain.domainId ?? '-'} nutrition=${nut ? nut.source.fdcId : '-'} price=no_source`);
      // report-only: live (GPU YUV->RGB) colour vs photo colour of the same item = channel-order check of the new live path
      if (hit && live && out.plan) {
        const cc = colourCheck(meanRgb(live.rgb, live.w, live.h, hit.t.box), meanRgb(still.rgb, still.w, still.h, [out.plan.crop.x, out.plan.crop.y, out.plan.crop.x + out.plan.crop.w, out.plan.crop.y + out.plan.crop.h]));
        nscv(`NSCV colourcheck verdict=${cc.verdict} dist=${cc.dist} dist_swapped=${cc.distSwapped}`);
      }
      const rec = diagRecord({ path: 'closeup', tMs: Date.now(), trackId: hit?.t.id ?? null, g3: out.closeup?.g3AtTap ?? null, competing: hit?.t.competing ?? [], wide, h2Top3: out.closeup?.h2Top3 ?? null,
        verify: out.verify, box: out.plan ? out.plan.stillBox : null, frame: [still.w, still.h], crop: out.closeup ? { w: out.closeup.cropW, h: out.closeup.cropH, sidePx: out.closeup.cropSidePx } : null,
        quality: out.plan ? qualityMetrics(still.rgb, still.w, still.h, out.plan.stillBox) : null, hints, shownLabel: out.display.identityLabel, title: out.display.title });
      nscv(diagLine(rec)); nativeCv?.appendDiag?.(JSON.stringify(rec)).catch(() => undefined);
      if (shouldSave(rec, recentSaves())) saveDiag(`closeup_${Date.now()}`, still.rgb, still.w, still.h, out.plan ? out.plan.stillBox : null);
      nscv(`NSCV latency tap_to_result_ms=${endTap()}`); lat.current.lines().forEach((l) => nscv(l));
      setState('Point at an item · tap one for a close-up check');
    } catch (e) {
      nscv(`NSCV event=pipeline_error error=${String(e).slice(0, 160)}`); setState('Error, see log'); setTitle('Unable to identify'); setBadgeReason('pipeline error');
    } finally { busy.current = false; }
  }

  // ---- J7 fallback (optional toggle): tap -> 3-photo burst. Unchanged behaviour.
  async function onTap(x: number, y: number) {
    if (busy.current || !sessions.current) return;
    busy.current = true; setTitle(null); setFromPipeline(false); setDomainLine(null); setBadgeReason('running'); setState(`Hold still… (${BURST} photos)`);
    const endTap = lat.current.start('tap_to_result');
    try {
      const stills: UprightStill[] = [];
      const endCap = lat.current.start('capture_burst');
      for (let i = 0; i < BURST; i++) stills.push(await grabUpright());
      endCap();
      const S = sessions.current;
      const out = await runDebugPipeline(stills, [x, y], [width, height], async (m, input, dims) => {
        const sess = S[m]; const feeds = { [sess.inputNames[0]]: new Tensor('float32', input, dims) };
        const end = lat.current.start(`infer_${m}`); const r = await sess.run(feeds); end(); return r[sess.outputNames[0]].data as Float32Array;
      });
      out.logLines.forEach((l) => nscv(l));
      if (out.plan) nscv(`NSCV map tap=${x.toFixed(1)},${y.toFixed(1)} view=${width}x${height} still=${stills[stills.length - 1].w}x${stills[stills.length - 1].h} crop=${out.plan.crop.x},${out.plan.crop.y},${out.plan.crop.w},${out.plan.crop.h} src=${out.plan.source} rot=0 mirror=0`);
      nscv(nscvResultLine(out.display));
      if (out.displayErrors.length) { nscv(`NSCV event=display_refused errors=${out.displayErrors.join('|')}`); setTitle('Unable to identify'); }
      else { setTitle(out.display.state === 'unknown' && out.guard.tooSmallAtTap ? 'Unable to identify — move closer' : out.display.title); setFromPipeline(true); }
      logGuard('tap3', stills[stills.length - 1].w, stills[stills.length - 1].h, out.guard);
      const nut = nutritionForCv(out.domain.cvClass);
      setDomainLine(out.domain.domainId ? `domain=${out.domain.domainId} · nutrition ${nut ? 'USDA FDC per 100 g' : 'n/a'} · price: no verified source loaded` : null);
      nscv(`NSCV domain cv=${out.domain.cvClass ?? '-'} domain=${out.domain.domainId ?? '-'} nutrition=${nut ? nut.source.fdcId : '-'} price=no_source`);
      nscv(`NSCV latency tap_to_result_ms=${endTap()}`); lat.current.lines().forEach((l) => nscv(l));
      const last = stills[stills.length - 1];
      setBoxes(overlayBoxes(out.detections[out.detections.length - 1] ?? [], out.plan, [last.w, last.h], [width, height]));
      setState('Tap an item');
    } catch (e) {
      nscv(`NSCV event=pipeline_error error=${String(e).slice(0, 160)}`); setState('Error, see log'); setTitle('Unable to identify'); setBadgeReason('pipeline error');
    } finally { busy.current = false; }
  }

  const camOn = cameraActive(life);
  const outputs = mode.mode === 'live' && fpActive ? [photoOutput, frameOutput] : [photoOutput];
  return <View style={StyleSheet.absoluteFill} testID="cv-debug-layer">
    {pv.showCamera && device ? <Camera style={StyleSheet.absoluteFill} device={device} outputs={outputs} isActive={camOn} resizeMode="cover" /> : null}
    <Pressable style={StyleSheet.absoluteFill} accessibilityLabel={mode.mode === 'live' ? 'Tap a tracked item for a close-up check (debug)' : 'Tap an item to identify (debug)'}
      onPress={(e) => (mode.mode === 'live' ? onTapLive : onTap)(e.nativeEvent.locationX, e.nativeEvent.locationY)} />
    {mode.mode === 'tap3' ? boxes.map((b, i) => <View key={i} pointerEvents="none" style={{ position: 'absolute', left: b.left, top: b.top, width: b.width, height: b.height, borderWidth: 2, borderColor: b.kind === 'crop' ? '#f2c946' : '#7fd38b' }}>
      <Text style={{ color: '#fff', fontSize: 11, backgroundColor: '#0008', alignSelf: 'flex-start', paddingHorizontal: 3 }}>{b.label}</Text></View>) : null}
    {mode.mode === 'live' && liveBuf ? tracks.map((t) => {
      const v = stillBoxToView(t.box, [liveBuf.w, liveBuf.h], [width, height]); const ok = t.state === 'identified';
      const hint = t.hints[0]?.text;
      return <View key={t.id} pointerEvents="none" testID={`cv-live-track-${t.state}`} style={{ position: 'absolute', left: v.left, top: v.top, width: v.width, height: v.height, borderWidth: ok ? 3 : 1.5, borderColor: ok ? '#7fd38b' : '#ffffffaa', borderStyle: ok ? 'solid' : 'dashed', borderRadius: 6 }}>
        {ok ? <Text style={{ color: '#111', fontSize: 13, fontWeight: '700', backgroundColor: '#7fd38b', alignSelf: 'flex-start', paddingHorizontal: 4 }}>{t.label}</Text> : null}
        {hint ? <Text style={{ color: '#111', fontSize: 11, backgroundColor: '#f2c946', alignSelf: 'flex-start', paddingHorizontal: 4, marginTop: 2 }}>{hint}</Text> : null}
      </View>;
    }) : null}
    <View pointerEvents="box-none" style={{ position: 'absolute', left: 12, right: 12, top: 12, flexDirection: 'row', justifyContent: 'space-between' }}>
      <Pressable accessibilityLabel="Close camera" onPress={back} style={{ padding: 10, backgroundColor: '#0009', borderRadius: 20 }}><Text style={{ color: '#fff' }}>Close</Text></Pressable>
      <Pressable accessibilityLabel="Switch scan mode" testID="cv-mode-toggle" onPress={() => { setPref(pref === 'live' ? 'tap3' : 'live'); setTitle(null); setBoxes([]); clearLive(); nscv(`NSCV event=mode_toggle to=${pref === 'live' ? 'tap3' : 'live'}`); }}
        style={{ padding: 8, backgroundColor: '#0009', borderRadius: 8 }}><Text style={{ color: '#f2c946' }}>{mode.mode === 'live' ? 'LIVE · switch to tap-3' : 'TAP-3 · switch to live'}</Text></Pressable>
    </View>
    {(() => { const b = inferenceBadge(!!sessions.current, fromPipeline, badgeReason); return <Text testID={`cv-inference-${b.source}`} style={{ position: 'absolute', left: 12, right: 12, top: 64, color: '#111', backgroundColor: b.color, padding: 6, borderRadius: 8, fontWeight: '700', textAlign: 'center' }}>{b.text}</Text>; })()}
    {mode.mode === 'live' && closer ? <Text pointerEvents="none" testID="cv-move-closer" accessibilityLiveRegion="polite" style={{ position: 'absolute', alignSelf: 'center', top: '42%', color: '#111', backgroundColor: '#f2c946e6', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12, fontSize: 13, fontWeight: '600' }}>Move closer</Text> : null}
    {mode.mode === 'live' ? <CvPerfOverlay p={perf} /> : null}
    <View pointerEvents="none" style={{ position: 'absolute', left: 12, right: 12, bottom: 12, backgroundColor: '#172017d4', borderRadius: 16, padding: 12 }}>
      {title ? <Text style={{ color: '#fff', fontSize: 18, fontWeight: '700' }}>{title}</Text> : null}
      {banner ? <Text style={{ color: '#f2c946', fontSize: 13, fontWeight: '700' }}>{banner}</Text> : null}
      {mode.note ? <Text style={{ color: '#f2a446', fontSize: 12 }}>{mode.note}</Text> : null}
      {domainLine ? <Text style={{ color: '#cfe8d0', fontSize: 12 }}>{domainLine}</Text> : null}
      {mode.mode === 'live' && tracks.some((t) => t.state === 'identified') ? <Text style={{ color: '#ddd', fontSize: 12 }}>Live label = detector, 3 matching frames. Tap the item for the close-up check.</Text> : null}
      <Text style={{ color: '#ddd', fontSize: 13 }}>{pv.showCamera ? state : pv.message}</Text>
    </View>
    {pv.action === 'open_settings' ? <Pressable onPress={() => Linking.openSettings()} style={{ position: 'absolute', alignSelf: 'center', top: '45%', padding: 14, backgroundColor: '#f2c946', borderRadius: 12 }}><Text>Open Settings</Text></Pressable> : null}
  </View>;
}
