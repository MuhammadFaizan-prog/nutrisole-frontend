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

// G3 app-side detection guard. EXACT mirror of ml/eval/scene_guard.py (parity: tests/cvSceneGuard.test.ts).
// Applied per frame after decode + score threshold + mapping to normalised frame coords, before the tracker:
//  1. drop boxes smaller than minAreaFrac of the frame;
//  2. the app grades ONE item: more than maxSameClass boxes of one class = a scene/pile/texture
//     (stadium seats -> 'tomato' x30), so every box of that class is dropped for this frame (<= 0 disables).
export type SceneGuardParams = { maxSameClass: number; minAreaFrac: number };
export const DEFAULT_SCENE_GUARD: SceneGuardParams = { maxSameClass: 0, minAreaFrac: 0.01 }; // G4: rule 2 off (0) after the deterministic TEST replay; see ml/eval/scene_guard.py

export function sceneGuard(dets: Detection[], params: Partial<SceneGuardParams> = {}): Detection[] {
  const P = { ...DEFAULT_SCENE_GUARD, ...params };
  const keep = dets.filter((d) => (d.box[2] - d.box[0]) * (d.box[3] - d.box[1]) >= P.minAreaFrac);
  if (P.maxSameClass <= 0) return keep;
  const n = new Map<number, number>();
  for (const d of keep) n.set(d.classId, (n.get(d.classId) ?? 0) + 1);
  return keep.filter((d) => (n.get(d.classId) ?? 0) <= P.maxSameClass);
}

/** False-alarm episodes: runs of frames with >= 1 displayed box; runs separated by <= mergeGapS are merged. */
export function faEpisodes(shownFlags: boolean[], fps: number, mergeGapS = 0.5): number {
  let eps = 0;
  let lastOn: number | null = null;
  const gap = Math.round(mergeGapS * fps);
  shownFlags.forEach((on, i) => {
    if (!on) return;
    if (lastOn === null || i - lastOn > gap + 1) eps += 1;
    lastOn = i;
  });
  return eps;
}

// G7.4 citrus-family ambiguity ("citrus (lemon/orange?)"). EXACT mirror of ml/eval/citrus_ambiguity.py `mark`
// (parity: tests/cvCitrus.test.ts replays ml/eval/fixtures/citrus_parity.json). Behind config, DEFAULT OFF.
// A kept box whose top class is citrus or lemon_lime is ambiguous when the OTHER family class's score at the SAME
// anchor is >= ratio * top score. The box keeps its classId (tracking/grading unchanged); only the label text changes.
export type CitrusAmbiguityParams = { enabled: boolean; ratio: number; citrusId: number; lemonId: number };
export const DEFAULT_CITRUS_AMBIGUITY: CitrusAmbiguityParams = { enabled: false, ratio: 0.5, citrusId: 3, lemonId: 6 };
export type AmbiguousDetection = Detection & { citrusAmbiguous?: boolean };

export function isCitrusAmbiguous(topClass: number, scores: ArrayLike<number>, params: Partial<CitrusAmbiguityParams> = {}): boolean {
  const P = { ...DEFAULT_CITRUS_AMBIGUITY, ...params };
  if (topClass !== P.citrusId && topClass !== P.lemonId) return false;
  const other = topClass === P.citrusId ? P.lemonId : P.citrusId;
  return scores[other] >= P.ratio * scores[topClass];
}

/** decodeRawWithNms + citrus ambiguity flag. With enabled=false the boxes are identical to decodeRawWithNms. */
export function decodeRawWithNmsCitrus(out: Float32Array, nc: number, n: number, scoreThr: number, params: Partial<CitrusAmbiguityParams> = {},
  iouThr = 0.7, maxDet = 300): AmbiguousDetection[] {
  const P = { ...DEFAULT_CITRUS_AMBIGUITY, ...params };
  const cands: Array<AmbiguousDetection & { anchor: number }> = [];
  for (let j = 0; j < n; j++) {
    let best = -1;
    let bestS = scoreThr;
    for (let c = 0; c < nc; c++) {
      const s = out[(4 + c) * n + j];
      if (s > bestS) { bestS = s; best = c; }
    }
    if (best < 0) continue;
    const cx = out[j], cy = out[n + j], w = out[2 * n + j], h = out[3 * n + j];
    cands.push({ box: [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2] as Box, score: bestS, classId: best, anchor: j });
  }
  return (nms(cands, iouThr, maxDet) as Array<AmbiguousDetection & { anchor: number }>).map(({ anchor, ...d }) => {
    if (!P.enabled) return d;
    const scores = Array.from({ length: nc }, (_, c) => out[(4 + c) * n + anchor]);
    return isCitrusAmbiguous(d.classId, scores, P) ? { ...d, citrusAmbiguous: true } : d;
  });
}

/** Display text for a (possibly ambiguous) citrus-family label. */
export function citrusDisplayLabel(baseLabel: string, ambiguous: boolean | undefined): string {
  return ambiguous ? 'citrus (lemon/orange?)' : baseLabel;
}
