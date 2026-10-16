// G9 Stage J8 (cv-gauntlet-device): REAL-TIME live-frame CV, pure TypeScript (unit-tested in Node; small helpers are also
// worklet-callable). Nothing in this file changes a model, a score, a threshold or a verification policy:
//   - G3 / H2 weights and FROZEN_VERIFY / DEFAULT_ID / FROZEN_GATE are imported unchanged.
//   - The identification policy is the EXISTING wide policy idPolicy(DEFAULT_ID) via burstWide(): idMinHits (3) observations,
//     idMinScore 0.5. In J7 the 3 observations were 3 tapped stills; in J8 they are the last 3 live frames of ONE tracked object.
//   - Guidance hints (move closer / hold steady / improve lighting / keep in view) reuse existing constants (FROZEN_GATE,
//     DEFAULT_TRACKER_PARAMS, H2 input 224) and are UI hints only: they never change a label or a score.
// Live data path (CvDebugScan.tsx): VisionCamera frame output -> GPU resizer (worklet, sensor orientation, letterbox inner size)
// -> uint8 RGB copied to the RN thread (single in-flight, throttled) -> rotateRgb (upright) -> detectorInput (same 114-pad
// letterbox as the tap path) -> ORT (its own native thread) -> decodeRawWithNms -> mergeAgnostic -> LiveTracker -> overlay.
import type { Box } from '../pipeline/preprocess.ts';
import { iou } from '../pipeline/preprocess.ts';
import type { Detection } from '../pipeline/tracker.ts';
import { DEFAULT_TRACKER_PARAMS } from '../pipeline/tracker.ts';
import { DEFAULT_ID, FROZEN_GATE, letterboxTransform, DETECTOR_INPUT, touchesEdge, type IdResult } from '../pipeline/closeup.ts';
import { H2_INPUT } from '../pipeline/camera.ts';
import { burstWide, labelOf } from './debugPipeline.ts';

// ---------------------------------------------------------------- throttling (adaptive 3-8 detection updates / s)
export const LIVE_THROTTLE = { minIntervalMs: 125, maxIntervalMs: 333, startIntervalMs: 200, headroom: 1.25, emaAlpha: 0.3 } as const;
/** Android PowerManager.THERMAL_STATUS_* (0 none .. 6 shutdown); -1 = not available (API < 29). */
export type ThermalStatus = -1 | 0 | 1 | 2 | 3 | 4 | 5 | 6;
/** Floor on the interval under thermal pressure: moderate -> 4/s, severe -> 3/s, critical+ -> 2/s (protective, below target). */
export function thermalFloorMs(t: number): number { return t >= 4 ? 500 : t >= 3 ? 333 : t >= 2 ? 250 : LIVE_THROTTLE.minIntervalMs; }

export type GateState = { busy: boolean; nextDueMs: number };
export type GateVerdict = 'send' | 'skip_busy' | 'skip_interval';
/** Frame-thread decision: one inference in flight at most; frames are DROPPED (never queued). Worklet-callable. */
export function gateVerdict(g: GateState, nowMs: number): GateVerdict {
  'worklet';
  if (g.busy) return 'skip_busy';
  if (nowMs < g.nextDueMs) return 'skip_interval';
  return 'send';
}

export type Throttler = { intervalMs: number; latencyEmaMs: number | null; onResult: (nowMs: number, latencyMs: number, thermal?: number) => GateState; onError: (nowMs: number) => GateState };
/** Adaptive interval: keep >= latency * headroom (so the queue never builds), clamp to [125, 333] ms (8..3 Hz), thermal floor. */
export function createThrottler(): Throttler {
  const t: Throttler = {
    intervalMs: LIVE_THROTTLE.startIntervalMs, latencyEmaMs: null,
    onResult(nowMs, latencyMs, thermal = -1) {
      if (Number.isFinite(latencyMs) && latencyMs >= 0) t.latencyEmaMs = t.latencyEmaMs === null ? latencyMs : t.latencyEmaMs + LIVE_THROTTLE.emaAlpha * (latencyMs - t.latencyEmaMs);
      const want = (t.latencyEmaMs ?? LIVE_THROTTLE.startIntervalMs) * LIVE_THROTTLE.headroom;
      const floor = thermalFloorMs(thermal); const lo = Math.max(LIVE_THROTTLE.minIntervalMs, floor); const hi = Math.max(LIVE_THROTTLE.maxIntervalMs, floor);
      t.intervalMs = Math.round(Math.min(hi, Math.max(lo, want)));
      return { busy: false, nextDueMs: nowMs + Math.max(0, t.intervalMs - Math.max(0, latencyMs)) };
    },
    onError(nowMs) { t.intervalMs = LIVE_THROTTLE.maxIntervalMs; return { busy: false, nextDueMs: nowMs + t.intervalMs }; },
  };
  return t;
}

// ---------------------------------------------------------------- orientation + letterbox of the live buffer
export type CamOrientation = 'up' | 'right' | 'down' | 'left';
/** Resizer output size (SENSOR orientation) = the 480-letterbox INNER size, so detectorInput() only pads (114) and never resamples. */
export function liveResizeDims(frameW: number, frameH: number, side = DETECTOR_INPUT): { w: number; h: number } {
  const t = letterboxTransform(frameW, frameH, side);
  return { w: Math.round(frameW * t.sx), h: Math.round(frameH * t.sy) };
}
/** Frame.orientation 'right' = pixel data rotated +90 deg (clockwise) relative to the output orientation, so it is undone by a
 *  90 deg counter-clockwise rotation (VisionCamera 5 Frame.orientation docs; same convention as orientation.ts). Then mirror. */
export function rotateRgb(rgb: Uint8Array, w: number, h: number, o: CamOrientation, mirrored = false): { rgb: Uint8Array; w: number; h: number } {
  if (rgb.length !== w * h * 3) throw new Error(`rgb ${rgb.length} != ${w}x${h}x3`);
  const swap = o === 'left' || o === 'right'; const W = swap ? h : w; const H = swap ? w : h;
  if (o === 'up' && !mirrored) return { rgb, w, h };
  const out = new Uint8Array(W * H * 3);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const ux = mirrored ? W - 1 - x : x; let sx: number; let sy: number;
    switch (o) {
      case 'up': sx = ux; sy = y; break;
      case 'down': sx = w - 1 - ux; sy = h - 1 - y; break;
      case 'right': sx = w - 1 - y; sy = ux; break;   // data rotated CW: undo with CCW, upright(ux, y) <- source(w-1-y, ux)
      default: sx = y; sy = h - 1 - ux; break;         // 'left': data rotated CCW, undo with CW
    }
    const s = (sy * w + sx) * 3; const d = (y * W + x) * 3; out[d] = rgb[s]; out[d + 1] = rgb[s + 1]; out[d + 2] = rgb[s + 2];
  }
  return { rgb: out, w: W, h: H };
}
/** Upright-buffer box -> upright full frame-output pixels (the frame the camera delivered, before the 480 resize). */
export function bufferBoxToFrame(b: Box, bufW: number, bufH: number, frameUprightW: number, frameUprightH: number): Box {
  const sx = frameUprightW / bufW; const sy = frameUprightH / bufH; return [b[0] * sx, b[1] * sy, b[2] * sx, b[3] * sy];
}

// ---------------------------------------------------------------- one object per item (class-agnostic grouping for display)
export type LiveObject = { box: Box; classId: number; score: number; competing: { classId: number; score: number }[] };
/** decodeRawWithNms keeps class-wise NMS (unchanged, = Ultralytics). The same fruit can therefore carry an apple box AND a citrus
 *  box. For the live overlay they are grouped into ONE object (top score wins, others kept as `competing` for the diagnostic log)
 *  so the screen never prints two class names on one fruit. iouThr = the NMS IoU (0.7). Scores are untouched. */
export function mergeAgnostic(dets: Detection[], iouThr = 0.7): LiveObject[] {
  const s = [...dets].sort((a, b) => b.score - a.score); const out: LiveObject[] = [];
  for (const d of s) {
    const host = out.find((o) => iou(o.box, d.box) > iouThr);
    if (host) { if (d.classId !== host.classId) host.competing.push({ classId: d.classId, score: d.score }); continue; }
    out.push({ box: [...d.box] as Box, classId: d.classId, score: d.score, competing: [] });
  }
  return out;
}

// ---------------------------------------------------------------- IoU tracker + consistency-from-frames
export type LiveTrackerParams = { iouMatch: number; maxMissed: number; stableIou: number; window: number };
export const LIVE_TRACKER: LiveTrackerParams = { iouMatch: DEFAULT_TRACKER_PARAMS.iouMatch, maxMissed: DEFAULT_TRACKER_PARAMS.maxMissed, stableIou: DEFAULT_TRACKER_PARAMS.stableIou, window: DEFAULT_ID.idMinHits };
export type TrackState = 'confirming' | 'identified' | 'unable';
export type LiveTrack = {
  id: number; box: Box; rawBox: Box; obs: (Detection | null)[]; missed: number; hits: number; firstSeenMs: number; lastSeenMs: number;
  jitter: number[]; shownClass: number | null; wide: IdResult; competing: { classId: number; score: number }[];
};
export type LiveTrackView = { id: number; box: Box; state: TrackState; label: string | null; classId: number | null; reason: string; missed: number; stable: boolean; competing: { classId: number; score: number }[] };

/** The 3-observation policy from successive live frames of ONE track: exactly burstWide() (the J7 burst policy) applied to the
 *  track's last `window` (= DEFAULT_ID.idMinHits) frame observations; a frame where the track was not matched counts as null. */
export function trackWide(obs: (Detection | null)[], window = DEFAULT_ID.idMinHits): IdResult {
  return burstWide(obs.slice(-window));
}

export class LiveTracker {
  P: LiveTrackerParams; tracks: LiveTrack[] = []; nextId = 1; droppedBySuppression = 0;
  constructor(p: Partial<LiveTrackerParams> = {}) { this.P = { ...LIVE_TRACKER, ...p }; }
  reset(): void { this.tracks = []; }

  /** J9: `suppressed` = boxes the frozen scene guard removed this frame (guard.ts). They are NEVER matched or counted as a hit.
   *  An unmatched track that overlaps one (same iouMatch) is the same item now too small: it is dropped AT ONCE (no held box or
   *  label, no stale overlay), instead of coasting through maxMissed frames. Default [] = J8 behaviour exactly. */
  update(objs: LiveObject[], tMs: number, suppressed: Box[] = []): LiveTrackView[] {
    const P = this.P; const pairs: [number, number, number][] = [];
    this.tracks.forEach((t, ti) => objs.forEach((o, oi) => { const v = iou(t.rawBox, o.box); if (v >= P.iouMatch) pairs.push([v, ti, oi]); }));
    pairs.sort((a, b) => b[0] - a[0] || this.tracks[a[1]].id - this.tracks[b[1]].id || a[2] - b[2]);
    const uT = new Set<number>(); const uO = new Set<number>();
    for (const [v, ti, oi] of pairs) {
      if (uT.has(ti) || uO.has(oi)) continue; uT.add(ti); uO.add(oi);
      const t = this.tracks[ti]; const o = objs[oi];
      t.jitter.push(v); if (t.jitter.length > P.window) t.jitter.shift();
      t.rawBox = [...o.box] as Box; t.box = o.box.map((x, k) => 0.4 * t.box[k] + 0.6 * x) as Box;
      t.obs.push({ box: o.box, classId: o.classId, score: o.score }); t.competing = o.competing;
      t.missed = 0; t.hits += 1; t.lastSeenMs = tMs;
    }
    const keep: LiveTrack[] = [];
    this.tracks.forEach((t, ti) => {
      if (!uT.has(ti)) {
        if (suppressed.length && suppressed.some((b) => iou(t.rawBox, b) >= P.iouMatch)) { this.droppedBySuppression += 1; return; }
        t.missed += 1; t.obs.push(null);
      }
      if (t.obs.length > 4 * P.window) t.obs.splice(0, t.obs.length - 4 * P.window);
      if (t.missed <= P.maxMissed) keep.push(t);   // lost tracks die: their label can never move to a new object
    });
    this.tracks = keep;
    objs.forEach((o, oi) => {
      if (uO.has(oi)) return;
      this.tracks.push({ id: this.nextId++, box: [...o.box] as Box, rawBox: [...o.box] as Box, obs: [{ box: o.box, classId: o.classId, score: o.score }], missed: 0, hits: 1,
        firstSeenMs: tMs, lastSeenMs: tMs, jitter: [], shownClass: null, wide: { status: 'pending', reason: 'confirming' }, competing: o.competing });
    });
    return this.tracks.map((t) => this.view(t));
  }

  /** Anti-flicker without ever showing an unverified label:
   *  - the label appears only when trackWide() returns 'identified' for this track (the existing policy, unchanged);
   *  - it is held through MISSED frames only (no new evidence) while the track lives (<= maxMissed);
   *  - any observed frame in the window with another class or a score < idMinScore hides it at once;
   *  - a new track always starts unlabelled (no carry-over), and a dead track's label dies with it. */
  private view(t: LiveTrack): LiveTrackView {
    const w = trackWide(t.obs, this.P.window); t.wide = w;
    const seen = t.obs.slice(-this.P.window).filter((d): d is Detection => d !== null);
    if (w.status === 'identified') t.shownClass = w.classId;
    else if (t.shownClass !== null) {
      const contradicted = seen.some((d) => d.classId !== t.shownClass || d.score < DEFAULT_ID.idMinScore);
      if (contradicted || !seen.length) t.shownClass = null;
    }
    const stable = t.jitter.length >= 2 && t.jitter.slice(-2).every((v) => v >= this.P.stableIou);
    const state: TrackState = t.shownClass !== null ? 'identified' : w.status === 'unable' ? 'unable' : 'confirming';
    const reason = t.shownClass !== null ? (w.status === 'identified' ? 'wide_policy_passed' : 'held_through_missed_frame') : w.status === 'identified' ? 'wide_policy_passed' : w.reason.replace(/ /g, '_');
    return { id: t.id, box: t.box, state, label: t.shownClass !== null ? labelOf(t.shownClass) : null, classId: t.shownClass, reason, missed: t.missed, stable, competing: t.competing };
  }
}

// ---------------------------------------------------------------- guidance hints (UI only)
export type HintCode = 'move_closer' | 'hold_steady' | 'improve_lighting' | 'keep_in_view';
export const HINT_TEXT: Record<HintCode, string> = { move_closer: 'Move closer', hold_steady: 'Hold steady', improve_lighting: 'Improve lighting', keep_in_view: 'Keep the whole item in view' };
/** Cut-offs, all EXISTING constants (no new model threshold):
 *  - quality-eligible size: FROZEN_GATE.minSidePx = 96 px (sqrt of box area in full-resolution source pixels, Stage G gate);
 *  - close-up identity size: H2 input = 224 px; a close-up crop smaller than this is UPSAMPLED into H2 (UI hint only);
 *  - blur: FROZEN_GATE.minBlurVar = 15 (Laplacian variance); box jitter: DEFAULT_TRACKER_PARAMS.stableIou = 0.8 between frames;
 *  - light: FROZEN_GATE.minMeanV 80 / maxMeanV 245 (mean HSV V); edge: FROZEN_GATE.edgeMarginFrac 0.01. */
export const HINT_LIMITS = { minSidePx: FROZEN_GATE.minSidePx, h2InputPx: H2_INPUT, minBlurVar: FROZEN_GATE.minBlurVar, stableIou: DEFAULT_TRACKER_PARAMS.stableIou,
  minMeanV: FROZEN_GATE.minMeanV, maxMeanV: FROZEN_GATE.maxMeanV, edgeMarginFrac: FROZEN_GATE.edgeMarginFrac } as const;
export type HintInputs = { sidePx: number; closeupCropSidePx?: number; blurVar?: number; jitterIou?: number; meanV?: number; touchesEdge?: boolean };
export type Hint = { code: HintCode; text: string; why: string };
export function guidanceHints(q: HintInputs): Hint[] {
  const h: Hint[] = []; const L = HINT_LIMITS;
  if (q.sidePx < L.minSidePx) h.push({ code: 'move_closer', text: HINT_TEXT.move_closer, why: `side_${Math.round(q.sidePx)}px_lt_quality_min_${L.minSidePx}` });
  else if (q.closeupCropSidePx !== undefined && q.closeupCropSidePx < L.h2InputPx) h.push({ code: 'move_closer', text: HINT_TEXT.move_closer, why: `closeup_crop_${Math.round(q.closeupCropSidePx)}px_lt_h2_input_${L.h2InputPx}` });
  if ((q.blurVar !== undefined && q.blurVar < L.minBlurVar) || (q.jitterIou !== undefined && q.jitterIou < L.stableIou))
    h.push({ code: 'hold_steady', text: HINT_TEXT.hold_steady, why: q.blurVar !== undefined && q.blurVar < L.minBlurVar ? `blur_var_${q.blurVar.toFixed(1)}_lt_${L.minBlurVar}` : `box_iou_${(q.jitterIou ?? 0).toFixed(2)}_lt_${L.stableIou}` });
  if (q.meanV !== undefined && (q.meanV < L.minMeanV || q.meanV > L.maxMeanV)) h.push({ code: 'improve_lighting', text: HINT_TEXT.improve_lighting, why: q.meanV < L.minMeanV ? `too_dark_v_${Math.round(q.meanV)}` : `overexposed_v_${Math.round(q.meanV)}` });
  if (q.touchesEdge) h.push({ code: 'keep_in_view', text: HINT_TEXT.keep_in_view, why: 'box_touches_frame_edge' });
  return h;
}

// ---------------------------------------------------------------- quality metrics (diagnostic + hints)
/** sqrt(box area) in pixels, the same "side" the Stage G gate uses (cropRect.sidePx). */
export const boxSide = (b: Box) => Math.sqrt(Math.max(0, b[2] - b[0]) * Math.max(0, b[3] - b[1]));
export type QualityMetrics = { sidePx: number; areaFrac: number; meanV: number; luma: number; blurVar: number; touchesEdge: boolean; cropW: number; cropH: number };
/** Metrics on the box region of an HWC RGB buffer. blurVar = variance of the 4-neighbour Laplacian on the grey crop, box-reduced to
 *  <= 256 px side (ANALYSIS_MAX_SIDE, as Stage G); meanV = mean of max(R,G,B) (HSV V) over the crop; sidePx is in `sideScale` units. */
export function qualityMetrics(rgb: Uint8Array, w: number, h: number, b: Box, sideScale = 1): QualityMetrics {
  const x0 = Math.max(0, Math.floor(b[0])); const y0 = Math.max(0, Math.floor(b[1])); const x1 = Math.min(w, Math.ceil(b[2])); const y1 = Math.min(h, Math.ceil(b[3]));
  const cw = Math.max(0, x1 - x0); const ch = Math.max(0, y1 - y0);
  const base = { sidePx: boxSide(b) * sideScale, areaFrac: (cw * ch) / Math.max(1, w * h), touchesEdge: touchesEdge(b, w, h, HINT_LIMITS.edgeMarginFrac), cropW: cw, cropH: ch };
  if (cw < 3 || ch < 3) return { ...base, meanV: 0, luma: 0, blurVar: 0 };
  const k = Math.max(1, Math.ceil(Math.max(cw, ch) / 256)); const gw = Math.floor(cw / k); const gh = Math.floor(ch / k);
  const g = new Float64Array(gw * gh); let vSum = 0; let ySum = 0; let n = 0;
  for (let gy = 0; gy < gh; gy++) for (let gx = 0; gx < gw; gx++) {
    let acc = 0;
    for (let dy = 0; dy < k; dy++) for (let dx = 0; dx < k; dx++) {
      const p = ((y0 + gy * k + dy) * w + (x0 + gx * k + dx)) * 3; const r = rgb[p]; const gg = rgb[p + 1]; const bb = rgb[p + 2];
      const l = 0.299 * r + 0.587 * gg + 0.114 * bb; acc += l; vSum += Math.max(r, gg, bb); ySum += l; n++;
    }
    g[gy * gw + gx] = acc / (k * k);
  }
  return { ...base, meanV: vSum / n, luma: ySum / n, blurVar: laplacianVar(g, gw, gh) };
}
export function laplacianVar(g: ArrayLike<number>, w: number, h: number): number {
  if (w < 3 || h < 3) return 0; let s = 0; let s2 = 0; let n = 0;
  for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
    const v = g[(y - 1) * w + x] + g[(y + 1) * w + x] + g[y * w + x - 1] + g[y * w + x + 1] - 4 * g[y * w + x]; s += v; s2 += v * v; n++;
  }
  const m = s / n; return s2 / n - m * m;
}

// ---------------------------------------------------------------- lifecycle + mode
export type LifeState = { permission: 'unknown' | 'granted' | 'denied'; models: 'loading' | 'ready' | 'failed'; appActive: boolean; focused: boolean; mounted: boolean };
export type LifeEvent = { type: 'permission'; granted: boolean } | { type: 'models'; ok: boolean } | { type: 'app_state'; active: boolean } | { type: 'focus'; focused: boolean } | { type: 'unmount' };
export const LIFE_INITIAL: LifeState = { permission: 'unknown', models: 'loading', appActive: true, focused: true, mounted: true };
export function lifeReduce(s: LifeState, e: LifeEvent): LifeState {
  switch (e.type) {
    case 'permission': return { ...s, permission: e.granted ? 'granted' : 'denied' };
    case 'models': return { ...s, models: e.ok ? 'ready' : 'failed' };
    case 'app_state': return { ...s, appActive: e.active };
    case 'focus': return { ...s, focused: e.focused };
    case 'unmount': return { ...s, mounted: false };
  }
}
/** Camera preview runs whenever permitted + foreground + focused; the frame processor additionally needs the ORT sessions. */
export const cameraActive = (s: LifeState) => s.mounted && s.permission === 'granted' && s.appActive && s.focused;
export const frameProcessorActive = (s: LifeState, mode: ScanMode) => cameraActive(s) && s.models === 'ready' && mode === 'live';

export type ScanMode = 'live' | 'tap3';
export const DEFAULT_SCAN_MODE: ScanMode = 'live';
/** The J7 tap -> 3-photo burst stays available as an OPTIONAL fallback; it is never the default. If the live path cannot run
 *  (no GPU resizer on the device) the screen falls back to tap3 and says why. */
export function effectiveMode(pref: ScanMode, liveSupported: boolean): { mode: ScanMode; note: string | null } {
  if (pref === 'live' && !liveSupported) return { mode: 'tap3', note: 'Live mode unavailable on this device (GPU resizer missing); using tap-to-analyze.' };
  return { mode: pref, note: null };
}

// ---------------------------------------------------------------- perf meter (numbers come only from the device that runs it)
export type PerfSnapshot = { windowS: number; cameraFps: number; detUps: number; inferP50: number | null; inferP95: number | null; e2eP50: number | null; e2eP95: number | null;
  skippedBusy: number; skippedInterval: number; dropped: number; intervalMs: number; thermal: number; jsHeapMb: number | null; nativeHeapMb: number | null };
const pct = (a: number[], p: number) => { if (!a.length) return null; const b = [...a].sort((x, y) => x - y); return Math.round(b[Math.min(b.length - 1, Math.max(0, Math.ceil(p * b.length) - 1))]); };
export function createPerfMeter(now: () => number) {
  let t0 = now(); let frames = 0; let dets = 0; let sb = 0; let si = 0; let dr = 0; let inf: number[] = []; let e2e: number[] = [];
  return {
    frame(n = 1) { frames += n; }, skipped(busy: number, interval: number) { sb += busy; si += interval; }, dropped(n = 1) { dr += n; },
    detection(inferMs: number, e2eMs: number) { dets += 1; inf.push(inferMs); e2e.push(e2eMs); },
    snapshot(intervalMs: number, thermal: number, jsHeapMb: number | null = null, nativeHeapMb: number | null = null, reset = true): PerfSnapshot {
      const s = Math.max(1e-3, (now() - t0) / 1000);
      const r: PerfSnapshot = { windowS: Math.round(s * 10) / 10, cameraFps: Math.round((frames / s) * 10) / 10, detUps: Math.round((dets / s) * 10) / 10, inferP50: pct(inf, 0.5), inferP95: pct(inf, 0.95),
        e2eP50: pct(e2e, 0.5), e2eP95: pct(e2e, 0.95), skippedBusy: sb, skippedInterval: si, dropped: dr, intervalMs, thermal, jsHeapMb, nativeHeapMb };
      if (reset) { t0 = now(); frames = 0; dets = 0; sb = 0; si = 0; dr = 0; inf = []; e2e = []; }
      return r;
    },
  };
}
export const perfLine = (p: PerfSnapshot) => `NSCV perf window_s=${p.windowS} camera_fps=${p.cameraFps} det_ups=${p.detUps} infer_p50_ms=${p.inferP50 ?? '-'} infer_p95_ms=${p.inferP95 ?? '-'} ` +
  `e2e_p50_ms=${p.e2eP50 ?? '-'} e2e_p95_ms=${p.e2eP95 ?? '-'} skipped_busy=${p.skippedBusy} skipped_interval=${p.skippedInterval} dropped=${p.dropped} interval_ms=${p.intervalMs} ` +
  `thermal=${p.thermal} js_heap_mb=${p.jsHeapMb ?? '-'} native_heap_mb=${p.nativeHeapMb ?? '-'}`;

// ---------------------------------------------------------------- resizer buffer -> tightly packed RGB
/** The GPU resizer (uint8, rgb, interleaved) may hand back 3 or 4 bytes per pixel and may pad rows. Accept exactly:
 *  w*h*3 (RGB), w*h*4 (RGBX, alpha dropped) or a whole-number row stride >= w*3; anything else is refused (no guessing). */
export function unpackResized(buf: ArrayBuffer | Uint8Array, w: number, h: number): { rgb: Uint8Array; layout: string } {
  const src = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  if (src.length === w * h * 3) return { rgb: src, layout: 'rgb' };
  const bpp = src.length === w * h * 4 ? 4 : 3; const stride = bpp === 4 ? w * 4 : src.length / h;
  if (!Number.isInteger(stride) || stride < w * bpp) throw new Error(`resizer buffer ${src.length} B does not fit ${w}x${h}`);
  const out = new Uint8Array(w * h * 3);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { const s = y * stride + x * bpp; const d = (y * w + x) * 3; out[d] = src[s]; out[d + 1] = src[s + 1]; out[d + 2] = src[s + 2]; }
  return { rgb: out, layout: bpp === 4 ? 'rgbx' : `rgb_stride_${stride}` };
}

// ---------------------------------------------------------------- on-device YUV->RGB sanity check (report-only)
/** Mean RGB of a box. */
export function meanRgb(rgb: Uint8Array, w: number, h: number, b: Box): [number, number, number] {
  const x0 = Math.max(0, Math.floor(b[0])); const y0 = Math.max(0, Math.floor(b[1])); const x1 = Math.min(w, Math.ceil(b[2])); const y1 = Math.min(h, Math.ceil(b[3]));
  let r = 0; let g = 0; let bl = 0; let n = 0;
  for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) { const p = (y * w + x) * 3; r += rgb[p]; g += rgb[p + 1]; bl += rgb[p + 2]; n++; }
  return n ? [r / n, g / n, bl / n] : [0, 0, 0];
}
/** Compares the live (GPU YUV->RGB) colour of the tapped item with the same item in the high-res photo (JPEG decode, known RGB).
 *  'rb_swapped' when swapping R/B in the live mean fits the photo clearly better: a channel-order bug in the live path. Exposure
 *  differs between the two captures, so only the channel ORDER is judged (normalised chromaticity). Report-only, logged as NSCV. */
export function colourCheck(live: [number, number, number], photo: [number, number, number]): { verdict: 'ok' | 'rb_swapped' | 'inconclusive'; dist: number; distSwapped: number } {
  const chroma = (c: [number, number, number]) => { const s = c[0] + c[1] + c[2] || 1; return [c[0] / s, c[1] / s, c[2] / s]; };
  const a = chroma(live); const p = chroma(photo); const sw = chroma([live[2], live[1], live[0]]);
  const d = (u: number[], v: number[]) => Math.hypot(u[0] - v[0], u[1] - v[1], u[2] - v[2]);
  const dist = d(a, p); const distSwapped = d(sw, p);
  if (Math.abs(live[0] - live[2]) < 12) return { verdict: 'inconclusive', dist, distSwapped };   // grey-ish item: order not observable
  return { verdict: distSwapped + 0.03 < dist ? 'rb_swapped' : 'ok', dist: Math.round(dist * 1e4) / 1e4, distSwapped: Math.round(distSwapped * 1e4) / 1e4 };
}
