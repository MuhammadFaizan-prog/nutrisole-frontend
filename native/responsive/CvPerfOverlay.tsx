// G9 Stage J8: QA-build performance overlay for the live CV debug layer (loaded only inside CvDebugScan, i.e. only when the QA flag
// is on). Every number is measured on the phone running it (perf meter in src/cv/device/live.ts + NsModelAssets.runtimeStats);
// a value that is not available is shown as "-", never estimated. This is an engineering readout, not a product screen.
import { Text, View } from 'react-native';
import type { PerfSnapshot } from '../src/cv/device/live.ts';

const THERMAL = ['none', 'light', 'moderate', 'severe', 'critical', 'emergency', 'shutdown'];
const v = (x: number | null, unit = '') => (x === null || x === undefined ? '-' : `${x}${unit}`);

export default function CvPerfOverlay({ p }: { p: PerfSnapshot | null }) {
  if (!p) return null;
  const rows = [
    `camera frames/s ${p.cameraFps} · detection updates/s ${p.detUps}`,
    `G3 inference p50/p95 ${v(p.inferP50, ' ms')} / ${v(p.inferP95, ' ms')}`,
    `frame→overlay p50/p95 ${v(p.e2eP50, ' ms')} / ${v(p.e2eP95, ' ms')}`,
    `skipped busy ${p.skippedBusy} · skipped interval ${p.skippedInterval} · dropped ${p.dropped} · interval ${p.intervalMs} ms`,
    `thermal ${p.thermal < 0 ? 'n/a' : THERMAL[p.thermal] ?? p.thermal} · JS heap ${v(p.jsHeapMb, ' MB')} · native heap ${v(p.nativeHeapMb, ' MB')}`,
  ];
  return <View pointerEvents="none" testID="cv-perf-overlay" style={{ position: 'absolute', left: 8, right: 8, top: 100, backgroundColor: '#000a', borderRadius: 8, padding: 6 }}>
    <Text style={{ color: '#f2c946', fontSize: 10, fontWeight: '700' }}>QA PERF (this phone, last {p.windowS} s)</Text>
    {rows.map((r) => <Text key={r} style={{ color: '#e8e8e8', fontSize: 10 }}>{r}</Text>)}
  </View>;
}
