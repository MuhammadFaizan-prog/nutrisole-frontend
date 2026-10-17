import test from 'node:test';
import assert from 'node:assert/strict';
import { nativeCaptureResult, type NativeCaptureResult } from '../../src/nutrisole/glucose/ocr/nativeResult.ts';
import { parseReportText } from '../../src/nutrisole/glucose/import/labText.ts';
import { fileToBatch } from '../../src/nutrisole/glucose/import/fileImport.ts';

const result: NativeCaptureResult = { engine: 'ML Kit Latin (on this phone)', durationMs: 45, pages: [{ page: 1, boxes: [
  { text: 'Collected: Oct 15, 2026 8:15 AM', x: 30, y: 10, width: 500, height: 25, angle: 0, confidence: null },
  { text: 'Glucose Fasting', x: 30, y: 80, width: 210, height: 25, angle: 0, confidence: 0.97 },
  { text: '98', x: 400, y: 80, width: 40, height: 25, angle: 0, confidence: 0.96 },
  { text: 'mg/dL', x: 520, y: 80, width: 90, height: 25, angle: 0, confidence: 0.98 },
  { text: '70 - 110', x: 700, y: 80, width: 130, height: 25, angle: 0, confidence: 0.98 },
] }] };

test('native OCR preserves table columns and page provenance', () => {
  const ocr = nativeCaptureResult(result);
  assert.equal(ocr.durationMs, 45); assert.equal(ocr.lines[1].cells!.length, 4);
  const batch = parseReportText(ocr.lines, { format: 'image-ocr', method: 'ocr', fileName: 'report.jpg', fileSha256: 'a'.repeat(64), batchId: 'native', engine: ocr.engine });
  assert.equal(batch.candidates[0].value, '98'); assert.equal(batch.candidates[0].unit, 'mg/dL');
  assert.match(batch.candidates[0].provenance.locator, /page 1/);
});

test('unknown native OCR scores stay unknown and require review', () => {
  const r = nativeCaptureResult({ ...result, pages: result.pages.map(p => ({ ...p, boxes: p.boxes.map(b => ({ ...b, confidence: null })) })) });
  assert.equal(r.confidence, null);
  assert.ok(r.lines.every(l => (l.confidence ?? 0) <= 0.55));
});

test('Android PDF reader uses the native document path instead of the unsupported web message', async () => {
  let calls = 0;
  const batch = await fileToBatch({ name: 'scan.pdf', mime: 'application/pdf', bytes: new Uint8Array([37,80,68,70,45]) }, { pdfDocument: async () => { calls++; return nativeCaptureResult(result); } });
  assert.equal(calls, 1); assert.equal(batch.candidates[0].value, '98');
  assert.match(batch.notes.join(' '), /45 ms/);
});
