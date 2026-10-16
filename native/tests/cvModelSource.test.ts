// G9 Stage J7 (cv-gauntlet-device): bundled-model loading for the QA APK. Fake native module only (no phone, no real weights here).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { resolveModel, resolveDebugModels, MODELS_NOT_LOADED, type ModelNative, type ModelFileInfo } from '../src/cv/device/modelSource.ts';
import { DEVICE_MODELS, modelPath } from '../src/cv/device/models.ts';
import { CV_DEBUG_PIPELINE } from '../src/cv/device/flags.ts';
import * as qa from '../src/cv/device/flags.qa.ts';
import { inferenceBadge } from '../src/cv/device/instrument.ts';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = (p: string) => readFileSync(path.join(root, p), 'utf8');
const good = (k: 'h2' | 'g3_det', p: string): ModelFileInfo => ({ path: p, bytes: DEVICE_MODELS[k].bytes, sha256: DEVICE_MODELS[k].sha256 });
const keyOf = (file: string) => (file === DEVICE_MODELS.h2.file ? 'h2' : 'g3_det') as 'h2' | 'g3_det';
const keyOfPath = (p: string) => (p.endsWith(DEVICE_MODELS.h2.file) ? 'h2' : 'g3_det') as 'h2' | 'g3_det';

function fake(bundled: 'good' | 'missing' | 'bad', pushed: 'good' | 'missing' | 'bad'): ModelNative {
  return {
    prepareBundled: async (file) => {
      if (bundled === 'missing') throw new Error(`models/${file} is not bundled in this APK`);
      const k = keyOf(file); const g = good(k, `/data/user/0/app/files/models/${file}`);
      return bundled === 'good' ? g : { ...g, sha256: '0'.repeat(64) };
    },
    describeFile: async (p) => {
      if (pushed === 'missing') throw new Error(`${p} not found`);
      const g = good(keyOfPath(p), p);
      return pushed === 'good' ? g : { ...g, bytes: g.bytes - 1 };
    },
  };
}

test('bundled asset with matching sha256 + size is used first', async () => {
  const r = await resolveModel('h2', fake('good', 'good'));
  assert.equal(r.ok, true); if (r.ok) { assert.equal(r.source, 'bundled'); assert.match(r.path, /files\/models\/h2_mnv3s\.onnx$/); }
});

test('falls back to the hash-verified adb push when the asset is missing or its hash mismatches', async () => {
  for (const b of ['missing', 'bad'] as const) {
    const r = await resolveModel('g3_det', fake(b, 'good'));
    assert.equal(r.ok, true); if (r.ok) { assert.equal(r.source, 'adb_push'); assert.equal(r.path, modelPath('g3_det')); assert.ok(r.tried[0].startsWith('bundled:')); }
  }
});

test('nothing verified -> Models not loaded, never a mock path', async () => {
  for (const [b, p] of [['missing', 'missing'], ['bad', 'bad'], ['bad', 'missing']] as const) {
    const r = await resolveModel('h2', fake(b, p)); assert.equal(r.ok, false);
    if (!r.ok) { assert.equal(r.tried.length, 2); assert.match(r.reason, /bundled: .*; adb_push: /); }
  }
  const none = await resolveModel('h2', null); assert.equal(none.ok, false);
  const all = await resolveDebugModels(fake('missing', 'missing'));
  assert.equal(all.ok, false); if (!all.ok) { assert.ok(all.message.startsWith(`${MODELS_NOT_LOADED}: `)); assert.match(all.message, /h2_mnv3s\.onnx/); assert.match(all.message, /det_yolo11n_640_raw\.onnx/); }
  assert.ok(all.lines.every((l) => /^NSCV model_source model=(h2|g3_det) source=none reason=/.test(l)));
  assert.equal(inferenceBadge(false, false, 'models not loaded').source, 'placeholder');   // what the screen shows in that case
});

test('both verified -> both paths; NSCV lines name the source', async () => {
  const r = await resolveDebugModels(fake('good', 'missing'));
  assert.equal(r.ok, true); if (r.ok) { assert.match(r.paths.h2, /h2_mnv3s/); assert.match(r.paths.g3_det, /det_yolo11n_640_raw/); }
  assert.deepEqual(r.lines, ['NSCV model_source model=h2 source=bundled sha256=ok', 'NSCV model_source model=g3_det source=bundled sha256=ok']);
});

test('debug screen loads through modelSource (no direct path, no mock), QA flag swap is bundle-time only', () => {
  const dbg = read('responsive/CvDebugScan.tsx');
  assert.match(dbg, /resolveDebugModels\(NativeModules\.NsModelAssets/);
  assert.match(dbg, /InferenceSession\.create\(src\.paths\.h2\)/); assert.match(dbg, /InferenceSession\.create\(src\.paths\.g3_det\)/);
  const code = dbg.split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');
  assert.doesNotMatch(code, /modelPath\(/); assert.doesNotMatch(code, /mock|fake/i);
  assert.equal(CV_DEBUG_PIPELINE, false);            // committed default stays off
  assert.equal(qa.CV_DEBUG_PIPELINE, true);          // only substituted by metro when NUTRISOLE_QA=1
  const metro = read('metro.config.js');
  assert.match(metro, /process\.env\.NUTRISOLE_QA === '1'/); assert.match(metro, /qaBuild && resolved\.type === 'sourceFile'/);
  const kt = read('android/app/src/main/java/com/muhammadfaizan/nutrisole/ModelAssetsModule.kt');
  assert.match(kt, /"NsModelAssets"/); assert.match(kt, /assets\.open\("models\/\$file"\)/); assert.match(kt, /SHA-256/);
  assert.match(read('android/app/src/main/java/com/muhammadfaizan/nutrisole/MainApplication.kt'), /add\(ModelAssetsPackage\(\)\)/);
  assert.match(read('android/.gitignore'), /app\/src\/main\/assets\/models\//);
});
