// CvAssessment contract (master prompt rule 8.14). Pure TypeScript, no React Native
// imports, so it runs under `node --experimental-strip-types --test` and in a worklet.
// Absent fields mean "not measured"; the validator rejects invented shapes.

export type CvStatus = 'supported' | 'uncertain' | 'unsupported' | 'poor_capture' | 'error';
export type VisualGradeValue = 'A' | 'B' | 'C' | 'Reject' | 'ungradable';

export type CvObject = {
  trackingId?: string;
  bboxNormalized: [number, number, number, number]; // x1, y1, x2, y2 in [0,1] of the camera frame
  produce: { classId: string; label: string; calibratedConfidence?: number };
  ripeness?: { stage: string; confidence?: number; status: 'assessed' | 'unknown' };
  visibleDefects?: Array<{ type: string; areaPercent?: number; severity?: string; confidence?: number }>;
  visualGrade?: { grade: VisualGradeValue; reasons: string[]; confidence?: number };
  // G7 (GPT review item 6): three SEPARATE heads, each with an explicit "unable to assess" state. Optional for
  // backward compatibility; when present all three keys are required. The A/B/C grade never reads these silently.
  assessments?: ObjectAssessments;
};

export type AssessmentStatus = 'assessed' | 'unable_to_assess' | 'not_applicable';
export type RipenessAssessment = { status: AssessmentStatus; stage?: 'unripe' | 'ripe' | 'overripe'; confidence?: number; reason?: string };
export type FreshnessAssessment = { status: AssessmentStatus; level?: 'fresh' | 'rotten'; confidence?: number; reason?: string };
export type DefectsAssessment = {
  status: AssessmentStatus; reason?: string;
  defects?: Array<{ type: string; areaPercent?: number; severity?: string; confidence?: number }>;
};
export type ObjectAssessments = { ripeness: RipenessAssessment; visibleDefects: DefectsAssessment; freshness: FreshnessAssessment };
export const ASSESSMENT_STATUSES: readonly AssessmentStatus[] = ['assessed', 'unable_to_assess', 'not_applicable'];

export type CvAssessment = {
  assessmentId: string;
  frameTimestampMs: number;
  modelVersion: string;
  rubricVersion: string;
  status: CvStatus;
  imageQuality?: { blur?: number; lighting?: 'ok' | 'low' | 'overexposed'; reasons: string[] };
  objects: CvObject[];
  limitations: string[];
};

const STATUSES: readonly CvStatus[] = ['supported', 'uncertain', 'unsupported', 'poor_capture', 'error'];
const GRADES: readonly VisualGradeValue[] = ['A', 'B', 'C', 'Reject', 'ungradable'];
// Wording that would claim more than visible condition (rule 8.4).
const BANNED_CLAIMS = [/\bsafe\b/i, /disease/i, /formalin/i, /shelf[- ]?life/i, /calorie/i, /\bprice\b/i, /toxic/i];

export type ValidationResult = { ok: true; value: CvAssessment } | { ok: false; errors: string[] };

const isObj = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);
const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const isProb = (v: unknown) => isNum(v) && v >= 0 && v <= 1;
const isStrArr = (v: unknown): v is string[] => Array.isArray(v) && v.every((s) => typeof s === 'string');

export function validateCvAssessment(input: unknown): ValidationResult {
  const e: string[] = [];
  if (!isObj(input)) return { ok: false, errors: ['assessment must be an object'] };
  const a = input;
  for (const k of ['assessmentId', 'modelVersion', 'rubricVersion'] as const) {
    if (typeof a[k] !== 'string' || (a[k] as string).length === 0) e.push(`${k} must be a non-empty string`);
  }
  if (!isNum(a.frameTimestampMs) || (a.frameTimestampMs as number) < 0) e.push('frameTimestampMs must be a non-negative number');
  if (!STATUSES.includes(a.status as CvStatus)) e.push(`status must be one of ${STATUSES.join(', ')}`);
  if (!isStrArr(a.limitations)) e.push('limitations must be string[]');
  if (a.imageQuality !== undefined) {
    const q = a.imageQuality;
    if (!isObj(q)) e.push('imageQuality must be an object');
    else {
      if (q.blur !== undefined && !isNum(q.blur)) e.push('imageQuality.blur must be a number');
      if (q.lighting !== undefined && !['ok', 'low', 'overexposed'].includes(q.lighting as string)) e.push('imageQuality.lighting invalid');
      if (!isStrArr(q.reasons)) e.push('imageQuality.reasons must be string[]');
    }
  }
  if (!Array.isArray(a.objects)) e.push('objects must be an array');
  else {
    a.objects.forEach((o, i) => {
      const p = `objects[${i}]`;
      if (!isObj(o)) { e.push(`${p} must be an object`); return; }
      if (o.trackingId !== undefined && typeof o.trackingId !== 'string') e.push(`${p}.trackingId must be a string`);
      const b = o.bboxNormalized;
      if (!Array.isArray(b) || b.length !== 4 || !b.every((v) => isNum(v) && v >= 0 && v <= 1)) e.push(`${p}.bboxNormalized must be 4 numbers in [0,1]`);
      else if (!((b[2] as number) > (b[0] as number) && (b[3] as number) > (b[1] as number))) e.push(`${p}.bboxNormalized must have x2>x1 and y2>y1`);
      const pr = o.produce;
      if (!isObj(pr) || typeof pr.classId !== 'string' || typeof pr.label !== 'string') e.push(`${p}.produce needs classId and label`);
      else if (pr.calibratedConfidence !== undefined && !isProb(pr.calibratedConfidence)) e.push(`${p}.produce.calibratedConfidence must be in [0,1]`);
      if (o.ripeness !== undefined) {
        const r = o.ripeness;
        if (!isObj(r) || typeof r.stage !== 'string' || !['assessed', 'unknown'].includes(r.status as string)) e.push(`${p}.ripeness invalid`);
        else if (r.confidence !== undefined && !isProb(r.confidence)) e.push(`${p}.ripeness.confidence must be in [0,1]`);
      }
      if (o.visibleDefects !== undefined) {
        if (!Array.isArray(o.visibleDefects)) e.push(`${p}.visibleDefects must be an array`);
        else o.visibleDefects.forEach((d, j) => {
          if (!isObj(d) || typeof d.type !== 'string') e.push(`${p}.visibleDefects[${j}].type required`);
          else {
            if (d.areaPercent !== undefined && !(isNum(d.areaPercent) && d.areaPercent >= 0 && d.areaPercent <= 100)) e.push(`${p}.visibleDefects[${j}].areaPercent must be 0-100`);
            if (d.confidence !== undefined && !isProb(d.confidence)) e.push(`${p}.visibleDefects[${j}].confidence must be in [0,1]`);
          }
        });
      }
      if (o.assessments !== undefined) e.push(...validateAssessments(o.assessments, `${p}.assessments`));
      if (o.visualGrade !== undefined) {
        const g = o.visualGrade;
        if (!isObj(g) || !GRADES.includes(g.grade as VisualGradeValue) || !isStrArr(g.reasons)) e.push(`${p}.visualGrade invalid`);
        else {
          if (g.grade !== 'ungradable' && (g.reasons as string[]).length === 0) e.push(`${p}.visualGrade needs at least one reason`);
          if (g.confidence !== undefined && !isProb(g.confidence)) e.push(`${p}.visualGrade.confidence must be in [0,1]`);
          for (const r of g.reasons as string[]) if (BANNED_CLAIMS.some((re) => re.test(r))) e.push(`${p}.visualGrade reason makes a non-visual claim: "${r}"`);
        }
      }
    });
  }
  if (a.status === 'supported' && Array.isArray(a.objects) && a.objects.length === 0) e.push("status 'supported' requires at least one object");
  return e.length ? { ok: false, errors: e } : { ok: true, value: a as unknown as CvAssessment };
}

/** G7: validate the separated ripeness / visibleDefects / freshness heads. Rules: every head present; status in
 *  ASSESSMENT_STATUSES; 'assessed' carries its value (stage / level / defects array, possibly empty); 'unable_to_assess'
 *  and 'not_applicable' carry a non-empty reason and no value; confidences in [0,1]; reasons make no non-visual claim. */
export function validateAssessments(x: unknown, p = 'assessments'): string[] {
  const e: string[] = [];
  if (!isObj(x)) return [`${p} must be an object`];
  const heads: Array<['ripeness' | 'visibleDefects' | 'freshness', string]> = [['ripeness', 'stage'], ['visibleDefects', 'defects'], ['freshness', 'level']];
  for (const [k, valueKey] of heads) {
    const h = x[k];
    const q = `${p}.${k}`;
    if (!isObj(h)) { e.push(`${q} required`); continue; }
    if (!ASSESSMENT_STATUSES.includes(h.status as AssessmentStatus)) { e.push(`${q}.status must be one of ${ASSESSMENT_STATUSES.join(', ')}`); continue; }
    if (h.confidence !== undefined && !isProb(h.confidence)) e.push(`${q}.confidence must be in [0,1]`);
    if (h.status === 'assessed') {
      if (k === 'ripeness' && !['unripe', 'ripe', 'overripe'].includes(h.stage as string)) e.push(`${q}.stage required when assessed`);
      if (k === 'freshness' && !['fresh', 'rotten'].includes(h.level as string)) e.push(`${q}.level required when assessed`);
      if (k === 'visibleDefects') {
        if (!Array.isArray(h.defects)) e.push(`${q}.defects array required when assessed`);
        else h.defects.forEach((d, j) => {
          if (!isObj(d) || typeof d.type !== 'string') e.push(`${q}.defects[${j}].type required`);
          else if (d.areaPercent !== undefined && !(isNum(d.areaPercent) && d.areaPercent >= 0 && d.areaPercent <= 100)) e.push(`${q}.defects[${j}].areaPercent must be 0-100`);
        });
      }
    } else {
      if (typeof h.reason !== 'string' || h.reason.length === 0) e.push(`${q}.reason required when ${h.status}`);
      if (h[valueKey] !== undefined) e.push(`${q}.${valueKey} must be absent when ${h.status}`);
    }
    if (typeof h.reason === 'string' && BANNED_CLAIMS.some((re) => re.test(h.reason as string))) e.push(`${q}.reason makes a non-visual claim`);
  }
  return e;
}

/** Placeholder-aware builder: a head that is not available returns unable_to_assess with a reason, never a guess. */
export function buildAssessments(inp: {
  ripeness?: { stage: string; status: 'assessed' | 'unknown'; confidence?: number } | null; ripenessEnabled?: boolean; ripenessApplicable?: boolean;
  freshness?: { level: 'fresh' | 'rotten'; confidence?: number } | null; freshnessReason?: string;
  defects?: DefectsAssessment['defects'] | null;
}): ObjectAssessments {
  let ripeness: RipenessAssessment;
  if (inp.ripenessApplicable === false) ripeness = { status: 'not_applicable', reason: 'no ripeness model for this produce class' };
  else if (!inp.ripenessEnabled) ripeness = { status: 'unable_to_assess', reason: 'ripeness head disabled in config' };
  else if (!inp.ripeness || inp.ripeness.status !== 'assessed') ripeness = { status: 'unable_to_assess', reason: 'low confidence or classifier disagrees on the fruit', ...(inp.ripeness?.confidence !== undefined ? { confidence: inp.ripeness.confidence } : {}) };
  else ripeness = { status: 'assessed', stage: inp.ripeness.stage as RipenessAssessment['stage'], ...(inp.ripeness.confidence !== undefined ? { confidence: inp.ripeness.confidence } : {}) };
  const freshness: FreshnessAssessment = inp.freshness
    ? { status: 'assessed', level: inp.freshness.level, ...(inp.freshness.confidence !== undefined ? { confidence: inp.freshness.confidence } : {}) }
    : { status: 'unable_to_assess', reason: inp.freshnessReason ?? 'item not stable or quality classifier abstained' };
  const visibleDefects: DefectsAssessment = inp.defects
    ? { status: 'assessed', defects: inp.defects }
    : { status: 'unable_to_assess', reason: 'no localised defect model yet (placeholder head)' };
  return { ripeness, visibleDefects, freshness };
}
