// G9 Stage J4: model-runtime presence check reports missing packages, weights and camera permission clearly.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { checkRuntime, formatReport, CV_PACKAGES, MODEL_FILES, type RuntimeFacts } from '../src/cv/runtimeCheck.ts';

const none: RuntimeFacts = { declared: {}, installed: {}, modelFiles: {}, androidManifest: '<manifest/>', modelsDir: 'android/app/src/main/assets/models' };
const all = (): RuntimeFacts => ({
  declared: Object.fromEntries(CV_PACKAGES.map((p) => [p.name, p.version])),
  installed: Object.fromEntries(CV_PACKAGES.map((p) => [p.name, p.version])),
  modelFiles: Object.fromEntries(MODEL_FILES.map((m) => [m.file, 5_000_000])),
  androidManifest: '<uses-permission android:name="android.permission.CAMERA" />', modelsDir: 'x',
});

test('nothing installed -> NOT READY with a MISSING line and a fix for every item', () => {
  const r = checkRuntime(none);
  assert.equal(r.ready, false); assert.equal(r.cameraReady, false); assert.equal(r.inferenceReady, false); assert.equal(r.weightsReady, false);
  assert.equal(r.items.filter((i) => i.status === 'MISSING').length, CV_PACKAGES.length + MODEL_FILES.length + 1);
  assert.ok(r.items.every((i) => i.status === 'OK' || i.fix));
  const txt = formatReport(r); assert.match(txt, /NOT READY/); assert.match(txt, /h2_mnv3s\.onnx/); assert.match(txt, /android\.permission\.CAMERA/);
});

test('everything present -> ready, and the report says it is not an accuracy result', () => {
  const r = checkRuntime(all()); assert.equal(r.ready, true); assert.match(formatReport(r), /NOT an accuracy or latency result/);
});

test('version mismatch, declared-but-not-installed and LFS-pointer weights are flagged', () => {
  const f = all(); f.declared['onnxruntime-react-native'] = '^1.20.0'; f.installed['react-native-executorch'] = null; f.modelFiles['h2_mnv3s.onnx'] = 130;
  const r = checkRuntime(f);
  const by = Object.fromEntries(r.items.map((i) => [i.item, i]));
  assert.equal(by['onnxruntime-react-native'].status, 'MISMATCH'); assert.equal(by['react-native-executorch'].status, 'MISSING');
  assert.equal(by['h2_mnv3s.onnx'].status, 'MISMATCH'); assert.equal(r.inferenceReady, false); assert.equal(r.weightsReady, false);
  const g = all(); g.installed['react-native-executorch'] = null; assert.equal(checkRuntime(g).inferenceReady, true);   // ONNX fallback alone suffices
});

test('the real native/package.json currently has no camera/inference packages (reported, not hidden)', async () => {
  const { readFileSync } = await import('node:fs');
  const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
  const r = checkRuntime({ ...none, declared: { ...pkg.dependencies, ...pkg.devDependencies } });
  assert.equal(r.ready, false);
});
