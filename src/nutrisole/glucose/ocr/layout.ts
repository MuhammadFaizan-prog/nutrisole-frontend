// Groups OCR boxes into table rows using their geometry, so a test name, its result, unit
// and reference range on one printed row stay together even on a tilted or keystoned photo.
// Works with any engine that returns rotated line boxes (PP-OCR, ML Kit frames).
import type { OcrBox } from './ppocr';
import type { TextCell, TextLine } from '../import/labText';

type Row = { boxes: OcrBox[] };

function median(xs: number[]): number { if (!xs.length) return 0; const s = xs.slice().sort((a, b) => a - b); return s[Math.floor(s.length / 2)]; }

/** Predict where the row would be at x (line through its boxes, or the last box's own slope). */
function rowYAt(row: Row, x: number, globalAngle: number): number {
  const b = row.boxes; const last = b[b.length - 1];
  let slope = Math.tan(b.length === 1 ? (Math.abs(last.angle) < 0.35 && last.w > 2 * last.h ? last.angle : globalAngle) : 0);
  if (b.length > 1) { const first = b[0]; const dx = last.cx - first.cx; slope = dx > 4 * last.h ? (last.cy - first.cy) / dx : Math.tan(globalAngle); }
  return last.cy + slope * (x - last.cx);
}

export function boxesToRows(boxes: OcrBox[]): TextLine[] {
  if (!boxes.length) return [];
  const globalAngle = median(boxes.filter(b => b.w > 3 * b.h).map(b => b.angle));
  const ca = Math.cos(globalAngle), sa = Math.sin(globalAngle);
  const left = (b: OcrBox) => (b.cx * ca + b.cy * sa) - b.w / 2; // position along the text direction
  const sorted = boxes.slice().sort((a, b) => left(a) - left(b));
  const rows: Row[] = [];
  for (const b of sorted) {
    let best: Row | null = null; let bestD = Infinity;
    for (const r of rows) {
      const last = r.boxes[r.boxes.length - 1];
      if (left(b) < left(last) + last.w * 0.5) continue; // overlaps horizontally: a different line
      const d = Math.abs(rowYAt(r, b.cx, globalAngle) - b.cy); const tol = 0.55 * Math.min(b.h, median(r.boxes.map(x => x.h)));
      if (d < tol && d < bestD) { best = r; bestD = d; }
    }
    if (best) best.boxes.push(b); else rows.push({ boxes: [b] });
  }
  const perp = (b: OcrBox) => -b.cx * sa + b.cy * ca;
  rows.sort((a, b) => median(a.boxes.map(perp)) - median(b.boxes.map(perp)));
  return rows.map((r, i) => {
    const cells: TextCell[] = r.boxes.map(b => ({ text: b.text, x0: left(b), x1: left(b) + b.w, confidence: b.confidence, h: b.h }));
    const conf = cells.reduce((s, c) => s + c.confidence * c.text.length, 0) / Math.max(1, cells.reduce((s, c) => s + c.text.length, 0));
    return { text: cells.map(c => c.text).join('  '), confidence: conf, locator: `row ${i + 1}`, cells };
  });
}
