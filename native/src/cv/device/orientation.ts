// G9 Stage J5: photo orientation / mirroring -> the existing camera.ts / cropmap.ts geometry. Pure.
// VisionCamera 5 Photo.orientation: 'up' | 'right' | 'down' | 'left' ('right' = content rotated 90 deg clockwise); Photo.toImage()
// applies orientation and mirroring, so the debug pipeline works on an UPRIGHT image that matches the preview. These helpers exist
// for the raw (not-yet-rotated) path and for the NSCV log.
import type { Rotation, Size } from '../pipeline/camera.ts';
import { stillCropPlan, type StillCropPlan } from '../pipeline/camera.ts';
import { srcToScreen, type Box } from '../pipeline/preprocess.ts';

export type CameraOrientation = 'up' | 'right' | 'down' | 'left';
export const orientationToRotation = (o: CameraOrientation): Rotation => ({ up: 0, right: 90, down: 180, left: 270 } as const)[o];
export const uprightSize = (w: number, h: number, o: CameraOrientation): Size => (o === 'left' || o === 'right' ? [h, w] : [w, h]);

/** Tap on the preview (view points, preview resizeMode 'cover') -> crop plan on the upright still. The still is already rotated and
 *  mirrored like the preview, so rotation 0 / mirrored false here; frameBoxes are detector boxes in still pixels. */
export function planTapOnUprightStill(tap: [number, number], view: Size, still: Size, stillBoxes: Box[]): StillCropPlan | null {
  return stillCropPlan(tap, view, still, still, stillBoxes, 0, false, 'cover');
}

/** Raw sensor-oriented still (not yet rotated): use the frame rotation + mirror so the tap still lands on the right pixels. */
export function planTapOnRawStill(tap: [number, number], view: Size, rawStill: Size, o: CameraOrientation, mirrored: boolean): StillCropPlan | null {
  return stillCropPlan(tap, view, rawStill, rawStill, [], orientationToRotation(o), mirrored, 'cover');
}

/** Still-pixel box -> on-screen rectangle (preview 'cover'), for drawing. */
export function stillBoxToView(b: Box, still: Size, view: Size): { left: number; top: number; width: number; height: number } {
  const s = srcToScreen(b, still[0], still[1], view[0], view[1], 'cover');
  return { left: s[0], top: s[1], width: Math.max(0, s[2] - s[0]), height: Math.max(0, s[3] - s[1]) };
}
