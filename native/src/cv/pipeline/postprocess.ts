// Decode detector outputs into model-input-pixel boxes.
//  - YOLO26 end-to-end (NMS-free) export: output (1, 300, 6) = x1, y1, x2, y2, score, classId.
//  - YOLO11 raw export: output (1, 4 + nc, N) = cx, cy, w, h, per-class scores; needs NMS.
import { iou, type Box } from './preprocess.ts';
import type { Detection } from './tracker.ts';

export function decodeEndToEnd(out: Float32Array, maxDet: number, scoreThr: number): Detection[] {
  const dets: Detection[] = [];
  for (let i = 0; i < maxDet; i++) {
    const o = i * 6;
    const score = out[o + 4];
    if (score < scoreThr) continue;
    dets.push({ box: [out[o], out[o + 1], out[o + 2], out[o + 3]], score, classId: Math.round(out[o + 5]) });
  }
  return dets.sort((a, b) => b.score - a.score);
}

export function decodeRawWithNms(out: Float32Array, nc: number, n: number, scoreThr: number, iouThr = 0.7, maxDet = 300): Detection[] {
  const cands: Detection[] = [];
  for (let j = 0; j < n; j++) {
    let best = -1;
    let bestS = scoreThr;
    for (let c = 0; c < nc; c++) {
      const s = out[(4 + c) * n + j];
      if (s > bestS) { bestS = s; best = c; }
    }
    if (best < 0) continue;
    const cx = out[j], cy = out[n + j], w = out[2 * n + j], h = out[3 * n + j];
    cands.push({ box: [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2] as Box, score: bestS, classId: best });
  }
  return nms(cands, iouThr, maxDet);
}

/** Class-wise greedy NMS (same as torchvision batched_nms ordering by score). */
export function nms(dets: Detection[], iouThr: number, maxDet = 300): Detection[] {
  const sorted = [...dets].sort((a, b) => b.score - a.score);
  const keep: Detection[] = [];
  for (const d of sorted) {
    if (keep.length >= maxDet) break;
    if (keep.some((k) => k.classId === d.classId && iou(k.box, d.box) > iouThr)) continue;
    keep.push(d);
  }
  return keep;
}
