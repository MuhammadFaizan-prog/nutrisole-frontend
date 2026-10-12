import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { grade, RUBRIC, BAND_ROLES, type Measurements, type QualityProbs } from '../src/cv/pipeline/rules.ts';

const read = (p: string) => JSON.parse(readFileSync(new URL(p, import.meta.url), 'utf8'));
const rubric = read('../../ml/grading/rubric_v0.json');
const bands = read('../../ml/grading/colour_bands.json');
const golden = read('../../ml/grading/golden_rules.json') as Array<{ name: string; produce: string; det: number; probs: QualityProbs | null; m: Measurements | null; grade: string; status: string }>;

test('TS rubric thresholds equal the Python rubric file', () => {
  const { _comment, ...py } = rubric;
  assert.deepEqual(JSON.parse(JSON.stringify(RUBRIC)), py);
});

test('TS colour band roles equal ml/grading/colour_bands.json', () => {
  for (const [produce, def] of Object.entries(bands)) {
    if (produce.startsWith('_')) continue;
    const roles = Object.fromEntries(Object.entries((def as { bands: Record<string, { role: string }> }).bands).map(([k, v]) => [k, v.role]));
    assert.deepEqual(BAND_ROLES[produce], roles, produce);
  }
});

for (const c of golden) {
  test(`golden: ${c.name}`, () => {
    const g = grade(c.produce, c.det, c.probs, c.m);
    assert.equal(g.grade, c.grade);
    assert.equal(g.status, c.status);
    assert.ok(g.reasons.length >= 1 && g.reasons.length <= 2);
    for (const r of g.reasons) assert.ok(!/safe|disease|formalin|shelf|calorie|price|toxic/i.test(r), r);
  });
}

test('every non-ungradable grade shows the numbers behind it', () => {
  for (const c of golden) {
    const g = grade(c.produce, c.det, c.probs, c.m);
    if (g.grade !== 'ungradable') assert.ok(g.reasons.some((r) => /\d/.test(r)), `${c.name}: ${g.reasons}`);
  }
});
