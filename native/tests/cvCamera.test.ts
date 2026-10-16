// G9 Stage I: camera integration layer parity with the Python reference (ml/eval/camera_io.py) + model I/O contract.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { tapToFrame, frameToStillBox, identityCrop, h2Input, checkModelIO, stillCropPlan, rotatePoint, MODEL_IO, type Rotation } from '../src/cv/pipeline/camera.ts';
import { cropRect } from '../src/cv/pipeline/closeup.ts';
import type { Box } from '../src/cv/pipeline/preprocess.ts';

const F = JSON.parse(readFileSync(new URL('../../ml/eval/fixtures/camera_parity.json', import.meta.url), 'utf8'));

test('preview tap -> analysis frame matches Python (rotation, mirror, cover/letterbox, letterbox bars)', () => {
  assert.ok(F.taps.length >= 50);
  for (const c of F.taps) {
    const r = tapToFrame(c.tap, c.view[0], c.view[1], c.frame[0], c.frame[1], c.rotation as Rotation, c.mirrored, c.mode);
    if (c.out === null) { assert.equal(r, null); continue; }
    assert.ok(r !== null); r!.forEach((v, i) => assert.ok(Math.abs(v - c.out[i]) < 1e-9, `${JSON.stringify(c)} ${v}`));
  }
});

test('rotations invert', () => {
  for (const d of [0, 90, 180, 270] as Rotation[]) {
    const p = rotatePoint(rotatePoint([0.2, 0.7], d), ((360 - d) % 360) as Rotation); assert.ok(Math.abs(p[0] - 0.2) < 1e-12 && Math.abs(p[1] - 0.7) < 1e-12);
  }
});

test('16:9 analysis frame maps into the 4:3 still (centre crop of one sensor)', () => {
  assert.deepEqual(frameToStillBox([0, 0, 1920, 1080], 1920, 1080, 4000, 3000).map((v) => Math.round(v * 1e6) / 1e6), [0, 375, 4000, 2625]);
});

test('identity crops match Python; stageH equals the Stage G cropRect', () => {
  for (const c of F.crops) {
    const r = identityCrop(c.box as Box, c.W, c.H, c.mode); assert.deepEqual(r, c.out, JSON.stringify(c));
    if (c.mode === 'stageH') { const g = cropRect(c.box as Box, c.W, c.H, 0.08); assert.deepEqual([g.x, g.y, g.w, g.h], [r.x, r.y, r.w, r.h]); }
    else { assert.equal(r.w, r.h); assert.ok(r.x >= 0 && r.y >= 0 && r.x + r.w <= c.W && r.y + r.h <= c.H); }
  }
});

test('preview tap -> full-resolution still crop plan matches Python', () => {
  for (const c of F.plans) {
    const r = stillCropPlan(c.tap, c.view, c.frame, c.still, c.boxes, c.rotation as Rotation, c.mirrored, c.mode, c.cropMode);
    if (c.out === null) { assert.equal(r, null); continue; }
    assert.ok(r); assert.equal(r!.source, c.out.source); assert.deepEqual(r!.crop, c.out.crop);
    r!.stillBox.forEach((v, i) => assert.ok(Math.abs(v - c.out.stillBox[i]) < 1e-6));
    assert.ok(Math.abs(r!.sidePx - c.out.sidePx) < 1e-3);
  }
});

test('H2 input tensor equals Python (shape, sampled values, sum)', () => {
  for (const c of F.h2) {
    const rgb = new Uint8Array(Buffer.from(c.rgb, 'base64')); const x = h2Input(rgb, c.w, c.h, c.mode);
    assert.equal(x.length, 3 * 224 * 224);
    c.idx.forEach((k: number, i: number) => assert.ok(Math.abs(x[k] - c.vals[i]) < 1e-4, `${c.w}x${c.h} ${k}: ${x[k]} vs ${c.vals[i]}`));
    let s = 0; for (const v of x) s += v; assert.ok(Math.abs(s - c.sum) / Math.max(1, Math.abs(c.sum)) < 1e-5);
  }
});

test('model I/O: real ONNX metadata passes the contract; a wrong layout fails', () => {
  for (const k of ['h2', 'g3_det', 'condition'] as const) assert.deepEqual(checkModelIO(k, F.io[k]), [], k);
  assert.ok(checkModelIO('h2', { inputs: [{ name: 'images', shape: [1, 224, 224, 3] }], outputs: [{ name: 'probs', shape: [1, 12] }] }).length >= 2);
  assert.deepEqual(MODEL_IO.h2.inputs[0].shape, ['n', 3, 224, 224]);
});

import { targetedReasons, DEFAULT_TARGETED, occlusionReasons, FROZEN_OCC } from '../src/cv/pipeline/verify.ts';
test('targeted occlusion reasons mirror Python and only add rejections', () => {
  const t = { sideTouch: 0.99, skinFrac: 0.9, specFrac: 0.9, hullGap: 5 };
  assert.deepEqual(targetedReasons(t), []); assert.deepEqual(targetedReasons(t, DEFAULT_TARGETED), []);
  assert.deepEqual(targetedReasons(t, { maxSideTouch: 0.5 }), ['cut_by_box']);
  assert.deepEqual(targetedReasons(t, { maxSkinFrac: 0.2, maxSpecFrac: 0.2, maxHullGap: 0.3 }), ['hand_near_item', 'packaging_glare', 'outline_bite']);
  assert.equal(FROZEN_OCC.minSolidity, 0.8); assert.equal(FROZEN_OCC.maxBorderFrac, 0.7);  // Stage H frozen rule untouched
  assert.ok(occlusionReasons({ solidity: 0.5, ellipseIoU: 0.9, straightFrac: 0, borderFrac: 0, segAgree: 1, flatFrac: 0, colourSplit: 0 }, FROZEN_OCC).includes('outline_incomplete'));
});
