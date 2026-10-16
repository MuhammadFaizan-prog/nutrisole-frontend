// G9 Stage J4: crop-coordinate mapping (frame -> crop -> original, rotation/orientation, letterbox). Pure maths, no device.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { computeTransform, srcToDst, dstToSrc, rotateBoxNormalized, type Box } from '../src/cv/pipeline/preprocess.ts';
import { tapToFrame, frameToStillBox, identityCrop, stillCropPlan, rotatePoint, H2_INPUT, type Rotation } from '../src/cv/pipeline/camera.ts';
import { detectorToFrame } from '../src/cv/pipeline/closeup.ts';
import { cropToOriginalBox, originalToCropBox, h2Geometry, h2InputToCropPoint, h2VisibleCropRect, frameBoxToDisplayNormalized, boxInside } from '../src/cv/pipeline/cropmap.ts';

const near = (a: number[], b: number[], tol = 1e-6) => a.every((v, i) => Math.abs(v - b[i]) <= tol);
const ROT: Rotation[] = [0, 90, 180, 270];

test('letterbox: source -> 480 input -> source round-trips; pad bars clamp to the image', () => {
  for (const [w, h] of [[1920, 1080], [1080, 1920], [640, 480], [4000, 3000], [480, 480]]) {
    const t = computeTransform(w, h, 480, 480, 'letterbox');
    const b: Box = [w * 0.1, h * 0.2, w * 0.7, h * 0.9];
    assert.ok(near(dstToSrc(srcToDst(b, t), t), b, 1e-6), `${w}x${h}`);
    // a box drawn entirely in the top pad bar maps to a zero-height box on the image edge
    if (t.padY > 1) { const r = dstToSrc([10, 0, 100, t.padY - 0.5], t); assert.equal(r[1], 0); assert.equal(r[3], 0); }
    // detector box -> frame agrees with the generic transform (closeup.detectorToFrame uses Python rounding)
    const d = srcToDst(b, t); assert.ok(near(detectorToFrame(d, w, h), b, 1e-6));
  }
});

test('rotation: four 90 degree turns are the identity; 90 then 270 inverts; box stays ordered', () => {
  const b: Box = [0.1, 0.2, 0.45, 0.8];
  for (const d of ROT) {
    const r = rotateBoxNormalized(b, d);
    assert.ok(r[2] > r[0] && r[3] > r[1]);
    assert.ok(near(rotateBoxNormalized(r, ((360 - d) % 360) as Rotation), b, 1e-12));
  }
  let r = b; for (let i = 0; i < 4; i++) r = rotateBoxNormalized(r, 90); assert.ok(near(r, b, 1e-12));
});

test('display orientation: a frame box drawn on screen contains the frame point the tap maps to', () => {
  const frame: [number, number] = [1280, 720]; const view: [number, number] = [400, 800]; let checked = 0;
  for (const rot of ROT) for (const mir of [false, true]) {
    const box: Box = [500, 200, 700, 450];
    const disp = frameBoxToDisplayNormalized(box, frame[0], frame[1], rot, mir);
    // centre of the box on screen, with the preview stretched over the view (cover mode with matching aspect after rotation)
    const [dw, dh] = rot === 90 || rot === 270 ? [frame[1], frame[0]] : frame;
    const s = Math.max(view[0] / dw, view[1] / dh); const px = (view[0] - dw * s) / 2; const py = (view[1] - dh * s) / 2;
    const cx = ((disp[0] + disp[2]) / 2) * dw * s + px; const cy = ((disp[1] + disp[3]) / 2) * dh * s + py;
    const p = tapToFrame([cx, cy], view[0], view[1], frame[0], frame[1], rot, mir, 'cover');
    if (p === null) continue;   // centre may fall outside the cover crop for some rotations
    const fx = p[0] * frame[0]; const fy = p[1] * frame[1];
    assert.ok(fx >= box[0] - 1e-6 && fx <= box[2] + 1e-6 && fy >= box[1] - 1e-6 && fy <= box[3] + 1e-6, `rot ${rot} mirror ${mir}: ${fx},${fy}`); checked++;
  }
  assert.ok(checked >= 6, `only ${checked} orientation cases checked`);
});

test('frame -> still: same aspect scales linearly; 16:9 frame sits in the 4:3 still centre band', () => {
  assert.ok(near(frameToStillBox([64, 48, 320, 240], 640, 480, 4000, 3000), [400, 300, 2000, 1500], 1e-9));
  const s = frameToStillBox([0, 0, 1920, 1080], 1920, 1080, 4000, 3000);
  assert.ok(near(s, [0, 375, 4000, 2625], 1e-9));
});

test('crop <-> original round-trip and the H2 224 window maps back inside the crop', () => {
  const W = 4000, H = 3000; const still: Box = [1200, 900, 1800, 1500];
  for (const mode of ['stageH', 'square'] as const) {
    const c = identityCrop(still, W, H, mode);
    const inCrop = originalToCropBox(still, c); assert.ok(near(cropToOriginalBox(inCrop, c), still));
    assert.ok(boxInside(still, [c.x, c.y, c.x + c.w, c.y + c.h]), `${mode} crop must contain the box`);
    const vis = h2VisibleCropRect(c.w, c.h, mode);
    assert.ok(vis[0] >= -1e-9 && vis[1] >= -1e-9 && vis[2] <= c.w + 1e-9 && vis[3] <= c.h + 1e-9);
    const centre = h2InputToCropPoint([H2_INPUT / 2, H2_INPUT / 2], c.w, c.h, mode);
    assert.ok(Math.abs(centre[0] - c.w / 2) < 1.5 && Math.abs(centre[1] - c.h / 2) < 1.5, `${mode} centre ${centre}`);
  }
});

test('H2 geometry matches h2Input arithmetic for a landscape crop (short side 256, centre 224)', () => {
  const g = h2Geometry(300, 200);
  assert.deepEqual([g.ow, g.oh, g.x0, g.y0], [384, 256, 80, 16]);
  assert.ok(near(h2InputToCropPoint([0, 0], 300, 200), [62.5, 12.5], 1e-9));
  assert.throws(() => h2Geometry(0, 10));
});

test('end to end: preview tap -> still crop contains the tapped point mapped to the still (portrait, rotated sensor)', () => {
  const view: [number, number] = [412, 915]; const frame: [number, number] = [1920, 1080]; const still: [number, number] = [4032, 3024];
  for (const rot of [90, 270] as Rotation[]) {
    const tap: [number, number] = [206, 457];
    const plan = stillCropPlan(tap, view, frame, still, [], rot, false, 'cover', 'stageH');
    assert.ok(plan);
    const fp = plan!.framePoint; const sp = frameToStillBox([fp[0] * frame[0], fp[1] * frame[1], fp[0] * frame[0], fp[1] * frame[1]], frame[0], frame[1], still[0], still[1]);
    const c = plan!.crop;
    assert.ok(sp[0] >= c.x && sp[0] <= c.x + c.w && sp[1] >= c.y && sp[1] <= c.y + c.h, `rot ${rot}`);
    assert.ok(near(rotatePoint(rotatePoint(fp, rot), ((360 - rot) % 360) as Rotation), fp, 1e-12));
  }
});
