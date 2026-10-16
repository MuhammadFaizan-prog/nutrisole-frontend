// Turns an image into the row-structured OCR result the glucose parser reads. 'document'
// runs PP-OCRv5 once at report resolution; 'sparse' (used when a document pass finds no
// glucose value, e.g. a meter screen) adds low-resolution detector passes so very large
// seven-segment digits become detectable, then merges them with the document boxes.
import { ppOcr, recognizeRegion, PPOCR_ENGINE, type OcrBox, type OcrRunner, type Rgba } from './ppocr';
import { boxesToRows } from './layout';
import type { OcrResult } from '../import/fileImport';

function overlaps(a: Pick<OcrBox, 'cx' | 'cy' | 'w' | 'h'>, b: Pick<OcrBox, 'cx' | 'cy' | 'w' | 'h'>): boolean {
  return Math.abs(a.cx - b.cx) < (a.w + b.w) / 4 && Math.abs(a.cy - b.cy) < (a.h + b.h) / 4;
}

function toResult(boxes: OcrBox[]): OcrResult {
  const lines = boxesToRows(boxes);
  const chars = boxes.reduce((n, b) => n + b.text.length, 0);
  const confidence = chars ? boxes.reduce((s, b) => s + b.confidence * b.text.length, 0) / chars : null;
  return { lines, confidence, engine: PPOCR_ENGINE };
}

export class PpOcrEngine {
  private cache = new WeakMap<Rgba, OcrBox[]>();
  private runner: OcrRunner;
  constructor(runner: OcrRunner) { this.runner = runner; }
  async documentBoxes(img: Rgba, onProgress?: (p: string) => void): Promise<OcrBox[]> {
    const hit = this.cache.get(img); if (hit) return hit;
    const boxes = await ppOcr(img, this.runner, { detLongSide: 1280 }, onProgress); this.cache.set(img, boxes); return boxes;
  }
  async recognize(img: Rgba, mode: 'document' | 'sparse' = 'document', onProgress?: (p: string) => void): Promise<OcrResult> {
    const doc = await this.documentBoxes(img, onProgress);
    if (mode === 'document') return toResult(doc);
    onProgress?.('Reading large digits (meter screen)…');
    const merged = doc.slice();
    for (const side of [640, 480, 320]) {
      for (const b of await ppOcr(img, this.runner, { detLongSide: side, boxThresh: 0.4, skipBox: c => merged.some(m => overlaps(m, c) && c.h < 1.6 * m.h) })) {
        const same = merged.findIndex(m => overlaps(m, b));
        if (same < 0) merged.push(b); else {
          const m = merged[same]; // prefer the box that covers more of the digits (a split detection reads "14" as "77")
          if ((b.w > 1.2 * m.w && b.confidence >= 0.6) || (b.w >= 0.8 * m.w && b.confidence > m.confidence && b.text.length >= m.text.length)) merged[same] = b;
        }
      }
    }
    const region = meterDigitRegion(merged);
    if (region) {
      const box = await recognizeRegion(img, this.runner, region);
      const digits = box.text.replace(/[oO]/g, '0').replace(/[lI|]/g, '1').replace(/[^\d.]/g, '');
      if (/^\d{2,3}(\.\d)?$/.test(digits) && box.confidence >= 0.5) {
        for (let i = merged.length - 1; i >= 0; i--) if (overlaps(merged[i], box) && merged[i].h > 1.5 * medianH(merged)) merged.splice(i, 1);
        merged.push({ ...box, text: digits });
      }
    }
    return toResult(merged);
  }
}

const medianH = (bs: OcrBox[]) => { const h = bs.map(b => b.h).sort((a, b) => a - b); return h[Math.floor(h.length / 2)] || 0; };
const UNIT = /^(mg\s*\/\s*d[lL1I]|mmo[l1I]\s*\/\s*[lL1I])\.?$/i;
/** Meter layout: the reading sits left of (and ends on the baseline of) the small unit label. When the
 *  detector misses or splits the seven-segment digits, read that region in one recogniser pass. */
export function meterDigitRegion(boxes: OcrBox[]): { cx: number; cy: number; w: number; h: number; angle: number } | null {
  const unit = boxes.find(b => UNIT.test(b.text.replace(/\s/g, ''))); if (!unit) return null;
  const goodTall = boxes.some(b => b.h > 2 * unit.h && b.confidence >= 0.85 && /^\d{2,3}(\.\d)?$/.test(b.text.replace(/\s/g, '')));
  if (goodTall) return null;
  const a = unit.angle, ux = Math.cos(a), uy = Math.sin(a), vx = -uy, vy = ux;
  const along = (b: OcrBox) => b.cx * ux + b.cy * uy, across = (b: OcrBox) => b.cx * vx + b.cy * vy;
  const unitLeft = along(unit) - unit.w / 2; const unitBottom = across(unit) + unit.h / 2;
  const above = boxes.filter(b => b !== unit && across(b) < across(unit) - unit.h && b.h < 2 * unit.h); // time/date row
  const top = above.length ? Math.max(...above.map(b => across(b) + b.h / 2)) + unit.h * 0.2 : unitBottom - unit.h * 5;
  const left = above.length ? Math.min(...above.map(b => along(b) - b.w / 2)) : unitLeft - unit.h * 9;
  const h = unitBottom - top; const w = unitLeft - left; if (h < unit.h * 1.5 || w < unit.h * 2) return null;
  const cu = (left + unitLeft) / 2, cv = (top + unitBottom) / 2;
  return { cx: cu * ux + cv * vx, cy: cu * uy + cv * vy, w, h, angle: a };
}
