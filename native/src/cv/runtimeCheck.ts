// G9 Stage J4: model-runtime presence check (pure; the CLI is native/scripts/check-cv-runtime.ts).
// Reports, without installing anything, whether the pinned camera / inference packages are declared and installed, whether the
// model weight files are present, and whether the Android manifest declares the camera permission. Missing items are reported
// as MISSING with the exact fix; the check never fakes a pass. Package set = docs/cv/gauntlet/G9_stageH_device_test.md §1-2.
import { MODEL_IO } from './pipeline/camera.ts';

export type PkgReq = { name: string; version: string; role: string; group: 'camera' | 'primary_runtime' | 'fallback_runtime' };
export const CV_PACKAGES: readonly PkgReq[] = [
  { name: 'react-native-vision-camera', version: '5.2.3', role: 'camera + frame processors', group: 'camera' },
  { name: 'react-native-nitro-modules', version: '0.37.1', role: 'VisionCamera 5 dependency', group: 'camera' },
  { name: 'react-native-nitro-image', version: '0.15.2', role: 'VisionCamera 5 dependency', group: 'camera' },
  { name: 'react-native-vision-camera-worklets', version: '5.2.3', role: 'frame-processor worklets', group: 'camera' },
  { name: 'react-native-vision-camera-resizer', version: '5.2.3', role: 'GPU resize / letterbox', group: 'camera' },
  { name: 'react-native-worklets', version: '0.12.2', role: 'worklets runtime', group: 'camera' },
  { name: 'react-native-executorch', version: '0.10.5', role: 'primary runtime (.pte; H2 .pte export not done)', group: 'primary_runtime' },
  { name: 'onnxruntime-react-native', version: '1.24.3', role: 'fallback runtime (runs the .onnx files)', group: 'fallback_runtime' },
];
export const MODEL_FILES: readonly { key: keyof typeof MODEL_IO; file: string }[] =
  (Object.keys(MODEL_IO) as (keyof typeof MODEL_IO)[]).map((k) => ({ key: k, file: MODEL_IO[k].file }));
export const DEFAULT_MODELS_DIR = 'android/app/src/main/assets/models';   // proposed bundle location; override with --models-dir

export type RuntimeFacts = {
  declared: Record<string, string>;                 // native/package.json dependencies + devDependencies
  installed: Record<string, string | null>;         // node_modules/<pkg>/package.json version, or null when absent
  modelFiles: Record<string, number | null>;        // file name -> size in bytes, or null when absent
  androidManifest: string | null;                   // AndroidManifest.xml text, or null when absent
  modelsDir: string;
};
export type CheckItem = { item: string; status: 'OK' | 'MISSING' | 'MISMATCH'; detail: string; fix?: string };
export type RuntimeReport = { ready: boolean; cameraReady: boolean; inferenceReady: boolean; weightsReady: boolean; items: CheckItem[] };

const clean = (v: string) => v.replace(/^[\^~=v]/, '');

export function checkRuntime(f: RuntimeFacts): RuntimeReport {
  const items: CheckItem[] = [];
  const pkgOk: Record<string, boolean> = {};
  for (const p of CV_PACKAGES) {
    const d = f.declared[p.name]; const i = f.installed[p.name];
    const fix = `cd native; npm i ${p.name}@${p.version}   (device branch only, after review)`;
    if (!d) { items.push({ item: p.name, status: 'MISSING', detail: `not declared in native/package.json (${p.role})`, fix }); pkgOk[p.name] = false; continue; }
    if (clean(d) !== p.version) { items.push({ item: p.name, status: 'MISMATCH', detail: `declared ${d}, pinned ${p.version}`, fix }); pkgOk[p.name] = false; continue; }
    if (!i) { items.push({ item: p.name, status: 'MISSING', detail: 'declared but not installed in node_modules', fix: 'cd native; npm ci' }); pkgOk[p.name] = false; continue; }
    if (i !== p.version) { items.push({ item: p.name, status: 'MISMATCH', detail: `installed ${i}, pinned ${p.version}`, fix: 'cd native; npm ci' }); pkgOk[p.name] = false; continue; }
    items.push({ item: p.name, status: 'OK', detail: `${i} (${p.role})` }); pkgOk[p.name] = true;
  }
  let weightsReady = true;
  for (const m of MODEL_FILES) {
    const sz = f.modelFiles[m.file];
    if (sz === null || sz === undefined) { weightsReady = false; items.push({ item: m.file, status: 'MISSING', detail: `model weights for '${m.key}' not found in ${f.modelsDir}`, fix: `copy ${m.file} into native/${f.modelsDir}/ (not committed to git)` }); }
    else if (sz < 1024) { weightsReady = false; items.push({ item: m.file, status: 'MISMATCH', detail: `${sz} bytes: too small to be real weights (Git LFS pointer?)`, fix: 'fetch the real file' }); }
    else items.push({ item: m.file, status: 'OK', detail: `${sz} bytes in ${f.modelsDir}` });
  }
  const cam = !!f.androidManifest && /android\.permission\.CAMERA/.test(f.androidManifest);
  items.push(cam ? { item: 'android.permission.CAMERA', status: 'OK', detail: 'declared in AndroidManifest.xml' }
    : { item: 'android.permission.CAMERA', status: 'MISSING', detail: 'AndroidManifest.xml has no CAMERA permission', fix: 'add <uses-permission android:name="android.permission.CAMERA" /> on the device branch' });
  const group = (g: PkgReq['group']) => CV_PACKAGES.filter((p) => p.group === g).every((p) => pkgOk[p.name]);
  const cameraReady = group('camera') && cam;
  const inferenceReady = group('primary_runtime') || group('fallback_runtime');
  return { ready: cameraReady && inferenceReady && weightsReady, cameraReady, inferenceReady, weightsReady, items };
}

export function formatReport(r: RuntimeReport): string {
  const lines = r.items.map((i) => `${i.status.padEnd(8)} ${i.item.padEnd(38)} ${i.detail}${i.fix ? `\n         fix: ${i.fix}` : ''}`);
  lines.push('', `camera ready: ${r.cameraReady ? 'yes' : 'NO'} | inference runtime ready: ${r.inferenceReady ? 'yes' : 'NO'} | weights ready: ${r.weightsReady ? 'yes' : 'NO'}`);
  lines.push(r.ready ? 'RESULT: runtime prerequisites present (this is NOT an accuracy or latency result)' : 'RESULT: NOT READY - see MISSING / MISMATCH lines above');
  return lines.join('\n');
}
