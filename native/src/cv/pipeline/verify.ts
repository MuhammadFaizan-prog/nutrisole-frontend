// G9 Stage H close-up identity verification, occlusion check and Stage H close-up decision.
// EXACT mirror of ml/eval/verify.py + ml/eval/occlusion.py (occlusion_reasons); parity: native/tests/cvVerify.test.ts replays
// ml/eval/fixtures/verify_parity.json.
// Order: wide G3 identification -> tap -> INDEPENDENT identity verification on the full-res crop (H2 close-up classifier with an explicit
// `unknown` output; optional H1 veto = G3 re-run on the crop) -> occlusion / visibility check -> Stage G gate (closeup.ts) -> grader.
// Uncertain or contradictory identity -> "Unable to identify"; it is never passed to the grader. The user-assisted fallback unlocks the
// category reference price only (never a grade) and is not counted as identity accuracy. In Stage H no A/B/C grade is displayed.
import type { IdResult } from './closeup.ts';

export const H2_CLASSES = ['banana', 'apple', 'mango', 'citrus', 'guava', 'pomegranate', 'lemon_lime', 'tomato', 'potato', 'cucumber', 'carrot', 'capsicum', 'unknown'] as const;
export const UNKNOWN = 12;
export const H2_INPUT = { side: 224, resizeShort: 256, mean: [0.485, 0.456, 0.406], std: [0.229, 0.224, 0.225], layout: 'NCHW RGB float32' } as const;

export type VerifyPolicy = 'H0' | 'P-a' | 'P-b' | 'P-c' | 'H2-only';
export type VerifyParams = { policy: VerifyPolicy; tau: number; margin: number; maxUnknown: number; h1VetoScore: number; suggestMinP: number };
export const DEFAULT_VERIFY: VerifyParams = { policy: 'P-a', tau: 0.6, margin: 0.2, maxUnknown: 0.3, h1VetoScore: 0.5, suggestMinP: 0.15 };
// Stage H frozen pick (tune splits only; docs/cv/gauntlet/G9_stageH.md). Kept equal to ml/eval/verify.py FROZEN_VERIFY.
export const FROZEN_VERIFY: VerifyParams = { ...DEFAULT_VERIFY };

export type H2Decision = { accept: true; classId: number; p: number; suggestions: number[] } | { accept: false; reason: string; top: number; suggestions: number[] };

const r6 = (v: number) => Math.round(v * 1e6) / 1e6;

export function h2Decision(probs: readonly number[], p: Partial<VerifyParams> = {}): H2Decision {
  const P = { ...DEFAULT_VERIFY, ...p };
  const order = Array.from({ length: UNKNOWN }, (_, i) => i).sort((a, b) => probs[b] - probs[a] || a - b);
  const top = order[0]; const second = order[1]; const pu = probs[UNKNOWN]; const pt = probs[top]; const ps = probs[second];
  const suggestions = order.slice(0, 2).filter((i) => probs[i] >= P.suggestMinP);
  if (pu >= P.maxUnknown || pu > pt) return { accept: false, reason: 'close_up_unknown', top, suggestions };
  if (pt < P.tau) return { accept: false, reason: 'close_up_uncertain', top, suggestions };
  if (pt - ps < P.margin) return { accept: false, reason: 'close_up_ambiguous', top, suggestions };
  return { accept: true, classId: top, p: r6(pt), suggestions };
}

export type H1Result = { classId: number; score: number; hasWide?: boolean } | null;
export type VerifyResult =
  | { status: 'verified'; classId: number; evidence: string }
  | { status: 'user_confirmed'; classId: number; evidence: 'user' }
  | { status: 'unable'; reason: string; suggestions: number[] };

const CITRUS = [3, 6];

export function verifyIdentity(wide: IdResult, h1: H1Result, h2Probs: readonly number[], p: Partial<VerifyParams> = {}): VerifyResult {
  const P = { ...DEFAULT_VERIFY, ...p };
  if (P.policy === 'H0') {
    return wide.status === 'identified' ? { status: 'verified', classId: wide.classId, evidence: 'wide_only' } : { status: 'unable', reason: 'not_identified_wide', suggestions: [] };
  }
  const d = h2Decision(h2Probs, P);
  if (P.policy === 'P-c') {
    if (wide.status !== 'identified') return { status: 'unable', reason: 'not_identified_wide', suggestions: d.suggestions };
    if (h1 && h1.classId === wide.classId && h1.score >= P.h1VetoScore) return { status: 'verified', classId: wide.classId, evidence: 'wide+h1' };
    return { status: 'unable', reason: 'h1_not_confirmed', suggestions: d.suggestions };
  }
  if (P.policy === 'H2-only') {
    return d.accept ? { status: 'verified', classId: d.classId, evidence: 'h2' } : { status: 'unable', reason: d.reason, suggestions: d.suggestions };
  }
  if (wide.status !== 'identified') return { status: 'unable', reason: 'not_identified_wide', suggestions: d.suggestions };
  if (!d.accept) return { status: 'unable', reason: d.reason, suggestions: d.suggestions };
  if (d.classId !== wide.classId) {
    const citrus = CITRUS.includes(d.classId) && CITRUS.includes(wide.classId);
    return { status: 'unable', reason: citrus ? 'citrus_family_contradiction' : 'close_up_contradicts_wide', suggestions: [wide.classId, d.classId] };
  }
  if (P.policy === 'P-b' && h1 && h1.classId !== wide.classId && h1.score >= P.h1VetoScore && !(h1.hasWide ?? false)) {
    return { status: 'unable', reason: 'h1_contradicts', suggestions: [wide.classId, h1.classId] };
  }
  return { status: 'verified', classId: wide.classId, evidence: P.policy === 'P-b' ? 'wide+h2+h1' : 'wide+h2' };
}

/** User-assisted fallback: chosen = a class id the user picked from the suggestions, or null for "something else". */
export function userConfirm(v: VerifyResult, chosen: number | null): VerifyResult {
  if (v.status === 'verified' || v.status === 'user_confirmed') return v;
  if (chosen === null || chosen === UNKNOWN || !v.suggestions.includes(chosen)) return { status: 'unable', reason: 'user_declined', suggestions: [] };
  return { status: 'user_confirmed', classId: chosen, evidence: 'user' };
}

/** Fraction of half-crops (left/right/top/bottom) whose H2 top class is classId with p >= minP (unknown never agrees). */
export function partAgreement(halfProbs: readonly (readonly number[])[], classId: number, minP = 0.3): number {
  if (!halfProbs.length) return 1;
  let ok = 0;
  for (const pr of halfProbs) {
    let top = 0;
    for (let i = 1; i < pr.length; i++) if (pr[i] > pr[top]) top = i;
    if (top === classId && pr[top] >= minP) ok++;
  }
  return r6(ok / halfProbs.length);
}

export type OcclusionCues = { solidity: number; ellipseIoU: number; straightFrac: number; borderFrac: number; segAgree: number; flatFrac: number; colourSplit: number; partAgree?: number };
export type OcclusionParams = { minSolidity: number; minEllipseIoU: number; maxStraightFrac: number; maxBorderFrac: number; minSegAgree: number; maxFlatFrac: number; maxColourSplit: number; minPartAgree: number };
export const DEFAULT_OCC: OcclusionParams = { minSolidity: 0, minEllipseIoU: 0, maxStraightFrac: 1, maxBorderFrac: 1, minSegAgree: 0, maxFlatFrac: 1, maxColourSplit: 1e9, minPartAgree: 0 };
// Stage H frozen pick (CU-tune occluder suite). Kept equal to ml/eval/occlusion.py FROZEN_OCC.
export const FROZEN_OCC: OcclusionParams = { ...DEFAULT_OCC };

export function occlusionReasons(c: OcclusionCues, p: Partial<OcclusionParams> = {}): string[] {
  const P = { ...DEFAULT_OCC, ...p }; const r: string[] = [];
  if (c.solidity < P.minSolidity || c.ellipseIoU < P.minEllipseIoU) r.push('outline_incomplete');
  if (c.straightFrac > P.maxStraightFrac) r.push('straight_occluder_edge');
  if (c.borderFrac > P.maxBorderFrac) r.push('partial_object');
  if (c.segAgree < P.minSegAgree) r.push('foreground_inconsistent');
  if (c.flatFrac > P.maxFlatFrac) r.push('flat_foreign_region');
  if (c.colourSplit > P.maxColourSplit) r.push('mixed_materials');
  if (c.partAgree !== undefined && c.partAgree < P.minPartAgree) r.push('parts_disagree');
  return r;
}

/** Mask-geometry cues that need no OpenCV: solidity needs a hull, so the native side supplies area + hull area; this keeps the rule testable. */
export function solidityFrom(maskArea: number, hullArea: number): number { return hullArea > 0 ? r6(maskArea / hullArea) : 0; }

export type StageHOutcome = {
  outcome: 'unable_to_identify' | 'category_confirmed_by_user' | 'not_graded' | 'quality_check_unavailable' | 'graded';
  identity: { classId: number; source: 'verified' | 'user_confirmed' } | null;
  gradeShown: null | 'internal_only'; priceKind: 'category_reference' | null; reasons: string[];
};

/** Final close-up outcome. gradeDisplayEnabled is false in Stage H: a passing gate yields 'quality_check_unavailable', never an A/B/C. */
export function stageHDecision(v: VerifyResult, occReasons: string[], gateStatus: string, gateReasons: string[], gradeDisplayEnabled = false): StageHOutcome {
  if (v.status === 'unable') return { outcome: 'unable_to_identify', identity: null, gradeShown: null, priceKind: null, reasons: [v.reason] };
  const identity = { classId: v.classId, source: v.status };
  if (v.status === 'user_confirmed') return { outcome: 'category_confirmed_by_user', identity, gradeShown: null, priceKind: 'category_reference', reasons: ['user_confirmed_category'] };
  if (occReasons.length) return { outcome: 'not_graded', identity, gradeShown: null, priceKind: 'category_reference', reasons: [...occReasons] };
  if (gateStatus !== 'graded') return { outcome: 'not_graded', identity, gradeShown: null, priceKind: 'category_reference', reasons: [...gateReasons] };
  if (!gradeDisplayEnabled) return { outcome: 'quality_check_unavailable', identity, gradeShown: null, priceKind: 'category_reference', reasons: ['grades_not_enabled'] };
  return { outcome: 'graded', identity, gradeShown: 'internal_only', priceKind: 'category_reference', reasons: [] };
}

export function stageHMessage(o: StageHOutcome, label?: string): string {
  switch (o.outcome) {
    case 'unable_to_identify': return 'Unable to identify';
    case 'category_confirmed_by_user': return `${label ?? 'Item'} (confirmed by you). Quality not checked`;
    case 'not_graded': return `${label ?? 'Item'}. Not graded: ${o.reasons[0]?.replace(/_/g, ' ') ?? 'could not check quality'}`;
    case 'quality_check_unavailable': return `${label ?? 'Item'}. Quality grading is not available yet`;
    default: return `${label ?? 'Item'}`;
  }
}
