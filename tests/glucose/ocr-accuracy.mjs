// OCR accuracy on the SYNTHETIC G-2 fixtures (tests/glucose/fixtures) with the app's engine:
// PP-OCRv5 mobile via onnxruntime-web (identical pipeline on web and Android). These fixtures were
// used while building the G-2 parser, so this is a smoke check, not the honest number: the
// held-out evaluation lives in tests/glucose/ocr-eval/ (npm run ocr:eval:run / ocr:eval:score).
// The parser tests keep the old tesseract text in fixtures/ocr/*.txt as plain-text input cases.
// Usage: npm run test:glucose:ocr
import fs from 'node:fs';
import { nodeRunner } from './ocr-eval/node-ocr.mjs';
import { PpOcrEngine } from '../../src/nutrisole/glucose/ocr/engine.ts';
import { decodeImage } from '../../src/nutrisole/glucose/ocr/decode.ts';
import { parseReportText } from '../../src/nutrisole/glucose/import/labText.ts';

const dir = new URL('./fixtures/', import.meta.url).pathname;
const truth = JSON.parse(fs.readFileSync(dir + 'truth.json', 'utf8'));
const engine = new PpOcrEngine(await nodeRunner());
const meta = f => ({ format: 'image-ocr', method: 'ocr', fileName: f, fileSha256: 'x', batchId: 'acc', engine: 'PP-OCRv5', now: new Date('2026-10-16T17:00:00+05:00') });
const tot = { value: [0, 0], unit: [0, 0], context: [0, 0], date: [0, 0], time: [0, 0] };
for (const file of Object.keys(truth).filter(f => /\.(png|jpe?g)$/.test(f))) {
  const img = decodeImage(fs.readFileSync(dir + file));
  let r = parseReportText((await engine.recognize(img, 'document')).lines, meta(file));
  if (!r.candidates.length && !r.nonGlucose.length) r = parseReportText((await engine.recognize(img, 'sparse')).lines, meta(file));
  for (const w of truth[file].readings) {
    const got = r.candidates.find(c => c.value === w.value) || r.candidates[truth[file].readings.indexOf(w)];
    for (const k of Object.keys(tot)) { tot[k][1]++; const g = got ? { value: got.value, unit: got.unit, context: got.mealContext, date: got.date, time: got.time }[k] : null; if (g === w[k]) tot[k][0]++; }
  }
  console.log(file, r.candidates.map(c => `${c.value} ${c.unit} ${c.mealContext} ${c.date} ${c.time}`).join('; ') || '(none)');
}
console.log(Object.fromEntries(Object.entries(tot).map(([k, [a, b]]) => [k, `${a}/${b}`])));
