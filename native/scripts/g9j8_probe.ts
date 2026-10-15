// G9 Stage J8 HOST-SIDE probe harness (report-only diagnosis). Runs the SAME TypeScript the QA APK runs - live path
// (detectorInput on the 480-inner live buffer -> decodeRawWithNms -> mergeAgnostic -> LiveTracker/trackWide, guidance hints) and
// close-up path (runCloseupFromTrack: high-res still, tap crop, H2, FROZEN_VERIFY P-a) - plus the J7 behaviour for comparison
// (raw class-wise overlay labels and the 3-still runDebugPipeline). Same ONNX files, onnxruntime-node on the sandbox CPU.
// NOT a phone: a static image stands in for 3 identical live frames, the live buffer is a PIL bilinear resize (not the GPU resizer).
//   ORT_NODE_DIR=/workspace/work/g9j6/harness node --experimental-strip-types scripts/g9j8_probe.ts --raw <dir> --models <dir> --out <json> [--from i --to j]
import { readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { detectorInput, cropRgb, asProbs } from '../src/cv/device/pixels.ts';
import { h2Input, identityCrop } from '../src/cv/pipeline/camera.ts';
import { decodeRawWithNms } from '../src/cv/pipeline/postprocess.ts';
import { detectorToFrame } from '../src/cv/pipeline/closeup.ts';
import { runDebugPipeline, runCloseupFromTrack, h2Top3, labelOf } from '../src/cv/device/debugPipeline.ts';
import { mergeAgnostic, LiveTracker, trackWide, guidanceHints, qualityMetrics, boxSide, bufferBoxToFrame } from '../src/cv/device/live.ts';
import { diagRecord } from '../src/cv/device/diag.ts';
import { stillBoxToView } from '../src/cv/device/orientation.ts';
import { DEVICE_MODELS } from '../src/cv/device/models.ts';
import type { Box } from '../src/cv/pipeline/preprocess.ts';

const arg = (k: string, d = '') => { const i = process.argv.indexOf(`--${k}`); return i > 0 ? process.argv[i + 1] : d; };
const RAW = arg('raw'); const MODELS = arg('models', '/workspace/work/g9j6/models'); const OUT = arg('out');
const req = createRequire(path.join(process.env.ORT_NODE_DIR ?? process.cwd(), 'x.js')); const ort = req('onnxruntime-node');

async function main() {
  const idx = JSON.parse(readFileSync(path.join(RAW, 'index.json'), 'utf8')) as any[];
  const from = Number(arg('from', '0')); const to = Number(arg('to', String(idx.length)));
  const h2 = await ort.InferenceSession.create(path.join(MODELS, DEVICE_MODELS.h2.file));
  const g3 = await ort.InferenceSession.create(path.join(MODELS, DEVICE_MODELS.g3_det.file));
  const run = async (s: any, x: Float32Array, dims: number[]) => (await s.run({ [s.inputNames[0]]: new ort.Tensor('float32', x, dims) }))[s.outputNames[0]].data as Float32Array;
  const infer = async (m: 'h2' | 'g3_det', x: Float32Array, dims: number[]) => run(m === 'h2' ? h2 : g3, x, dims);
  const rows: any[] = [];
  for (const it of idx.slice(from, to)) {
    const still = new Uint8Array(readFileSync(path.join(RAW, `${it.key}.rgb`))); const lo = new Uint8Array(readFileSync(path.join(RAW, `${it.key}.lo.rgb`)));
    const view: [number, number] = [360, Math.round(360 * it.h / it.w)];   // preview with the frame's aspect (no cover crop)
    // ---- LIVE (J8): 3 identical frames of the live buffer -> tracker
    const raw = decodeRawWithNms(await infer('g3_det', detectorInput(lo, it.lw, it.lh), [1, 3, 480, 480]), 12, 4725, 0.25).map((d) => ({ ...d, box: detectorToFrame(d.box, it.lw, it.lh) }));
    const objs = mergeAgnostic(raw); const tr = new LiveTracker(); let views = tr.update(objs, 0); views = tr.update(objs, 200); views = tr.update(objs, 400);
    const prim = views.length ? views.reduce((a, b) => (boxSide(b.box) > boxSide(a.box) ? b : a)) : null;
    const primTrack = prim ? tr.tracks.find((t) => t.id === prim.id)! : null;
    // J7 overlay behaviour: every raw class-wise box was drawn with its class name; which names landed on the primary object?
    const j7NamesOnPrimary = prim ? [...new Set(raw.filter((d) => boxIou(d.box, prim.box) > 0.5).map((d) => d.classId))] : [];
    let q = null; let hints: any[] = []; let liveH2: any = null;
    if (prim) {
      const scale = it.w / it.lw;   // live buffer px -> source (still) px
      q = qualityMetrics(lo, it.lw, it.lh, prim.box, scale);
      // report-only: H2 on a PREVIEW-resolution crop vs the high-res crop (crop-source check)
      const c = identityCrop(prim.box, it.lw, it.lh); const pc = cropRgb(lo, it.lw, it.lh, c);
      liveH2 = h2Top3(asProbs(await infer('h2', h2Input(pc.rgb, pc.w, pc.h), [1, 3, 224, 224])));
    }
    // ---- CLOSE-UP (J8): tap the primary object's centre, one high-res still
    let cu: any = null; let j7: any = null; let bgr: any = null;
    if (prim) {
      const fb = bufferBoxToFrame(prim.box, it.lw, it.lh, it.w, it.h); const v = stillBoxToView(fb, [it.w, it.h], view);
      const tap: [number, number] = [v.left + v.width / 2, v.top + v.height / 2];
      const o = await runCloseupFromTrack({ rgb: still, w: it.w, h: it.h }, tap, view, trackWide(primTrack!.obs), infer);
      cu = { title: o.display.title, verify: o.verify, closeup: o.closeup, hints: guidanceHints({ sidePx: boxSide(fb), closeupCropSidePx: o.closeup?.cropSidePx }) };
      const d7 = await runDebugPipeline([{ rgb: still, w: it.w, h: it.h }, { rgb: still, w: it.w, h: it.h }, { rgb: still, w: it.w, h: it.h }], tap, view, infer);
      j7 = { title: d7.display.title, wide: d7.wide, verify: d7.verify };
      if (o.plan) {   // report-only colour-order check: H2 on the same crop with R/B swapped
        const cr = cropRgb(still, it.w, it.h, o.plan.crop); const sw = new Uint8Array(cr.rgb.length);
        for (let i = 0; i < sw.length; i += 3) { sw[i] = cr.rgb[i + 2]; sw[i + 1] = cr.rgb[i + 1]; sw[i + 2] = cr.rgb[i]; }
        bgr = h2Top3(asProbs(await infer('h2', h2Input(sw, cr.w, cr.h), [1, 3, 224, 224])))[0];
      }
      hints = guidanceHints({ sidePx: q!.sidePx, blurVar: q!.blurVar, meanV: q!.meanV, touchesEdge: q!.touchesEdge });
    }
    const rec = prim ? diagRecord({ path: 'live', tMs: 400, trackId: prim.id, g3: { classId: primTrack!.obs[primTrack!.obs.length - 1]!.classId, score: primTrack!.obs[primTrack!.obs.length - 1]!.score },
      competing: prim.competing, wide: primTrack!.wide, h2Top3: cu?.closeup?.h2Top3 ?? null, verify: cu?.verify ?? null, box: prim.box, frame: [it.lw, it.lh], quality: q, hints, shownLabel: prim.label }) : null;
    rows.push({ key: it.key, id: it.id, n: it.n, variant: it.variant, synthetic: it.synthetic, label: it.label, attr: it.attr, truth_set: it.truth_set,
      n_raw: raw.length, n_objects: objs.length, live_labels: views.filter((v) => v.label).map((v) => v.label), live_primary: prim ? { label: prim.label, state: prim.state, reason: prim.reason, side_src_px: Math.round(boxSide(prim.box) * it.w / it.lw), competing: prim.competing.map((c) => labelOf(c.classId)) } : null,
      j7_overlay_names_on_primary: j7NamesOnPrimary.map(labelOf), live_preview_h2_top1: liveH2?.[0] ?? null, closeup: cu, j7_tap: j7, bgr_swap_top1: bgr, diag: rec });
    process.stdout.write('.');
  }
  writeFileSync(OUT, JSON.stringify(rows));
  console.log('\nwrote', rows.length, OUT);
}
function boxIou(a: Box, b: Box) { const ix = Math.max(0, Math.min(a[2], b[2]) - Math.max(a[0], b[0])); const iy = Math.max(0, Math.min(a[3], b[3]) - Math.max(a[1], b[1])); const i = ix * iy; const u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i; return u > 0 ? i / u : 0; }
main().catch((e) => { console.error(e); process.exit(1); });
