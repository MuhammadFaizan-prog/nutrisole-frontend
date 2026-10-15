// G9 Stage J4: crop-coordinate mapping helpers (additive; camera.ts / closeup.ts / preprocess.ts are unchanged).
// Purpose: map a point or box seen in a model input or a crop back to the analysis frame / full-resolution still /
// display orientation, so overlays, debug logs and the Android phone test can check that the crop the identity model
// saw is the region the user tapped. Pure TypeScript, no React Native imports. No accuracy claim is made here.
import type { Box } from './preprocess.ts';
import { H2_INPUT, H2_RESIZE_SHORT, rh, type CropMode, type Rect, type Rotation } from './camera.ts';
import { rotateBoxNormalized } from './preprocess.ts';

/** Box in crop pixels -> box in the image the crop was cut from (still or frame pixels). */
export function cropToOriginalBox(b: Box, crop: Rect): Box {
  return [b[0] + crop.x, b[1] + crop.y, b[2] + crop.x, b[3] + crop.y];
}

/** Box in original pixels -> box in crop pixels (not clipped; values outside [0,w]x[0,h] lie outside the crop). */
export function originalToCropBox(b: Box, crop: Rect): Box {
  return [b[0] - crop.x, b[1] - crop.y, b[2] - crop.x, b[3] - crop.y];
}

/** Geometry of h2Input(): crop (w x h) -> resized (ow x oh) -> 224 window at (x0, y0). Same arithmetic as camera.h2Input. */
export function h2Geometry(w: number, h: number, mode: CropMode = 'stageH'): { ow: number; oh: number; x0: number; y0: number; sx: number; sy: number } {
  if (!(w > 0 && h > 0)) throw new Error('crop size must be positive');
  if (mode === 'stageH') {
    const sc = H2_RESIZE_SHORT / Math.min(w, h);
    const ow = Math.max(H2_RESIZE_SHORT, rh(w * sc)); const oh = Math.max(H2_RESIZE_SHORT, rh(h * sc));
    return { ow, oh, x0: Math.floor((ow - H2_INPUT) / 2), y0: Math.floor((oh - H2_INPUT) / 2), sx: ow / w, sy: oh / h };
  }
  return { ow: H2_INPUT, oh: H2_INPUT, x0: 0, y0: 0, sx: H2_INPUT / w, sy: H2_INPUT / h };
}

/** Point in the 224x224 H2 input -> point in crop pixels. */
export function h2InputToCropPoint(p: [number, number], w: number, h: number, mode: CropMode = 'stageH'): [number, number] {
  const g = h2Geometry(w, h, mode);
  return [(p[0] + g.x0) / g.sx, (p[1] + g.y0) / g.sy];
}

/** Region of the crop actually seen by H2 (stageH centre-crops the resized crop), in crop pixels. */
export function h2VisibleCropRect(w: number, h: number, mode: CropMode = 'stageH'): Box {
  const a = h2InputToCropPoint([0, 0], w, h, mode); const b = h2InputToCropPoint([H2_INPUT, H2_INPUT], w, h, mode);
  return [a[0], a[1], b[0], b[1]];
}

/** Pixel box in a sensor-oriented frame -> normalised box in display orientation (clockwise rotation, as the preview shows it). */
export function frameBoxToDisplayNormalized(b: Box, frameW: number, frameH: number, rotation: Rotation = 0, mirrored = false): Box {
  const n: Box = [b[0] / frameW, b[1] / frameH, b[2] / frameW, b[3] / frameH];
  const r = rotateBoxNormalized(n, rotation);
  return mirrored ? [1 - r[2], r[1], 1 - r[0], r[3]] : r;
}

/** True when box `inner` lies inside `outer` (tolerance in pixels). Used by the phone-test debug log as a sanity check. */
export function boxInside(inner: Box, outer: Box, tol = 1e-6): boolean {
  return inner[0] >= outer[0] - tol && inner[1] >= outer[1] - tol && inner[2] <= outer[2] + tol && inner[3] <= outer[3] + tol;
}
