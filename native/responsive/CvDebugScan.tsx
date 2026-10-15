// G9 Stage J5 (cv-gauntlet-device): phone-test layer for the Scan screen. Loaded ONLY when CV_DEBUG_PIPELINE is true
// (native/src/cv/device/flags.ts, default false); with the flag off this module is never required, so no camera permission is
// requested and no native camera / inference module is touched. Shows: live camera, tap -> 3-still burst -> G3 + H2 frozen pipeline
// -> title only ("<name>. Not graded" or "Unable to identify"). Never a grade, never a percentage, never a frame-rate figure.
import { useEffect, useRef, useState } from 'react';
import { Linking, Pressable, StyleSheet, Text, View } from 'react-native';
import { Camera, useCameraDevice, useCameraPermission, usePhotoOutput } from 'react-native-vision-camera';
import { InferenceSession, Tensor } from 'onnxruntime-react-native';
import { permissionView } from '../src/cv/device/permissions.ts';
import { rawToRgb, type PixelFormat } from '../src/cv/device/pixels.ts';
import { runDebugPipeline, BURST, type UprightStill } from '../src/cv/device/debugPipeline.ts';
import { overlayBoxes, type OverlayBox } from '../src/cv/device/overlay.ts';
import { modelPath, DEVICE_MODELS } from '../src/cv/device/models.ts';
import { checkModelIO, type RuntimeMeta } from '../src/cv/pipeline/camera.ts';
import { nscv, setCvDebug, nscvResultLine } from '../src/cv/debug.ts';
import { inferenceBadge, createLatencyRecorder, createLagSampler } from '../src/cv/device/instrument.ts';
import { nutritionForCv } from '../src/cv/data/nutrition.ts';

const MAX_SIDE = 1280;   // upright still is downscaled to this longest side before inference (crop still >> 224 px)
type Sessions = { h2: InferenceSession; g3_det: InferenceSession };

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
  const lat = useRef(createLatencyRecorder(() => Date.now()));
  const pv = permissionView(true, status, !!canRequestPermission);

  useEffect(() => { setCvDebug(true); }, []);
  useEffect(() => {   // J6: UI responsiveness hook (JS event-loop lag), logged every 10 s
    const lag = createLagSampler(() => Date.now(), 100); const a = setInterval(lag.tick, 100); const b = setInterval(() => nscv(lag.line()), 10000);
    return () => { clearInterval(a); clearInterval(b); };
  }, []);
  useEffect(() => { if (pv.action === 'request') requestPermission(); }, [pv.action, requestPermission]);
  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const t0 = Date.now(); const h2 = await InferenceSession.create(modelPath('h2')); const t1 = Date.now();
        const g3 = await InferenceSession.create(modelPath('g3_det')); const t2 = Date.now();
        nscv(`NSCV stage=init model=h2 ms=${t1 - t0}`); nscv(`NSCV stage=init model=g3_det ms=${t2 - t1}`);
        nscv(`NSCV model h2 inputs=${h2.inputNames.join('|')} outputs=${h2.outputNames.join('|')} io=${JSON.stringify(checkModelIO('h2', meta(h2)).filter((e) => !/rank|dim/.test(e)))}`);
        nscv(`NSCV model g3_det inputs=${g3.inputNames.join('|')} outputs=${g3.outputNames.join('|')}`);
        if (live) { sessions.current = { h2, g3_det: g3 }; setState('Tap an item'); setBadgeReason('models loaded, tap an item'); }
      } catch (e) {
        nscv(`NSCV event=model_load_failed error=${String(e).slice(0, 160)}`);
        if (live) setBadgeReason('models not loaded');
        if (live) setState(`Models not found. Push ${DEVICE_MODELS.h2.file} and ${DEVICE_MODELS.g3_det.file} (see P1 guide).`);
      }
    })();
    return () => { live = false; };
  }, []);

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
      else { setTitle(out.display.title); setFromPipeline(true); }
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

  return <View style={StyleSheet.absoluteFill} testID="cv-debug-layer">
    {pv.showCamera && device ? <Camera style={StyleSheet.absoluteFill} device={device} outputs={[photoOutput]} isActive resizeMode="cover" /> : null}
    <Pressable style={StyleSheet.absoluteFill} accessibilityLabel="Tap an item to identify (debug)" onPress={(e) => onTap(e.nativeEvent.locationX, e.nativeEvent.locationY)} />
    {boxes.map((b, i) => <View key={i} pointerEvents="none" style={{ position: 'absolute', left: b.left, top: b.top, width: b.width, height: b.height, borderWidth: 2, borderColor: b.kind === 'crop' ? '#f2c946' : '#7fd38b' }}>
      <Text style={{ color: '#fff', fontSize: 11, backgroundColor: '#0008', alignSelf: 'flex-start', paddingHorizontal: 3 }}>{b.label}</Text></View>)}
    <View pointerEvents="box-none" style={{ position: 'absolute', left: 12, right: 12, top: 12, flexDirection: 'row', justifyContent: 'space-between' }}>
      <Pressable accessibilityLabel="Close camera" onPress={back} style={{ padding: 10, backgroundColor: '#0009', borderRadius: 20 }}><Text style={{ color: '#fff' }}>Close</Text></Pressable>
      <Text style={{ color: '#f2c946', backgroundColor: '#0009', padding: 8, borderRadius: 8 }}>DEBUG · phone test</Text>
    </View>
    {(() => { const b = inferenceBadge(!!sessions.current, fromPipeline, badgeReason); return <Text testID={`cv-inference-${b.source}`} style={{ position: 'absolute', left: 12, right: 12, top: 64, color: '#111', backgroundColor: b.color, padding: 6, borderRadius: 8, fontWeight: '700', textAlign: 'center' }}>{b.text}</Text>; })()}
    <View pointerEvents="none" style={{ position: 'absolute', left: 12, right: 12, bottom: 12, backgroundColor: '#172017d4', borderRadius: 16, padding: 12 }}>
      {title ? <Text style={{ color: '#fff', fontSize: 18, fontWeight: '700' }}>{title}</Text> : null}
      {domainLine ? <Text style={{ color: '#cfe8d0', fontSize: 12 }}>{domainLine}</Text> : null}
      <Text style={{ color: '#ddd', fontSize: 13 }}>{pv.showCamera ? state : pv.message}</Text>
    </View>
    {pv.action === 'open_settings' ? <Pressable onPress={() => Linking.openSettings()} style={{ position: 'absolute', alignSelf: 'center', top: '45%', padding: 14, backgroundColor: '#f2c946', borderRadius: 12 }}><Text>Open Settings</Text></Pressable> : null}
  </View>;
}
