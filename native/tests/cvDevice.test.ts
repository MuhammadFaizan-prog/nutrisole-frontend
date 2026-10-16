// G9 Stage J5 (cv-gauntlet-device): unit tests for the phone-test pipeline helpers. Synthetic inputs only; no model accuracy,
// no latency and no FPS is measured or claimed here.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { CV_DEBUG_PIPELINE } from '../src/cv/device/flags.ts';
import { permissionView } from '../src/cv/device/permissions.ts';
import { rawToRgb, cropRgb, detectorInput, asProbs } from '../src/cv/device/pixels.ts';
import { orientationToRotation, uprightSize, planTapOnUprightStill, planTapOnRawStill, stillBoxToView } from '../src/cv/device/orientation.ts';
import { burstWide, runDebugPipeline, tappedDetection, BURST } from '../src/cv/device/debugPipeline.ts';
import { overlayBoxes } from '../src/cv/device/overlay.ts';
import { DEVICE_MODELS, DEVICE_MODEL_DIR, APP_ID } from '../src/cv/device/models.ts';
import { CV_PACKAGES, MODEL_FILES, checkRuntime } from '../src/cv/runtimeCheck.ts';
import { letterboxTransform } from '../src/cv/pipeline/closeup.ts';
import { checkDisplayResult } from '../src/cv/pipeline/result.ts';
import { H2_CLASSES } from '../src/cv/pipeline/verify.ts';
import type { Box } from '../src/cv/pipeline/preprocess.ts';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = (p: string) => readFileSync(path.join(root, p), 'utf8');

test('debug flag is OFF by default and the Scan screen only requires the camera layer behind it', () => {
  assert.equal(CV_DEBUG_PIPELINE, false);
  const scan = read('responsive/ScanScreen.tsx');
  assert.match(scan, /CV_DEBUG_PIPELINE \? require\('\.\/CvDebugScan'\)\.default : null/);
  assert.doesNotMatch(scan, /^import .*react-native-vision-camera/m); assert.doesNotMatch(scan, /^import .*onnxruntime/m);
  assert.match(scan, /\{CvDebugLayer \? <CvDebugLayer/);
  const dbg = read('responsive/CvDebugScan.tsx');
  assert.doesNotMatch(dbg, /Grade\s+[ABC]|confidence|%\s*<\/Text>|fps/i);
});

test('permissions: nothing requested with the flag off; request / settings / restricted paths', () => {
  for (const s of ['authorized', 'denied', 'not-determined', 'restricted'] as const) assert.deepEqual(permissionView(false, s, true), { state: 'off', action: 'none', showCamera: false, message: '' });
  assert.equal(permissionView(true, 'authorized', false).showCamera, true);
  assert.equal(permissionView(true, 'not-determined', true).action, 'request');
  assert.equal(permissionView(true, 'not-determined', false).action, 'open_settings');
  assert.equal(permissionView(true, 'denied', false).action, 'open_settings');
  assert.equal(permissionView(true, 'restricted', false).state, 'unavailable');
  assert.equal(permissionView(true, undefined, false).showCamera, false);
});

test('preprocessing: raw pixel formats -> RGB; size mismatch and unknown format refused', () => {
  const px = (f: string) => ({ RGBA: [10, 20, 30, 255], BGRA: [30, 20, 10, 255], ARGB: [255, 10, 20, 30], ABGR: [255, 30, 20, 10], RGBX: [10, 20, 30, 0], BGRX: [30, 20, 10, 0], XRGB: [0, 10, 20, 30], XBGR: [0, 30, 20, 10], RGB: [10, 20, 30], BGR: [30, 20, 10] } as Record<string, number[]>)[f];
  for (const f of ['RGBA', 'BGRA', 'ARGB', 'ABGR', 'RGBX', 'BGRX', 'XRGB', 'XBGR', 'RGB', 'BGR'] as const) {
    const one = px(f); const buf = new Uint8Array([...one, ...one]);
    assert.deepEqual([...rawToRgb(buf.buffer, 2, 1, f)], [10, 20, 30, 10, 20, 30], f);
  }
  assert.throws(() => rawToRgb(new Uint8Array(7), 2, 1, 'RGBA'), /row padding/);
  assert.throws(() => rawToRgb(new Uint8Array(8), 2, 1, 'unknown'), /unsupported/);
  assert.deepEqual(asProbs([0.2, 0.8]), [0.2, 0.8]);
  const s = asProbs([1, 2, 3]); assert.ok(Math.abs(s.reduce((a, b) => a + b) - 1) < 1e-9 && s[2] > s[1]);
});

test('preprocessing: detector letterbox places pixels like closeup.letterboxTransform and pads with 114', () => {
  const w = 64, h = 32; const rgb = new Uint8Array(w * h * 3).fill(200);
  const x = detectorInput(rgb, w, h, 64); const t = letterboxTransform(w, h, 64); const N = 64 * 64;
  assert.equal(x.length, 3 * N); assert.equal(t.py, 16);
  assert.ok(Math.abs(x[0] - 114 / 255) < 1e-6);                         // top padding
  assert.ok(Math.abs(x[(t.py + 5) * 64 + 10] - 200 / 255) < 1e-6);       // image row
  assert.ok(Math.abs(x[2 * N + (63) * 64 + 63] - 114 / 255) < 1e-6);     // bottom padding, blue plane
});

test('crop extraction: exact pixels, clamped to the image, empty crop refused', () => {
  const w = 4, h = 3; const rgb = new Uint8Array(w * h * 3); for (let i = 0; i < w * h; i++) rgb.set([i, i, i], i * 3);
  const c = cropRgb(rgb, w, h, { x: 1, y: 1, w: 2, h: 2 });
  assert.deepEqual([c.w, c.h], [2, 2]); assert.deepEqual([...c.rgb].filter((_, k) => k % 3 === 0), [5, 6, 9, 10]);
  const cl = cropRgb(rgb, w, h, { x: 3, y: 2, w: 10, h: 10 }); assert.deepEqual([cl.w, cl.h], [1, 1]);
  assert.throws(() => cropRgb(rgb, w, h, { x: 9, y: 9, w: 2, h: 2 }), /empty/);
});

test('orientation, rotation and mirroring: raw-still plans agree with the upright-still plan', () => {
  assert.deepEqual(['up', 'right', 'down', 'left'].map((o) => orientationToRotation(o as any)), [0, 90, 180, 270]);
  assert.deepEqual(uprightSize(4000, 3000, 'right'), [3000, 4000]); assert.deepEqual(uprightSize(4000, 3000, 'up'), [4000, 3000]);
  const view: [number, number] = [360, 640];
  const up = planTapOnUprightStill([180, 320], view, [3000, 4000], [])!;
  const cx = (up.crop.x + up.crop.w / 2) / 3000, cy = (up.crop.y + up.crop.h / 2) / 4000;
  assert.ok(Math.abs(cx - 0.5) < 0.01 && Math.abs(cy - 0.5) < 0.01);
  // tap near the top-left of a portrait preview over a landscape sensor still rotated 90: lands near the sensor's (top-left -> rotated) corner
  const raw = planTapOnRawStill([60, 100], view, [4000, 3000], 'right', false)!;
  const upr = planTapOnUprightStill([60, 100], view, [3000, 4000], [])!;
  const [rx, ry] = raw.framePoint; const [ux, uy] = upr.framePoint;
  assert.ok(Math.abs(rx - uy) < 1e-6 && Math.abs(ry - (1 - ux)) < 1e-6, `rot90 ${raw.framePoint} vs ${upr.framePoint}`);
  const m = planTapOnRawStill([60, 320], view, [3000, 4000], 'up', true)!;     // front camera: mirrored horizontally
  assert.ok(m.framePoint[0] > 0.5);
});

test('coordinate mapping and box rendering: still box -> view rect (cover), names only on boxes', () => {
  const still: [number, number] = [3000, 4000], view: [number, number] = [300, 400];
  assert.deepEqual(stillBoxToView([0, 0, 3000, 4000], still, view), { left: 0, top: 0, width: 300, height: 400 });
  const r = stillBoxToView([1000, 1000, 2000, 3000], still, view); assert.deepEqual([r.left, r.top, r.width, r.height], [100, 100, 100, 200]);
  const plan = planTapOnUprightStill([150, 200], view, still, [[1000, 1000, 2000, 3000]])!;
  assert.equal(plan.source, 'track');
  const boxes = overlayBoxes([{ box: [1000, 1000, 2000, 3000] as Box, classId: 1, score: 0.93 }], plan, still, view);
  assert.equal(boxes.length, 2); assert.equal(boxes[0].label, 'Apple'); assert.equal(boxes[1].kind, 'crop');
  for (const b of boxes) assert.doesNotMatch(b.label, /\d|%|Grade/);
  assert.ok(boxes[1].left <= boxes[0].left && boxes[1].left + boxes[1].width >= boxes[0].left + boxes[0].width);   // crop pads the box
});

test('burst wide identity follows the frozen id policy (3 agreeing stills, score >= 0.5)', () => {
  const d = (c: number, s = 0.9) => ({ box: [0, 0, 10, 10] as Box, classId: c, score: s });
  assert.equal(BURST, 3);
  assert.deepEqual(burstWide([d(1), d(1), d(1)]), { status: 'identified', classId: 1 });
  assert.equal(burstWide([d(1), d(1), null]).status, 'pending');
  assert.equal(burstWide([d(1), d(7), d(1)]).status, 'pending');
  assert.equal(burstWide([d(1), d(1, 0.3), d(1)]).status, 'unable');
  assert.equal(burstWide([null, null, null]).status, 'unable');
  assert.equal(tappedDetection([d(1), { box: [2, 2, 5, 5], classId: 7, score: 0.6 }], [0.3, 0.3], 10, 10)!.classId, 7);   // smallest containing box
});

function fakeInfer(detClass: number, h2Top: number, unknown = 0.02) {
  return async (m: 'h2' | 'g3_det', input: Float32Array, dims: number[]) => {
    if (m === 'g3_det') {
      assert.deepEqual(dims, [1, 3, 480, 480]); assert.equal(input.length, 3 * 480 * 480);
      const n = 4725, out = new Float32Array(16 * n); const j = 7;
      out[j] = 240; out[n + j] = 240; out[2 * n + j] = 160; out[3 * n + j] = 160; out[(4 + detClass) * n + j] = 0.9; return out;
    }
    assert.deepEqual(dims, [1, 3, 224, 224]); assert.equal(input.length, 3 * 224 * 224);
    const p = new Float32Array(H2_CLASSES.length).fill((1 - 0.9 - unknown) / (H2_CLASSES.length - 2)); p[h2Top] = 0.9; p[12] = unknown; return p;
  };
}
const still = () => ({ rgb: new Uint8Array(640 * 480 * 3).fill(128), w: 640, h: 480 });

test('end-to-end debug pipeline (fake models): name + Not graded, never a grade or a confidence', async () => {
  const out = await runDebugPipeline([still(), still(), still()], [200, 150], [400, 300], fakeInfer(1, 1));
  assert.equal(out.wide.status, 'identified'); assert.equal(out.verify?.status, 'verified');
  assert.equal(out.display.title, 'Apple. Not graded'); assert.deepEqual(out.displayErrors, []);
  assert.equal(out.display.grade, null); assert.equal(out.display.confidenceText, null); assert.doesNotMatch(out.display.title, /\d|%/);
  assert.equal(out.plan?.source, 'track'); assert.ok(out.display.reasons.includes('quality_gate_not_run_in_debug'));
  assert.ok(out.logLines.every((l) => /^NSCV stage=(det|h2) ms=/.test(l)));
});

test('end-to-end debug pipeline: disagreement / unknown / no detection -> Unable to identify', async () => {
  for (const [det, top, unk] of [[1, 7, 0.02], [1, 1, 0.6]] as const) {
    const out = await runDebugPipeline([still(), still(), still()], [200, 150], [400, 300], fakeInfer(det, top, unk));
    assert.equal(out.display.title, 'Unable to identify'); assert.deepEqual(checkDisplayResult(out.display), []);
  }
  const none = await runDebugPipeline([still(), still(), still()], [20, 20], [400, 300], fakeInfer(1, 1));   // tap outside the detected box
  assert.equal(none.wide.status, 'unable'); assert.equal(none.display.title, 'Unable to identify'); assert.equal(none.plan?.source, 'tap_roi');
});

test('device branch wiring: pinned packages, CAMERA permission, model files and sha256 recorded', () => {
  const pkg = JSON.parse(read('package.json')); const deps = { ...pkg.dependencies, ...pkg.devDependencies };
  for (const p of CV_PACKAGES.filter((x) => x.group !== 'primary_runtime')) assert.equal(deps[p.name], p.version, p.name);
  assert.equal(deps['react-native-executorch'], undefined);   // optional: no H2 .pte export exists
  assert.equal(deps['react-native'], '0.86.3');
  assert.match(read('android/app/src/main/AndroidManifest.xml'), /android\.permission\.CAMERA/);
  assert.match(read('babel.config.js'), /react-native-worklets\/plugin/);
  assert.deepEqual(Object.values(DEVICE_MODELS).map((m) => m.file).sort(), MODEL_FILES.map((m) => m.file).sort());
  for (const m of Object.values(DEVICE_MODELS)) assert.match(m.sha256, /^[0-9a-f]{64}$/);
  assert.equal(DEVICE_MODEL_DIR, `/sdcard/Android/data/${APP_ID}/files/models`);
  assert.match(read('android/app/build.gradle'), new RegExp(`applicationId "${APP_ID}"`));
  // runtime check: declared but not installed in the sandbox -> still NOT READY, never a faked pass
  const declared = deps as Record<string, string>; const installed: Record<string, string | null> = {}; CV_PACKAGES.forEach((p) => { installed[p.name] = null; });
  const r = checkRuntime({ declared, installed, modelFiles: {}, androidManifest: read('android/app/src/main/AndroidManifest.xml'), modelsDir: 'x' });
  assert.equal(r.ready, false); assert.ok(r.items.some((i) => i.item === 'android.permission.CAMERA' && i.status === 'OK'));
});
