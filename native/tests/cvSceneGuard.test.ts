import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { sceneGuard, faEpisodes, DEFAULT_SCENE_GUARD } from '../src/cv/pipeline/postprocess.ts';
import type { Detection } from '../src/cv/pipeline/tracker.ts';

type Fixture = {
  cases: Array<{ params: { maxSameClass: number; minAreaFrac: number }; dets: Detection[]; expected: Detection[] }>;
  episodes: { shown_flags: boolean[]; fps: number; merge_gap_s: number; expected: number };
};
const fx = JSON.parse(readFileSync(new URL('../../ml/eval/fixtures/scene_guard_parity.json', import.meta.url), 'utf8')) as Fixture;

test('TypeScript sceneGuard reproduces the Python gauntlet guard case by case', () => {
  fx.cases.forEach((c, i) => {
    const got = sceneGuard(c.dets, c.params);
    assert.equal(got.length, c.expected.length, `case ${i} count`);
    got.forEach((g, k) => {
      assert.equal(g.classId, c.expected[k].classId, `case ${i} class`);
      assert.equal(g.score, c.expected[k].score, `case ${i} score`);
      g.box.forEach((v, j) => assert.equal(v, c.expected[k].box[j], `case ${i} box`));
    });
  });
});

test('faEpisodes matches Python', () => {
  assert.equal(faEpisodes(fx.episodes.shown_flags, fx.episodes.fps, fx.episodes.merge_gap_s), fx.episodes.expected);
});

test('a frame full of same-class boxes (stadium seats) shows nothing for that class', () => {
  const seats: Detection[] = Array.from({ length: 30 }, (_, i) => ({ box: [0.03 * i, 0.5, 0.03 * i + 0.03, 0.55], classId: 7, score: 0.6 }));
  const one: Detection = { box: [0.2, 0.2, 0.5, 0.5], classId: 0, score: 0.9 };
  const out = sceneGuard([...seats, one], DEFAULT_SCENE_GUARD);
  assert.deepEqual(out, [one]);
});
