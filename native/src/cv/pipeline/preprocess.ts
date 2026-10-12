// Geometry for camera frame -> model input -> screen overlay. Pure math, unit tested.
// Must match ml/eval/geometry.py (the Python gauntlet uses the same conventions).
//
// Conventions:
//  - Boxes are [x1, y1, x2, y2] in pixels of the space they belong to (or normalized
//    [0,1] where the name says so).
//  - letterbox: scale = min(dst/srcW, dst/srcH), image centred, padding value 114,
//    new size and left/top pad rounded exactly like Ultralytics LetterBox(center=True)
//    and ml/eval/geometry.py.
//  - cover: scale = max(...), centred crop (what VisionCamera resizer scaleMode 'cover'
//    and an on-screen preview with resizeMode 'cover' do).
//  - Rotation: sensor frames on Android are usually landscape; `rotateBoxNormalized`
//    turns a normalized box by 90/180/270 degrees clockwise into the display orientation.

export type Box = [number, number, number, number];
export type ResizeMode = 'letterbox' | 'cover' | 'stretch';

export type Transform = {
  mode: ResizeMode;
  srcW: number; srcH: number; dstW: number; dstH: number;
  scaleX: number; scaleY: number; // src px -> dst px
  padX: number; padY: number;      // dst px offset (negative for cover = cropped)
};

export function computeTransform(srcW: number, srcH: number, dstW: number, dstH: number, mode: ResizeMode): Transform {
  if (!(srcW > 0 && srcH > 0 && dstW > 0 && dstH > 0)) throw new Error('sizes must be positive');
  if (mode === 'stretch') return { mode, srcW, srcH, dstW, dstH, scaleX: dstW / srcW, scaleY: dstH / srcH, padX: 0, padY: 0 };
  const s = mode === 'letterbox' ? Math.min(dstW / srcW, dstH / srcH) : Math.max(dstW / srcW, dstH / srcH);
  if (mode === 'letterbox') {
    // Ultralytics: new_unpad = round(w*r), round(h*r); dw,dh = (dst-new)/2
    const nw = Math.round(srcW * s);
    const nh = Math.round(srcH * s);
    // Ultralytics rounds the left/top pad: round(dw - 0.1)
    return { mode, srcW, srcH, dstW, dstH, scaleX: nw / srcW, scaleY: nh / srcH, padX: Math.round((dstW - nw) / 2 - 0.1), padY: Math.round((dstH - nh) / 2 - 0.1) };
  }
  return { mode, srcW, srcH, dstW, dstH, scaleX: s, scaleY: s, padX: (dstW - srcW * s) / 2, padY: (dstH - srcH * s) / 2 };
}

/** Source-pixel box -> model-input-pixel box. */
export function srcToDst(b: Box, t: Transform): Box {
  return [b[0] * t.scaleX + t.padX, b[1] * t.scaleY + t.padY, b[2] * t.scaleX + t.padX, b[3] * t.scaleY + t.padY];
}

/** Model-input-pixel box -> source-pixel box, clipped to the source image. */
export function dstToSrc(b: Box, t: Transform, clip = true): Box {
  const out: Box = [(b[0] - t.padX) / t.scaleX, (b[1] - t.padY) / t.scaleY, (b[2] - t.padX) / t.scaleX, (b[3] - t.padY) / t.scaleY];
  if (!clip) return out;
  return [clamp(out[0], 0, t.srcW), clamp(out[1], 0, t.srcH), clamp(out[2], 0, t.srcW), clamp(out[3], 0, t.srcH)];
}

/** Visible source region for a cover crop (what the model / preview actually sees). */
export function visibleSourceRect(t: Transform): Box {
  return dstToSrc([0, 0, t.dstW, t.dstH], t, true);
}

/** Map a source-pixel box to screen points for a preview drawn with the given mode. */
export function srcToScreen(b: Box, srcW: number, srcH: number, viewW: number, viewH: number, mode: Exclude<ResizeMode, 'stretch'> = 'cover'): Box {
  const t = computeTransformExact(srcW, srcH, viewW, viewH, mode);
  const d = srcToDst(b, t);
  return [clamp(d[0], 0, viewW), clamp(d[1], 0, viewH), clamp(d[2], 0, viewW), clamp(d[3], 0, viewH)];
}

/** Like computeTransform but without Ultralytics rounding (for continuous screen layout). */
export function computeTransformExact(srcW: number, srcH: number, dstW: number, dstH: number, mode: Exclude<ResizeMode, 'stretch'>): Transform {
  const s = mode === 'letterbox' ? Math.min(dstW / srcW, dstH / srcH) : Math.max(dstW / srcW, dstH / srcH);
  return { mode, srcW, srcH, dstW, dstH, scaleX: s, scaleY: s, padX: (dstW - srcW * s) / 2, padY: (dstH - srcH * s) / 2 };
}

/** Rotate a normalized box clockwise by 0/90/180/270 degrees (sensor -> display). */
export function rotateBoxNormalized(b: Box, degrees: 0 | 90 | 180 | 270): Box {
  const [x1, y1, x2, y2] = b;
  switch (degrees) {
    case 0: return [x1, y1, x2, y2];
    case 90: return [1 - y2, x1, 1 - y1, x2];
    case 180: return [1 - x2, 1 - y2, 1 - x1, 1 - y1];
    case 270: return [y1, 1 - x2, y2, 1 - x1];
  }
}

export function normalizeBox(b: Box, w: number, h: number): Box {
  return [clamp(b[0] / w, 0, 1), clamp(b[1] / h, 0, 1), clamp(b[2] / w, 0, 1), clamp(b[3] / h, 0, 1)];
}

export function iou(a: Box, b: Box): number {
  const ix = Math.max(0, Math.min(a[2], b[2]) - Math.max(a[0], b[0]));
  const iy = Math.max(0, Math.min(a[3], b[3]) - Math.max(a[1], b[1]));
  const inter = ix * iy;
  const ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter;
  return ua > 0 ? inter / ua : 0;
}

/** RGB uint8 HWC -> float32 CHW in [0,1] (Ultralytics normalisation: /255, no mean/std). */
export function toChwFloat(rgb: Uint8Array, w: number, h: number): Float32Array {
  if (rgb.length !== w * h * 3) throw new Error('rgb buffer size mismatch');
  const out = new Float32Array(w * h * 3);
  const plane = w * h;
  for (let i = 0; i < plane; i++) {
    out[i] = rgb[i * 3] / 255;
    out[plane + i] = rgb[i * 3 + 1] / 255;
    out[2 * plane + i] = rgb[i * 3 + 2] / 255;
  }
  return out;
}

function clamp(v: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, v));
}
