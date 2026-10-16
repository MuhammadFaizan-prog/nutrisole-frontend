// G9 Stage G close-up path. EXACT mirror of ml/eval/closeup.py
// (parity: native/tests/cvCloseup.test.ts replays ml/eval/fixtures/closeup_parity.json).
// Flow: wide scan (G3 480, unchanged) -> identification policy (else "Unable to identify") -> user taps an item (ROI) ->
// move-closer gate on FULL-RESOLUTION frame pixels (never the 480 input) -> quality checks -> condition / ripeness / rules on
// the full-res crop -> N consistent assessments -> grade, else "Not graded" with reasons. Confidence alone never grades.
// Pure TypeScript: no React Native imports, runs under node --test and inside a VisionCamera worklet.
import type { Box } from './preprocess.ts';

export const DETECTOR_INPUT = 480;
/** The full-res crop is analysed at <= 256 px side (area resample); the gate size stays in native frame pixels. */
export const ANALYSIS_MAX_SIDE = 256;
export type IdParams = { idMinScore: number; idMinHits: number };
export const DEFAULT_ID: IdParams = { idMinScore: 0.5, idMinHits: 3 };
export type GateParams = {
  minSidePx: number; minFrames: number; mode: 'count' | 'score'; scoreTol: number; minBlurVar: number; minMeanV: number; maxMeanV: number;
  edgeMarginFrac: number; minVisibleFrac: number; minMaxProb: number; minMargin: number; maxBlockiness: number;
};
// Candidate values from the Stage F proposal. FROZEN_GATE (below) holds the Stage G pick; see docs/cv/gauntlet/G9_stageG.md.
export const DEFAULT_GATE: GateParams = {
  minSidePx: 96, minFrames: 3, mode: 'count', scoreTol: 0.15, minBlurVar: 15.0, minMeanV: 40.0, maxMeanV: 245.0,
  edgeMarginFrac: 0.01, minVisibleFrac: 0.25, minMaxProb: 0.7, minMargin: 0.3, maxBlockiness: 1.5,
};
// Stage G frozen pick (CU-tune, DEV only): 96 px full-res, 3 agreeing assessments, minMeanV 80, maxBlockiness 1.4.
export const FROZEN_GATE: GateParams = { ...DEFAULT_GATE, minMeanV: 80.0, maxBlockiness: 1.4 };

const pyRound = (v: number): number => {
  // Python round(): banker's rounding on exact .5
  const f = Math.floor(v); const d = v - f;
  if (Math.abs(d - 0.5) < 1e-12) return f % 2 === 0 ? f : f + 1;
  return Math.round(v);
};

export type Letterbox = { sx: number; sy: number; px: number; py: number; w: number; h: number };
export function letterboxTransform(srcW: number, srcH: number, dst = DETECTOR_INPUT): Letterbox {
  const s = Math.min(dst / srcW, dst / srcH); const nw = pyRound(srcW * s); const nh = pyRound(srcH * s);
  return { sx: nw / srcW, sy: nh / srcH, px: pyRound((dst - nw) / 2 - 0.1), py: pyRound((dst - nh) / 2 - 0.1), w: srcW, h: srcH };
}

/** 480-letterbox detector box -> full-resolution frame pixels (clipped). */
export function detectorToFrame(box: Box, frameW: number, frameH: number, dst = DETECTOR_INPUT): Box {
  const t = letterboxTransform(frameW, frameH, dst);
  const c = (v: number, hi: number) => Math.min(hi, Math.max(0, v));
  return [c((box[0] - t.px) / t.sx, frameW), c((box[1] - t.py) / t.sy, frameH), c((box[2] - t.px) / t.sx, frameW), c((box[3] - t.py) / t.sy, frameH)];
}

export type CropRect = { x: number; y: number; w: number; h: number; sidePx: number };
/** Integer crop on the full-res frame (box padded by pad*side), clamped. sidePx = sqrt(area) of the UNPADDED box. */
export function cropRect(box: Box, frameW: number, frameH: number, pad = 0.08): CropRect {
  const w = box[2] - box[0]; const h = box[3] - box[1]; const px = pad * w; const py = pad * h;
  const x1 = Math.max(0, Math.floor(box[0] - px)); const y1 = Math.max(0, Math.floor(box[1] - py));
  const x2 = Math.min(frameW, Math.ceil(box[2] + px)); const y2 = Math.min(frameH, Math.ceil(box[3] + py));
  return { x: x1, y: y1, w: Math.max(0, x2 - x1), h: Math.max(0, y2 - y1), sidePx: Math.round(Math.sqrt(Math.max(0, w) * Math.max(0, h)) * 100) / 100 };
}

export function touchesEdge(box: Box, frameW: number, frameH: number, marginFrac: number): boolean {
  const mx = marginFrac * frameW; const my = marginFrac * frameH;
  return box[0] <= mx || box[1] <= my || box[2] >= frameW - mx || box[3] >= frameH - my;
}

export type Roi = { source: 'track' | 'tap_roi'; box: Box };
/** Tap (normalised) -> ROI: the smallest tracked box containing the tap, else a square user ROI (roiFrac * min side) centred on
 *  the tap and clamped inside the frame (fallback when tracking is fragmented). */
export function roiFromTap(tap: [number, number], frameW: number, frameH: number, frameBoxes: Box[], roiFrac = 0.35): Roi {
  const x = tap[0] * frameW; const y = tap[1] * frameH;
  const hits = frameBoxes.filter((b) => b[0] <= x && x <= b[2] && b[1] <= y && y <= b[3]);
  if (hits.length) {
    let best = hits[0];
    for (const b of hits) if ((b[2] - b[0]) * (b[3] - b[1]) < (best[2] - best[0]) * (best[3] - best[1])) best = b;
    return { source: 'track', box: [...best] as Box };
  }
  const s = roiFrac * Math.min(frameW, frameH);
  const x1 = Math.min(Math.max(0, x - s / 2), frameW - s); const y1 = Math.min(Math.max(0, y - s / 2), frameH - s);
  return { source: 'tap_roi', box: [x1, y1, x1 + s, y1 + s] };
}

export type IdResult = { status: 'identified'; classId: number } | { status: 'unable' | 'pending'; reason: string };
/** Name (and price) only under this policy; otherwise the UI says "Unable to identify". Never a forced label. */
export function idPolicy(label: number, score: number, hits: number, citrusAmbiguous = false, p: Partial<IdParams> = {}): IdResult {
  const P = { ...DEFAULT_ID, ...p };
  if (citrusAmbiguous) return { status: 'unable', reason: 'citrus family ambiguous' };
  if (hits < P.idMinHits) return { status: 'pending', reason: 'confirming' };
  if (score < P.idMinScore) return { status: 'unable', reason: 'low confidence' };
  return { status: 'identified', classId: label };
}

export type QualityInputs = { sidePx: number; blurVar: number; meanV: number; touchesEdge: boolean; visibleFrac: number; maxProb: number; margin: number; blockiness?: number };
/** 'Not graded' reasons (empty = OK). */
export function qualityReasons(q: QualityInputs, p: Partial<GateParams> = {}): string[] {
  const P = { ...DEFAULT_GATE, ...p }; const r: string[] = [];
  if (q.sidePx < P.minSidePx) r.push('too_small: move closer');
  if (q.touchesEdge) r.push('truncated: keep the whole item in view');
  if (q.meanV < P.minMeanV) r.push('too_dark');
  if (q.meanV > P.maxMeanV) r.push('overexposed');
  if (q.blurVar < P.minBlurVar) r.push('blurry');
  if (q.visibleFrac < P.minVisibleFrac) r.push('occluded_or_little_surface');
  if (q.blockiness !== undefined && q.blockiness > P.maxBlockiness) r.push('compression_artifacts');
  if (q.maxProb < P.minMaxProb || q.margin < P.minMargin) r.push('model_uncertain');
  return r;
}

export type Assessment = { ok: boolean; grade: string; pFresh: number; reasons: string[] };
export type GateDecision =
  | { status: 'graded'; grade: string }
  | { status: 'pending'; reasons: string[]; have: number; need: number }
  | { status: 'not_graded'; reasons: string[] };

/** Consecutive-assessment gate (count mode or quality-score stability mode). A failed assessment or a disagreement resets. */
export class GradeGate {
  P: GateParams; hist: Assessment[] = [];
  constructor(p: Partial<GateParams> = {}) { this.P = { ...DEFAULT_GATE, ...p }; }
  reset(): void { this.hist = []; }
  push(a: Assessment): GateDecision {
    const P = this.P;
    if (!a.ok) { this.hist = []; return { status: 'not_graded', reasons: [...a.reasons] }; }
    if (this.hist.length && this.hist[this.hist.length - 1].grade !== a.grade) {
      this.hist = [a]; return { status: 'pending', reasons: ['assessments_disagree'], have: 1, need: P.minFrames };
    }
    this.hist.push(a); this.hist = this.hist.slice(-P.minFrames);
    if (this.hist.length < P.minFrames) return { status: 'pending', reasons: ['confirming'], have: this.hist.length, need: P.minFrames };
    if (P.mode === 'score') {
      const fs = this.hist.map((h) => h.pFresh);
      if (Math.max(...fs) - Math.min(...fs) > P.scoreTol) return { status: 'pending', reasons: ['quality_score_unstable'], have: this.hist.length, need: P.minFrames };
    }
    return { status: 'graded', grade: a.grade };
  }
}

/** UI text for a gate decision (English; Urdu strings live with the other UI copy). */
export function gateMessage(d: GateDecision): string {
  if (d.status === 'graded') return `Visual grade ${d.grade} (appearance only)`;
  if (d.status === 'pending') return d.reasons[0] === 'confirming' ? 'Hold steady…' : 'Checking again…';
  if (d.reasons.some((r) => r.startsWith('too_small'))) return 'Move closer to check quality';
  return 'Could not be graded reliably';
}

/** Phase-invariant 8x8 blocking measure on a grayscale crop (row-major, w x h): max / median of the mean |gradient| per position
 *  mod 8, horizontal and vertical (1.0 = none). Mirrors closeup.py blockiness. */
export function blockiness(gray: ArrayLike<number>, w: number, h: number): number {
  if (Math.min(w, h) < 24) return 1;
  const dx = new Float64Array(w - 1); const dy = new Float64Array(h - 1);
  for (let y = 0; y < h; y++) for (let x = 0; x < w - 1; x++) dx[x] += Math.abs(gray[y * w + x + 1] - gray[y * w + x]) / h;
  for (let y = 0; y < h - 1; y++) for (let x = 0; x < w; x++) dy[y] += Math.abs(gray[(y + 1) * w + x] - gray[y * w + x]) / w;
  const prof = (d: Float64Array) => Array.from({ length: 8 }, (_, i) => { let s = 0; let n = 0; for (let j = i; j < d.length; j += 8) { s += d[j]; n++; } return s / n; });
  const med = (a: number[]) => { const b = [...a].sort((p, q) => p - q); return (b[3] + b[4]) / 2; };
  const px = prof(dx); const py = prof(dy);
  const v = Math.max(Math.max(...px) / Math.max(med(px), 1e-6), Math.max(...py) / Math.max(med(py), 1e-6));
  return Math.round(v * 10000) / 10000;
}

/** Map one close-up result onto the existing CvAssessment contract (contracts.ts), the only CV API/DB interface in the repo.
 *  Not graded -> visualGrade 'ungradable' with the gate reasons as imageQuality.reasons; no price ever enters the assessment. */
export function toCvAssessment(inp: {
  assessmentId: string; frameTimestampMs: number; modelVersion: string; rubricVersion: string; frameW: number; frameH: number;
  box: Box; trackingId?: string; id: IdResult; classIds: readonly string[]; labels: readonly string[]; decision: GateDecision;
  freshness?: { level: 'fresh' | 'rotten'; confidence?: number }; blurVar?: number;
}) {
  const [x1, y1, x2, y2] = inp.box;
  const c = (v: number) => Math.min(1, Math.max(0, v));
  const bboxNormalized: [number, number, number, number] = [c(x1 / inp.frameW), c(y1 / inp.frameH), c(x2 / inp.frameW), c(y2 / inp.frameH)];
  if (inp.id.status !== 'identified') {
    return { assessmentId: inp.assessmentId, frameTimestampMs: inp.frameTimestampMs, modelVersion: inp.modelVersion, rubricVersion: inp.rubricVersion,
      status: 'unsupported' as const, objects: [], limitations: ['Unable to identify'] };
  }
  const graded = inp.decision.status === 'graded';
  const reasons: string[] = inp.decision.status === 'graded' ? [] : inp.decision.reasons;
  const tooSmall = reasons.some((r) => r.startsWith('too_small'));
  return {
    assessmentId: inp.assessmentId, frameTimestampMs: inp.frameTimestampMs, modelVersion: inp.modelVersion, rubricVersion: inp.rubricVersion,
    status: graded ? ('supported' as const) : tooSmall ? ('uncertain' as const) : ('poor_capture' as const),
    imageQuality: { ...(inp.blurVar !== undefined ? { blur: inp.blurVar } : {}), reasons },
    objects: [{
      ...(inp.trackingId ? { trackingId: inp.trackingId } : {}), bboxNormalized,
      produce: { classId: inp.classIds[inp.id.classId], label: inp.labels[inp.id.classId] },
      visualGrade: graded
        ? { grade: (inp.decision as { grade: string }).grade as 'A' | 'B' | 'C' | 'Reject', reasons: ['Consistent over 3 close-up assessments (appearance only)'] }
        : { grade: 'ungradable' as const, reasons: [tooSmall ? 'Move closer to check quality' : 'Could not be graded reliably'] },
    }],
    limitations: ['Visual appearance only; agent-verified evaluation labels; not a certified grade'],
  };
}
