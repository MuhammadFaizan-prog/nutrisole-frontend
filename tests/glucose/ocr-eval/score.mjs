// Scores cached OCR output (ocr-run.mjs) against ground truth for four pipelines:
//   old = tesseract.js + G-2 parser (frozen copy) | new = PP-OCRv5 + geometry rows + G-3 parser
//   plus the two cross combinations, to show what the engine vs. the parser contributes.
// Field-level: value, unit, test type per ground-truth reading; date per image; false positives
// (extra glucose candidates, e.g. a reference range or HbA1c read as a reading).
// Usage: node ... score.mjs <imagesDir> <cacheDir> [--json out.json] [--detail]
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { parseReportText as parseNew } from '../../../src/nutrisole/glucose/import/labText.ts';
import { parseReportText as parseOld } from './legacy-labText.ts';
import { displayDate } from '../../../src/nutrisole/glucose/import/dates.ts';
const args = process.argv.slice(2); const [dir, cache] = args; const jsonOut = args.includes('--json') ? args[args.indexOf('--json') + 1] : null; const detail = args.includes('--detail');
const truth = JSON.parse(readFileSync(path.join(dir, 'ground-truth.json'), 'utf8'));
const NOW = new Date('2026-10-16T12:00:00+05:00');
const stripCells = r => ({ ...r, lines: r.lines.map(({ cells, ...l }) => l) });
function run(parse, ocr, keepCells) {
  const meta = { format: 'image-ocr', method: 'ocr', fileName: 'x.jpg', fileSha256: 'f'.repeat(64), batchId: 'b', engine: ocr.doc.engine, now: NOW };
  const doc = keepCells ? ocr.doc : stripCells(ocr.doc); let r = parse(doc.lines, meta);
  if (!r.candidates.length && !r.nonGlucose.length) { const sp = keepCells ? ocr.sparse : stripCells(ocr.sparse); const r2 = parse(sp.lines, meta); if (r2.candidates.length || r2.nonGlucose.length) r = r2; }
  return r;
}
const num = v => (v == null || v === '' ? NaN : Number(v));
function score(img, res) {
  const cands = res.candidates.slice(); const used = new Set(); const fields = [];
  for (const g of img.readings) {
    let k = cands.findIndex((c, i) => !used.has(i) && c.mealContext === g.type && num(c.value) === num(g.value));
    if (k < 0) k = cands.findIndex((c, i) => !used.has(i) && c.mealContext === g.type);
    if (k < 0) k = cands.findIndex((c, i) => !used.has(i) && num(c.value) === num(g.value));
    const c = k >= 0 ? cands[k] : null; if (k >= 0) used.add(k);
    fields.push({ gt: g, got: c ? { value: c.value, unit: c.unit, type: c.mealContext, conf: c.confidence, flags: c.flags } : null,
      value: !!c && num(c.value) === num(g.value), unit: !!c && c.unit === g.unit, type: !!c && c.mealContext === g.type });
  }
  const expDate = displayDate({ year: img.date.y, month: img.date.m - 1, day: img.date.d });
  const dates = res.candidates.map(c => c.date).filter(Boolean);
  return { fields, date: dates.length > 0 && dates.every(d => d === expDate), gotDate: dates[0] || null, expDate, fp: cands.length - used.size, fpValues: cands.filter((_, i) => !used.has(i)).map(c => `${c.value} ${c.unit} ${c.mealContext}`) };
}
const pipes = { old: ['tess', parseOld, false], new: ['pp', parseNew, true], 'tesseract+newParser': ['tess', parseNew, true], 'ppocr+oldParser': ['pp', parseOld, false] };
const report = { split: truth.split, images: truth.images.length, readings: truth.images.reduce((n, i) => n + i.readings.length, 0), pipelines: {} };
const perImage = [];
for (const [name, [eng, parse, cells]] of Object.entries(pipes)) {
  const agg = { value: 0, unit: 0, type: 0, allThree: 0, readings: 0, date: 0, images: 0, fp: 0, lowConfFlaggedWrong: 0, wrongValues: 0, byKind: {} };
  for (const img of truth.images) {
    const c = JSON.parse(readFileSync(path.join(cache, img.file + '.json'), 'utf8'));
    const s = score(img, run(parse, c[eng], cells));
    const k = (agg.byKind[img.kind] ??= { value: 0, readings: 0, date: 0, images: 0 });
    for (const f of s.fields) { agg.readings++; k.readings++; if (f.value) { agg.value++; k.value++; } if (f.unit) agg.unit++; if (f.type) agg.type++; if (f.value && f.unit && f.type) agg.allThree++; if (f.got && !f.value) { agg.wrongValues++; if (f.got.flags.includes('low-confidence') || f.got.conf < 0.6) agg.lowConfFlaggedWrong++; } }
    agg.images++; k.images++; if (s.date) { agg.date++; k.date++; } agg.fp += s.fp;
    if (detail && (name === 'new' || name === 'old')) perImage.push({ pipe: name, file: img.file, ...s });
  }
  const pct = (a, b) => b ? Math.round((1000 * a) / b) / 10 : null;
  report.pipelines[name] = { valuePct: pct(agg.value, agg.readings), unitPct: pct(agg.unit, agg.readings), typePct: pct(agg.type, agg.readings), allThreePct: pct(agg.allThree, agg.readings), datePct: pct(agg.date, agg.images), falsePositives: agg.fp, wrongValuesReturned: agg.wrongValues, byKind: Object.fromEntries(Object.entries(agg.byKind).map(([k, v]) => [k, { valuePct: pct(v.value, v.readings), datePct: pct(v.date, v.images), readings: v.readings, images: v.images }])) };
}
console.log(JSON.stringify(report, null, 1));
if (detail) for (const p of perImage) { const bad = p.fields.filter(f => !(f.value && f.unit && f.type)); if (bad.length || !p.date || p.fp) console.log(p.pipe, p.file, bad.map(f => `GT ${f.gt.value} ${f.gt.unit} ${f.gt.type} -> ${f.got ? `${f.got.value} ${f.got.unit} ${f.got.type}` : 'MISSING'}`).join('; '), p.date ? '' : `DATE ${p.gotDate} vs ${p.expDate}`, p.fp ? `FP ${p.fpValues.join(',')}` : ''); }
if (jsonOut) writeFileSync(jsonOut, JSON.stringify({ ...report, perImage }, null, 1));
