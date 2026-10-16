// PP-OCRv5 pipeline pieces (geometry, CTC decoding, row grouping) and the geometry-aware parser.
import test from 'node:test';
import assert from 'node:assert/strict';
import { minAreaRect, ctcDecode, type OcrBox } from '../../src/nutrisole/glucose/ocr/ppocr.ts';
import { boxesToRows } from '../../src/nutrisole/glucose/ocr/layout.ts';
import { meterDigitRegion } from '../../src/nutrisole/glucose/ocr/engine.ts';
import { decodeImage } from '../../src/nutrisole/glucose/ocr/decode.ts';
import { parseReportText, type TextLine } from '../../src/nutrisole/glucose/import/labText.ts';
import { EN_DICT } from '../../src/nutrisole/glucose/ocr/enDict.ts';

const now = new Date('2026-10-16T12:00:00+05:00');
const meta = { format: 'image-ocr' as const, method: 'ocr' as const, fileName: 'r.jpg', fileSha256: 'f'.repeat(64), batchId: 'b', engine: 'PP-OCRv5 mobile (on-device)', now };

test('minAreaRect recovers a rotated rectangle; width is the near-horizontal side', () => {
  const a = (5 * Math.PI) / 180; const pts = [];
  for (let u = -50; u <= 50; u += 2) for (let v = -8; v <= 8; v += 2) pts.push({ x: 200 + u * Math.cos(a) - v * Math.sin(a), y: 100 + u * Math.sin(a) + v * Math.cos(a) });
  const r = minAreaRect(pts);
  assert.ok(Math.abs(r.angle - a) < 0.02, `angle ${r.angle}`); assert.ok(Math.abs(r.w - 101) < 3 && Math.abs(r.h - 17) < 3, `${r.w}x${r.h}`);
  assert.ok(Math.abs(r.cx - 200) < 1 && Math.abs(r.cy - 100) < 1);
});

test('CTC greedy decode collapses repeats, drops blanks and maps the PP-OCR en dictionary', () => {
  const C = EN_DICT.length + 2; const seq = [EN_DICT.indexOf('9') + 1, EN_DICT.indexOf('9') + 1, 0, EN_DICT.indexOf('9') + 1, EN_DICT.indexOf('8') + 1, 0, C - 1, EN_DICT.indexOf('m') + 1];
  const data = new Float32Array(seq.length * C); seq.forEach((k, t) => { data[t * C + k] = 0.9; });
  assert.deepEqual(ctcDecode({ data, dims: [1, seq.length, C] }), { text: '998 m', confidence: 0.8999999761581421 });
});

const box = (text: string, cx: number, cy: number, w: number, h = 30, angle = 0, confidence = 0.98): OcrBox => ({ text, cx, cy, w, h, angle, confidence, poly: [] });

test('rows: boxes on a tilted / keystoned photo stay on their printed row; columns ordered left to right', () => {
  const t = Math.tan(0.06); // ~3.4° tilt
  const row = (y: number, cells: [string, number, number][]) => cells.map(([s, x, w]) => box(s, x, y + x * t, w, 30, 0.06));
  const boxes = [...row(100, [['Glucose Fasting', 150, 220], ['98', 560, 40], ['mg/dL', 760, 80], ['70 - 110', 980, 120]]),
    ...row(150, [['Triglycerides', 140, 200], ['247', 565, 50], ['mg/dL', 760, 80], ['< 150', 975, 80]])];
  const rows = boxesToRows(boxes.reverse());
  assert.deepEqual(rows.map(r => r.cells!.map(c => c.text)), [['Glucose Fasting', '98', 'mg/dL', '70 - 110'], ['Triglycerides', '247', 'mg/dL', '< 150']]);
});

const cellsLine = (i: number, cells: [string, number][]): TextLine => ({ text: cells.map(c => c[0]).join('  '), confidence: 0.95, locator: `row ${i}`, cells: cells.map(([text, x]) => ({ text, x0: x, x1: x + 10 * text.length, confidence: 0.95, h: 30 })) });

test('parser pairs a test with the value in the Result column, never the reference range; unit may be last', () => {
  const lines = [
    cellsLine(1, [['Sample Collected: 06.01.2026 09:28 AM', 600]]),
    cellsLine(2, [['BLOOD GLUCOSE', 80]]),
    cellsLine(3, [['Investigation', 80], ['Result', 500], ['Normal Range', 700], ['Units', 1000]]),
    cellsLine(4, [['ALT (SGPT)', 80], ['57', 505], ['< 40', 700], ['U/L', 1000]]),
    cellsLine(5, [['Sugar (F)', 80], ['126 H', 500], ['70 - 110', 700], ['mg/dL', 1000]]),
    cellsLine(6, [['RBS', 80], ['< 200', 700], ['mg/dL', 1000]]), // result cell missing (OCR miss): must not take the range
    cellsLine(7, [['2 hr PP', 80], ['8.4', 505], ['< 7.8', 700], ['mmol/L', 1000]]),
    cellsLine(8, [['HbA1c', 80], ['7.5', 505], ['4.0 - 5.6', 700], ['%', 1000]]),
    cellsLine(9, [['Random glucose >= 200 mg/dL with symptoms suggests diabetes.', 80]]),
  ];
  const r = parseReportText(lines, meta);
  assert.deepEqual(r.candidates.map(c => [c.value, c.unit, c.mealContext, c.date, c.time]), [['126', 'mg/dL', 'fasting', 'Jan 6, 2026', '9:28 AM'], ['8.4', 'mmol/L', 'after_meal', 'Jan 6, 2026', '9:28 AM']]);
  assert.deepEqual(r.nonGlucose.map(n => [n.kind, n.value, n.unit]), [['hba1c', '7.5', '%']]);
});

test('meter screen: the tallest number is the reading, not the date or the time', () => {
  const lines: TextLine[] = [
    { text: '08:13  11/02', locator: 'row 1', confidence: 0.99, cells: [{ text: '08:13', x0: 0, x1: 100, confidence: 0.99, h: 60 }, { text: '11/02', x0: 500, x1: 600, confidence: 0.99, h: 60 }] },
    { text: '11.7', locator: 'row 2', confidence: 0.99, cells: [{ text: '11.7', x0: 150, x1: 500, confidence: 0.99, h: 250 }] },
    { text: 'mmol/L', locator: 'row 3', confidence: 1, cells: [{ text: 'mmol/L', x0: 520, x1: 640, confidence: 1, h: 60 }] },
  ];
  const r = parseReportText(lines, meta);
  assert.equal(r.kind, 'meter-screen'); const c = r.candidates[0];
  assert.deepEqual([c.value, c.unit, c.date, c.time], ['11.7', 'mmol/L', 'Feb 11, 2026', '8:13 AM']);
  assert.ok(c.confidence < 0.6, 'meter readings are always flagged for a look');
});

test('meter digit region: left of the unit label, below the date/time row', () => {
  const g = meterDigitRegion([box('08:13', 300, 180, 140, 60), box('11/02', 800, 190, 130, 60), box('mmol/L', 820, 500, 170, 55), box('1', 450, 420, 40, 140, 0, 0.4)])!;
  assert.ok(g && g.cx < 735 && g.cy > 210 && g.cy < 528 && g.w > 300, JSON.stringify(g));
  assert.equal(meterDigitRegion([box('mg/dL', 820, 500, 150, 55), box('154', 500, 420, 300, 250, 0, 0.97)]), null, 'skips when the digits were read confidently');
});

test('decodeImage: PNG (fflate) and JPEG (jpeg-js) to RGBA, downscaled', async () => {
  const fs = await import('node:fs');
  const png = decodeImage(fs.readFileSync(new URL('./fixtures/meter-mgdl.png', import.meta.url)), 400);
  assert.ok(png.width <= 400 && png.height <= 400 && png.data.length === png.width * png.height * 4);
  const jpg = decodeImage(fs.readFileSync(new URL('./ocr-eval/heldout/heldout-03-meter-screen-photo.jpg', import.meta.url)), 500);
  assert.ok(Math.max(jpg.width, jpg.height) === 500);
});
