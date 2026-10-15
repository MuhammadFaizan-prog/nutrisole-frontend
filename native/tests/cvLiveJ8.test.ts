// G9 Stage J8 (cv-gauntlet-device): live CV unit tests. Synthetic inputs only; nothing here measures a phone or a model's accuracy.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  gateVerdict, createThrottler, thermalFloorMs, LIVE_THROTTLE, liveResizeDims, rotateRgb, bufferBoxToFrame, mergeAgnostic, LiveTracker, trackWide, LIVE_TRACKER,
  guidanceHints, HINT_LIMITS, qualityMetrics, laplacianVar, boxSide, lifeReduce, LIFE_INITIAL, cameraActive, frameProcessorActive, effectiveMode, DEFAULT_SCAN_MODE,
  createPerfMeter, perfLine, unpackResized, meanRgb, colourCheck, type LiveObject,
} from '../src/cv/device/live.ts';
import { burstWide, runCloseupFromTrack, h2Top3 } from '../src/cv/device/debugPipeline.ts';
import { diagRecord, isContested, reasonCode, shouldSave, toBase64, DIAG_MAX_SAVES_PER_MIN } from '../src/cv/device/diag.ts';
import { DEFAULT_ID, FROZEN_GATE, letterboxTransform } from '../src/cv/pipeline/closeup.ts';
import { DEFAULT_TRACKER_PARAMS, type Detection } from '../src/cv/pipeline/tracker.ts';
import { FROZEN_VERIFY, H2_CLASSES } from '../src/cv/pipeline/verify.ts';
import { detectorInput } from '../src/cv/device/pixels.ts';
import { stillBoxToView } from '../src/cv/device/orientation.ts';
import { srcToScreen, type Box } from '../src/cv/pipeline/preprocess.ts';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = (p: string) => readFileSync(path.join(root, p), 'utf8');
const det = (classId: number, score: number, box: Box = [100, 100, 200, 200]): Detection => ({ box, classId, score });
const obj = (classId: number, score: number, box: Box = [100, 100, 200, 200]): LiveObject => ({ box, classId, score, competing: [] });

test('frozen constants are untouched by J8 (no threshold / policy change)', () => {
  assert.deepEqual(DEFAULT_ID, { idMinScore: 0.5, idMinHits: 3 });
  assert.deepEqual(FROZEN_VERIFY, { policy: 'P-a', tau: 0.4, margin: 0.0, maxUnknown: 0.5, h1VetoScore: 0.5, suggestMinP: 0.15 });
  assert.equal(FROZEN_GATE.minSidePx, 96); assert.equal(FROZEN_GATE.minBlurVar, 15); assert.equal(FROZEN_GATE.minMeanV, 80); assert.equal(FROZEN_GATE.maxMeanV, 245);
  assert.equal(LIVE_TRACKER.window, DEFAULT_ID.idMinHits); assert.equal(LIVE_TRACKER.iouMatch, DEFAULT_TRACKER_PARAMS.iouMatch);
});

test('throttler: single in-flight, drop not queue, adaptive 125..333 ms, thermal back-off', () => {
  assert.equal(gateVerdict({ busy: true, nextDueMs: 0 }, 1000), 'skip_busy');
  assert.equal(gateVerdict({ busy: false, nextDueMs: 1100 }, 1000), 'skip_interval');
  assert.equal(gateVerdict({ busy: false, nextDueMs: 1000 }, 1000), 'send');
  const t = createThrottler(); assert.equal(t.intervalMs, LIVE_THROTTLE.startIntervalMs);
  let g = t.onResult(1000, 40); assert.equal(t.intervalMs, 125); assert.equal(g.busy, false); assert.equal(g.nextDueMs, 1000 + 125 - 40);
  for (let i = 0; i < 20; i++) g = t.onResult(2000, 600);   // slow phone: capped at 3 updates/s, never queues
  assert.equal(t.intervalMs, 333); assert.equal(g.nextDueMs, 2000);
  const u = createThrottler(); u.onResult(0, 40, 2); assert.equal(u.intervalMs, 250); u.onResult(0, 40, 3); assert.equal(u.intervalMs, 333); u.onResult(0, 40, 4); assert.equal(u.intervalMs, 500);
  assert.equal(thermalFloorMs(-1), 125); assert.equal(u.onError(10).nextDueMs, 10 + 333);
  // rate stays inside 3..8 per second when not throttled thermally
  for (const lat of [5, 50, 150, 250, 400]) { const k = createThrottler(); for (let i = 0; i < 30; i++) k.onResult(0, lat); assert.ok(1000 / k.intervalMs >= 3 - 1e-9 && 1000 / k.intervalMs <= 8 + 1e-9, String(lat)); }
});

test('live buffer = letterbox inner size, so detectorInput pads (114) without resampling: same tensor as the tap path', () => {
  assert.deepEqual(liveResizeDims(1280, 720), { w: 480, h: 270 }); assert.deepEqual(liveResizeDims(720, 1280), { w: 270, h: 480 }); assert.deepEqual(liveResizeDims(1920, 1080), { w: 480, h: 270 });
  const w = 48, h = 27; const rgb = new Uint8Array(w * h * 3); for (let i = 0; i < rgb.length; i++) rgb[i] = (i * 37) % 251;
  const x = detectorInput(rgb, w, h, 48); const t = letterboxTransform(w, h, 48); const N = 48 * 48;
  for (let yy = 0; yy < h; yy++) for (let xx = 0; xx < w; xx++) for (let c = 0; c < 3; c++) assert.ok(Math.abs(x[c * N + (yy + t.py) * 48 + xx + t.px] - rgb[(yy * w + xx) * 3 + c] / 255) < 1e-6);
  assert.ok(Math.abs(x[0] - 114 / 255) < 1e-6);
});

test('rotateRgb: all orientations + mirror, and boxes map back to the preview consistently', () => {
  // 3x2 image, pixel value = index
  const w = 3, h = 2; const rgb = new Uint8Array(w * h * 3); for (let i = 0; i < w * h; i++) rgb.fill(i, i * 3, i * 3 + 3);
  const px = (r: { rgb: Uint8Array; w: number }, x: number, y: number) => r.rgb[(y * r.w + x) * 3];
  const up = rotateRgb(rgb, w, h, 'up'); assert.equal(up.rgb, rgb);
  const right = rotateRgb(rgb, w, h, 'right'); assert.deepEqual([right.w, right.h], [2, 3]);
  // 'right' = data rotated +90 (CW); undo with CCW: upright top-left = source top-right
  assert.equal(px(right, 0, 0), 2); assert.equal(px(right, 1, 0), 5); assert.equal(px(right, 0, 2), 0);
  const left = rotateRgb(rgb, w, h, 'left'); assert.equal(px(left, 0, 0), 3); assert.equal(px(left, 1, 2), 2);
  const down = rotateRgb(rgb, w, h, 'down'); assert.equal(px(down, 0, 0), 5); assert.equal(px(down, 2, 1), 0);
  const m = rotateRgb(rgb, w, h, 'up', true); assert.equal(px(m, 0, 0), 2);
  // right then left = 180 of identity check: rotating 'right' result by 'left' twice returns to the source
  const back = rotateRgb(right.rgb, right.w, right.h, 'left'); assert.deepEqual([back.w, back.h], [3, 2]); assert.deepEqual([...back.rgb], [...rgb]);
  assert.throws(() => rotateRgb(new Uint8Array(5), 3, 2, 'up'), /rgb/);
  // coordinate mapping reuse: an upright-buffer box -> preview ('cover') through the existing srcToScreen, portrait + landscape
  for (const [bw, bh, vw, vh] of [[270, 480, 360, 780], [480, 270, 780, 360], [360, 480, 360, 480]] as const) {
    const b: Box = [bw * 0.25, bh * 0.25, bw * 0.75, bh * 0.75]; const v = stillBoxToView(b, [bw, bh], [vw, vh]); const s = srcToScreen(b, bw, bh, vw, vh, 'cover');
    assert.deepEqual([v.left, v.top, v.left + v.width, v.top + v.height].map((q) => Math.round(q * 1000)), s.map((q) => Math.round(q * 1000)));
    assert.ok(Math.abs((v.left + v.width / 2) - vw / 2) < 1e-6 && Math.abs((v.top + v.height / 2) - vh / 2) < 1e-6);   // centred box stays centred
  }
  assert.deepEqual(bufferBoxToFrame([10, 20, 30, 40], 270, 480, 720, 1280).map((v) => Math.round(v * 1e6) / 1e6), [26.666667, 53.333333, 80, 106.666667]);
});

test('mergeAgnostic: one object per fruit, competing class kept for the log, scores untouched', () => {
  const o = mergeAgnostic([det(1, 0.62), det(3, 0.31, [102, 101, 199, 201]), det(10, 0.7, [400, 400, 450, 500])]);
  assert.equal(o.length, 2); const a = o.find((x) => x.classId === 1)!; assert.equal(a.score, 0.62); assert.deepEqual(a.competing, [{ classId: 3, score: 0.31 }]);
});

test('consistency from frames == the J7 burst policy (burstWide) on the same observations', () => {
  const cases: (Detection | null)[][] = [
    [det(1, 0.9), det(1, 0.8), det(1, 0.7)], [det(1, 0.9), det(1, 0.45), det(1, 0.7)], [det(1, 0.9), det(3, 0.8), det(1, 0.7)],
    [det(1, 0.9), null, det(1, 0.7)], [null, null, null], [det(3, 0.6), det(3, 0.6), det(6, 0.9)], [det(1, 0.5), det(1, 0.5), det(1, 0.5)],
  ];
  for (const c of cases) assert.deepEqual(trackWide(c), burstWide(c), JSON.stringify(c));
  // the tracker feeds trackWide exactly the per-frame matched detections
  for (const c of cases) {
    const tr = new LiveTracker(); let v: any[] = []; let t = 0;
    tr.update([obj(0, 0.99, [0, 0, 10, 10])], t);   // unrelated item, keeps ids honest
    const first = c.findIndex(Boolean); if (first < 0) continue;
    for (let i = 0; i < c.length; i++) { const d = c[i]; v = tr.update(d ? [obj(d.classId, d.score)] : [], (t += 200)); }
    const trk = tr.tracks.find((k) => k.rawBox[0] === 100); if (!trk) continue;
    assert.deepEqual(trackWide(trk.obs), burstWide(c.slice(first).length === 3 ? c : [...Array(3 - c.slice(first).length).fill(null), ...c.slice(first)]));
  }
});

test('tracker: label only after the policy passes, no carry-over to a new object, anti-flicker never shows an unverified label', () => {
  const tr = new LiveTracker(); let v = tr.update([obj(1, 0.8)], 0);
  assert.equal(v[0].label, null); assert.equal(v[0].state, 'confirming');
  v = tr.update([obj(1, 0.8)], 200); assert.equal(v[0].label, null);
  v = tr.update([obj(1, 0.8)], 400); assert.equal(v[0].label, 'Apple'); const id = v[0].id;
  v = tr.update([], 600); assert.equal(v[0].label, 'Apple'); assert.equal(v[0].reason, 'held_through_missed_frame');   // missed frame: hold
  v = tr.update([obj(3, 0.8)], 800); assert.equal(v.find((x) => x.id === id)!.label, null);                            // contradiction: hide at once
  // low score observation hides too
  const t2 = new LiveTracker(); for (let i = 0; i < 3; i++) t2.update([obj(1, 0.8)], i); assert.equal(t2.update([obj(1, 0.3)], 3)[0].label, null);
  // lost track dies; a new fruit at the same place starts unlabelled with a new id
  const t3 = new LiveTracker(); for (let i = 0; i < 3; i++) t3.update([obj(1, 0.8)], i);
  for (let i = 0; i <= LIVE_TRACKER.maxMissed; i++) t3.update([], 10 + i);
  const nv = t3.update([obj(1, 0.8)], 100); assert.equal(nv.length, 1); assert.notEqual(nv[0].id, 1); assert.equal(nv[0].label, null);
  // IoU drop (jump) = new track, old label not moved
  const t4 = new LiveTracker(); for (let i = 0; i < 3; i++) t4.update([obj(1, 0.8)], i);
  const j = t4.update([obj(1, 0.8, [400, 400, 500, 500])], 3); const moved = j.find((x) => x.box[0] >= 300)!; assert.equal(moved.label, null); assert.notEqual(moved.id, 1);
  // stable ids across frames
  const t5 = new LiveTracker(); const a = t5.update([obj(1, 0.8), obj(0, 0.8, [300, 0, 400, 100])], 0).map((x) => x.id);
  const b = t5.update([obj(0, 0.8, [302, 1, 401, 99]), obj(1, 0.8, [101, 101, 201, 201])], 1).map((x) => x.id).sort(); assert.deepEqual(b, [...a].sort());
});

test('guidance hints reuse existing constants and never touch labels or scores', () => {
  assert.deepEqual(HINT_LIMITS, { minSidePx: 96, h2InputPx: 224, minBlurVar: 15, stableIou: 0.8, minMeanV: 80, maxMeanV: 245, edgeMarginFrac: 0.01 });
  assert.deepEqual(guidanceHints({ sidePx: 95.9 }).map((h) => h.code), ['move_closer']);
  assert.deepEqual(guidanceHints({ sidePx: 96 }), []);
  assert.deepEqual(guidanceHints({ sidePx: 300, closeupCropSidePx: 223 }).map((h) => h.code), ['move_closer']);
  assert.deepEqual(guidanceHints({ sidePx: 300, closeupCropSidePx: 224 }), []);
  assert.deepEqual(guidanceHints({ sidePx: 300, blurVar: 14.9 }).map((h) => h.code), ['hold_steady']);
  assert.deepEqual(guidanceHints({ sidePx: 300, jitterIou: 0.5 }).map((h) => h.code), ['hold_steady']);
  assert.deepEqual(guidanceHints({ sidePx: 300, meanV: 60 }).map((h) => h.text), ['Improve lighting']);
  assert.deepEqual(guidanceHints({ sidePx: 300, meanV: 250 }).map((h) => h.code), ['improve_lighting']);
  assert.deepEqual(guidanceHints({ sidePx: 50, blurVar: 1, meanV: 10, touchesEdge: true }).map((h) => h.code), ['move_closer', 'hold_steady', 'improve_lighting', 'keep_in_view']);
  // labels are produced only by LiveTracker; hints are computed from pixels/geometry afterwards (source check)
  const src = read('src/cv/device/live.ts'); const fn = src.slice(src.indexOf('export function guidanceHints'), src.indexOf('// ---------------------------------------------------------------- quality metrics'));
  assert.doesNotMatch(fn, /shownClass|score|label/);
});

test('quality metrics: Laplacian variance, HSV V, side and edge on known patterns', () => {
  const w = 40, h = 40; const flat = new Uint8Array(w * h * 3).fill(100);
  const q = qualityMetrics(flat, w, h, [5, 5, 35, 35], 2); assert.equal(q.blurVar, 0); assert.equal(Math.round(q.meanV), 100); assert.equal(q.sidePx, 60); assert.equal(q.touchesEdge, false);
  const chk = new Uint8Array(w * h * 3); for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) chk.fill((x + y) % 2 ? 255 : 0, (y * w + x) * 3, (y * w + x) * 3 + 3);
  assert.ok(qualityMetrics(chk, w, h, [0, 0, 40, 40]).blurVar > 1000); assert.equal(qualityMetrics(chk, w, h, [0, 0, 40, 40]).touchesEdge, true);
  assert.equal(laplacianVar([1, 1, 1, 1, 5, 1, 1, 1, 1], 3, 3), 0);   // single interior sample -> variance 0
  assert.equal(boxSide([0, 0, 30, 120]), 60);
  const red = new Uint8Array(4 * 3); for (let i = 0; i < 4; i++) red.set([200, 30, 20], i * 3); assert.equal(qualityMetrics(red, 2, 2, [0, 0, 2, 2]).cropW, 2);
});

test('lifecycle: permission, models, background/foreground, unmount; frame processor only when live + ready + active', () => {
  let s = LIFE_INITIAL; assert.equal(cameraActive(s), false);
  s = lifeReduce(s, { type: 'permission', granted: true }); assert.equal(cameraActive(s), true); assert.equal(frameProcessorActive(s, 'live'), false);
  s = lifeReduce(s, { type: 'models', ok: true }); assert.equal(frameProcessorActive(s, 'live'), true); assert.equal(frameProcessorActive(s, 'tap3'), false);
  s = lifeReduce(s, { type: 'app_state', active: false }); assert.equal(cameraActive(s), false); assert.equal(frameProcessorActive(s, 'live'), false);
  s = lifeReduce(s, { type: 'app_state', active: true }); assert.equal(frameProcessorActive(s, 'live'), true);
  s = lifeReduce(s, { type: 'focus', focused: false }); assert.equal(cameraActive(s), false); s = lifeReduce(s, { type: 'focus', focused: true });
  assert.equal(cameraActive(lifeReduce(s, { type: 'permission', granted: false })), false);
  assert.equal(frameProcessorActive(lifeReduce(s, { type: 'models', ok: false }), 'live'), false);
  assert.equal(cameraActive(lifeReduce(s, { type: 'unmount' })), false);
});

test('fallback toggle: live is the default, tap-3 is optional, no GPU resizer -> tap-3 with a note', () => {
  assert.equal(DEFAULT_SCAN_MODE, 'live');
  assert.deepEqual(effectiveMode('live', true), { mode: 'live', note: null });
  assert.deepEqual(effectiveMode('tap3', true), { mode: 'tap3', note: null });
  assert.equal(effectiveMode('live', false).mode, 'tap3'); assert.match(effectiveMode('live', false).note!, /unavailable/);
  const src = read('responsive/CvDebugScan.tsx');
  assert.match(src, /useState<ScanMode>\(DEFAULT_SCAN_MODE\)/); assert.match(src, /testID="cv-mode-toggle"/);
  // live detection never uses capturePhoto: the only capturePhoto call is inside grabUpright (close-up / tap-3)
  const code = src.split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');
  assert.equal((code.match(/capturePhoto\(/g) ?? []).length, 1);
  const live = code.slice(code.indexOf('const onLiveFrame'), code.indexOf('const onLiveRef')); assert.doesNotMatch(live, /grabUpright|capturePhoto/);
  // ORT sessions loaded once per process and reused
  assert.match(code, /let SESSIONS: Promise/); assert.match(code, /if \(SESSIONS\) return SESSIONS/);
});

test('perf meter: only measured numbers; NSCV perf line', () => {
  let t = 0; const m = createPerfMeter(() => t); m.frame(30); m.skipped(20, 5); m.detection(40, 90); m.detection(60, 120); m.dropped(1); t = 1000;
  const s = m.snapshot(200, 1, null, 50.5);
  assert.deepEqual(s, { windowS: 1, cameraFps: 30, detUps: 2, inferP50: 40, inferP95: 60, e2eP50: 90, e2eP95: 120, skippedBusy: 20, skippedInterval: 5, dropped: 1, intervalMs: 200, thermal: 1, jsHeapMb: null, nativeHeapMb: 50.5 });
  assert.match(perfLine(s), /^NSCV perf window_s=1 camera_fps=30 det_ups=2 infer_p50_ms=40 .* js_heap_mb=- native_heap_mb=50.5$/);
  t = 2000; const e = m.snapshot(200, -1); assert.equal(e.inferP50, null); assert.equal(e.detUps, 0);
});

test('resizer buffer unpacking (RGB / RGBX / row stride) and on-device colour-order check', () => {
  assert.deepEqual([...unpackResized(new Uint8Array([1, 2, 3, 4, 5, 6]), 2, 1).rgb], [1, 2, 3, 4, 5, 6]);
  assert.deepEqual([...unpackResized(new Uint8Array([1, 2, 3, 9, 4, 5, 6, 9]), 2, 1).rgb], [1, 2, 3, 4, 5, 6]);
  assert.deepEqual([...unpackResized(new Uint8Array([1, 2, 3, 4, 5, 6, 0, 7, 8, 9, 10, 11, 12, 0]), 2, 2).rgb], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]);
  assert.throws(() => unpackResized(new Uint8Array(7), 2, 2), /does not fit/);
  assert.deepEqual(meanRgb(new Uint8Array([10, 20, 30, 30, 40, 50]), 2, 1, [0, 0, 2, 1]), [20, 30, 40]);
  assert.equal(colourCheck([200, 60, 40], [180, 50, 30]).verdict, 'ok');
  assert.equal(colourCheck([40, 60, 200], [180, 50, 30]).verdict, 'rb_swapped');
  assert.equal(colourCheck([100, 100, 104], [90, 90, 90]).verdict, 'inconclusive');
});

test('diagnostic records: fields, contested flag, reason codes, rate-limited saves, base64', () => {
  const rec = diagRecord({ path: 'live', tMs: 1, trackId: 4, g3: { classId: 1, score: 0.71234 }, competing: [{ classId: 3, score: 0.3 }], wide: { status: 'identified', classId: 1 },
    h2Top3: [{ classId: 3, p: 0.5 }, { classId: 1, p: 0.3 }, { classId: 12, p: 0.1 }], verify: null, box: [1.4, 2.6, 30, 40], frame: [480, 270],
    quality: { sidePx: 50.2, areaFrac: 0.01, meanV: 140, luma: 120, blurVar: 33.33, touchesEdge: false, cropW: 29, cropH: 38 }, hints: guidanceHints({ sidePx: 50 }), shownLabel: 'Apple' });
  assert.equal(rec.g3_class, 'apple'); assert.equal(rec.g3_score, 0.712); assert.deepEqual(rec.h2_top3, [{ cls: 'citrus', p: 0.5 }, { cls: 'apple', p: 0.3 }, { cls: 'unknown', p: 0.1 }]);
  assert.equal(rec.g3_h2_agree, false); assert.equal(rec.contested, true); assert.equal(rec.reasonCode, 'live_label_wide_policy'); assert.deepEqual(rec.box, [1, 3, 30, 40]);
  assert.deepEqual(rec.hints, ['move_closer:side_50px_lt_quality_min_96']);
  assert.equal(isContested({ g3: { classId: 1, score: 0.9 }, competing: [], wide: { status: 'identified', classId: 1 }, h2Top3: [{ classId: 1, p: 0.9 }], verify: { status: 'verified', classId: 1, evidence: 'wide+h2' } }), false);
  assert.equal(isContested({ g3: null, wide: null, verify: { status: 'unable', reason: 'close_up_contradicts_wide', suggestions: [] } }), true);
  assert.equal(reasonCode({ path: 'closeup', wide: null, verify: { status: 'unable', reason: 'close_up_unknown', suggestions: [] }, shownLabel: null }), 'closeup_unable_close_up_unknown');
  assert.equal(reasonCode({ path: 'closeup', wide: null, verify: { status: 'verified', classId: 1, evidence: 'wide+h2' }, shownLabel: 'Apple' }), 'closeup_verified_wide_h2');
  assert.equal(reasonCode({ path: 'live', wide: { status: 'pending', reason: 'confirming' }, verify: null, shownLabel: null }), 'live_pending_confirming');
  assert.equal(shouldSave(rec, 0), true); assert.equal(shouldSave(rec, DIAG_MAX_SAVES_PER_MIN), false);
  assert.equal(toBase64(new Uint8Array([77, 97, 110])), 'TWFu'); assert.equal(toBase64(new Uint8Array([77, 97])), 'TWE='); assert.equal(toBase64(new Uint8Array([77])), 'TQ==');
  assert.equal(toBase64(new Uint8Array(Buffer.from('hello world!!'))), Buffer.from('hello world!!').toString('base64'));
});

test('close-up from a live track: one still, H2 on the high-res crop, FROZEN_VERIFY P-a unchanged, G3/H2 contradiction abstains', async () => {
  const mk = (h2cls: number) => async (m: 'h2' | 'g3_det', _x: Float32Array, _d: number[]) => {
    if (m === 'g3_det') { const n = 4725, o = new Float32Array(16 * n); const j = 7; o[j] = 240; o[n + j] = 240; o[2 * n + j] = 160; o[3 * n + j] = 160; o[(4 + 1) * n + j] = 0.9; return o; }
    const p = new Float32Array(H2_CLASSES.length).fill(0.08 / 11); p[h2cls] = 0.9; p[12] = 0.02; return p;
  };
  const still = { rgb: new Uint8Array(640 * 480 * 3).fill(128), w: 640, h: 480 };
  const ok = await runCloseupFromTrack(still, [200, 150], [400, 300], { status: 'identified', classId: 1 }, mk(1));
  assert.match(ok.display.title, /^Apple\. Not graded$/); assert.equal(ok.closeup!.agree, true); assert.equal(ok.closeup!.h2Top3[0].classId, 1);
  assert.ok(ok.closeup!.cropSidePx > 0); assert.equal(ok.displayErrors.length, 0);
  const bad = await runCloseupFromTrack(still, [200, 150], [400, 300], { status: 'identified', classId: 1 }, mk(3));
  assert.equal(bad.display.title, 'Unable to identify'); assert.equal(bad.verify!.status, 'unable'); assert.equal((bad.verify as any).reason, 'close_up_contradicts_wide'); assert.equal(bad.closeup!.agree, false);
  const pend = await runCloseupFromTrack(still, [200, 150], [400, 300], { status: 'pending', reason: 'confirming' }, mk(1));
  assert.equal(pend.display.title, 'Unable to identify');
  assert.deepEqual(h2Top3([0.1, 0.6, 0.3]).map((t) => t.classId), [1, 2, 0]);
});

test('J8 screen: no grade / confidence on screen, perf overlay only inside the QA debug layer, Kotlin helpers present', () => {
  const src = read('responsive/CvDebugScan.tsx'); assert.doesNotMatch(src, /Grade\s+[ABC]|confidence|%\s*<\/Text>/i);
  assert.match(src, /import CvPerfOverlay from '\.\/CvPerfOverlay'/);
  assert.doesNotMatch(read('responsive/ScanScreen.tsx'), /CvPerfOverlay/);
  const kt = read('android/app/src/main/java/com/muhammadfaizan/nutrisole/ModelAssetsModule.kt');
  for (const re of [/Log\.i\("NutriSoleCV", line\)/, /currentThermalStatus/, /fun appendDiag/, /fun saveRgbJpeg/, /getExternalFilesDir\(null\)/, /"diag"/]) assert.match(kt, re);
  const perf = read('responsive/CvPerfOverlay.tsx'); assert.match(perf, /this phone/); assert.doesNotMatch(perf, /Grade|confidence/i);
});
