// G9 Stage H: identity verification, occlusion rule, Stage H decision and display contract, at parity with ml/eval/verify.py,
// ml/eval/occlusion.py and ml/prices/display.py (fixture ml/eval/fixtures/verify_parity.json).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  h2Decision, verifyIdentity, userConfirm, partAgreement, occlusionReasons, stageHDecision, stageHMessage, FROZEN_VERIFY, FROZEN_OCC, H2_CLASSES, UNKNOWN,
  type VerifyResult,
} from '../src/cv/pipeline/verify.ts';
import { closeupDisplay, GRADE_DISPLAY_ENABLED } from '../src/cv/prices/display.ts';
import type { PriceSource } from '../src/cv/prices/reference.ts';
import type { IdResult } from '../src/cv/pipeline/closeup.ts';

const F = JSON.parse(readFileSync(new URL('../../ml/eval/fixtures/verify_parity.json', import.meta.url), 'utf8'));
const C = JSON.parse(readFileSync(new URL('../../ml/eval/fixtures/closeup_parity.json', import.meta.url), 'utf8'));

test('frozen verify + occlusion params equal the Python frozen params', () => {
  for (const [k, v] of Object.entries(F.frozen_verify)) assert.equal((FROZEN_VERIFY as Record<string, unknown>)[k], v, k);
  for (const [k, v] of Object.entries(F.frozen_occ)) assert.equal((FROZEN_OCC as Record<string, unknown>)[k], v, k);
  assert.equal(H2_CLASSES.length, 13); assert.equal(H2_CLASSES[UNKNOWN], 'unknown');
});

test('h2Decision parity', () => { for (const c of F.h2) assert.deepEqual(h2Decision(c.probs, c.p), c.out); });
test('verifyIdentity parity (H0 / P-a / P-b / P-c / H2-only)', () => {
  for (const c of F.verify) assert.deepEqual(verifyIdentity(c.wide as IdResult, c.h1, c.probs, c.p), c.out, JSON.stringify(c.p));
});
test('userConfirm parity', () => { for (const c of F.confirm) assert.deepEqual(userConfirm(c.v as VerifyResult, c.chosen), c.out); });
test('partAgreement parity', () => { for (const c of F.part) assert.equal(partAgreement(c.halves, c.classId, c.minP), c.out); });
test('occlusionReasons parity', () => { for (const c of F.occ) assert.deepEqual(occlusionReasons(c.cues, c.p), c.out); });
test('stageHDecision parity', () => { for (const c of F.decision) assert.deepEqual(stageHDecision(c.v as VerifyResult, c.occ, c.gs, c.gr, c.en), c.out); });

test('uncertain or contradictory identity never reaches the grader', () => {
  const wide: IdResult = { status: 'identified', classId: 1 };
  const unsure = [0.3, 0.35, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.35];
  const contra = [0, 0.02, 0, 0.95, 0, 0, 0, 0, 0, 0, 0, 0, 0.03];
  for (const p of [unsure, contra]) {
    const v = verifyIdentity(wide, null, p, FROZEN_VERIFY);
    assert.equal(v.status, 'unable');
    const d = stageHDecision(v, [], 'graded', [], true);
    assert.equal(d.outcome, 'unable_to_identify'); assert.equal(d.gradeShown, null); assert.equal(d.priceKind, null);
    assert.equal(stageHMessage(d), 'Unable to identify');
  }
});

test('Stage H never shows a grade: a passing gate gives quality_check_unavailable', () => {
  assert.equal(GRADE_DISPLAY_ENABLED, false);
  const d = stageHDecision({ status: 'verified', classId: 1, evidence: 'wide+h2' }, [], 'graded', []);
  assert.equal(d.outcome, 'quality_check_unavailable'); assert.equal(d.gradeShown, null);
});

test('display contract: no A/B/C, no grade-specific price, category price only when identity verified', () => {
  const S = C.price_sources as PriceSource[]; const today = '2026-10-14';
  for (const outcome of ['quality_check_unavailable', 'not_graded', 'graded', 'category_confirmed_by_user']) {
    const v = closeupDisplay('verified', 'apple', 'Apple', outcome, S, today);
    assert.equal(v.gradeShown, false); assert.ok(!/\b[ABC]\b|grade 1|grade 2|Reject/.test(v.gradeText ?? ''), v.gradeText ?? '');
    if (v.price.show) { assert.equal(v.price.line.kind, 'category_reference'); assert.equal(v.price.line.listGrade, null); }
  }
  const u = closeupDisplay('unable', 'apple', 'Apple', 'graded', S, today);
  assert.equal(u.title, 'Unable to identify'); assert.equal(u.price.show, false);
  const uc = closeupDisplay('user_confirmed', 'apple', 'Apple', 'category_confirmed_by_user', S, today);
  assert.equal(uc.identityNote, 'Category confirmed by you'); assert.equal(uc.gradeShown, false);
  assert.equal(closeupDisplay('verified', 'apple', 'Apple', 'not_graded', S, '2026-10-30').price.show, false, 'stale list is not shown');
});
