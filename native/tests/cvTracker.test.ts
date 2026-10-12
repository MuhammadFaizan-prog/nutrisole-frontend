import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { IouTracker, type Detection, type TrackOutput } from '../src/cv/pipeline/tracker.ts';

type Fixture = { params: Record<string, number>; frames: Array<{ tMs: number; dets: Detection[]; reset: boolean }>; expected: Array<Array<{ id: number; box: number[]; label: number; score: number; stable: boolean; ageMs: number }>> };
const fx = JSON.parse(readFileSync(new URL('../../ml/eval/fixtures/tracker_parity.json', import.meta.url), 'utf8')) as Fixture;

test('TypeScript tracker reproduces the Python gauntlet tracker frame by frame', () => {
  const trk = new IouTracker(fx.params);
  fx.frames.forEach((f, i) => {
    if (f.reset) trk.reset();
    const got = trk.update(f.dets, f.tMs);
    const exp = fx.expected[i];
    assert.equal(got.length, exp.length, `frame ${i} track count`);
    got.forEach((g, k) => {
      const e = exp[k];
      assert.equal(g.id, e.id, `frame ${i} id`);
      assert.equal(g.label, e.label, `frame ${i} label`);
      assert.equal(g.stable, e.stable, `frame ${i} stable`);
      assert.ok(Math.abs(g.score - e.score) < 1e-9 && Math.abs(g.ageMs - e.ageMs) < 1e-6, `frame ${i} score/age`);
      g.box.forEach((v, j) => assert.ok(Math.abs(v - e.box[j]) < 1e-9, `frame ${i} box`));
    });
  });
});

const det = (cls: number, score = 0.8, x = 0.3): Detection => ({ box: [x, 0.3, x + 0.3, 0.6], classId: cls, score });

test('hysteresis: single-frame class noise does not flip the label', () => {
  const trk = new IouTracker();
  let out: TrackOutput[] = [];
  for (let f = 0; f < 10; f++) out = trk.update([det(f === 5 ? 3 : 1)], f * 33);
  assert.equal(out[0].label, 1);
});

test('a sustained class change does switch the label', () => {
  const trk = new IouTracker();
  let out: TrackOutput[] = [];
  for (let f = 0; f < 5; f++) out = trk.update([det(1)], f * 33);
  for (let f = 5; f < 20; f++) out = trk.update([det(3, 0.9)], f * 33);
  assert.equal(out[0].label, 3);
});

test('a new object after the old one leaves starts a fresh track (no label carry-over)', () => {
  const trk = new IouTracker();
  let out: TrackOutput[] = [];
  for (let f = 0; f < 20; f++) out = trk.update([det(1)], f * 33);
  const oldId = out[0].id;
  for (let f = 20; f < 26; f++) out = trk.update([], f * 33); // > maxMissed empty frames
  assert.equal(out.length, 0);
  for (let f = 26; f < 29; f++) out = trk.update([det(7)], f * 33);
  assert.equal(out[0].label, 7);
  assert.notEqual(out[0].id, oldId);
});

test('reset() clears state on a scene cut; minHits hides one-frame blips', () => {
  const trk = new IouTracker();
  for (let f = 0; f < 5; f++) trk.update([det(1)], f * 33);
  trk.reset();
  assert.equal(trk.update([det(7)], 200).length, 0); // first frame of new track hidden
  assert.equal(trk.update([det(7)], 233)[0].label, 7);
});

test('stable flag only after the box has stayed put for stableMs', () => {
  const trk = new IouTracker();
  let out: TrackOutput[] = [];
  for (let f = 0; f <= 10; f++) out = trk.update([det(1)], f * 33);
  assert.equal(out[0].stable, false); // 330 ms
  for (let f = 11; f <= 16; f++) out = trk.update([det(1)], f * 33);
  assert.equal(out[0].stable, true); // 528 ms
  out = trk.update([det(1, 0.8, 0.36)], 17 * 33); // jump (still matched, moved)
  assert.equal(out[0].stable, false);
});
