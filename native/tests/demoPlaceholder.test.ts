// G9 Stage J4: demo placeholders are labelled, never look like model output, and grades stay hidden ("Not graded").
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { DEMO_FLAGS, DEMO_PLACEHOLDER, demoConfidenceText, demoBadge, gradeDisplay, buildScene, NOT_GRADED } from '../../src/nutrisole/extensions/model.ts';

test('flags: grades blocked by default; demo placeholder has no confidence, grade or model version', () => {
  assert.equal(DEMO_FLAGS.gradeDisplayEnabled, false);
  assert.equal(DEMO_PLACEHOLDER.isModelOutput, false);
  assert.equal(DEMO_PLACEHOLDER.confidence, null); assert.equal(DEMO_PLACEHOLDER.grade, null); assert.equal(DEMO_PLACEHOLDER.modelVersion, null);
  assert.match(demoConfidenceText(), /^Demo data/); assert.doesNotMatch(demoConfidenceText(), /\d+\s?%/);
  assert.equal(demoConfidenceText({ showDemoPlaceholders: false, gradeDisplayEnabled: false }), '');
  assert.equal(demoBadge(), 'Demo data');
});

test('gradeDisplay: Not graded unless the flag is on AND a real model grade is supplied; the demo can never show a grade', () => {
  assert.deepEqual(gradeDisplay('A'), { shown: false, text: NOT_GRADED, reason: 'grades_blocked' });
  const on = { showDemoPlaceholders: true, gradeDisplayEnabled: true };
  assert.equal(gradeDisplay(DEMO_PLACEHOLDER.grade, on).shown, false);
  assert.equal(gradeDisplay('Z', on).shown, false);
  assert.deepEqual(gradeDisplay('B', on), { shown: true, text: 'B', reason: 'model_grade' });
});

test('assessment and market screens show Demo data + Not graded, no 97% and no Grade A', () => {
  for (const route of ['analysis-result', 'market-reference'] as const) {
    const texts = buildScene(route).layers.map((l) => l.text ?? '').join(' | ');
    assert.doesNotMatch(texts, /97\s?%|Grade A|Model v1\.0/, route);
    assert.match(texts, /Not graded/, route); assert.match(texts, /Demo data/, route);
    assert.ok(!buildScene(route).layers.some((l) => l.text === 'A'), `${route}: bare grade letter`);
  }
});

test('native scan banner and evidence notice no longer hard-code a confidence', () => {
  const scan = readFileSync(new URL('../responsive/ScanScreen.tsx', import.meta.url), 'utf8');
  assert.doesNotMatch(scan, /Confidence 97%/); assert.match(scan, /demoConfidenceText\(\)/);
  const ev = readFileSync(new URL('../../src/nutrisole/extensions/useExpansion.ts', import.meta.url), 'utf8');
  assert.doesNotMatch(ev, /Confidence: 97%/);
});
