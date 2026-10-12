import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { TemporalRescorer, DEFAULT_TEMPORAL, type TemporalParams } from '../src/cv/pipeline/temporal.ts';
import type { Detection } from '../src/cv/pipeline/tracker.ts';

type Fixture = { cases: Array<{ params: TemporalParams; frames: Array<{ dets: Detection[]; reset: boolean; expected: Detection[] }> }> };
const fx = JSON.parse(readFileSync(new URL('../../ml/eval/fixtures/temporal_parity.json', import.meta.url), 'utf8')) as Fixture;

test('TypeScript TemporalRescorer reproduces the Python gauntlet rescoring frame by frame', () => {
  fx.cases.forEach((c, ci) => {
    const r = new TemporalRescorer(c.params);
    c.frames.forEach((f, fi) => {
      if (f.reset) r.reset();
      const got = r.update(f.dets);
      assert.equal(got.length, f.expected.length, `case ${ci} frame ${fi} count`);
      got.forEach((g, k) => {
        const e = f.expected[k];
        assert.equal(g.classId, e.classId, `case ${ci} frame ${fi} class`);
        assert.ok(Math.abs(g.score - e.score) < 1e-9, `case ${ci} frame ${fi} score ${g.score} vs ${e.score}`);
        g.box.forEach((v, j) => assert.equal(v, e.box[j]));
      });
    });
  });
});

test('an isolated one-frame box is suppressed, a persistent box keeps its score', () => {
  const r = new TemporalRescorer({ ...DEFAULT_TEMPORAL, window: 5 });
  const item: Detection = { box: [0.2, 0.2, 0.6, 0.6], classId: 0, score: 0.8 };
  let out: Detection[] = [];
  for (let t = 0; t < 6; t++) out = r.update(t === 3 ? [item, { box: [0.7, 0.7, 0.9, 0.9], classId: 7, score: 0.9 }] : [item]);
  assert.equal(out.length, 1);
  assert.ok(Math.abs(out[0].score - 0.8) < 1e-9);
  const r2 = new TemporalRescorer({ ...DEFAULT_TEMPORAL, window: 5 });
  for (let t = 0; t < 4; t++) r2.update([]);
  assert.equal(r2.update([{ box: [0.7, 0.7, 0.9, 0.9], classId: 7, score: 0.9 }]).length, 0);
});
