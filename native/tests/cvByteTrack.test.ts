import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { ByteTrackTracker, DEFAULT_TRACKER_KIND, createTracker, linearAssignment } from '../src/cv/pipeline/bytetrack.ts';
import { IouTracker, type Detection } from '../src/cv/pipeline/tracker.ts';

type Out = { id: number; box: number[]; label: number; score: number; stable: boolean; ageMs: number };
type Fixture = { params: Record<string, number | boolean>; frames: Array<{ tMs: number; dets: Detection[]; reset: boolean }>; expected: Out[][] };
const fx = JSON.parse(readFileSync(new URL('../../ml/eval/fixtures/bytetrack_parity.json', import.meta.url), 'utf8')) as Fixture;
const trkFx = JSON.parse(readFileSync(new URL('../../ml/eval/fixtures/tracker_parity.json', import.meta.url), 'utf8')) as Fixture;

test('TypeScript ByteTrack reproduces the Python adapter (Ultralytics BYTETracker) frame by frame', () => {
  const p = fx.params;
  const trk = new ByteTrackTracker({
    trackHighThresh: p.track_high_thresh as number, trackLowThresh: p.track_low_thresh as number, newTrackThresh: p.new_track_thresh as number,
    trackBuffer: p.track_buffer as number, matchThresh: p.match_thresh as number, fuseScore: p.fuse_score as boolean,
    scoreAlpha: p.scoreAlpha as number, switchMargin: p.switchMargin as number, switchFrames: p.switchFrames as number, minHits: p.minHits as number,
    stableIou: p.stableIou as number, stableMs: p.stableMs as number, boxAlpha: p.boxAlpha as number,
  });
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

test('flag defaults to IouTracker and the iou path is byte-identical to IouTracker', () => {
  assert.equal(DEFAULT_TRACKER_KIND, 'iou');
  const a = createTracker();
  assert.ok(a instanceof IouTracker);
  const b = new IouTracker(trkFx.params);
  const c = createTracker('iou', trkFx.params);
  trkFx.frames.forEach((f) => {
    if (f.reset) { b.reset(); c.reset(); }
    assert.deepEqual(c.update(f.dets, f.tMs), b.update(f.dets, f.tMs));
  });
  assert.ok(createTracker('bytetrack') instanceof ByteTrackTracker);
});

test('linearAssignment follows lapjv cost_limit semantics', () => {
  const r = linearAssignment([[0.1, 0.9], [0.85, 0.2]], 0.8);
  assert.deepEqual(r.matches, [[0, 0], [1, 1]]);
  const r2 = linearAssignment([[0.9, 0.95]], 0.8); // every pair above the limit -> unmatched
  assert.deepEqual(r2.matches, []);
  assert.deepEqual(r2.uA, [0]);
  assert.deepEqual(r2.uB, [0, 1]);
  assert.deepEqual(linearAssignment([], 0.8).matches, []);
});

test('low-score box keeps an existing track alive (second association) but never starts one', () => {
  const trk = new ByteTrackTracker();
  const d = (s: number): Detection => ({ box: [0.3, 0.3, 0.6, 0.6], classId: 1, score: s });
  let out = trk.update([d(0.2)], 0);
  assert.equal(out.length, 0);
  for (let f = 1; f < 5; f++) out = trk.update([d(0.8)], f * 33);
  const id = out[0].id;
  out = trk.update([d(0.2)], 5 * 33);
  assert.equal(out.length, 1);
  assert.equal(out[0].id, id);
});
