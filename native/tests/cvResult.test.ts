// G9 Stage J4: explicit Unknown / Not graded result states; grades and confidences never reach the user.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fromStageH, fromAssessment, demoResult, checkDisplayResult, RESULT_STATES, USER_GRADES_ENABLED, NOT_GRADED_TEXT } from '../src/cv/pipeline/result.ts';
import { stageHDecision } from '../src/cv/pipeline/verify.ts';
import type { CvAssessment } from '../src/cv/contracts.ts';

const label = (id: number) => ['Banana', 'Apple'][id] ?? `class ${id}`;
const base: CvAssessment = { assessmentId: 'a', frameTimestampMs: 0, modelVersion: 'g3', rubricVersion: 'r', status: 'supported', objects: [], limitations: [] };

test('grades are compile-time blocked and there is no graded state', () => {
  assert.equal(USER_GRADES_ENABLED, false);
  assert.deepEqual([...RESULT_STATES], ['unknown', 'not_graded', 'poor_capture']);
});

test('Stage H outcomes map to unknown / not_graded, even when the gate passes', () => {
  const unable = fromStageH(stageHDecision({ status: 'unable', reason: 'close_up_unknown', suggestions: [] }, [], 'graded', []), label);
  assert.equal(unable.state, 'unknown'); assert.equal(unable.identityLabel, null); assert.equal(unable.title, 'Unable to identify');
  const passing = fromStageH(stageHDecision({ status: 'verified', classId: 1, evidence: 'wide+h2' }, [], 'graded', [], true), label);
  assert.equal(passing.state, 'not_graded'); assert.equal(passing.grade, null); assert.equal(passing.gradeText, NOT_GRADED_TEXT);
  assert.deepEqual(passing.reasons, ['grades_not_enabled']);
  const occl = fromStageH(stageHDecision({ status: 'verified', classId: 0, evidence: 'wide+h2' }, ['outline_incomplete'], 'graded', []), label);
  assert.equal(occl.title, 'Banana. Not graded'); assert.deepEqual(occl.reasons, ['outline_incomplete']);
  const user = fromStageH(stageHDecision({ status: 'user_confirmed', classId: 1, evidence: 'user' }, [], 'graded', []), label);
  assert.equal(user.identitySource, 'user_confirmed'); assert.match(user.title, /confirmed by you/);
  for (const r of [unable, passing, occl, user]) assert.deepEqual(checkDisplayResult(r), []);
});

test('wide assessments: uncertain, unsupported, several items and errors are unknown; poor capture asks for a retake', () => {
  const obj = { bboxNormalized: [0.1, 0.1, 0.5, 0.5] as [number, number, number, number], produce: { classId: 'apple', label: 'Apple', calibratedConfidence: 0.97 },
    visualGrade: { grade: 'A' as const, reasons: ['even colour'] } };
  for (const status of ['uncertain', 'unsupported', 'error'] as const) assert.equal(fromAssessment({ ...base, status, objects: [obj] }).state, 'unknown');
  assert.equal(fromAssessment({ ...base, objects: [obj, obj] }).state, 'unknown');
  const pc = fromAssessment({ ...base, status: 'poor_capture', imageQuality: { reasons: ['blur'] } });
  assert.equal(pc.state, 'poor_capture'); assert.deepEqual(pc.reasons, ['blur']);
  const one = fromAssessment({ ...base, objects: [obj] });
  assert.equal(one.state, 'not_graded'); assert.equal(one.grade, null); assert.equal(one.confidenceText, null);
  assert.doesNotMatch(JSON.stringify(one), /0\.97|"A"/);   // model confidence and grade never copied into the display result
});

test('demo content is labelled and can never pass as model output', () => {
  const d = demoResult('Apple');
  assert.equal(d.isModelOutput, false); assert.match(d.title, /Demo data/); assert.deepEqual(checkDisplayResult(d), []);
  assert.ok(checkDisplayResult({ ...d, isModelOutput: true }).length > 0);
  assert.ok(checkDisplayResult({ ...d, title: 'Apple' }).length > 0);
  assert.ok(checkDisplayResult({ ...d, title: 'Apple Confidence 97%' }).length > 0);
  assert.ok(checkDisplayResult({ ...d, grade: 'A' as unknown as null }).length > 0);
});
