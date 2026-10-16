// OCR accuracy on the SYNTHETIC fixtures (tests/glucose/fixtures). Runs tesseract.js (the
// web OCR engine) in Node, saves the raw OCR text to fixtures/ocr/*.txt (used by the
// deterministic parser tests) and scores the parser against truth.json per field.
// ML Kit (Android/iOS) cannot run here; its accuracy is NOT measured by this script.
// Usage: node --experimental-strip-types --import ./tests/glucose/resolve-ts.mjs tests/glucose/ocr-accuracy.mjs [file ...]
import fs from 'node:fs';
import path from 'node:path';
import { createWorker } from 'tesseract.js';
import { parseReportText } from '../../src/nutrisole/glucose/import/labText.ts';

const dir = new URL('./fixtures/', import.meta.url).pathname;
const truth = JSON.parse(fs.readFileSync(dir + 'truth.json', 'utf8'));
const only = process.argv.slice(2);
const images = Object.keys(truth).filter(f => /\.(png|jpe?g)$/.test(f) && (!only.length || only.includes(f)));
fs.mkdirSync(dir + 'ocr', { recursive: true });
const resultsPath = dir + 'ocr/results.json';
const results = fs.existsSync(resultsPath) ? JSON.parse(fs.readFileSync(resultsPath, 'utf8')) : {};
const worker = await createWorker('eng');
for (const file of images) {
  const t0 = Date.now();
  // Same strategy as the app (fileImport.ts): document layout first, sparse-text retry when nothing is found.
  const run = async psm => { await worker.setParameters({ tessedit_pageseg_mode: psm }); const { data } = await worker.recognize(dir + file); const conf = data.confidence / 100; const lines = data.text.split('\n').map((t, i) => ({ text: t, confidence: conf, locator: `line ${i + 1}` })).filter(l => l.text.trim()); return { text: data.text, conf, lines, r: parseReportText(lines, { format: 'image-ocr', method: 'ocr', fileName: file, fileSha256: 'x', batchId: 'acc', engine: 'tesseract.js', now: new Date('2026-10-16T12:00:00Z') }) }; };
  let pass = await run('3'); let mode = 'document';
  if (!pass.r.candidates.length && !pass.r.nonGlucose.length) { const sparse = await run('11'); if (sparse.r.candidates.length || sparse.r.nonGlucose.length) { pass = sparse; mode = 'sparse'; } }
  const { text, conf, r } = pass;
  fs.writeFileSync(`${dir}ocr/${file}.txt`, `# tesseract.js ${conf.toFixed(2)} ${mode}\n${text}`);
  const want = truth[file]; const fields = { value: [0, 0], unit: [0, 0], context: [0, 0], date: [0, 0], time: [0, 0] };
  for (const w of want.readings) {
    const got = r.candidates.find(c => c.value === w.value) || r.candidates[want.readings.indexOf(w)];
    for (const k of Object.keys(fields)) { fields[k][1]++; const g = got ? { value: got.value, unit: got.unit, context: got.mealContext, date: got.date, time: got.time }[k] : null; if (g === w[k]) fields[k][0]++; }
  }
  const extra = r.candidates.filter(c => !want.readings.some(w => w.value === c.value)).length;
  const ng = want.nonGlucose.every(k => r.nonGlucose.some(n => n.kind === k)) && !r.candidates.some(c => /hba1c|a1c/i.test(c.provenance.raw));
  results[file] = { fields, extraCandidates: extra, nonGlucoseSeparated: ng, ocrConfidence: Number(conf.toFixed(2)), mode, ms: Date.now() - t0 };
  console.log(file, JSON.stringify(results[file]));
}
await worker.terminate();
fs.writeFileSync(resultsPath, JSON.stringify(results, null, 1));
