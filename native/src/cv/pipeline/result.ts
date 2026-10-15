// G9 Stage J4: explicit user-facing result state for the scan / close-up pipeline (additive; verify.ts unchanged).
// Every pipeline output the UI shows goes through toDisplayResult(), which yields one of:
//   'unknown'      - identity not established (Unable to identify / unsupported / uncertain / error). No label, no grade.
//   'not_graded'   - identity established (verified, or category confirmed by the user) but no grade is shown.
//   'poor_capture' - capture unusable (blur, light, too far). No label, no grade.
// A 'graded' state is deliberately absent: user-facing A/B/C grades are blocked (G9 Stage J, H3 blocked, M-TEST sealed).
// Confidence numbers are never shown to the user from this layer, and demo content can never pass as a model output.
import type { StageHOutcome } from './verify.ts';
import type { CvAssessment } from '../contracts.ts';

export type ResultState = 'unknown' | 'not_graded' | 'poor_capture';
export const RESULT_STATES: readonly ResultState[] = ['unknown', 'not_graded', 'poor_capture'];
export const USER_GRADES_ENABLED = false as const;   // compile-time constant; see docs/cv/gauntlet/G9_stageJ4.md
export const NOT_GRADED_TEXT = 'Not graded';
export const UNKNOWN_TEXT = 'Unable to identify';

export type DisplayResult = {
  state: ResultState;
  title: string;                       // what the screen shows as the headline
  gradeText: typeof NOT_GRADED_TEXT;   // always "Not graded" while grades are blocked
  grade: null;                         // never a value
  confidenceText: null;                // never shown to the user
  identityLabel: string | null;
  identitySource: 'verified' | 'user_confirmed' | null;
  reasons: string[];
  origin: 'model' | 'demo';
  isModelOutput: boolean;
};

const base = (origin: 'model' | 'demo') => ({ gradeText: NOT_GRADED_TEXT, grade: null, confidenceText: null, origin, isModelOutput: origin === 'model' } as const);
const human = (r: string) => r.replace(/_/g, ' ');

/** Stage H close-up outcome (verify.stageHDecision) -> display result. labelOf maps a class id to its display name. */
export function fromStageH(o: StageHOutcome, labelOf: (classId: number) => string): DisplayResult {
  if (o.outcome === 'unable_to_identify' || !o.identity) {
    return { ...base('model'), state: 'unknown', title: UNKNOWN_TEXT, identityLabel: null, identitySource: null, reasons: [...o.reasons] };
  }
  const label = labelOf(o.identity.classId);
  const reasons = o.outcome === 'graded' ? ['grades_not_enabled'] : [...o.reasons];   // even a passing gate shows no grade
  const suffix = o.identity.source === 'user_confirmed' ? ' (confirmed by you)' : '';
  return { ...base('model'), state: 'not_graded', title: `${label}${suffix}. ${NOT_GRADED_TEXT}`, identityLabel: label, identitySource: o.identity.source, reasons };
}

/** Wide-scan CvAssessment -> display result. Only 'supported' with exactly one object yields a label; grades are dropped. */
export function fromAssessment(a: CvAssessment): DisplayResult {
  if (a.status === 'poor_capture') {
    return { ...base('model'), state: 'poor_capture', title: 'Retake the photo', identityLabel: null, identitySource: null, reasons: [...(a.imageQuality?.reasons ?? []), ...a.limitations] };
  }
  if (a.status !== 'supported' || a.objects.length !== 1) {
    const why = a.status === 'supported' ? 'more_than_one_item' : a.status;
    return { ...base('model'), state: 'unknown', title: UNKNOWN_TEXT, identityLabel: null, identitySource: null, reasons: [why, ...a.limitations] };
  }
  const o = a.objects[0];
  return { ...base('model'), state: 'not_graded', title: `${o.produce.label}. ${NOT_GRADED_TEXT}`, identityLabel: o.produce.label, identitySource: 'verified', reasons: ['grades_not_enabled'] };
}

/** Demo / sample content (no model run). Always labelled, never a model output, never graded. */
export function demoResult(sampleLabel: string): DisplayResult {
  return { ...base('demo'), state: 'not_graded', title: `${sampleLabel} · Demo data. ${NOT_GRADED_TEXT}`, identityLabel: sampleLabel, identitySource: null, reasons: ['demo_data_no_model_run'] };
}

/** Guard for UI adapters: refuses a result that shows a grade or a confidence, or demo content posing as model output. */
export function checkDisplayResult(r: DisplayResult): string[] {
  const e: string[] = [];
  if (!RESULT_STATES.includes(r.state)) e.push(`state ${String(r.state)}`);
  if (r.grade !== null) e.push('grade must be null while grades are blocked');
  if (r.gradeText !== NOT_GRADED_TEXT) e.push('gradeText must be "Not graded"');
  if (r.confidenceText !== null) e.push('confidence is never shown');
  if (r.origin === 'demo' && (r.isModelOutput || !/Demo data/.test(r.title))) e.push('demo content must be labelled and not marked as model output');
  if (r.origin === 'model' && !r.isModelOutput) e.push('model origin must be marked as model output');
  if (/\b\d{1,3}\s?%/.test(r.title) || /\bGrade\s+[ABC]\b/.test(r.title)) e.push('title contains a confidence or grade');
  if (r.state !== 'not_graded' && r.identityLabel !== null) e.push('unknown/poor_capture must not carry an identity label');
  return e;
}

export const reasonText = (r: DisplayResult) => r.reasons.map(human).join(', ');
