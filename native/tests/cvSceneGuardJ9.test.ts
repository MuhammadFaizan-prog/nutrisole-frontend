// G9 Stage J9 (cv-gauntlet-device): regression tests of the device scene guard (src/cv/device/guard.ts) against the FROZEN
// sceneGuard() and the Python parity fixture ml/eval/fixtures/scene_guard_parity.json. Synthetic inputs only; nothing here measures a
// phone or a model's accuracy.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { sceneGuard, DEFAULT_SCENE_GUARD } from '../src/cv/pipeline/postprocess.ts';
import { guardFrame, areaFracOf, normBox, closerCandidates, suppressedAt, createCloserHint, CLOSER_HINT } from '../src/cv/device/guard.ts';
import { LiveTracker, mergeAgnostic, rotateRgb, bufferBoxToFrame, guidanceHints, HINT_LIMITS, type LiveObject } from '../src/cv/device/live.ts';
import { runDebugPipeline, runCloseupFromTrack, DET_DECODE_FLOOR } from '../src/cv/device/debugPipeline.ts';
import { suppressedRecord, suppressedLine, createSuppressedLogger, SUPPRESSED_LOG_MIN_MS } from '../src/cv/device/diag.ts';
import { DEFAULT_ID, FROZEN_GATE, detectorToFrame, letterboxTransform } from '../src/cv/pipeline/closeup.ts';
import { H2_CLASSES, FROZEN_VERIFY } from '../src/cv/pipeline/verify.ts';
import type { Detection } from '../src/cv/pipeline/tracker.ts';
import type { Box } from '../src/cv/pipeline/preprocess.ts';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = (p: string) => readFileSync(path.join(root, p), 'utf8');
type Fixture = { cases: Array<{ params: { maxSameClass: number; minAreaFrac: number }; dets: Detection[]; expected: Detection[] }> };
const fx = JSON.parse(read('../ml/eval/fixtures/scene_guard_parity.json')) as Fixture;
const key = (d: Detection) => `${d.classId}|${d.score}|${d.box.join(',')}`;
const toPx = (d: Detection, w: number, h: number): Detection => ({ ...d, box: [d.box[0] * w, d.box[1] * h, d.box[2] * w, d.box[3] * h] });

test('J9 frozen policy: DEFAULT_SCENE_GUARD = {maxSameClass 0 (off since G4), minAreaFrac 0.01}, Python mirror agrees', () => {
  assert.deepEqual(DEFAULT_SCENE_GUARD, { maxSameClass: 0, minAreaFrac: 0.01 });
  const py = read('../ml/eval/scene_guard.py');
  assert.match(py, /DEFAULT_GUARD = dict\(maxSameClass=0, minAreaFrac=0\.01\)/);
  assert.equal(DET_DECODE_FLOOR, 0.25);   // decode floor reported, not changed
  assert.deepEqual(DEFAULT_ID, { idMinScore: 0.5, idMinHits: 3 });
  assert.equal(FROZEN_GATE.minSidePx, 96); assert.equal(HINT_LIMITS.minSidePx, 96);
  assert.equal(FROZEN_VERIFY.policy, 'P-a');
});

test('J9 guardFrame reproduces the Python parity fixture case by case (normalised frame, all 60 cases, fixture params)', () => {
  assert.equal(fx.cases.length, 60);
  fx.cases.forEach((c, i) => {
    const g = guardFrame(c.dets, 1, 1, c.params);
    assert.deepEqual(g.kept.map(key), c.expected.map(key), `case ${i}`);
    assert.equal(g.kept.length + g.suppressed.length, c.dets.length, `case ${i} partition`);
  });
});

test('J9 guardFrame in PIXEL space (1024x512 and 2048x1024 frames) = frozen sceneGuard on the normalised boxes', () => {
  for (const [W, H] of [[1024, 512], [2048, 1024]] as const) {
    fx.cases.forEach((c, i) => {
      const px = c.dets.map((d) => toPx(d, W, H));
      const g = guardFrame(px, W, H, c.params);
      assert.deepEqual(g.kept.map((d) => key({ ...d, box: normBox(d.box, W, H) })), c.expected.map(key), `case ${i} @${W}x${H}`);
    });
  }
});

test('J9 guardFrame with the DEFAULT (frozen) params equals sceneGuard(DEFAULT_SCENE_GUARD) on every fixture input', () => {
  fx.cases.forEach((c, i) => {
    const want = sceneGuard(c.dets, DEFAULT_SCENE_GUARD).map(key);
    assert.deepEqual(guardFrame(c.dets, 1, 1).kept.map(key), want, `case ${i}`);
    const g = guardFrame(c.dets, 1, 1);
    g.suppressed.forEach((s) => { assert.equal(s.reason, 'below_min_area'); assert.ok(s.areaFrac < 0.01); });   // rule 2 is off
  });
});

test('J9 boundary: exactly 1 % kept, just below suppressed, kept objects returned unchanged and in order', () => {
  const W = 1000, H = 1000;
  const at = { box: [0, 0, 100, 100] as Box, classId: 1, score: 0.9 }; const below = { box: [0, 0, 100, 99.9] as Box, classId: 1, score: 0.9 };
  const big = { box: [300, 300, 700, 700] as Box, classId: 3, score: 0.6 };
  const g = guardFrame([at, below, big], W, H);
  assert.deepEqual(g.kept, [at, big]); assert.strictEqual(g.kept[0], at);
  assert.equal(g.suppressed.length, 1); assert.equal(g.suppressed[0].reason, 'below_min_area'); assert.ok(Math.abs(g.suppressed[0].areaFrac - 0.00999) < 1e-9);
  assert.throws(() => guardFrame([at], 0, 10));
});

test('J9 coordinate space: area is taken in the ORIGINAL frame after undoing the letterbox, not in the 480 detector square', () => {
  // 1280x720 landscape frame -> 480x270 letterbox content, py = 105. A 52x52 detector box = 138.7x138.7 frame px = 2.09 % of the frame,
  // but only 1.17 % of the 480x480 detector square; a 40x40 box = 106.7 px = 1.23 % of the frame but 0.69 % of the square.
  const W = 1280, H = 720; const lb = letterboxTransform(W, H);
  assert.equal(lb.py, 105);
  const dbox: Box = [200, 200, 240, 240];
  const fbox = detectorToFrame(dbox, W, H);
  const fFrac = areaFracOf(fbox, W, H); const dFrac = (40 * 40) / (480 * 480);
  assert.ok(fFrac > 0.01 && dFrac < 0.01, `frame ${fFrac} detector ${dFrac}`);
  assert.equal(guardFrame([{ box: fbox, classId: 1, score: 0.9 }], W, H).kept.length, 1);
  // ...and the guard is scale-free: same verdicts on the 480-inner live buffer (uniform scale) and on the full camera frame
  const bw = Math.round(W * lb.sx), bh = Math.round(H * lb.sy);
  const bufBox = detectorToFrame(dbox, bw, bh);
  assert.ok(Math.abs(areaFracOf(bufBox, bw, bh) - areaFracOf(bufferBoxToFrame(bufBox, bw, bh, W, H), W, H)) < 1e-9);
});

test('J9 coordinate space: portrait (rotated) live buffer is guarded on the UPRIGHT buffer with its own dims, verdict rotation-invariant', () => {
  // sensor 640x360 buffer, orientation 'right' -> upright 360x640. A sensor box rotated into upright coords keeps its area fraction.
  const r = rotateRgb(new Uint8Array(640 * 360 * 3), 640, 360, 'right'); assert.equal(r.w, 360); assert.equal(r.h, 640);
  const sensor: Box = [100, 50, 160, 90];                                            // 60x40 = 2400 / 230400 = 1.04 %
  const upright: Box = [360 - 90, 100, 360 - 50, 160];                              // 40x60 in upright coords
  assert.ok(Math.abs(areaFracOf(sensor, 640, 360) - areaFracOf(upright, 360, 640)) < 1e-12);
  assert.equal(guardFrame([{ box: upright, classId: 1, score: 0.9 }], r.w, r.h).kept.length, 1);
  const small: Box = [270, 100, 305, 160];                                           // 35x60 = 0.91 %
  assert.equal(guardFrame([{ box: small, classId: 1, score: 0.9 }], r.w, r.h).kept.length, 0);
});

const obj = (box: Box, classId = 1, score = 0.9): LiveObject => ({ box, classId, score, competing: [] });
function liveStep(t: LiveTracker, dets: Detection[], W: number, H: number, tMs: number) {
  const g = guardFrame(dets, W, H); return { g, views: t.update(mergeAgnostic(g.kept), tMs, g.suppressed.map((d) => d.box)) };
}

test('J9 live: tiny detections never become a track, a hit, a label or a confirmation (5 frames of a 0.95 apple below 1 %)', () => {
  const tr = new LiveTracker(); const W = 640, H = 480; const tiny: Box = [300, 220, 340, 250];   // 40x30 = 0.39 %
  for (let k = 0; k < 5; k++) {
    const { g, views } = liveStep(tr, [{ box: tiny, classId: 1, score: 0.95 }], W, H, k * 200);
    assert.equal(g.kept.length, 0); assert.equal(g.suppressed.length, 1); assert.equal(views.length, 0);
  }
  assert.equal(tr.tracks.length, 0); assert.equal(tr.nextId, 1);
});

test('J9 live: apple close (identified after 3 frames), moved away slowly, then below 1 % -> no stale box or label', () => {
  const tr = new LiveTracker(); const W = 1000, H = 1000; const c = 500;
  const sq = (half: number): Box => [c - half, c - half, c + half, c + half];
  let views = [] as ReturnType<LiveTracker['update']>;
  let k = 0;
  for (; k < 3; k++) views = liveStep(tr, [{ box: sq(150), classId: 1, score: 0.9 }], W, H, k * 200).views;
  assert.equal(views.length, 1); assert.equal(views[0].label, 'Apple');
  const id = views[0].id;
  // move away slowly: 300 -> 120 px side, every step IoU >= 0.3 with the last one and >= 1 % (120^2 = 1.44 %): same track, label kept
  for (const half of [130, 110, 90, 75, 60]) {
    const r = liveStep(tr, [{ box: sq(half), classId: 1, score: 0.9 }], W, H, k++ * 200);
    assert.equal(r.g.kept.length, 1); assert.equal(r.views.length, 1); assert.equal(r.views[0].id, id); assert.equal(r.views[0].label, 'Apple');
  }
  // 96x96 = 0.92 % < 1 %: suppressed; the track is dropped in that same frame (J8 would have held the label up to maxMissed = 4 frames)
  const r = liveStep(tr, [{ box: sq(48), classId: 1, score: 0.9 }], W, H, k++ * 200);
  assert.equal(r.g.kept.length, 0); assert.equal(r.views.length, 0); assert.equal(tr.tracks.length, 0); assert.equal(tr.droppedBySuppression, 1);
  for (let j = 0; j < 4; j++) assert.equal(liveStep(tr, [{ box: sq(40), classId: 1, score: 0.95 }], W, H, k++ * 200).views.length, 0);
  // and the hint path: nameable too-small item, nothing guarded on screen
  const h = createCloserHint(); const sup = guardFrame([{ box: sq(40), classId: 1, score: 0.95 }], W, H).suppressed;
  h.update(closerCandidates(sup).length, 0, 0); assert.equal(h.update(closerCandidates(sup).length, 0, 200), true);
});

test('J9 live: a held identified track disappears the first frame its item is suppressed (vs J8 coasting maxMissed frames)', () => {
  const W = 1000, H = 1000; const a: Box = [400, 400, 520, 520];   // 1.44 %
  const shrunk: Box = [405, 405, 500, 500];                         // 0.9025 %, IoU with a = 9025/14400 = 0.63 >= iouMatch
  const j9 = new LiveTracker(); const j8 = new LiveTracker();
  for (let k = 0; k < 3; k++) { liveStep(j9, [{ box: a, classId: 1, score: 0.9 }], W, H, k); j8.update([obj(a)], k); }
  assert.equal(j9.update([], 3, []).length, 1);   // control: a plain missed frame (no suppression) still coasts, as in J8
  const j9b = new LiveTracker(); for (let k = 0; k < 3; k++) liveStep(j9b, [{ box: a, classId: 1, score: 0.9 }], W, H, k);
  const r = liveStep(j9b, [{ box: shrunk, classId: 1, score: 0.9 }], W, H, 3);
  assert.equal(r.views.length, 0); assert.equal(j9b.tracks.length, 0); assert.equal(j9b.droppedBySuppression, 1);
  const j8v = j8.update([], 3); assert.equal(j8v.length, 1); assert.equal(j8v[0].label, 'Apple');   // J8 default path (no suppressed arg) unchanged
});

test('J9 live: an unrelated tiny box elsewhere never drops or feeds a guarded track', () => {
  const tr = new LiveTracker(); const W = 1000, H = 1000; const a: Box = [100, 100, 400, 400];
  for (let k = 0; k < 3; k++) liveStep(tr, [{ box: a, classId: 1, score: 0.9 }, { box: [800, 800, 830, 830], classId: 3, score: 0.9 }], W, H, k);
  assert.equal(tr.tracks.length, 1); assert.equal(tr.droppedBySuppression, 0); assert.equal(tr.tracks[0].hits, 3);
});

test('J9 "Move closer" hint: needs 2 frames, only when nothing guarded is on screen, held 1.5 s, 2 s cooldown, hidden at once by an item', () => {
  assert.deepEqual(CLOSER_HINT, { minFrames: 2, holdMs: 1500, cooldownMs: 2000 });
  const h = createCloserHint();
  assert.equal(h.update(1, 0, 0), false);      // one noisy frame: nothing
  assert.equal(h.update(1, 0, 200), true);     // second frame in a row: shown
  assert.equal(h.update(0, 0, 400), true);     // cleared but held
  assert.equal(h.update(0, 0, 1700), false);   // hold elapsed -> hidden
  assert.equal(h.update(1, 0, 1900), false); assert.equal(h.update(1, 0, 2100), false);   // cooldown
  assert.equal(h.update(1, 0, 3800), true);    // after cooldown
  assert.equal(h.update(1, 1, 4000), false);   // a guarded item appears: hidden at once
  assert.equal(h.update(1, 0, 4200), false); assert.equal(h.update(1, 0, 4400), true);   // 2 frames again, but no cooldown after an item-hide
  h.reset(); assert.equal(h.visible, false);
  assert.equal(createCloserHint().update(3, 2, 0), false);   // never while guarded items are shown
});

test('J9 closerCandidates: only nameable (score >= idMinScore 0.5) too-small items can raise the hint', () => {
  const g = guardFrame([{ box: [0, 0, 5, 5], classId: 1, score: 0.3 }, { box: [10, 10, 15, 15], classId: 2, score: 0.7 }], 100, 100);
  assert.equal(g.suppressed.length, 2); assert.deepEqual(closerCandidates(g.suppressed).map((d) => d.classId), [2]);
  assert.equal(suppressedAt(g.suppressed, 12, 12)?.classId, 2); assert.equal(suppressedAt(g.suppressed, 50, 50), null);
});

test('J9 diagnostics: suppressed detections logged separately ("NSCV suppressed", kind scene_guard_suppressed), rate-limited, nothing lost', () => {
  const g = guardFrame([{ box: [0, 0, 5, 5], classId: 1, score: 0.8 }, { box: [0, 0, 60, 60], classId: 1, score: 0.9 }], 100, 100);
  const rec = suppressedRecord({ path: 'live', tMs: 5, frame: [100, 100], params: g.params, decodeFloor: DET_DECODE_FLOOR, nIn: 2, suppressed: g.suppressed, hintVisible: true });
  assert.equal(rec.kind, 'scene_guard_suppressed'); assert.equal(rec.n_in, 2); assert.equal(rec.n_kept, 1); assert.equal(rec.n_suppressed, 1);
  assert.deepEqual(rec.guard, { min_area_frac: 0.01, max_same_class: 0 }); assert.equal(rec.decode_floor, 0.25); assert.equal(rec.move_closer_hint, true);
  assert.match(suppressedLine(rec), /^NSCV suppressed \{"v":1,"kind":"scene_guard_suppressed"/);
  assert.equal((rec.items as any[])[0].reason, 'below_min_area'); assert.equal((rec.items as any[])[0].area_frac, 0.0025);
  const L = createSuppressedLogger();
  assert.deepEqual(L.feed(0, 2), { framesSinceLast: 1, suppressedSinceLast: 2 });
  assert.equal(L.feed(200, 1), null); assert.equal(L.feed(400, 0), null); assert.equal(L.feed(600, 3), null);
  assert.deepEqual(L.feed(SUPPRESSED_LOG_MIN_MS, 1), { framesSinceLast: 3, suppressedSinceLast: 5 });
  assert.equal(L.feed(SUPPRESSED_LOG_MIN_MS + 5000, 0), null);   // nothing pending, nothing logged
});

// detector output (1, 16, 4725) with one raw anchor box (cx, cy, w, h in 480 detector px)
function g3Out(cx: number, cy: number, w: number, h: number, cls = 1, s = 0.9) {
  const n = 4725, o = new Float32Array(16 * n); const j = 7; o[j] = cx; o[n + j] = cy; o[2 * n + j] = w; o[3 * n + j] = h; o[(4 + cls) * n + j] = s; return o;
}
const h2Probs = (c: number) => { const p = new Float32Array(H2_CLASSES.length).fill(0.08 / 11); p[c] = 0.9; p[12] = 0.02; return p; };

test('J9 close-up photo: a tapped item below 1 % is not a detection (tooSmallAtTap), the 96 px gate + refusal behaviour unchanged', async () => {
  const still = { rgb: new Uint8Array(640 * 480 * 3).fill(128), w: 640, h: 480 };   // letterbox scale 0.75, py 60
  const tiny = async (m: 'h2' | 'g3_det') => (m === 'g3_det' ? g3Out(240, 240, 30, 30) : h2Probs(1));   // 40x40 still px = 0.52 %
  const r = await runCloseupFromTrack(still, [200, 150], [400, 300], { status: 'unable', reason: 'nothing_detected_at_tap' }, tiny);
  assert.equal(r.detections[0].length, 0); assert.equal(r.guard.suppressed[0].length, 1); assert.equal(r.guard.tooSmallAtTap, true);
  assert.equal(r.closeup!.g3AtTap, null); assert.equal(r.display.title, 'Unable to identify');
  const ok = async (m: 'h2' | 'g3_det') => (m === 'g3_det' ? g3Out(240, 240, 160, 160) : h2Probs(1));
  const o = await runCloseupFromTrack(still, [200, 150], [400, 300], { status: 'identified', classId: 1 }, ok);
  assert.equal(o.guard.suppressed[0].length, 0); assert.equal(o.guard.tooSmallAtTap, false); assert.match(o.display.title, /^Apple\. Not graded$/);
  assert.equal(guidanceHints({ sidePx: 95 })[0].code, 'move_closer');   // the 96 px quality gate hint still fires
});

test('J9 tap-3 burst: tiny item at the tap in every still -> no tapped detection, wide refuses, tooSmallAtTap; large item unchanged', async () => {
  const still = { rgb: new Uint8Array(640 * 480 * 3).fill(128), w: 640, h: 480 };
  const tiny = async (m: 'h2' | 'g3_det') => (m === 'g3_det' ? g3Out(240, 240, 30, 30) : h2Probs(1));
  const r = await runDebugPipeline([still, still, still], [200, 150], [400, 300], tiny);
  assert.deepEqual(r.tappedPerStill, [null, null, null]); assert.equal(r.wide.status, 'unable'); assert.equal(r.guard.tooSmallAtTap, true);
  assert.ok(r.detections.every((d) => d.length === 0)); assert.equal(r.display.title, 'Unable to identify');
  const big = async (m: 'h2' | 'g3_det') => (m === 'g3_det' ? g3Out(240, 240, 160, 160) : h2Probs(1));
  const b = await runDebugPipeline([still, still, still], [200, 150], [400, 300], big);
  assert.deepEqual(b.tappedPerStill, [1, 1, 1]); assert.equal(b.guard.tooSmallAtTap, false); assert.match(b.display.title, /^Apple\. Not graded$/);
});

test('J9 wiring: every device decode is followed by the guard; the screen feeds only kept boxes to the tracker and logs suppressions', () => {
  const dp = read('src/cv/device/debugPipeline.ts');
  assert.equal((dp.match(/decodeRawWithNms\(/g) ?? []).length, 2); assert.equal((dp.match(/guardFrame\(raw, /g) ?? []).length, 2);
  const scr = read('responsive/CvDebugScan.tsx');
  assert.equal((scr.match(/decodeRawWithNms\(/g) ?? []).length, 1);
  assert.match(scr, /const g = guardFrame\(raw, up\.w, up\.h\);/);
  assert.match(scr, /tracker\.current\.update\(mergeAgnostic\(g\.kept\), t0, g\.suppressed\.map\(\(d\) => d\.box\)\)/);
  assert.doesNotMatch(scr, /mergeAgnostic\(dets\)/);
  assert.match(scr, /NSCV event=tap_on_suppressed/); assert.match(scr, /suppressedLine\(/); assert.match(scr, /testID="cv-move-closer"/);
  assert.match(scr, /DET_DECODE_FLOOR/); assert.doesNotMatch(scr, /N_ANCHORS, 0\.25\)/);
  // frozen policy source untouched: sceneGuard body identical to the J8 one
  const pp = read('src/cv/pipeline/postprocess.ts');
  assert.match(pp, /export const DEFAULT_SCENE_GUARD: SceneGuardParams = \{ maxSameClass: 0, minAreaFrac: 0\.01 \};/);
  assert.match(pp, /const keep = dets\.filter\(\(d\) => \(d\.box\[2\] - d\.box\[0\]\) \* \(d\.box\[3\] - d\.box\[1\]\) >= P\.minAreaFrac\);/);
});
