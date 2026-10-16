// Pure-JS image decoding for the OCR pipeline where no canvas exists (Android Hermes, Node
// tests): JPEG via jpeg-js (with EXIF orientation applied), PNG via fflate inflate.
// Large photos are downscaled so the long side is at most maxSide.
import { decode as decodeJpeg } from 'jpeg-js';
import { unzlibSync } from 'fflate';
import type { Rgba } from './ppocr';

function exifOrientation(b: Uint8Array): number {
  if (b[0] !== 0xff || b[1] !== 0xd8) return 1;
  let p = 2;
  while (p + 4 < b.length) {
    if (b[p] !== 0xff) return 1; const marker = b[p + 1]; const len = (b[p + 2] << 8) | b[p + 3];
    if (marker === 0xe1 && b[p + 4] === 0x45 && b[p + 5] === 0x78 && b[p + 6] === 0x69 && b[p + 7] === 0x66) {
      const t = p + 10; const le = b[t] === 0x49; const u16 = (o: number) => le ? b[o] | (b[o + 1] << 8) : (b[o] << 8) | b[o + 1];
      const u32 = (o: number) => le ? (b[o] | (b[o + 1] << 8) | (b[o + 2] << 16) | (b[o + 3] << 24)) >>> 0 : ((b[o] << 24) | (b[o + 1] << 16) | (b[o + 2] << 8) | b[o + 3]) >>> 0;
      const ifd = t + u32(t + 4); const n = u16(ifd);
      for (let i = 0; i < n; i++) { const e = ifd + 2 + i * 12; if (u16(e) === 0x0112) return u16(e + 8) || 1; }
      return 1;
    }
    if (marker === 0xda) return 1; p += 2 + len;
  }
  return 1;
}

function orient(img: Rgba, o: number): Rgba {
  if (o !== 3 && o !== 6 && o !== 8) return img;
  const { width: W, height: H, data } = img; const swap = o !== 3; const w = swap ? H : W, h = swap ? W : H; const out = new Uint8Array(w * h * 4);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const nx = o === 3 ? W - 1 - x : o === 6 ? H - 1 - y : y; const ny = o === 3 ? H - 1 - y : o === 6 ? x : W - 1 - x;
    const s = (y * W + x) * 4, d = (ny * w + nx) * 4; out[d] = data[s]; out[d + 1] = data[s + 1]; out[d + 2] = data[s + 2]; out[d + 3] = 255;
  }
  return { width: w, height: h, data: out };
}

export function downscale(img: Rgba, maxSide: number): Rgba {
  const s = maxSide / Math.max(img.width, img.height); if (s >= 1) return img;
  const w = Math.max(1, Math.round(img.width * s)), h = Math.max(1, Math.round(img.height * s)); const out = new Uint8Array(w * h * 4); const inv = 1 / s;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const x0 = Math.floor(x * inv), y0 = Math.floor(y * inv), x1 = Math.min(img.width, Math.floor((x + 1) * inv)), y1 = Math.min(img.height, Math.floor((y + 1) * inv));
    let r = 0, g = 0, b = 0, n = 0;
    for (let yy = y0; yy < Math.max(y0 + 1, y1); yy++) for (let xx = x0; xx < Math.max(x0 + 1, x1); xx++) { const k = (yy * img.width + xx) * 4; r += img.data[k]; g += img.data[k + 1]; b += img.data[k + 2]; n++; }
    const d = (y * w + x) * 4; out[d] = r / n; out[d + 1] = g / n; out[d + 2] = b / n; out[d + 3] = 255;
  }
  return { width: w, height: h, data: out };
}

function decodePng(b: Uint8Array): Rgba {
  let p = 8; let W = 0, H = 0, depth = 0, ctype = 0; const idat: Uint8Array[] = []; let palette: Uint8Array | null = null; let trns: Uint8Array | null = null;
  while (p < b.length) {
    const len = ((b[p] << 24) | (b[p + 1] << 16) | (b[p + 2] << 8) | b[p + 3]) >>> 0; const type = String.fromCharCode(b[p + 4], b[p + 5], b[p + 6], b[p + 7]); const d = b.subarray(p + 8, p + 8 + len);
    if (type === 'IHDR') { W = ((d[0] << 24) | (d[1] << 16) | (d[2] << 8) | d[3]) >>> 0; H = ((d[4] << 24) | (d[5] << 16) | (d[6] << 8) | d[7]) >>> 0; depth = d[8]; ctype = d[9]; if (d[12]) throw new Error('Interlaced PNG is not supported; save the image as JPG.'); }
    else if (type === 'PLTE') palette = d; else if (type === 'tRNS') trns = d; else if (type === 'IDAT') idat.push(d); else if (type === 'IEND') break;
    p += 12 + len;
  }
  if (depth !== 8) throw new Error('Only 8-bit PNG images are supported; save the image as JPG.');
  const all = new Uint8Array(idat.reduce((n, a) => n + a.length, 0)); let o = 0; for (const a of idat) { all.set(a, o); o += a.length; }
  const raw = unzlibSync(all); const ch = ctype === 6 ? 4 : ctype === 2 ? 3 : ctype === 4 ? 2 : 1; const stride = W * ch; const cur = new Uint8Array(stride * H);
  for (let y = 0; y < H; y++) {
    const f = raw[y * (stride + 1)]; const src = raw.subarray(y * (stride + 1) + 1, (y + 1) * (stride + 1)); const row = y * stride;
    for (let x = 0; x < stride; x++) {
      const a = x >= ch ? cur[row + x - ch] : 0, up = y ? cur[row - stride + x] : 0, c = x >= ch && y ? cur[row - stride + x - ch] : 0;
      let v = src[x];
      if (f === 1) v += a; else if (f === 2) v += up; else if (f === 3) v += (a + up) >> 1; else if (f === 4) { const pp = a + up - c, pa = Math.abs(pp - a), pb = Math.abs(pp - up), pc = Math.abs(pp - c); v += pa <= pb && pa <= pc ? a : pb <= pc ? up : c; }
      cur[row + x] = v & 255;
    }
  }
  const out = new Uint8Array(W * H * 4);
  for (let i = 0; i < W * H; i++) {
    const s = i * ch, d = i * 4;
    if (ctype === 3 && palette) { const k = cur[i]; out[d] = palette[k * 3]; out[d + 1] = palette[k * 3 + 1]; out[d + 2] = palette[k * 3 + 2]; }
    else if (ch >= 3) { out[d] = cur[s]; out[d + 1] = cur[s + 1]; out[d + 2] = cur[s + 2]; }
    else { out[d] = out[d + 1] = out[d + 2] = cur[s]; }
    let alpha = ch === 4 ? cur[s + 3] : ch === 2 ? cur[s + 1] : ctype === 3 && trns && cur[i] < trns.length ? trns[cur[i]] : 255;
    if (alpha < 255) { for (let c = 0; c < 3; c++) out[d + c] = Math.round((out[d + c] * alpha + 255 * (255 - alpha)) / 255); alpha = 255; } // flatten on white
    out[d + 3] = alpha;
  }
  return { width: W, height: H, data: out };
}

export function decodeImage(bytes: Uint8Array, maxSide = 2000): Rgba {
  let img: Rgba;
  if (bytes[0] === 0xff && bytes[1] === 0xd8) { const j = decodeJpeg(bytes, { useTArray: true, formatAsRGBA: true, maxMemoryUsageInMB: 512 }); img = orient({ width: j.width, height: j.height, data: j.data }, exifOrientation(bytes)); }
  else if (bytes[0] === 0x89 && bytes[1] === 0x50) img = decodePng(bytes);
  else throw new Error('Only JPG and PNG photos can be read on this phone. Save the image as JPG and try again.');
  return downscale(img, maxSide);
}
