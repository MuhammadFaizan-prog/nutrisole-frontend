// G9 Stage J6 (cv-gauntlet-device): host-side checks that need no phone. Real-vs-placeholder badge, CV->domain hook, latency /
// responsiveness / memory instrumentation, TS-vs-Python preprocessing parity (committed synthetic fixture), ONNX I/O vs MODEL_IO
// (committed host report). Nothing here is a phone measurement.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { inferenceBadge, domainOf, createLatencyRecorder, createLagSampler, modelMemoryEstimateBytes, REAL_BADGE_TEXT, PLACEHOLDER_BADGE_TEXT } from '../src/cv/device/instrument.ts';
import { runDebugPipeline } from '../src/cv/device/debugPipeline.ts';
import { detectorInput, cropRgb } from '../src/cv/device/pixels.ts';
import { h2Input, MODEL_IO } from '../src/cv/pipeline/camera.ts';
import { DEVICE_MODELS } from '../src/cv/device/models.ts';
import { CV_DEBUG_PIPELINE } from '../src/cv/device/flags.ts';
import { H2_CLASSES } from '../src/cv/pipeline/verify.ts';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = (p: string) => readFileSync(path.join(root, p), 'utf8');

test('debug camera labels real inference vs placeholder visibly', () => {
  assert.equal(inferenceBadge(true, true).source, 'real'); assert.equal(inferenceBadge(true, true).text, REAL_BADGE_TEXT);
  for (const [s, r] of [[false, false], [true, false], [false, true]] as const) {
    const b = inferenceBadge(s, r, 'models not loaded'); assert.equal(b.source, 'placeholder'); assert.ok(b.text.startsWith(PLACEHOLDER_BADGE_TEXT));
  }
  const src = read('responsive/CvDebugScan.tsx');
  assert.match(src, /inferenceBadge\(!!sessions\.current, fromPipeline, badgeReason\)/);
  assert.match(src, /testID=\{`cv-inference-\$\{b\.source\}`\}/);
  assert.match(src, /setFromPipeline\(true\)/); assert.match(src, /setFromPipeline\(false\)/);
  assert.equal(CV_DEBUG_PIPELINE, false);   // still off by default
});

test('CV -> domain hook in the debug pipeline goes through domainMap (citrus -> citrus_orange, lemon_lime -> none)', async () => {
  assert.deepEqual(domainOf({ status: 'verified', classId: 3, evidence: 'x' }), { cvClass: 'citrus', domainId: 'citrus_orange' });
  assert.deepEqual(domainOf({ status: 'verified', classId: 6, evidence: 'x' }), { cvClass: 'lemon_lime', domainId: null });
  assert.deepEqual(domainOf({ status: 'unable', reason: 'r', suggestions: [] }), { cvClass: null, domainId: null });
  assert.deepEqual(domainOf(null), { cvClass: null, domainId: null });
  const infer = async (m: 'h2' | 'g3_det', _x: Float32Array, _d: number[]) => {
    if (m === 'g3_det') { const n = 4725, o = new Float32Array(16 * n); const j = 7; o[j] = 240; o[n + j] = 240; o[2 * n + j] = 160; o[3 * n + j] = 160; o[(4 + 3) * n + j] = 0.9; return o; }
    const p = new Float32Array(H2_CLASSES.length).fill(0.08 / 11); p[3] = 0.9; p[12] = 0.02; return p;
  };
  const st = () => ({ rgb: new Uint8Array(640 * 480 * 3).fill(128), w: 640, h: 480 });
  const out = await runDebugPipeline([st(), st(), st()], [200, 150], [400, 300], infer);
  assert.equal(out.inference, 'real'); assert.deepEqual(out.domain, { cvClass: 'citrus', domainId: 'citrus_orange' });
  assert.match(out.display.title, /^Citrus .*Not graded$/);
  assert.match(read('responsive/CvDebugScan.tsx'), /nutritionForCv\(out\.domain\.cvClass\)/);
});

test('latency hooks: spans, percentiles, NSCV lines; event-loop lag sampler; init timing logged', () => {
  let t = 0; const now = () => t;
  const L = createLatencyRecorder(now);
  for (const d of [10, 20, 30, 40, 100]) { const e = L.start('infer_h2'); t += d; e(); }
  L.record('x', Number.NaN); L.record('x', -1);
  const s = L.summary(); assert.deepEqual(s.infer_h2, { n: 5, p50: 30, p95: 100, max: 100 }); assert.equal(s.x, undefined);
  assert.deepEqual(L.lines(), ['NSCV latency span=infer_h2 n=5 p50_ms=30 p95_ms=100 max_ms=100']);
  t = 0; const G = createLagSampler(now, 100); for (const d of [100, 100, 150, 400]) { t += d; G.tick(); }
  assert.equal(G.line(), 'NSCV ui_lag n=4 p50_ms=0 p95_ms=300 max_ms=300');
  const src = read('responsive/CvDebugScan.tsx');
  assert.match(src, /NSCV stage=init model=h2 ms=/); assert.match(src, /NSCV stage=init model=g3_det ms=/);
  assert.match(src, /start\('tap_to_result'\)/); assert.match(src, /start\(`infer_\$\{m\}`\)/); assert.match(src, /createLagSampler/);
  assert.doesNotMatch(src, /fps|FPS/);
});

test('model memory: host-side estimate only (weights + one input/output buffer each)', () => {
  const est = modelMemoryEstimateBytes([DEVICE_MODELS.h2.bytes, DEVICE_MODELS.g3_det.bytes], [[1, 3, 224, 224], [1, 13], [1, 3, 480, 480], [1, 16, 4725]]);
  assert.equal(est, DEVICE_MODELS.h2.bytes + DEVICE_MODELS.g3_det.bytes + 4 * (3 * 224 * 224 + 13 + 3 * 480 * 480 + 16 * 4725));
  assert.ok(est / 2 ** 20 > 19 && est / 2 ** 20 < 21);
});

test('RGB preprocessing parity: TS vs Python reference (Ultralytics LetterBox; camera_io.h2_input) on the synthetic fixture', () => {
  const fx = JSON.parse(read('tests/fixtures/g9j6_preproc_parity.json')) as { cases: any[] };
  assert.equal(fx.cases.length, 3);
  for (const c of fx.cases) {
    const rgb = new Uint8Array(Buffer.from(c.rgb_b64, 'base64')); assert.equal(rgb.length, c.w * c.h * 3);
    const det = detectorInput(rgb, c.w, c.h); assert.equal(det.length, c.det.n);
    let mx = 0; c.det.idx.forEach((i: number, k: number) => { mx = Math.max(mx, Math.abs(det[i] - c.det.val[k])); });
    assert.ok(mx <= 2 / 255 + 1e-6, `${c.name} det maxAbs ${mx}`);
    const cr = cropRgb(rgb, c.w, c.h, c.crop); const x2 = h2Input(cr.rgb, cr.w, cr.h); assert.equal(x2.length, c.h2.n);
    let m2 = 0; c.h2.idx.forEach((i: number, k: number) => { m2 = Math.max(m2, Math.abs(x2[i] - c.h2.val[k])); });
    assert.ok(m2 <= 1e-3, `${c.name} h2 maxAbs ${m2}`);
  }
});

test('G3 + H2 ONNX init on the host: real model I/O equals MODEL_IO and device sha256 (committed host report)', () => {
  const r = JSON.parse(readFileSync(path.join(root, '../ml/runs/G9/stageJ/out/j6/host/onnx_check.json'), 'utf8'));
  assert.match(r.label, /HOST-SIDE/);
  for (const k of ['h2', 'g3_det'] as const) {
    const m = r.models[k]; assert.deepEqual(m.io_errors, []); assert.equal(m.sha256_matches_device_models_ts, true);
    assert.equal(m.file, DEVICE_MODELS[k].file);
    const spec = MODEL_IO[k]; const dims = (s: (number | string)[]) => s.map((d) => (typeof d === 'number' ? d : 'dyn'));
    assert.deepEqual(dims(m.input.shape.map((d: number | string) => (typeof d === 'number' ? d : 'n'))), dims(spec.inputs[0].shape as (number | string)[]));
    assert.deepEqual(dims(m.output.shape.map((d: number | string) => (typeof d === 'number' ? d : 'n'))), dims(spec.outputs[0].shape as (number | string)[]));
  }
  const h = JSON.parse(readFileSync(path.join(root, '../ml/runs/G9/stageJ/out/j6/host/host_pipeline_report.json'), 'utf8'));
  assert.match(h.label, /NOT a physical device/); assert.deepEqual(h.io_errors, { h2: [], g3_det: [] });
  assert.ok(h.parity.det_tensor_maxAbs <= 2 / 255 && h.parity.h2_tensor_maxAbs <= 1e-3);
  assert.equal(h.parity.h2_top1_agree, h.parity.n); assert.equal(h.pipeline.display_errors, 0); assert.equal(h.pipeline.grades_shown, 0);
});
