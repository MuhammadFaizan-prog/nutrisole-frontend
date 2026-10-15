// G9 Stage J5: raw pixel buffers from react-native-nitro-image (Image.toRawPixelData) -> tightly packed RGB, crops and model inputs.
// Pure TypeScript; formats follow nitro-image PixelFormat. A buffer whose size does not match width*height*bpp is refused (no guessing
// about row padding).
import { resizeBilinear, type Rect } from '../pipeline/camera.ts';
import { letterboxTransform, DETECTOR_INPUT } from '../pipeline/closeup.ts';

export type PixelFormat = 'ARGB' | 'BGRA' | 'ABGR' | 'RGBA' | 'XRGB' | 'BGRX' | 'XBGR' | 'RGBX' | 'RGB' | 'BGR' | 'unknown';
const ORDER: Record<Exclude<PixelFormat, 'unknown'>, { bpp: number; r: number; g: number; b: number }> = {
  RGBA: { bpp: 4, r: 0, g: 1, b: 2 }, RGBX: { bpp: 4, r: 0, g: 1, b: 2 }, BGRA: { bpp: 4, r: 2, g: 1, b: 0 }, BGRX: { bpp: 4, r: 2, g: 1, b: 0 },
  ARGB: { bpp: 4, r: 1, g: 2, b: 3 }, XRGB: { bpp: 4, r: 1, g: 2, b: 3 }, ABGR: { bpp: 4, r: 3, g: 2, b: 1 }, XBGR: { bpp: 4, r: 3, g: 2, b: 1 },
  RGB: { bpp: 3, r: 0, g: 1, b: 2 }, BGR: { bpp: 3, r: 2, g: 1, b: 0 },
};

export function rawToRgb(buffer: ArrayBuffer | Uint8Array, w: number, h: number, format: PixelFormat): Uint8Array {
  if (format === 'unknown' || !(format in ORDER)) throw new Error(`unsupported pixel format ${format}`);
  const o = ORDER[format]; const src = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
  if (src.length !== w * h * o.bpp) throw new Error(`buffer ${src.length} bytes != ${w}x${h}x${o.bpp} (row padding not supported)`);
  const out = new Uint8Array(w * h * 3);
  for (let i = 0, j = 0; i < w * h; i++, j += o.bpp) { out[i * 3] = src[j + o.r]; out[i * 3 + 1] = src[j + o.g]; out[i * 3 + 2] = src[j + o.b]; }
  return out;
}

/** Integer crop of an HWC RGB buffer (rect clamped to the image; empty crop refused). */
export function cropRgb(rgb: Uint8Array, w: number, h: number, r: Rect): { rgb: Uint8Array; w: number; h: number } {
  const x0 = Math.max(0, Math.floor(r.x)); const y0 = Math.max(0, Math.floor(r.y));
  const x1 = Math.min(w, Math.floor(r.x + r.w)); const y1 = Math.min(h, Math.floor(r.y + r.h));
  const cw = x1 - x0; const ch = y1 - y0;
  if (cw <= 0 || ch <= 0) throw new Error('empty crop');
  const out = new Uint8Array(cw * ch * 3);
  for (let y = 0; y < ch; y++) out.set(rgb.subarray(((y0 + y) * w + x0) * 3, ((y0 + y) * w + x1) * 3), y * cw * 3);
  return { rgb: out, w: cw, h: ch };
}

/** G3 detector input: Ultralytics-style letterbox (pad 114, same rounding as closeup.letterboxTransform), /255, NCHW float32. */
export function detectorInput(rgb: Uint8Array, w: number, h: number, dst = DETECTOR_INPUT): Float32Array {
  const t = letterboxTransform(w, h, dst); const nw = Math.round(w * t.sx); const nh = Math.round(h * t.sy);
  const r = resizeBilinear(rgb, w, h, nw, nh); const N = dst * dst; const out = new Float32Array(3 * N).fill(114 / 255);
  for (let y = 0; y < nh; y++) for (let x = 0; x < nw; x++) {
    const dx = x + t.px; const dy = y + t.py;
    if (dx < 0 || dy < 0 || dx >= dst || dy >= dst) continue;
    for (let c = 0; c < 3; c++) out[c * N + dy * dst + dx] = r[(y * nw + x) * 3 + c] / 255;
  }
  return out;
}

/** Softmax guard: H2 exports softmax already (MODEL_IO.h2.output). Returns probabilities unchanged when they already sum to ~1. */
export function asProbs(v: ArrayLike<number>): number[] {
  const a = Array.from(v); const s = a.reduce((x, y) => x + y, 0);
  if (a.every((x) => x >= 0) && Math.abs(s - 1) < 1e-3) return a;
  const m = Math.max(...a); const e = a.map((x) => Math.exp(x - m)); const z = e.reduce((x, y) => x + y, 0); return e.map((x) => x / z);
}
