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
};

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
