// G9 Stage I (I4): RN camera integration layer, pure TypeScript (no runtime deps). EXACT mirror of ml/eval/camera_io.py
// (parity: tests/cvCamera.test.ts replays ml/eval/fixtures/camera_parity.json).
// Preview tap -> analysis frame -> full-resolution still; identity crop on the still; H2 input tensor; model I/O contract check.
// Device assumptions (preview 'cover' over the rotated sensor buffer, frame and still are centre crops of one sensor FOV) are
// checked by the Android steps in docs/cv/gauntlet/G9_stageI_android_test.md. No FPS claim is made anywhere.
import { roiFromTap } from './closeup.ts';
import type { Box } from './preprocess.ts';

export const H2_INPUT = 224;
export const H2_RESIZE_SHORT = 256;
export const IMAGENET_MEAN = [0.485, 0.456, 0.406] as const;
export const IMAGENET_STD = [0.229, 0.224, 0.225] as const;
export type Rotation = 0 | 90 | 180 | 270;
export type Size = [number, number];
type Dim = number | string;
type TensorSpec = { name: string | null; shape: Dim[]; type: 'float32' };
export type ModelSpec = { file: string; inputs: TensorSpec[]; outputs: TensorSpec[]; colour: string; norm: string; output: string };
export const MODEL_IO: Record<'h2' | 'g3_det' | 'condition', ModelSpec> = {
  h2: { file: 'h2_mnv3s.onnx', inputs: [{ name: 'images', shape: ['n', 3, 224, 224], type: 'float32' }], outputs: [{ name: 'probs', shape: ['n', 13], type: 'float32' }],
    colour: 'RGB', norm: 'imagenet', output: 'softmax (13 = 12 classes + unknown at index 12)' },
  g3_det: { file: 'det_yolo11n_640_raw.onnx', inputs: [{ name: null, shape: [1, 3, 480, 480], type: 'float32' }], outputs: [{ name: null, shape: [1, 16, 4725], type: 'float32' }],
    colour: 'RGB', norm: '/255 letterbox 114', output: 'raw YOLO (4 box + 12 class)' },
  condition: { file: 'E_224_e15_b64_sgd01.onnx', inputs: [{ name: null, shape: [1, 3, 224, 224], type: 'float32' }], outputs: [{ name: null, shape: [1, 2], type: 'float32' }],
    colour: 'RGB', norm: 'see Stage G', output: 'fresh/rotten (grades not displayed)' },
};

/** Half-up rounding, identical to Python floor(x + 0.5). */
export const rh = (x: number) => Math.floor(x + 0.5);

export function rotatePoint(p: [number, number], deg: Rotation): [number, number] {
  const [x, y] = p;
  switch (deg) {
    case 0: return [x, y];
    case 90: return [1 - y, x];
    case 180: return [1 - x, 1 - y];
    case 270: return [y, 1 - x];
  }
}

/** Tap in preview points -> normalised point in the analysis frame (sensor orientation); null when the tap is on a letterbox bar. */
export function tapToFrame(tap: [number, number], viewW: number, viewH: number, frameW: number, frameH: number, rotation: Rotation = 0,
  mirrored = false, mode: 'cover' | 'letterbox' = 'cover'): [number, number] | null {
  const [dw, dh] = rotation === 90 || rotation === 270 ? [frameH, frameW] : [frameW, frameH];
  const s = mode === 'cover' ? Math.max(viewW / dw, viewH / dh) : Math.min(viewW / dw, viewH / dh);
  const px = (viewW - dw * s) / 2; const py = (viewH - dh * s) / 2;
  let x = (tap[0] - px) / s / dw; const y = (tap[1] - py) / s / dh;
  if (!(x >= 0 && x <= 1 && y >= 0 && y <= 1)) return null;
  if (mirrored) x = 1 - x;
  return rotatePoint([x, y], ((360 - rotation) % 360) as Rotation);
}

/** Analysis-frame pixel box -> still pixel box (both centre crops of the sensor FOV; sensor aspect defaults to the still's). */
export function frameToStillBox(box: Box, frameW: number, frameH: number, stillW: number, stillH: number, sensorAspect?: number): Box {
  const a = sensorAspect ?? stillW / stillH;
  const fov = (w: number, h: number): [number, number] => { const r = w / h; return r >= a ? [1.0, a / r] : [r / a, 1.0]; };
  const [fw, fh] = fov(frameW, frameH); const [sw, sh] = fov(stillW, stillH);
  return box.map((v, i) => {
    if (i % 2 === 0) { const u = 0.5 + (v / frameW - 0.5) * fw; return ((u - 0.5) / sw + 0.5) * stillW; }
    const u = 0.5 + (v / frameH - 0.5) * fh; return ((u - 0.5) / sh + 0.5) * stillH;
  }) as Box;
}

export type Rect = { x: number; y: number; w: number; h: number };
export type CropMode = 'stageH' | 'square';
/** Close-up identity crop. 'stageH' (default, frozen Stage H behaviour) = box + pad*side per axis; 'square' = Stage I candidate
 *  square context crop (side = max(w,h)*(1+2*grow), shifted inside the image), NOT frozen - needs the human-labelled set first. */
export function identityCrop(box: Box, W: number, H: number, mode: CropMode = 'stageH', pad = 0.08, grow = 0.15): Rect {
  if (mode === 'stageH') {
    const w = box[2] - box[0]; const h = box[3] - box[1]; const px = pad * w; const py = pad * h;
    const x1 = Math.max(0, Math.floor(box[0] - px)); const y1 = Math.max(0, Math.floor(box[1] - py));
    const x2 = Math.min(W, Math.ceil(box[2] + px)); const y2 = Math.min(H, Math.ceil(box[3] + py));
    return { x: x1, y: y1, w: Math.max(0, x2 - x1), h: Math.max(0, y2 - y1) };
  }
  const cx = (box[0] + box[2]) / 2; const cy = (box[1] + box[3]) / 2;
  const s = Math.min(Math.max(box[2] - box[0], box[3] - box[1]) * (1 + 2 * grow), W, H); const si = rh(s);
  let x1 = rh(Math.min(Math.max(0, cx - s / 2), W - s)); let y1 = rh(Math.min(Math.max(0, cy - s / 2), H - s));
  x1 = Math.min(Math.max(0, x1), W - si); y1 = Math.min(Math.max(0, y1), H - si);
  return { x: x1, y: y1, w: si, h: si };
}

/** HWC uint8 RGB -> HWC float32, bilinear, half-pixel centres, edge clamp, no antialias (mirror of camera_io.resize_bilinear). */
export function resizeBilinear(rgb: ArrayLike<number>, w: number, h: number, ow: number, oh: number): Float32Array {
  if (rgb.length !== w * h * 3) throw new Error('rgb buffer size mismatch');
  const out = new Float32Array(ow * oh * 3);
  const xs = new Float64Array(ow); const ys = new Float64Array(oh);
  for (let i = 0; i < ow; i++) xs[i] = Math.min(Math.max((i + 0.5) * w / ow - 0.5, 0), w - 1);
  for (let j = 0; j < oh; j++) ys[j] = Math.min(Math.max((j + 0.5) * h / oh - 0.5, 0), h - 1);
  for (let j = 0; j < oh; j++) {
    const y0 = Math.floor(ys[j]); const y1 = Math.min(y0 + 1, h - 1); const wy = ys[j] - y0;
    for (let i = 0; i < ow; i++) {
      const x0 = Math.floor(xs[i]); const x1 = Math.min(x0 + 1, w - 1); const wx = xs[i] - x0;
      for (let c = 0; c < 3; c++) {
        const a = rgb[(y0 * w + x0) * 3 + c]; const b = rgb[(y0 * w + x1) * 3 + c]; const d = rgb[(y1 * w + x0) * 3 + c]; const e = rgb[(y1 * w + x1) * 3 + c];
        const top = a * (1 - wx) + b * wx; const bot = d * (1 - wx) + e * wx;
        out[(j * ow + i) * 3 + c] = top * (1 - wy) + bot * wy;
      }
    }
  }
  return out;
}

/** Integer box pre-reduction before bilinear when downscaling >= 2x (approximates INTER_AREA / antialiased resize); mirror of
 *  camera_io.box_reduce. Returns the (possibly unchanged) buffer and its size. */
export function boxReduce(rgb: ArrayLike<number>, w: number, h: number, ow: number, oh: number): { data: ArrayLike<number>; w: number; h: number } {
  const kx = Math.max(1, Math.floor(w / ow)); const ky = Math.max(1, Math.floor(h / oh));
  if (kx === 1 && ky === 1) return { data: rgb, w, h };
  const W2 = Math.floor(w / kx); const H2 = Math.floor(h / ky); const out = new Float32Array(W2 * H2 * 3); const n = kx * ky;
  for (let j = 0; j < H2; j++) for (let i = 0; i < W2; i++) for (let c = 0; c < 3; c++) {
    let acc = 0;
    for (let dy = 0; dy < ky; dy++) for (let dx = 0; dx < kx; dx++) acc += rgb[((j * ky + dy) * w + (i * kx + dx)) * 3 + c];
    out[(j * W2 + i) * 3 + c] = acc / n;
  }
  return { data: out, w: W2, h: H2 };
}

/** RGB uint8 crop -> H2 input, float32 NCHW (1,3,224,224) flattened, ImageNet mean/std. */
export function h2Input(rgb: Uint8Array, w: number, h: number, mode: CropMode = 'stageH'): Float32Array {
  let r: Float32Array; let ow: number; let x0 = 0; let y0 = 0;
  if (mode === 'stageH') {
    const sc = H2_RESIZE_SHORT / Math.min(w, h); ow = Math.max(H2_RESIZE_SHORT, rh(w * sc)); const oh = Math.max(H2_RESIZE_SHORT, rh(h * sc));
    const b = boxReduce(rgb, w, h, ow, oh); r = resizeBilinear(b.data, b.w, b.h, ow, oh); y0 = Math.floor((oh - H2_INPUT) / 2); x0 = Math.floor((ow - H2_INPUT) / 2);
  } else { ow = H2_INPUT; const b = boxReduce(rgb, w, h, H2_INPUT, H2_INPUT); r = resizeBilinear(b.data, b.w, b.h, H2_INPUT, H2_INPUT); }
  const N = H2_INPUT * H2_INPUT; const out = new Float32Array(3 * N);
  for (let j = 0; j < H2_INPUT; j++) for (let i = 0; i < H2_INPUT; i++) for (let c = 0; c < 3; c++) {
    const v = r[((j + y0) * ow + (i + x0)) * 3 + c];
    out[c * N + j * H2_INPUT + i] = (v / 255 - IMAGENET_MEAN[c]) / IMAGENET_STD[c];
  }
  return out;
}

export type RuntimeMeta = { inputs: { name?: string; shape: (number | string | null)[]; type?: string }[]; outputs: { name?: string; shape: (number | string | null)[]; type?: string }[] };
/** Compare tensor metadata read from ONNX Runtime / ExecuTorch with the contract. Empty list = compatible. */
export function checkModelIO(name: keyof typeof MODEL_IO, meta: RuntimeMeta): string[] {
  const spec = MODEL_IO[name]; const errs: string[] = [];
  for (const kind of ['inputs', 'outputs'] as const) {
    const got = meta[kind] ?? [];
    if (got.length !== spec[kind].length) { errs.push(`${kind}: expected ${spec[kind].length}, got ${got.length}`); continue; }
    spec[kind].forEach((s, k) => {
      const g = got[k];
      if (s.name && g.name !== s.name) errs.push(`${kind} name ${g.name} != ${s.name}`);
      if (!['float32', 'tensor(float)', 'float', undefined].includes(g.type)) errs.push(`${kind} type ${g.type}`);
      const gs = g.shape ?? [];
      if (gs.length !== s.shape.length) { errs.push(`${kind} rank ${gs.length} != ${s.shape.length}`); return; }
      gs.forEach((a, i) => {
        const b = s.shape[i]; const dynA = a === null || typeof a === 'string' || a === -1;
        if (typeof b === 'string') { if (!dynA && !(typeof a === 'number' && a >= 1)) errs.push(`${kind} dim ${i} ${a}`); }
        else if (!dynA && a !== b) errs.push(`${kind} dim ${i} ${a} != ${b}`);
      });
    });
  }
  return errs;
}

export type StillCropPlan = { source: 'track' | 'tap_roi'; framePoint: [number, number]; frameBox: Box; stillBox: Box; crop: Rect; sidePx: number };
/** Preview tap -> full-resolution still crop (the high-res crop the identity model sees). null when the tap misses the image. */
export function stillCropPlan(tap: [number, number], view: Size, frame: Size, still: Size, frameBoxes: Box[], rotation: Rotation = 0, mirrored = false,
  mode: 'cover' | 'letterbox' = 'cover', cropMode: CropMode = 'stageH', roiFrac = 0.35): StillCropPlan | null {
  const p = tapToFrame(tap, view[0], view[1], frame[0], frame[1], rotation, mirrored, mode);
  if (p === null) return null;
  const r = roiFromTap(p, frame[0], frame[1], frameBoxes, roiFrac);
  let sb = frameToStillBox(r.box, frame[0], frame[1], still[0], still[1]);
  sb = [Math.min(Math.max(sb[0], 0), still[0]), Math.min(Math.max(sb[1], 0), still[1]), Math.min(Math.max(sb[2], 0), still[0]), Math.min(Math.max(sb[3], 0), still[1])];
  const crop = identityCrop(sb, still[0], still[1], cropMode);
  return { source: r.source, framePoint: p, frameBox: r.box, stillBox: sb, crop, sidePx: Math.sqrt(Math.max(0, sb[2] - sb[0]) * Math.max(0, sb[3] - sb[1])) };
}
