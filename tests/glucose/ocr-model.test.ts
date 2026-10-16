// End-to-end with the real PP-OCRv5 models (onnxruntime-web WASM in Node, the web app's runtime):
// image → OCR → rows → parser, on two held-out synthetic images (never used for tuning).
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { nodeRunner } from './ocr-eval/node-ocr.mjs';
import { PpOcrEngine } from '../../src/nutrisole/glucose/ocr/engine.ts';
import { decodeImage } from '../../src/nutrisole/glucose/ocr/decode.ts';
import { parseReportText } from '../../src/nutrisole/glucose/import/labText.ts';

const gt = JSON.parse(fs.readFileSync(new URL('./ocr-eval/heldout/ground-truth.json', import.meta.url), 'utf8')).images;
const meta = { format: 'image-ocr' as const, method: 'ocr' as const, fileName: 'x.jpg', fileSha256: 'f'.repeat(64), batchId: 'b', engine: 'PP-OCRv5 mobile (on-device)', now: new Date('2026-10-16T12:00:00+05:00') };

test('PP-OCRv5 reads a held-out lab-report photo and a meter photo', { timeout: 120_000 }, async () => {
  const engine = new PpOcrEngine(await nodeRunner());
  for (const name of ['heldout-01-lab-report-photo.jpg', 'heldout-35-meter-screen-photo.jpg']) {
    const want = gt.find((g: { file: string }) => g.file === name);
    const img = decodeImage(fs.readFileSync(new URL(`./ocr-eval/heldout/${name}`, import.meta.url)));
    let r = parseReportText((await engine.recognize(img, 'document')).lines, meta);
    if (!r.candidates.length) r = parseReportText((await engine.recognize(img, 'sparse')).lines, meta);
    const got = r.candidates.map(c => `${c.mealContext}|${Number(c.value)}|${c.unit}`).sort();
    const exp = want.readings.map((g: { type: string; value: string; unit: string }) => `${g.type}|${Number(g.value)}|${g.unit}`).sort();
    assert.deepEqual(got, exp, name);
  }
});
