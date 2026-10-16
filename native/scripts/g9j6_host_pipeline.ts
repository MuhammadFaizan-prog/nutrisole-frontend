// G9 Stage J6 HOST-SIDE harness for the Android debug pipeline. Runs the SAME TypeScript code the phone runs (device/pixels.ts,
// pipeline/camera.ts h2Input, device/debugPipeline.ts) with the SAME ONNX files, but on the sandbox CPU through onnxruntime-node.
// It is NOT a phone measurement: no camera, the 3-still burst is the same still three times, and every number is host-side.
//
//   ORT_NODE_DIR=/path/with/node_modules/onnxruntime-node node --experimental-strip-types scripts/g9j6_host_pipeline.ts \
//     --models /workspace/work/g9j6/models --parity /workspace/work/g9j6/parity --out /workspace/work/g9j6/host_run.json --report <repo json>
// Inputs come from ml/runs/G9/stageJ/scripts/j6_host_parity.py (raw RGB stills + Python reference tensors and model outputs).
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { detectorInput, cropRgb } from '../src/cv/device/pixels.ts';
import { h2Input, checkModelIO, type RuntimeMeta } from '../src/cv/pipeline/camera.ts';
import { decodeRawWithNms } from '../src/cv/pipeline/postprocess.ts';
import { runDebugPipeline, type UprightStill } from '../src/cv/device/debugPipeline.ts';
import { DEVICE_MODELS } from '../src/cv/device/models.ts';
import { createLatencyRecorder, inferenceBadge } from '../src/cv/device/instrument.ts';
import { nutritionForCv } from '../src/cv/data/nutrition.ts';
import { stillBoxToView } from '../src/cv/device/orientation.ts';

const arg = (k: string, d = '') => { const i = process.argv.indexOf(`--${k}`); return i > 0 ? process.argv[i + 1] : d; };
const MODELS = arg('models', '/workspace/work/g9j6/models'); const PAR = arg('parity', '/workspace/work/g9j6/parity');
const OUT = arg('out', '/workspace/work/g9j6/host_run.json'); const REPORT = arg('report', '');
const req = createRequire(path.join(process.env.ORT_NODE_DIR ?? process.cwd(), 'x.js'));
const ort = req('onnxruntime-node');
const f32 = (p: string) => { const b = readFileSync(p); return new Float32Array(b.buffer, b.byteOffset, b.byteLength / 4); };
const diff = (a: ArrayLike<number>, b: ArrayLike<number>) => {
  if (a.length !== b.length) throw new Error(`length ${a.length} != ${b.length}`);
  let mx = 0; let s = 0; for (let i = 0; i < a.length; i++) { const d = Math.abs(a[i] - b[i]); s += d; if (d > mx) mx = d; } return { maxAbs: mx, meanAbs: s / a.length };
};
const r4 = (v: number) => Math.round(v * 1e4) / 1e4;
const mb = (v: number) => Math.round(v / 2 ** 20 * 10) / 10;

async function main() {
  const idx = JSON.parse(readFileSync(path.join(PAR, 'index.json'), 'utf8')) as { items: { id: string; w: number; h: number; crop: { x: number; y: number; w: number; h: number } }[] };
  // --- init (host) ---
  const rss0 = process.memoryUsage().rss; const t0 = performance.now();
  const h2 = await ort.InferenceSession.create(path.join(MODELS, DEVICE_MODELS.h2.file)); const t1 = performance.now();
  const g3 = await ort.InferenceSession.create(path.join(MODELS, DEVICE_MODELS.g3_det.file)); const t2 = performance.now();
  const rss1 = process.memoryUsage().rss;
  const metaOf = (s: any): RuntimeMeta => ({
    inputs: s.inputNames.map((n: string, i: number) => ({ name: n, shape: s.inputMetadata?.[i]?.shape ?? [], type: s.inputMetadata?.[i]?.type })),
    outputs: s.outputNames.map((n: string, i: number) => ({ name: n, shape: s.outputMetadata?.[i]?.shape ?? [], type: s.outputMetadata?.[i]?.type })),
  });
  const ioErr = { h2: checkModelIO('h2', metaOf(h2)), g3_det: checkModelIO('g3_det', metaOf(g3)) };
  const run = async (s: any, x: Float32Array, dims: number[]) => (await s.run({ [s.inputNames[0]]: new ort.Tensor('float32', x, dims) }))[s.outputNames[0]].data as Float32Array;

  // --- preprocessing + model-output parity: TS vs Python reference on the same stills ---
  const parity: any[] = [];
  for (const it of idx.items) {
    const rgb = new Uint8Array(readFileSync(path.join(PAR, `${it.id}.rgb`)));
    const det = detectorInput(rgb, it.w, it.h); const c = cropRgb(rgb, it.w, it.h, it.crop); const x2 = h2Input(c.rgb, c.w, c.h);
    const dDet = diff(det, f32(path.join(PAR, `${it.id}.det.f32`))); const dH2 = diff(x2, f32(path.join(PAR, `${it.id}.h2.f32`)));
    const yd = await run(g3, det, [1, 3, 480, 480]); const ydPy = f32(path.join(PAR, `${it.id}.detout.f32`));
    const y2 = await run(h2, x2, [1, 3, 224, 224]); const y2Py = f32(path.join(PAR, `${it.id}.h2out.f32`));
    const dTs = decodeRawWithNms(yd, 12, 4725, 0.25); const dPy = decodeRawWithNms(ydPy, 12, 4725, 0.25);
    const am = (a: ArrayLike<number>) => Array.from(a).reduce((bi, v, i, arr) => (v > arr[bi] ? i : bi), 0);
    parity.push({ id: it.id, det_tensor: { maxAbs: r4(dDet.maxAbs), meanAbs: r4(dDet.meanAbs) }, h2_tensor: { maxAbs: r4(dH2.maxAbs), meanAbs: r4(dH2.meanAbs) },
      h2_probs_maxAbs: r4(diff(y2, y2Py).maxAbs), h2_top1_agree: am(y2) === am(y2Py),
      det_dets_ts: dTs.length, det_dets_py: dPy.length, det_classes_agree: JSON.stringify(dTs.map((d) => d.classId).sort()) === JSON.stringify(dPy.map((d) => d.classId).sort()) });
  }

  // --- end-to-end debug pipeline on each still (simulated burst = same still x3, tap = view centre) ---
  const lat = createLatencyRecorder(() => performance.now());
  const runs: any[] = [];
  for (const it of idx.items) {
    const rgb = new Uint8Array(readFileSync(path.join(PAR, `${it.id}.rgb`)));
    const still: UprightStill = { rgb, w: it.w, h: it.h }; const view: [number, number] = [360, 780];
    // tap modes: 'centre' = view centre; 'det' = centre of the highest-score G3 box (simulates the tester tapping the item)
    const pre = decodeRawWithNms(await run(g3, detectorInput(rgb, it.w, it.h), [1, 3, 480, 480]), 12, 4725, 0.25);
    const taps: [string, [number, number]][] = [['centre', [view[0] / 2, view[1] / 2]]];
    if (pre.length) {
      const top = pre.reduce((a, b) => (b.score > a.score ? b : a));
      const { detectorToFrame } = await import('../src/cv/pipeline/closeup.ts');
      const v = stillBoxToView(detectorToFrame(top.box, it.w, it.h), [it.w, it.h], view);
      const tx = v.left + v.width / 2; const ty = v.top + v.height / 2;
      if (tx >= 0 && ty >= 0 && tx <= view[0] && ty <= view[1]) taps.push(['det', [tx, ty]]);
    }
    for (const [tapMode, tap] of taps) {
    const end = lat.start('pipeline_total');
    const out = await runDebugPipeline([still, still, still], tap, view, async (m, x, dims) => {
      const e = lat.start(`infer_${m}`); const y = await run(m === 'h2' ? h2 : g3, x, dims); e(); return y;
    }, () => performance.now());
    const ms = end();
    const nut = nutritionForCv(out.domain.cvClass);
    runs.push({ id: it.id, tapMode, tap, view, w: it.w, h: it.h, title: out.display.title, state: out.display.state, wide: out.wide, verify: out.verify, domain: out.domain,
      nutrition_fdc: nut ? nut.source.fdcId : null, price: 'no verified source supplied (host run)', badge: inferenceBadge(true, true).text,
      plan: out.plan, last_dets: out.detections[out.detections.length - 1].map((d) => ({ box: d.box.map((v) => Math.round(v)), classId: d.classId })),
      displayErrors: out.displayErrors, total_ms: Math.round(ms), logLines: out.logLines });
    }
  }
  const rss2 = process.memoryUsage().rss;
  const max = (k: string) => Math.max(...parity.map((p) => p[k].maxAbs));
  const report = {
    label: 'HOST-SIDE SIMULATION: sandbox CPU (2 vCPU), Node ' + process.version + ' + onnxruntime-node ' + (req('onnxruntime-node/package.json').version) + '. Same TS pipeline + same ONNX files as the debug build. NOT a physical device; no phone latency/FPS/memory claim.',
    io_errors: ioErr, metadata_available: !!h2.inputMetadata,
    host_init_ms: { h2: Math.round(t1 - t0), g3_det: Math.round(t2 - t1) }, host_rss_mb: { before: mb(rss0), after_init: mb(rss1), after_runs: mb(rss2), growth_init: mb(rss1 - rss0) },
    parity: { n: parity.length, det_tensor_maxAbs: r4(max('det_tensor')), h2_tensor_maxAbs: r4(max('h2_tensor')),
      h2_probs_maxAbs: r4(Math.max(...parity.map((p) => p.h2_probs_maxAbs))), h2_top1_agree: parity.filter((p) => p.h2_top1_agree).length,
      det_classes_agree: parity.filter((p) => p.det_classes_agree).length, tolerance: { det_tensor_maxAbs: 2 / 255, h2_tensor_maxAbs: 1e-3 }, items: parity },
    latency_host: lat.summary(),
    pipeline: { n: runs.length, titles: runs.map((r) => ({ id: r.id, tap: r.tapMode, title: r.title, domain: r.domain.domainId })), display_errors: runs.filter((r) => r.displayErrors.length).length,
      grades_shown: runs.filter((r) => /grade [ABC]|\d+%/i.test(r.title)).length },
  };
  mkdirSync(path.dirname(OUT), { recursive: true }); writeFileSync(OUT, JSON.stringify({ report, runs }, null, 1));
  if (REPORT) { mkdirSync(path.dirname(REPORT), { recursive: true }); writeFileSync(REPORT, JSON.stringify(report, null, 1)); }
  console.log(JSON.stringify({ io: ioErr, init: report.host_init_ms, rss: report.host_rss_mb, parity: { ...report.parity, items: undefined }, latency: report.latency_host, pipeline: report.pipeline }, null, 1));
}
main().catch((e) => { console.error(e); process.exit(1); });
