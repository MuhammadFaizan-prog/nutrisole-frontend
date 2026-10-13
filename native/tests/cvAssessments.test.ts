import assert from 'node:assert/strict';
import { test } from 'node:test';
import { buildAssessments, validateAssessments, validateCvAssessment } from '../src/cv/contracts.ts';

const base = (assessments: unknown) => ({
  assessmentId: 'a1', frameTimestampMs: 0, modelVersion: 'g3', rubricVersion: 'r', status: 'supported', limitations: [],
  objects: [{ bboxNormalized: [0.1, 0.1, 0.5, 0.5], produce: { classId: 'banana', label: 'Banana' }, assessments }],
});

test('placeholder heads produce explicit unable_to_assess / not_applicable states and validate', () => {
  const a = buildAssessments({});
  assert.equal(a.ripeness.status, 'unable_to_assess');
  assert.equal(a.visibleDefects.status, 'unable_to_assess');
  assert.equal(a.freshness.status, 'unable_to_assess');
  assert.deepEqual(validateAssessments(a), []);
  assert.equal(buildAssessments({ ripenessApplicable: false }).ripeness.status, 'not_applicable');
  assert.ok(validateCvAssessment(base(a)).ok);
});

test('assessed heads carry their values; the three heads stay separate', () => {
  const a = buildAssessments({ ripenessEnabled: true, ripeness: { stage: 'overripe', status: 'assessed', confidence: 0.9 }, freshness: { level: 'fresh', confidence: 0.8 }, defects: [] });
  assert.equal(a.ripeness.stage, 'overripe');
  assert.equal(a.freshness.level, 'fresh');
  assert.deepEqual(a.visibleDefects.defects, []);
  assert.deepEqual(validateAssessments(a), []);
  const unk = buildAssessments({ ripenessEnabled: true, ripeness: { stage: 'unknown', status: 'unknown', confidence: 0.41 } });
  assert.equal(unk.ripeness.status, 'unable_to_assess');
  assert.equal(unk.ripeness.confidence, 0.41);
});

test('validator rejects missing heads, missing reasons, values on unable states and non-visual claims', () => {
  assert.ok(validateAssessments({ ripeness: { status: 'assessed', stage: 'ripe' }, freshness: { status: 'assessed', level: 'fresh' } }).some((m) => m.includes('visibleDefects required')));
  const bad = {
    ripeness: { status: 'unable_to_assess' },
    visibleDefects: { status: 'assessed' },
    freshness: { status: 'unable_to_assess', reason: 'x', level: 'fresh' },
  };
  const errs = validateAssessments(bad);
  assert.ok(errs.some((m) => m.includes('ripeness.reason required')));
  assert.ok(errs.some((m) => m.includes('defects array required')));
  assert.ok(errs.some((m) => m.includes('level must be absent')));
  assert.ok(validateAssessments({ ripeness: { status: 'maybe' }, visibleDefects: { status: 'not_applicable', reason: 'n/a' }, freshness: { status: 'unable_to_assess', reason: 'it is safe to eat' } }).length >= 2);
  assert.equal(validateCvAssessment(base({ ripeness: { status: 'assessed' } })).ok, false);
});
