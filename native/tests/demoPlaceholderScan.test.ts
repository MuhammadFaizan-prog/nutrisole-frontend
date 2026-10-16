// G9 Stage J5: regression guard. Demo placeholder values (sample identity, "confidence", grade) can never render as a model prediction,
// on the protected web Scan screen (approved diff, 2026-10-15 22:53 PKT), the native Scan screen, or any shared screen source.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { DEMO_PLACEHOLDER, DEMO_FLAGS, demoBadge, demoConfidenceText, gradeDisplay } from '../../src/nutrisole/extensions/model.ts';
import { demoResult, checkDisplayResult, fromAssessment } from '../src/cv/pipeline/result.ts';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const read = (p: string) => readFileSync(path.join(root, p), 'utf8');

test('web Scan.tsx: the approved diff is applied (Demo data badge, central identity, no percentage, no grade)', () => {
  const src = read('src/nutrisole/Scan.tsx');
  assert.doesNotMatch(src, /Confidence\s*\d/); assert.doesNotMatch(src, /\d{1,3}\s?%/); assert.doesNotMatch(src, /Grade\s+[ABC]\b/);
  assert.match(src, /\{demoBadge\(\)\}<\/Txt>/);
  assert.match(src, /useState<string>\(DEMO_PLACEHOLDER\.identity\)/);
  assert.doesNotMatch(src, /setSelected\('Apple'\)|useState\('Apple'\)/);
  // layout preserved: the badge sits exactly where the 97% text was
  assert.match(src, /<Txt x=\{395\} y=\{497\} w=\{340\} fs=\{38\} color="#fff">\{demoBadge\(\)\}<\/Txt>/);
});

test('web Scan.tsx baseline hash was updated through the recorded approval, not bypassed', () => {
  const base = JSON.parse(read('artifacts/expansion/six-screen-baseline.json'));
  const h = createHash('sha256').update(readFileSync(path.join(root, 'src/nutrisole/Scan.tsx'))).digest('hex');
  assert.equal(base['src/nutrisole/Scan.tsx'], h);
  const log = read('artifacts/expansion/six-screen-baseline.CHANGES.md');
  assert.ok(log.includes(h) && log.includes('2a13b25514bfc563908755a2c22bc1eed216cf3d8513acb881b306ccc0c03710') && /22:53/.test(log));
  assert.equal(Object.keys(base).length, 119);
});

test('native ScanScreen uses the central demo source for identity and confidence slot', () => {
  const src = read('native/responsive/ScanScreen.tsx');
  assert.match(src, /useState<string>\(DEMO_PLACEHOLDER\.identity\)/); assert.doesNotMatch(src, /setSelected\('Apple'\)/);
  assert.doesNotMatch(src, /Confidence\s*\d|\d{1,3}\s?%\s*<|Grade\s+[ABC]\b/);
});

test('demo placeholder can never look like a model prediction', () => {
  assert.equal(DEMO_PLACEHOLDER.isModelOutput, false); assert.equal(DEMO_PLACEHOLDER.confidence, null); assert.equal(DEMO_PLACEHOLDER.grade, null);
  assert.ok(Object.isFrozen(DEMO_PLACEHOLDER) && Object.isFrozen(DEMO_FLAGS));
  assert.throws(() => { (DEMO_PLACEHOLDER as any).confidence = 0.97; });
  assert.equal(demoBadge(), 'Demo data'); assert.doesNotMatch(demoConfidenceText(), /\d/);
  for (const g of [DEMO_PLACEHOLDER.grade, 'A', 'B', 'C']) assert.equal(gradeDisplay(g as any).shown, false);
  const d = demoResult(DEMO_PLACEHOLDER.identity);
  assert.equal(d.isModelOutput, false); assert.equal(d.origin, 'demo'); assert.deepEqual(checkDisplayResult(d), []);
  assert.match(d.title, /Demo data/); assert.equal(d.grade, null); assert.equal(d.confidenceText, null);
  // a demo result relabelled as model output is refused by the UI guard
  assert.notDeepEqual(checkDisplayResult({ ...d, isModelOutput: true }), []);
  assert.notDeepEqual(checkDisplayResult({ ...d, title: `${DEMO_PLACEHOLDER.identity} 97%` }), []);
  assert.notDeepEqual(checkDisplayResult({ ...d, title: 'Apple' }), []);   // unlabelled demo
});

test('no shared screen source hard-codes a confidence percentage or a letter grade as a result', () => {
  const dirs = ['src/nutrisole', 'native/responsive'];
  const files: string[] = [];
  const walk = (d: string) => { for (const f of readdirSync(path.join(root, d))) { const p = path.join(d, f); if (statSync(path.join(root, p)).isDirectory()) walk(p); else if (/\.(tsx?|ts)$/.test(f) && !/\.test\./.test(f)) files.push(p); } };
  dirs.forEach(walk);
  assert.ok(files.length > 20);
  for (const f of files) {
    const s = read(f);
    assert.doesNotMatch(s, /Confidence:?\s*\d{1,3}\s?%/, f);
    assert.doesNotMatch(s, /['"`]Grade\s+[ABC]['"`]/, f);
    assert.doesNotMatch(s, /Model v1\.0/, f);
  }
  // a model-origin result never carries a grade either
  const m = fromAssessment({ status: 'supported', objects: [{ produce: { label: 'Apple' } }], limitations: [] } as any);
  assert.equal(m.grade, null); assert.equal(m.confidenceText, null); assert.deepEqual(checkDisplayResult(m), []);
});

test('Figma export files carry Demo data, not the old 97% / Grade A / Model v1.0 placeholders (approved 2026-10-15 22:53 PKT)', () => {
  for (const f of ['artifacts/figma/scenes.json', 'artifacts/figma/scenes.ascii.json', 'artifacts/figma/source-markup.json',
    'artifacts/figma-expansion/scene-manifest.json', 'artifacts/figma-expansion/ui.html', 'artifacts/expansion/scene-manifest.json']) {
    const s = read(f);
    assert.doesNotMatch(s, /Confidence:?\s*97\s?%/, f); assert.doesNotMatch(s, /"Grade A"/, f); assert.doesNotMatch(s, /Model v1\.0/, f);
    assert.match(s, /Demo data/, f);
  }
});
