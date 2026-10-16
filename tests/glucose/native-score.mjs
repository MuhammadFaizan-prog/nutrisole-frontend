// Scores real Android reader output against fixed synthetic ground truth.
// node --experimental-strip-types --import ./tests/glucose/resolve-ts.mjs tests/glucose/native-score.mjs INPUT.json OUTPUT.json
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { nativeCaptureResult } from '../../src/nutrisole/glucose/ocr/nativeResult.ts';
import { parseReportText } from '../../src/nutrisole/glucose/import/labText.ts';
import { displayDate } from '../../src/nutrisole/glucose/import/dates.ts';
const root = path.resolve(import.meta.dirname, '../..');
const [inputFile, outputFile] = process.argv.slice(2);
if (!inputFile || !outputFile)
    throw new Error('Usage: native-score.mjs INPUT.json OUTPUT.json');
const output = JSON.parse(fs.readFileSync(inputFile, 'utf8'));
const truth = JSON.parse(fs.readFileSync(path.join(root, 'tests/glucose/ocr-eval/heldout2/ground-truth.json'), 'utf8'));
const details = [];
const agg = { images: 0, readings: 0, value: 0, unit: 0, type: 0, allThree: 0, date: 0, extras: 0, wrongReturned: 0, byKind: {} };
for (const img of truth.images) {
    const native = output[img.file];
    if (!native)
        throw new Error('Missing ' + img.file);
    const ocr = nativeCaptureResult(native);
    const parsed = parseReportText(ocr.lines, { format: 'image-ocr', method: 'ocr', fileName: img.file, fileSha256: 'f'.repeat(64), batchId: img.file, engine: ocr.engine, now: new Date('2026-10-16T12:00:00Z') });
    const used = new Set();
    const fields = [];
    const bucket = agg.byKind[img.kind] ??= { images: 0, readings: 0, value: 0, allThree: 0 };
    for (const g of img.readings) {
        let k = parsed.candidates.findIndex((c, i) => !used.has(i) && c.mealContext === g.type && Number(c.value) === Number(g.value));
        if (k < 0)
            k = parsed.candidates.findIndex((c, i) => !used.has(i) && c.mealContext === g.type);
        if (k < 0)
            k = parsed.candidates.findIndex((c, i) => !used.has(i) && Number(c.value) === Number(g.value));
        const c = k >= 0 ? parsed.candidates[k] : null;
        if (k >= 0)
            used.add(k);
        const v = !!c && Number(c.value) === Number(g.value), u = !!c && c.unit === g.unit, t = !!c && c.mealContext === g.type;
        agg.readings++;
        bucket.readings++;
        if (v) {
            agg.value++;
            bucket.value++;
        }
        if (u)
            agg.unit++;
        if (t)
            agg.type++;
        if (v && u && t) {
            agg.allThree++;
            bucket.allThree++;
        }
        if (c && !v)
            agg.wrongReturned++;
        fields.push({ expected: g, actual: c ? { value: c.value, unit: c.unit, type: c.mealContext } : null, correct: v && u && t });
    }
    const expectedDate = displayDate({ year: img.date.y, month: img.date.m - 1, day: img.date.d });
    if (parsed.candidates.length && parsed.candidates.every(c => c.date === expectedDate))
        agg.date++;
    agg.extras += parsed.candidates.length - used.size;
    agg.images++;
    bucket.images++;
    details.push({ file: img.file, durationMs: native.durationMs, fields, dates: parsed.candidates.map(c => c.date), expectedDate });
}
const times = Object.values(output).map(r => r.durationMs).sort((a, b) => a - b);
const report = { syntheticOnly: true, summary: agg, timing: { files: times.length, min: times[0], median: times[Math.floor(times.length / 2)], p95: times[Math.floor(times.length * .95)], max: times.at(-1) }, details };
fs.writeFileSync(outputFile, JSON.stringify(report, null, 2));
console.log(JSON.stringify({ ...report, details: undefined }, null, 2));
// A functioning engine must recover the known clean baseline. Report the wider
// held-out result as measured; it is not a clinical accuracy certification.
const baseline = details.find(d => d.file === 'heldout2-00-lab-report-clean.jpg');
assert.ok(baseline?.fields.length && baseline.fields.every(f => f.correct), 'Native OCR must recover the clean baseline values, units and reading types');
