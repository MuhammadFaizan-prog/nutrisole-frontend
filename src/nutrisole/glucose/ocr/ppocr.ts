// PaddleOCR PP-OCRv5 mobile (text detection + English recognition, Apache-2.0) as pure
// TypeScript pre/post-processing around an injected ONNX runner. The same code runs on web
// (onnxruntime-web, WASM), on Android (onnxruntime-react-native) and in Node tests
// (onnxruntime-web), so every platform reads a photo identically. No network: the two
// .onnx files ship with the app (public/ocr/ppocrv5/), and the image never leaves the device.
import { EN_DICT } from './enDict';

export type Rgba = { width: number; height: number; data: Uint8Array | Uint8ClampedArray };
export type Tensor = { data: Float32Array; dims: number[] };
/** Platform adapter: run one model on one float32 NCHW tensor. */
export type OcrRunner = { run(model: 'det' | 'rec', input: Tensor): Promise<Tensor> };
export type Pt = { x: number; y: number };
/** One detected text line: rotated rectangle (in original image pixels) + recognised text. */
export type OcrBox = { text: string; confidence: number; cx: number; cy: number; w: number; h: number; angle: number; poly: Pt[] };
export type PpOcrOptions = { /** Skip recognition for boxes already read (e.g. by an earlier pass). */ skipBox?: (b: { cx: number; cy: number; w: number; h: number }) => boolean; detLongSide?: number; detThresh?: number; boxThresh?: number; unclipRatio?: number; minRecConfidence?: number };
export const PPOCR_ENGINE = 'PP-OCRv5 mobile (on-device)';

const MEAN = [0.485, 0.456, 0.406]; const STD = [0.229, 0.224, 0.225];

/** Resize so the long side is <= longSide (never upscale below 32), both sides multiples of 32. */
function detResize(img: Rgba, longSide: number): { w: number; h: number; sx: number; sy: number } {
  const ratio = Math.min(1, longSide / Math.max(img.width, img.height));
  const w = Math.max(32, Math.round((img.width * ratio) / 32) * 32); const h = Math.max(32, Math.round((img.height * ratio) / 32) * 32);
  return { w, h, sx: img.width / w, sy: img.height / h };
}

/** Bilinear sample of channel c at (x, y). */
function sample(img: Rgba, x: number, y: number, c: number): number {
  const W = img.width, H = img.height, d = img.data;
  if (x < 0) x = 0; if (y < 0) y = 0; if (x > W - 1) x = W - 1; if (y > H - 1) y = H - 1;
  const x0 = Math.floor(x), y0 = Math.floor(y), x1 = Math.min(W - 1, x0 + 1), y1 = Math.min(H - 1, y0 + 1);
  const fx = x - x0, fy = y - y0;
  const a = d[(y0 * W + x0) * 4 + c], b = d[(y0 * W + x1) * 4 + c], e = d[(y1 * W + x0) * 4 + c], f = d[(y1 * W + x1) * 4 + c];
  return a + (b - a) * fx + (e - a) * fy + (a - b - e + f) * fx * fy;
}

/** Area-averaged downscale (box filter) to w x h, BGR-normalised CHW for the detector. */
function detTensor(img: Rgba, w: number, h: number): Float32Array {
  const out = new Float32Array(3 * w * h); const sx = img.width / w, sy = img.height / h; const plane = w * h;
  const step = Math.max(1, Math.floor(Math.min(sx, sy)));
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let r = 0, g = 0, b = 0, n = 0;
    const bx = x * sx, by = y * sy;
    for (let j = 0; j < step; j++) for (let i = 0; i < step; i++) {
      const px = Math.min(img.width - 1, Math.floor(bx + (i + 0.5) * (sx / step))); const py = Math.min(img.height - 1, Math.floor(by + (j + 0.5) * (sy / step)));
      const k = (py * img.width + px) * 4; r += img.data[k]; g += img.data[k + 1]; b += img.data[k + 2]; n++;
    }
    const o = y * w + x; // channel order B, G, R (Paddle decodes BGR)
    out[o] = (b / n / 255 - MEAN[0]) / STD[0]; out[plane + o] = (g / n / 255 - MEAN[1]) / STD[1]; out[2 * plane + o] = (r / n / 255 - MEAN[2]) / STD[2];
  }
  return out;
}

function cross(o: Pt, a: Pt, b: Pt) { return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x); }
function convexHull(pts: Pt[]): Pt[] {
  const p = pts.slice().sort((a, b) => a.x - b.x || a.y - b.y); if (p.length < 3) return p;
  const lo: Pt[] = []; for (const q of p) { while (lo.length >= 2 && cross(lo[lo.length - 2], lo[lo.length - 1], q) <= 0) lo.pop(); lo.push(q); }
  const up: Pt[] = []; for (let i = p.length - 1; i >= 0; i--) { const q = p[i]; while (up.length >= 2 && cross(up[up.length - 2], up[up.length - 1], q) <= 0) up.pop(); up.push(q); }
  return lo.slice(0, -1).concat(up.slice(0, -1));
}
/** Minimum-area rotated rectangle (rotating calipers over the hull). Width is the long, near-horizontal side. */
export function minAreaRect(pts: Pt[]): { cx: number; cy: number; w: number; h: number; angle: number } {
  const hull = convexHull(pts);
  if (hull.length < 3) { const xs = pts.map(p => p.x), ys = pts.map(p => p.y); const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys); return { cx: (x0 + x1) / 2, cy: (y0 + y1) / 2, w: x1 - x0 + 1, h: y1 - y0 + 1, angle: 0 }; }
  let best = { area: Infinity, cx: 0, cy: 0, w: 0, h: 0, angle: 0 };
  for (let i = 0; i < hull.length; i++) {
    const a = hull[i], b = hull[(i + 1) % hull.length]; const len = Math.hypot(b.x - a.x, b.y - a.y); if (!len) continue;
    const ux = (b.x - a.x) / len, uy = (b.y - a.y) / len;
    let minU = Infinity, maxU = -Infinity, minV = Infinity, maxV = -Infinity;
    for (const q of hull) { const u = q.x * ux + q.y * uy, v = -q.x * uy + q.y * ux; if (u < minU) minU = u; if (u > maxU) maxU = u; if (v < minV) minV = v; if (v > maxV) maxV = v; }
    const area = (maxU - minU) * (maxV - minV);
    if (area < best.area) { const cu = (minU + maxU) / 2, cv = (minV + maxV) / 2; best = { area, cx: cu * ux - cv * uy, cy: cu * uy + cv * ux, w: maxU - minU, h: maxV - minV, angle: Math.atan2(uy, ux) }; }
  }
  let { cx, cy, w, h, angle } = best;
  // Normalise: angle in (-45°, 45°], w along that angle.
  while (angle > Math.PI / 4) { angle -= Math.PI / 2; [w, h] = [h, w]; }
  while (angle <= -Math.PI / 4) { angle += Math.PI / 2; [w, h] = [h, w]; }
  return { cx, cy, w: w + 1, h: h + 1, angle };
}

/** DB post-processing: connected components of prob > thresh → scored, unclipped rotated boxes. */
export function dbBoxes(prob: Float32Array, W: number, H: number, o: Required<Pick<PpOcrOptions, 'detThresh' | 'boxThresh' | 'unclipRatio'>>) {
  const label = new Int32Array(W * H); const boxes: { cx: number; cy: number; w: number; h: number; angle: number; score: number }[] = [];
  const stack = new Int32Array(W * H); let next = 0;
  for (let s = 0; s < W * H; s++) {
    if (label[s] || prob[s] <= o.detThresh) continue;
    next++; let sp = 0; stack[sp++] = s; label[s] = next;
    let sum = 0, n = 0; const rowMin = new Map<number, number>(), rowMax = new Map<number, number>();
    while (sp) {
      const p = stack[--sp]; const x = p % W, y = (p - x) / W; sum += prob[p]; n++;
      const mn = rowMin.get(y); if (mn === undefined || x < mn) rowMin.set(y, x); const mx = rowMax.get(y); if (mx === undefined || x > mx) rowMax.set(y, x);
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        if (!dx && !dy) continue; const nx = x + dx, ny = y + dy; if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
        const q = ny * W + nx; if (!label[q] && prob[q] > o.detThresh) { label[q] = next; stack[sp++] = q; }
      }
    }
    if (n < 6) continue;
    const score = sum / n; if (score < o.boxThresh) continue;
    const pts: Pt[] = []; for (const [y, x0] of rowMin) { const x1 = rowMax.get(y)!; pts.push({ x: x0, y }, { x: x0, y: y + 1 }, { x: x1 + 1, y }, { x: x1 + 1, y: y + 1 }); }
    const r = minAreaRect(pts); if (Math.min(r.w, r.h) < 3) continue;
    const d = (r.w * r.h * o.unclipRatio) / (2 * (r.w + r.h)); // Vatti offset distance for a rectangle
    const w = r.w + 2 * d, h = r.h + 2 * d; if (Math.min(w, h) < 5) continue;
    boxes.push({ cx: r.cx, cy: r.cy, w, h, angle: r.angle, score });
  }
  return boxes;
}

/** Crop a rotated rectangle and build the 48-px-high recogniser tensor (BGR, (x/255-0.5)/0.5, padded to >= 320). */
function recTensor(img: Rgba, b: { cx: number; cy: number; w: number; h: number; angle: number }): Tensor {
  let { w, h, angle } = b; let ux = Math.cos(angle), uy = Math.sin(angle);
  if (h > w * 1.5) { [w, h] = [h, w]; const t = ux; ux = -uy; uy = t; } // vertical strip: read along the long side
  const vx = -uy, vy = ux; const H = 48; const ratio = w / Math.max(1, h);
  const outW = Math.max(8, Math.min(1600, Math.ceil(H * ratio))); const padW = Math.max(320, outW);
  const data = new Float32Array(3 * H * padW); const plane = H * padW;
  for (let j = 0; j < H; j++) for (let i = 0; i < outW; i++) {
    const u = ((i + 0.5) / outW - 0.5) * w, v = ((j + 0.5) / H - 0.5) * h;
    const x = b.cx + u * ux + v * vx - 0.5, y = b.cy + u * uy + v * vy - 0.5; const o = j * padW + i;
    data[o] = sample(img, x, y, 2) / 127.5 - 1; data[plane + o] = sample(img, x, y, 1) / 127.5 - 1; data[2 * plane + o] = sample(img, x, y, 0) / 127.5 - 1;
  }
  return { data, dims: [1, 3, H, padW] };
}

/** Greedy CTC decode over [1, T, C] softmax output. */
export function ctcDecode(out: Tensor, dict: readonly string[] = EN_DICT): { text: string; confidence: number } {
  const T = out.dims[1], C = out.dims[2]; let prev = 0; let text = ''; let confSum = 0, n = 0;
  for (let t = 0; t < T; t++) {
    let best = 0, bp = -1; const base = t * C;
    for (let c = 0; c < C; c++) { const v = out.data[base + c]; if (v > bp) { bp = v; best = c; } }
    if (best !== 0 && best !== prev) { text += best - 1 < dict.length ? dict[best - 1] : ' '; confSum += bp; n++; }
    prev = best;
  }
  return { text: text.trim(), confidence: n ? confSum / n : 0 };
}

/** Recognise one rotated region directly (no detection), e.g. the big digits of a meter screen. */
export async function recognizeRegion(img: Rgba, runner: OcrRunner, b: { cx: number; cy: number; w: number; h: number; angle: number }): Promise<OcrBox> {
  const rec = ctcDecode(await runner.run('rec', recTensor(img, b)));
  return { text: rec.text, confidence: rec.confidence, ...b, poly: polyOf(b) };
}

function polyOf(b: { cx: number; cy: number; w: number; h: number; angle: number }): Pt[] {
  const ux = Math.cos(b.angle), uy = Math.sin(b.angle), vx = -uy, vy = ux, hw = b.w / 2, hh = b.h / 2;
  return [[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]].map(([u, v]) => ({ x: b.cx + u * ux + v * vx, y: b.cy + u * uy + v * vy }));
}

export async function ppOcr(img: Rgba, runner: OcrRunner, opts: PpOcrOptions = {}, onProgress?: (p: string) => void): Promise<OcrBox[]> {
  const o = { detLongSide: opts.detLongSide ?? 1280, detThresh: opts.detThresh ?? 0.3, boxThresh: opts.boxThresh ?? 0.5, unclipRatio: opts.unclipRatio ?? 1.6, minRecConfidence: opts.minRecConfidence ?? 0.3 };
  const r = detResize(img, o.detLongSide);
  onProgress?.('Finding text on the page…');
  const det = await runner.run('det', { data: detTensor(img, r.w, r.h), dims: [1, 3, r.h, r.w] });
  const dw = det.dims[3], dh = det.dims[2];
  const raw = dbBoxes(det.data, dw, dh, o);
  const scaled = raw.map(b => {
    // Map from detector space to the original image (anisotropic scale on a rotated box).
    const ux = Math.cos(b.angle) * r.sx, uy = Math.sin(b.angle) * r.sy; const s = Math.hypot(ux, uy);
    const vx = -Math.sin(b.angle) * r.sx, vy = Math.cos(b.angle) * r.sy; const t = Math.hypot(vx, vy);
    return { cx: b.cx * r.sx, cy: b.cy * r.sy, w: b.w * s, h: b.h * t, angle: Math.atan2(uy, ux) };
  }).sort((a, b) => a.cy - b.cy || a.cx - b.cx);
  const out: OcrBox[] = [];
  for (const [i, b] of scaled.entries()) {
    if (opts.skipBox?.(b)) continue;
    if (i % 8 === 0) onProgress?.(`Reading text ${i + 1} of ${scaled.length}…`);
    const rec = ctcDecode(await runner.run('rec', recTensor(img, b)));
    if (!rec.text || rec.confidence < o.minRecConfidence) continue;
    out.push({ text: rec.text, confidence: rec.confidence, ...b, poly: polyOf(b) });
  }
  return out;
}
