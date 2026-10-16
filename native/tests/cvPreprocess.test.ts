import assert from 'node:assert/strict';
import { test } from 'node:test';
import { computeTransform, srcToDst, dstToSrc, srcToScreen, rotateBoxNormalized, normalizeBox, visibleSourceRect, iou, toChwFloat, type Box } from '../src/cv/pipeline/preprocess.ts';

const close = (a: number[], b: number[], tol = 1e-6) => a.forEach((v, i) => assert.ok(Math.abs(v - b[i]) <= tol, `${a} vs ${b}`));

test('letterbox matches Ultralytics LetterBox for portrait and landscape frames', () => {
  const t = computeTransform(1080, 1920, 384, 384, 'letterbox');
  assert.equal(Math.round(1080 * (384 / 1920)), 216);
  close([t.scaleX * 1080, t.scaleY * 1920, t.padX, t.padY], [216, 384, 84, 0]);
  const l = computeTransform(640, 480, 320, 320, 'letterbox');
  close([l.padX, l.padY, l.scaleX], [0, 40, 0.5]);
});

test('letterbox and cover round-trip src -> model -> src for several frame sizes', () => {
  const sizes: Array<[number, number]> = [[1080, 1920], [1920, 1080], [720, 1280], [480, 640], [3000, 4000], [384, 384]];
  const box: Box = [0.21, 0.33, 0.67, 0.71];
  for (const [w, h] of sizes) for (const mode of ['letterbox', 'cover', 'stretch'] as const) {
    const t = computeTransform(w, h, 384, 384, mode);
    const src: Box = [box[0] * w, box[1] * h, box[2] * w, box[3] * h];
    close(dstToSrc(srcToDst(src, t), t, false), src, 1e-6);
  }
});

test('cover crops the long side symmetrically and clips boxes outside the visible area', () => {
  const t = computeTransform(1080, 1920, 384, 384, 'cover');
  const vis = visibleSourceRect(t);
  close(vis, [0, 420, 1080, 1500], 1e-6);
  const clipped = dstToSrc([-50, -50, 100, 100], t);
  assert.ok(clipped[0] >= 0 && clipped[1] >= 0);
});

test('screen mapping for a cover preview on phones of different aspect ratios', () => {
  // 4:3 sensor frame (portrait 3000x4000) shown full-screen on a 20:9 phone (412x915 dp)
  const b = srcToScreen([1500 - 300, 2000 - 300, 1500 + 300, 2000 + 300], 3000, 4000, 412, 915, 'cover');
  const cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2;
  close([cx, cy], [206, 457.5], 1e-6); // centred object stays centred
  const s = 915 / 4000;
  close([b[2] - b[0], b[3] - b[1]], [600 * s, 600 * s], 1e-6); // uniform scale (no stretch)
  // contain preview on a tablet
  const c = srcToScreen([0, 0, 3000, 4000], 3000, 4000, 800, 1280, 'letterbox');
  close(c, [0, 106.66666666666669, 800, 1173.3333333333333], 1e-6);
});

test('rotation of normalized boxes (sensor landscape -> portrait display)', () => {
  const b: Box = [0.1, 0.2, 0.3, 0.6];
  close(rotateBoxNormalized(b, 90), [0.4, 0.1, 0.8, 0.3]);
  close(rotateBoxNormalized(rotateBoxNormalized(b, 90), 270), b);
  close(rotateBoxNormalized(rotateBoxNormalized(b, 180), 180), b);
  close(rotateBoxNormalized(rotateBoxNormalized(rotateBoxNormalized(rotateBoxNormalized(b, 90), 90), 90), 90), b);
  close(normalizeBox([10, 20, 30, 40], 100, 200), [0.1, 0.1, 0.3, 0.2]);
});

test('iou and CHW normalisation', () => {
  assert.equal(iou([0, 0, 2, 2], [1, 1, 3, 3]), 1 / 7);
  assert.equal(iou([0, 0, 1, 1], [2, 2, 3, 3]), 0);
  const rgb = new Uint8Array([255, 0, 51, 0, 255, 102]);
  close(Array.from(toChwFloat(rgb, 2, 1)), [1, 0, 0, 1, 0.2, 0.4]);
  assert.throws(() => toChwFloat(rgb, 3, 1));
});

test('letterbox transform equals the Python gauntlet (ml/eval/geometry.py) incl. odd padding', async () => {
  const { readFileSync } = await import('node:fs');
  const cases = JSON.parse(readFileSync(new URL('../../ml/eval/fixtures/letterbox_parity.json', import.meta.url), 'utf8')) as Array<{ w: number; h: number; S: number; t: { scaleX: number; scaleY: number; padX: number; padY: number }; src_box: Box; dst_box: Box }>;
  for (const c of cases) {
    const t = computeTransform(c.w, c.h, c.S, c.S, 'letterbox');
    close([t.scaleX, t.scaleY, t.padX, t.padY], [c.t.scaleX, c.t.scaleY, c.t.padX, c.t.padY], 1e-9);
    close(srcToDst(c.src_box, t), c.dst_box, 1e-6);
  }
});
