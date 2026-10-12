// Rule table: calibrated quality probabilities + measurements -> visual grade.
// Port of ml/grading/rules.py; thresholds must equal ml/grading/rubric_v0.json and the
// band roles must equal ml/grading/colour_bands.json (asserted in native/tests/cvRules.test.ts,
// which also replays ml/grading/golden_rules.json). Visible condition only (rule 8.4).

import type { CvStatus, VisualGradeValue } from '../contracts.ts';

export const RUBRIC = {
  rubricVersion: 'rubric-v0.1-g1',
  detectorMinScore: 0.35,
  qualityMinMaxProb: 0.5,
  minMaskFraction: 0.08,
  minBlurVar: 15.0,
  minMeanV: 40.0,
  maxMeanV: 245.0,
  reject: { pRotten: 0.5, defectPct: 25.0 },
  c: { pMild: 0.4, defectPct: 10.0, overripeBandPct: 30.0 },
  b: { defectPct: 2.0, unripeBandPct: 40.0, shapeScore: 0.85 },
  a: { pFresh: 0.7, targetBandPct: 50.0 },
} as const;

export type BandRole = 'target' | 'unripe' | 'overripe';
export const BAND_ROLES: Record<string, Record<string, BandRole>> = {
  banana: { green: 'unripe', yellow: 'target', brown: 'overripe' },
  apple: { red: 'target', green_yellow: 'target', brown: 'overripe' },
  citrus: { orange: 'target', green: 'unripe', brown: 'overripe' },
  guava: { green: 'target', yellow: 'target', brown: 'overripe' },
  pomegranate: { red: 'target', brown: 'overripe' },
  tomato: { red: 'target', orange: 'unripe', green: 'unripe' },
  mango: { green: 'target', yellow_orange: 'target', brown: 'overripe' },
  lemon_lime: { yellow: 'target', green: 'target', brown: 'overripe' },
};

export type QualityProbs = { fresh: number; rotten: number; mild?: number };
export type Measurements = {
  mask_fraction: number; colour_bands: Record<string, number>; defect_area_pct: number;
  shape_score: number; blur_var: number; mean_v: number;
};
export type GradeResult = { grade: VisualGradeValue; status: CvStatus; reasons: string[]; numbers: Record<string, unknown> };

export function bandRoles(produce: string, bands: Record<string, number> | undefined) {
  const table = BAND_ROLES[produce] ?? {};
  const out = { target: 0, unripe: 0, overripe: 0 };
  for (const [name, pct] of Object.entries(bands ?? {})) {
    const role = table[name];
    if (role) out[role] += pct;
  }
  return out;
}

const pct = (p: number) => Math.round(100 * p);

export function grade(produce: string, detScore: number, probs: QualityProbs | null, m: Measurements | null): GradeResult {
  const R = RUBRIC;
  if (detScore < R.detectorMinScore) return { grade: 'ungradable', status: 'unsupported', reasons: ['Point the camera at one fruit or vegetable'], numbers: { detScore } };
  if (m) {
    if (m.mean_v < R.minMeanV) return { grade: 'ungradable', status: 'poor_capture', reasons: ['Too dark: try better light'], numbers: { meanV: m.mean_v } };
    if (m.mean_v > R.maxMeanV) return { grade: 'ungradable', status: 'poor_capture', reasons: ['Overexposed: avoid direct glare'], numbers: { meanV: m.mean_v } };
    if (m.blur_var < R.minBlurVar) return { grade: 'ungradable', status: 'poor_capture', reasons: ['Image is blurry: hold the phone steady'], numbers: { blurVar: m.blur_var } };
    if (m.mask_fraction < R.minMaskFraction) return { grade: 'ungradable', status: 'poor_capture', reasons: ['Cannot assess this view: item too small or obstructed'], numbers: { maskFraction: m.mask_fraction } };
  }
  const maxP = probs ? Math.max(...Object.values(probs).filter((v): v is number => typeof v === 'number')) : null;
  if (!probs || maxP === null || maxP < R.qualityMinMaxProb) return { grade: 'ungradable', status: 'uncertain', reasons: ['Not sure, try better light'], numbers: { maxProb: maxP } };

  const pF = probs.fresh ?? 0;
  const pR = probs.rotten ?? 0;
  const pM = probs.mild;
  const defect = m ? m.defect_area_pct : null;
  const shape = m ? m.shape_score : null;
  const roles = m ? bandRoles(produce, m.colour_bands) : null;
  const hasTable = produce in BAND_ROLES;
  const numbers = { pFresh: pF, pRotten: pR, pMild: pM ?? null, defectPct: defect, shapeScore: shape, bandRoles: roles };
  const out = (g: VisualGradeValue, reasons: string[]): GradeResult => ({ grade: g, status: 'supported', reasons: reasons.slice(0, 2), numbers });

  let rs: string[] = [];
  if (pR >= R.reject.pRotten) rs.push(`Visible rot likely (${pct(pR)}%)`);
  if (defect !== null && defect >= R.reject.defectPct) rs.push(`Dark marks ~${Math.round(defect)}% of visible surface`);
  if (rs.length) return out('Reject', rs);

  rs = [];
  if (pM !== undefined && pM >= R.c.pMild) rs.push(`Mild visible deterioration (${pct(pM)}%)`);
  if (defect !== null && defect >= R.c.defectPct) rs.push(`Dark marks ~${Math.round(defect)}% of visible surface`);
  if (roles && hasTable && roles.overripe >= R.c.overripeBandPct) rs.push(`Overripe colour on ~${Math.round(roles.overripe)}% of surface`);
  if (rs.length) return out('C', rs);

  rs = [];
  if (defect !== null && defect >= R.b.defectPct) rs.push(`Small dark marks ~${Math.round(defect)}% of visible surface`);
  if (roles && hasTable && roles.unripe >= R.b.unripeBandPct) rs.push(`Not yet ripe colour on ~${Math.round(roles.unripe)}% of surface`);
  if (shape !== null && shape < R.b.shapeScore) rs.push(`Irregular shape (score ${shape.toFixed(2)})`);
  if (rs.length) return out('B', rs);

  const colourOk = !hasTable || (roles !== null && roles.target >= R.a.targetBandPct);
  if (pF >= R.a.pFresh && defect !== null && colourOk) {
    const reasons = [`Looks fresh (${pct(pF)}%), dark marks ~${Math.round(defect)}%`];
    if (!hasTable) reasons.push('Colour not assessed for this produce yet');
    return out('A', reasons);
  }
  const reasons: string[] = [];
  if (pF < R.a.pFresh) reasons.push(`Freshness confidence only ${pct(pF)}%`);
  if (!colourOk) reasons.push('Colour outside the usual ripe range');
  if (defect === null) reasons.push('Surface marks not measured');
  return out('B', reasons.length ? reasons : ['Minor visible issues']);
}
