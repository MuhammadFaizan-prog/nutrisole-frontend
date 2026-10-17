// Stage G-2 import tests: CSV/XLSX/PDF-text/OCR-text parsers, unit detection, review flow,
// dedupe, Health Connect / HealthKit mapping and the BLE Glucose Profile byte parser.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileToBatch, detectKind, remapBatch, decodeUtf8 } from '../../src/nutrisole/glucose/import/fileImport.ts';
import { parseDelimited, autoMap, remap } from '../../src/nutrisole/glucose/import/tabular.ts';
import { readXlsx } from '../../src/nutrisole/glucose/import/xlsx.ts';
import { parseReportText, normalizeOcrLine, resultNumbers } from '../../src/nutrisole/glucose/import/labText.ts';
import { groupTextItems, pdfTextLines } from '../../src/nutrisole/glucose/import/pdfText.ts';
import { inferUnit, unitFromText, plausibilityFlags, contextFromText, inferColumnUnit } from '../../src/nutrisole/glucose/import/unitDetect.ts';
import { assessBatch, bulk, setDecision, editCandidate, draftsToSave, summarize, canConfirm, dedupeKey } from '../../src/nutrisole/glucose/import/review.ts';
import { healthConnectToBatch, healthKitToBatch, glsToBatch } from '../../src/nutrisole/glucose/import/devices.ts';
import { parseGlsMeasurement, parseGlsContext, parseRacp, racpReportAll, racpReportSince, downloadRecords, SimulatedGlucoseMeter, encodeMeasurement, encodeSfloat } from '../../src/nutrisole/glucose/import/gls.ts';
import { sha256Hex } from '../../src/nutrisole/glucose/import/sha256.ts';
import { findDate, findTime, detectDateOrder, excelSerialToParts } from '../../src/nutrisole/glucose/import/dates.ts';
import type { GlucoseReading } from '../../src/nutrisole/glucose/types.ts';
import type { ImportBatch } from '../../src/nutrisole/glucose/import/types.ts';

const fx = (name: string) => new URL(`./fixtures/${name}`, import.meta.url);
const file = (name: string, mime: string | null = null) => ({ name, mime, bytes: new Uint8Array(fs.readFileSync(fx(name))) });
const now = new Date('2026-10-16T12:00:00Z');
const noText = {};
const brief = (b: ImportBatch) => b.candidates.map(c => [c.value, c.unit, c.date, c.time, c.mealContext]);
const reading = (measuredAt: string, valueMgDl: number, extra: Partial<GlucoseReading> = {}): GlucoseReading => ({ id: 'r1', userId: 'u', measuredAt, tzOffsetMinutes: 300, tzName: null, valueOriginal: String(valueMgDl), unitOriginal: 'mg/dL', valueMgDl, mealContext: 'fasting', note: null, source: { type: 'manual', provider: null, device: null, recordId: null }, createdAt: measuredAt, updatedAt: measuredAt, ...extra });
process.env.TZ = process.env.TZ || 'Asia/Karachi';

test('CSV: Accu-Chek-360-style export (semicolons, preamble, dd.mm.yyyy, unit column, control test)', async () => {
  const b = await fileToBatch(file('accuchek-360-style.csv'), noText, { now });
  assert.equal(b.format, 'csv'); assert.equal(b.table!.mapping.headerRow, 3);
  assert.deepEqual(brief(b).slice(0, 3), [['108', 'mg/dL', 'Oct 12, 2026', '7:10 AM', 'before_meal'], ['171', 'mg/dL', 'Oct 12, 2026', '1:45 PM', 'after_meal'], ['96', 'mg/dL', 'Oct 13, 2026', '7:05 AM', 'fasting']]);
  assert.ok(b.candidates[3].flags.includes('control-solution'));
  assert.equal(b.candidates[0].unitSource, 'explicit'); assert.equal(b.candidates[0].provenance.locator, 'row 5'); assert.equal(b.candidates[0].provenance.provider, 'file:csv');
  assert.equal(b.candidates[0].provenance.fileSha256, sha256Hex(file('accuchek-360-style.csv').bytes));
});

test('CSV: mySugr-style export skips non-glucose log rows and reads the unit from the header', async () => {
  const b = await fileToBatch(file('mysugr-style.csv'), noText, { now });
  assert.deepEqual(brief(b), [['99', 'mg/dL', 'Oct 14, 2026', '7:12 AM', 'fasting'], ['165', 'mg/dL', 'Oct 14, 2026', '10:05 AM', 'after_meal'], ['104', 'mg/dL', 'Oct 15, 2026', '7:20 AM', 'fasting'], ['138', 'mg/dL', 'Oct 15, 2026', '11:40 PM', 'bedtime']]);
  assert.ok(b.candidates.every(c => c.unitSource === 'column' && !c.flags.includes('unit-inferred')));
  assert.ok(b.notes.some(n => /1 row had no glucose value/.test(n)));
});

test('CSV: Contour-style mmol/L export detects MM/DD from a day > 12', async () => {
  const b = await fileToBatch(file('contour-style.csv'), noText, { now });
  assert.equal(b.table!.mapping.dateOrder, 'MDY');
  assert.deepEqual(brief(b)[1], ['8.4', 'mmol/L', 'Oct 13, 2026', '2:05 PM', 'after_meal']);
  assert.equal(b.candidates[3].mealContext, 'bedtime');
});

test('CSV: generic export ignores the HbA1c column, flags unit, implausible, duplicate and missing time', async () => {
  const b = await fileToBatch(file('generic.csv'), noText, { now });
  const m = b.table!.mapping; assert.equal(b.table!.mapping.header[m.value!], 'glucose'); assert.equal(m.header[m.unit!], 'unit');
  assert.ok(!b.candidates.some(c => c.value === '6.1'), 'HbA1c column never becomes a reading');
  const a = assessBatch(b, [], now);
  assert.deepEqual(a[1].unit, 'mmol/L');
  assert.ok(a[2].allFlags.includes('unit-inferred'));
  assert.ok(a[3].allFlags.includes('implausible'));
  assert.ok(a[4].allFlags.includes('duplicate-batch'));
  assert.ok(a[5].allFlags.includes('missing-time'));
});

test('manual column mapper: re-mapping changes candidates; no value column is reported honestly', async () => {
  const b = await fileToBatch(file('generic.csv'), noText, { now });
  const none = remapBatch(b, remap(b.table!.mapping, 'value', null));
  assert.equal(none.candidates.length, 0); assert.match(none.notes.join(' '), /No glucose value column/);
  const back = remapBatch(none, remap(none.table!.mapping, 'value', 1));
  assert.equal(back.candidates.length, 6); assert.equal(back.table!.mapping.auto, false);
});

test('XLSX: Contour-style workbook with real date cells and a preamble row', async () => {
  const wb = readXlsx(file('contour-style.xlsx').bytes);
  assert.equal(wb.sheetName, 'Readings'); assert.deepEqual(wb.rows[1], ['Date and Time', 'Reading [mg/dL]', 'Meal Marker', 'Notes']); assert.equal(wb.rows[2][0], '2026-10-13 07:30');
  const b = await fileToBatch(file('contour-style.xlsx'), noText, { now });
  assert.equal(b.format, 'xlsx'); assert.deepEqual(brief(b)[1], ['152', 'mg/dL', 'Oct 13, 2026', '2:05 PM', 'after_meal']);
  assert.equal(b.candidates[3].note, 'bedtime check'); assert.equal(b.candidates[3].mealContext, 'bedtime');
});

test('file type detection and honest errors', async () => {
  assert.equal(detectKind(file('chughtai-style.pdf')), 'pdf'); assert.equal(detectKind(file('meter-mgdl.png')), 'image'); assert.equal(detectKind(file('chughtai-style-photo.jpg')), 'image'); assert.equal(detectKind(file('contour-style.xlsx')), 'xlsx');
  await assert.rejects(fileToBatch({ name: 'x.csv', mime: 'text/csv', bytes: new Uint8Array() }, noText), /empty/);
  await assert.rejects(fileToBatch({ name: 'x.docx', mime: null, bytes: new Uint8Array([1, 2, 3, 4, 5]) }, noText), /not a supported file/);
  await assert.rejects(fileToBatch(file('chughtai-style.pdf'), { pdfText: async () => null }), /web app/);
  await assert.rejects(fileToBatch(file('meter-mgdl.png'), noText), /not available/);
  assert.equal(decodeUtf8(new TextEncoder().encode('Glucose µ ✓')), 'Glucose µ ✓');
});

test('PDF text layer (pdf.js legacy build in Node): Chughtai-style report parses; scanned PDF falls back to OCR', async () => {
  const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs');
  const pdfText = (bytes: Uint8Array) => pdfTextLines(bytes, pdfjs as never);
  const b = await fileToBatch(file('chughtai-style.pdf'), { pdfText }, { now });
  assert.equal(b.format, 'pdf-text');
  assert.deepEqual(brief(b), [['112', 'mg/dL', 'Oct 12, 2026', '8:20 AM', 'fasting']]);
  assert.deepEqual(b.nonGlucose.map(n => n.kind).sort(), ['eag', 'hba1c']);
  let ocrCalled = false;
  const scanned = await fileToBatch(file('idc-style-scanned.pdf'), { pdfText, pdfOcr: async () => { ocrCalled = true; return { lines: ocrLines('idc-style.png'), confidence: 0.9, engine: 'test-ocr' }; } }, { now });
  assert.ok(ocrCalled); assert.equal(scanned.format, 'pdf-ocr'); assert.equal(scanned.method, 'ocr'); assert.deepEqual(brief(scanned), [['134', 'mg/dL', 'Oct 16, 2026', '8:10 AM', 'random']]);
  assert.deepEqual(groupTextItems([{ str: '112', x: 200, y: 700, width: 20, height: 10 }, { str: 'Glucose Fasting', x: 40, y: 701, width: 80, height: 10 }, { str: 'Header', x: 40, y: 750, width: 40, height: 10 }], 1).map(l => l.text), ['Header', 'Glucose Fasting   112']);
});

const ocrLines = (name: string) => fs.readFileSync(fx(`ocr/${name}.txt`), 'utf8').split('\n').slice(1).map((text, i) => ({ text, confidence: 0.85, locator: `line ${i + 1}` })).filter(l => l.text.trim());
const truth = JSON.parse(fs.readFileSync(fx('truth.json'), 'utf8'));

test('OCR text (real tesseract.js output on synthetic fixtures): lab layouts and meter screens', () => {
  for (const name of Object.keys(truth).filter(f => /\.(png|jpe?g)$/.test(f))) {
    const r = parseReportText(ocrLines(name), { format: 'image-ocr', method: 'ocr', fileName: name, fileSha256: 'h', batchId: 'b', engine: 'tesseract.js', now });
    const got = r.candidates.map(c => ({ value: c.value, unit: c.unit, context: c.mealContext, date: c.date, time: c.time }));
    // The old reader guessed mg/dL when this OCR transcript omitted the unit.
    // Missing units now require a clearer image or manual entry.
    if (name === 'meter-mgdl.png') assert.deepEqual(got, [], 'a unit-less number is not sufficient meter evidence');
    else assert.deepEqual(got, truth[name].readings, name);
    for (const k of truth[name].nonGlucose) assert.ok(r.nonGlucose.some(n => n.kind === k), `${name}: ${k} separated`);
    assert.ok(r.candidates.every(c => c.provenance.method === 'ocr' && c.provenance.engine === 'tesseract.js'));
  }
});

test('lab text: HbA1c / eAG / urine sugar are never readings; reference ranges and commentary are ignored', () => {
  const lines = ['Collected On: 03/04/2026 08:00 AM', 'Glycated Hemoglobin (HbA1c) 7.2 % 4.0-5.6', 'eAG 160 mg/dL', 'Urine Glucose Nil', 'Fasting glucose 100 - 125 mg/dL : impaired fasting glucose', 'Plasma Glucose (F) 98 mg/dL 70 - 100', 'Blood Sugar Random 7.4 mmol/L 3.9-7.8', 'Glucose 2 Hrs After Breakfast 142 H mg/dL < 140']
    .map((text, i) => ({ text, locator: `line ${i + 1}` }));
  const r = parseReportText(lines, { format: 'pdf-text', method: 'file', fileName: 'r.pdf', fileSha256: 'h', batchId: 'b', engine: null, now });
  assert.deepEqual(r.candidates.map(c => [c.value, c.unit, c.mealContext, c.date]), [['98', 'mg/dL', 'fasting', 'Apr 3, 2026'], ['7.4', 'mmol/L', 'random', 'Apr 3, 2026'], ['142', 'mg/dL', 'after_meal', 'Apr 3, 2026']]);
  assert.deepEqual(r.nonGlucose.map(n => [n.kind, n.value]), [['hba1c', '7.2'], ['eag', '160']]);
  assert.deepEqual(resultNumbers('Glucose 112 mg/dL 70 - 110'), ['112']); assert.deepEqual(resultNumbers('< 200'), []);
  assert.equal(normalizeOcrLine('RBS 1O8 mg/d1'), 'RBS 108 mg/dL');
  const none = parseReportText([{ text: 'Lipid profile only', locator: 'l1' }], { format: 'pdf-text', method: 'file', fileName: null, fileSha256: null, batchId: 'b', engine: null, now });
  assert.equal(none.kind, 'none'); assert.equal(none.candidates.length, 0);
});

test('units: detection, inference, plausibility (10–600 mg/dL) and contexts', () => {
  assert.equal(unitFromText('Reading [mmol/L]'), 'mmol/L'); assert.equal(unitFromText('mg/dl'), 'mg/dL'); assert.equal(unitFromText('mgdl'), 'mg/dL'); assert.equal(unitFromText('kcal'), null);
  assert.deepEqual(inferUnit('6.1'), { unit: 'mmol/L', ambiguous: false, confidence: 0.75 }); assert.equal(inferUnit('110').unit, 'mg/dL'); assert.ok(inferUnit('25').ambiguous);
  assert.equal(inferColumnUnit(['5.6', '7.1', '6.0']), 'mmol/L'); assert.equal(inferColumnUnit(['101', '140', '99']), 'mg/dL');
  assert.deepEqual(plausibilityFlags('650', 'mg/dL'), ['implausible']); assert.deepEqual(plausibilityFlags('33.4', 'mmol/L'), ['implausible']); assert.deepEqual(plausibilityFlags('5.5', 'mmol/L'), []); assert.deepEqual(plausibilityFlags('9', 'mg/dL'), ['implausible']);
  assert.equal(contextFromText('PPBS 2 hrs'), 'after_meal'); assert.equal(contextFromText('FBS'), 'fasting'); assert.equal(contextFromText('Breakfast'), 'unspecified');
  assert.equal(detectDateOrder(['03/04/2026', '13/04/2026']), 'DMY'); assert.equal(detectDateOrder(['04/13/2026']), 'MDY');
  assert.deepEqual(findDate('Collected: 16-Oct-2026')!.date, { year: 2026, month: 9, day: 16 }); assert.deepEqual(findTime('at 8:05 pm')!.time, { hour: 20, minute: 5 }); assert.equal(findDate('31/02/2026'), null);
  assert.deepEqual(excelSerialToParts(46308.3125), { year: 2026, month: 9, day: 13, hour: 7, minute: 30 });
});

test('review: nothing saves until confirmed; bulk confirm skips flagged rows; edit keeps the original', async () => {
  const b0 = await fileToBatch(file('generic.csv'), noText, { now });
  assert.equal(draftsToSave(b0, [], now).drafts.length, 0, 'pending rows are never saved');
  const b1 = bulk(b0, 'confirm-clean', [], now);
  assert.deepEqual(b1.candidates.map(c => c.decision), ['confirmed', 'confirmed', 'pending', 'pending', 'pending', 'pending']);
  const s = summarize(assessBatch(b1, [], now)); assert.equal(s.confirmed, 2); assert.equal(s.flagged, 4);
  // Row 3 (unit inferred): the user checks it, sets the unit explicitly and confirms that one row.
  let b2 = editCandidate(b1, b1.candidates[2].id, { unit: 'mg/dL' }); b2 = setDecision(b2, b2.candidates[2].id, 'confirmed');
  assert.equal(b2.candidates[2].original.value, '95'); assert.equal(b2.candidates[2].edited, true);
  // Implausible 850 cannot be confirmed in bulk; missing time blocks saving until edited.
  b2 = setDecision(b2, b2.candidates[5].id, 'confirmed');
  const res = draftsToSave(b2, [], now);
  assert.equal(res.drafts.length, 3); assert.equal(res.blocked.length, 1); assert.match(res.blocked[0].reason, /No time found/);
  const d = res.drafts[0];
  assert.equal(d.source.type, 'file'); assert.equal(d.source.provider, 'file:csv'); assert.match(d.source.recordId!, /:row2$/); assert.equal(d.source.batchId, b0.id);
  assert.equal(d.valueOriginal, '110'); assert.equal(d.unitOriginal, 'mg/dL'); assert.equal((d.source.meta as Record<string, unknown>).originalValue, '110');
  assert.equal(res.drafts[1].unitOriginal, 'mmol/L'); assert.equal(res.drafts[1].valueOriginal, '7.9'); assert.equal(res.drafts[1].valueMgDl, 142.34);
  const rejected = bulk(b2, 'reject-all', [], now); assert.equal(draftsToSave(rejected, [], now).drafts.length, 0);
  b2 = editCandidate(b2, b2.candidates[5].id, { time: '7:30 AM' });
  assert.equal(draftsToSave(b2, [], now).drafts.length, 4);
});

test('dedupe: same value + minute in history is flagged; re-importing the same file row is blocked', async () => {
  const b = await fileToBatch(file('accuchek-360-style.csv'), noText, { now });
  const first = assessBatch(b, [], now)[0];
  const manual = reading(first.measuredAt!, 108);
  assert.ok(assessBatch(b, [manual], now)[0].allFlags.includes('duplicate-existing'));
  assert.ok(!bulk(b, 'confirm-clean', [manual], now).candidates[0].decision.startsWith('confirm'));
  const imported = reading(first.measuredAt!, 108, { id: 'r2', source: { type: 'file', provider: 'file:csv', device: null, recordId: first.provenance.recordId } });
  const again = assessBatch(b, [imported], now)[0];
  assert.ok(again.allFlags.includes('already-imported')); assert.equal(canConfirm(again).ok, false);
  assert.equal(dedupeKey('2026-10-12T02:10:30.000Z', 108), '2026-10-12T02:10:00.000Z|108.0');
});

test('Health Connect: BloodGlucoseRecord mapping keeps provenance and offset; CGM is flagged', () => {
  const b = healthConnectToBatch([
    { metadata: { id: 'hc-1', dataOrigin: 'com.example.meter' }, time: '2026-10-15T03:00:00Z', zoneOffset: { totalSeconds: 18000 }, level: { inMilligramsPerDeciliter: 104, inMillimolesPerLiter: 5.77 }, specimenSource: 2, relationToMeal: 2 },
    { metadata: { id: 'hc-2', dataOrigin: 'com.example.cgm' }, time: '2026-10-15T04:00:00Z', zoneOffset: { totalSeconds: 18000 }, level: { inMilligramsPerDeciliter: 99 }, specimenSource: 1, relationToMeal: 0 },
    { time: '2026-10-15T05:00:00Z', level: { inMilligramsPerDeciliter: 99 } },
  ], now);
  assert.equal(b.candidates.length, 2);
  assert.deepEqual(brief(b)[0], ['104', 'mg/dL', 'Oct 15, 2026', '8:00 AM', 'fasting']);
  assert.equal(b.candidates[0].provenance.recordId, 'hc-1'); assert.equal(b.candidates[0].provenance.provider, 'com.example.meter'); assert.equal(b.candidates[0].tzOffsetMinutes, 300);
  const a = assessBatch(b, [], now); assert.ok(a[1].allFlags.includes('specimen')); assert.equal(canConfirm(a[1]).ok, false);
  const saved = draftsToSave(setDecision(b, b.candidates[0].id, 'confirmed'), [], now).drafts[0];
  assert.equal(saved.measuredAt, '2026-10-15T03:00:00.000Z'); assert.equal(saved.source.type, 'health_connect');
  assert.equal(healthConnectToBatch([], now).notes[0], 'Health Connect returned no blood glucose records for that period.');
});

test('HealthKit (typed path, iOS unverified): sample mapping', () => {
  const b = healthKitToBatch([{ uuid: 'u-1', startDate: '2026-10-15T03:00:00Z', value: 101, sourceBundleId: 'com.example.app', metadata: { HKBloodGlucoseMealTime: 2 } }], now);
  assert.equal(b.candidates[0].mealContext, 'after_meal'); assert.equal(b.candidates[0].provenance.recordId, 'u-1'); assert.equal(b.method, 'healthkit');
});

// GLS spec-style byte vectors (little-endian; SFLOAT = 4-bit exponent + 12-bit mantissa).
test('BLE 0x2A18: SFLOAT kg/L and mol/L, time offset, type/location, sensor status', () => {
  // flags 0x0B: time offset + concentration (kg/L) + sensor status; seq 0x0102; 2026-10-16 08:15:30; offset -60 min; 0xB06E = 110e-5 kg/L; type 1 loc 1; status 0x0001
  const m = parseGlsMeasurement(new Uint8Array([0x0b, 0x02, 0x01, 0xea, 0x07, 10, 16, 8, 15, 30, 0xc4, 0xff, 0x6e, 0xb0, 0x11, 0x01, 0x00]));
  assert.deepEqual([m.sequence, m.wallClock, m.timeOffsetMinutes, m.value, m.unit, m.specimen, m.location, m.sensorStatus], [258, '2026-10-16T07:15:30', -60, '110', 'mg/dL', 'capillary_whole_blood', 'finger', ['device battery low']]);
  // flags 0x06: concentration in mol/L; 0xC03D = 61e-4 mol/L = 6.1 mmol/L; type 2 (capillary plasma), location 2 (AST)
  const mm = parseGlsMeasurement(new Uint8Array([0x06, 0x03, 0x00, 0xea, 0x07, 10, 16, 21, 5, 0, 0x3d, 0xc0, 0x22]));
  assert.deepEqual([mm.value, mm.unit, mm.specimen, mm.location], ['6.1', 'mmol/L', 'capillary_plasma', 'alternate site test']);
  // NaN concentration (0x07FF) → no value; ISF type 9; context follows (0x10)
  const nan = parseGlsMeasurement(new Uint8Array([0x12, 0x04, 0x00, 0xea, 0x07, 10, 16, 9, 0, 0, 0xff, 0x07, 0x19]));
  assert.deepEqual([nan.value, nan.specimen, nan.contextFollows], [null, 'interstitial_fluid', true]);
  assert.throws(() => parseGlsMeasurement(new Uint8Array([0x03, 0x01, 0x00, 0xea, 0x07, 10, 16, 8, 15, 0, 0x00])), /truncated/);
  assert.throws(() => parseGlsMeasurement(new Uint8Array([0x02, 0x01, 0x00, 0x00, 0x00, 0, 0, 0, 0, 0, 0x6e, 0xb0, 0x11])), /base time/);
  assert.equal(encodeSfloat(110e-5, -5), 0xb06e); assert.equal(encodeSfloat(61e-4, -4), 0xc03d);
});

test('BLE 0x2A34 context and 0x2A52 RACP', () => {
  // flags 0x46: meal + tester/health + HbA1c; seq 2; meal 3 (fasting); tester self (1) / health none (5); HbA1c 6.4 % (0xF040)
  const c = parseGlsContext(new Uint8Array([0x46, 0x02, 0x00, 0x03, 0x51, 0x40, 0xf0]));
  assert.deepEqual([c.sequence, c.meal, c.tester, c.health, c.hba1cPercent], [2, 'fasting', 'self', 'no health issues', 6.4]);
  // carbohydrate: id 1 (breakfast), 0.045 kg = 45 g → SFLOAT mantissa 45 exp -3 (0xD02D)
  assert.equal(parseGlsContext(new Uint8Array([0x01, 0x05, 0x00, 0x01, 0x2d, 0xd0])).carbsGrams, 45);
  assert.deepEqual([...racpReportAll()], [0x01, 0x01]); assert.deepEqual([...racpReportSince(0x0102)], [0x01, 0x03, 0x01, 0x02, 0x01]);
  assert.deepEqual(parseRacp(new Uint8Array([0x06, 0x00, 0x01, 0x06])), { kind: 'response', requestOpCode: 1, code: 6, message: 'no records found' });
  assert.deepEqual(parseRacp(new Uint8Array([0x05, 0x00, 0x2c, 0x01])), { kind: 'count', count: 300 });
});

test('BLE simulated meter: report all, since-last-sequence, no records, unsupported operator, dropped link', async () => {
  const recs = [
    { sequence: 1, wall: [2026, 10, 15, 7, 30, 0] as [number, number, number, number, number, number], mgDl: 104, meal: 3 },
    { sequence: 2, wall: [2026, 10, 15, 13, 50, 0] as [number, number, number, number, number, number], mmolL: 8.2, meal: 2, hba1c: 6.4 },
    { sequence: 3, wall: [2026, 10, 15, 21, 0, 0] as [number, number, number, number, number, number], mgDl: 120, type: 10, location: 4 },
    { sequence: 4, wall: [2026, 10, 16, 7, 10, 0] as [number, number, number, number, number, number], mgDl: 97, status: 0x0004 },
  ];
  const all = await downloadRecords(new SimulatedGlucoseMeter(recs), { timeoutMs: 500 });
  assert.equal(all.outcome, 'success'); assert.equal(all.records.length, 4); assert.equal(all.lastSequence, 4); assert.equal(all.records[1].context?.meal, 'after_meal');
  const since = await downloadRecords(new SimulatedGlucoseMeter(recs), { sinceSequence: 3, timeoutMs: 500 }); assert.deepEqual(since.records.map(r => r.sequence), [3, 4]);
  assert.equal((await downloadRecords(new SimulatedGlucoseMeter(recs), { sinceSequence: 9, timeoutMs: 500 })).outcome, 'no-records');
  const old = await downloadRecords(new SimulatedGlucoseMeter(recs, { supportsSince: false }), { sinceSequence: 2, timeoutMs: 500 }); assert.equal(old.outcome, 'failed'); assert.match(old.message, /operator not supported/);
  const dropped = await downloadRecords(new SimulatedGlucoseMeter(recs, { dropBeforeResponse: true }), { timeoutMs: 50 }); assert.equal(dropped.outcome, 'failed'); assert.equal(dropped.records.length, 4);
  const b = glsToBatch(all, { id: 'AA:BB', name: 'Sim meter' }, now);
  assert.deepEqual(brief(b), [['104', 'mg/dL', 'Oct 15, 2026', '7:30 AM', 'fasting'], ['8.2', 'mmol/L', 'Oct 15, 2026', '1:50 PM', 'after_meal'], ['120', 'mg/dL', 'Oct 15, 2026', '9:00 PM', 'unspecified'], ['97', 'mg/dL', 'Oct 16, 2026', '7:10 AM', 'unspecified']]);
  assert.deepEqual(b.nonGlucose.map(n => [n.kind, n.value]), [['hba1c', '6.4']]);
  const a = assessBatch(b, [], now);
  assert.ok(a[2].allFlags.includes('control-solution')); assert.ok(a[3].allFlags.includes('sensor-status')); assert.ok(a.every(x => x.allFlags.includes('meter-clock')));
  const confirmed = bulk(b, 'confirm-clean', [], now); assert.deepEqual(confirmed.candidates.map(c => c.decision), ['confirmed', 'confirmed', 'pending', 'pending']);
  const drafts = draftsToSave(confirmed, [], now).drafts; assert.equal(drafts[0].source.type, 'ble_meter'); assert.equal(drafts[0].source.recordId, 'seq1@2026-10-15T07:30:00'); assert.equal(drafts[1].valueMgDl, 147.75);
  assert.deepEqual([...encodeMeasurement(recs[0])].slice(0, 3), [0x12, 0x01, 0x00]);
});

test('import actions end to end with a fake platform: file → review → bulk confirm → save (demo store); web device import is mobile-only', async () => {
  const { importAction, setImportPlatform } = await import('../../src/nutrisole/glucose/importActions.ts');
  const { createGlucoseStore } = await import('../../src/nutrisole/glucose/store.ts');
  const { initialExpansionState, buildScene } = await import('../../src/nutrisole/extensions/model.ts');
  const { buildImportView } = await import('../../src/nutrisole/glucose/import/view.ts');
  const { base64ToBytes, bytesToBase64 } = await import('../../src/nutrisole/glucose/import/base64.ts');
  assert.equal(bytesToBase64(base64ToBytes('AQID/w==')), 'AQID/w==');
  setImportPlatform({ kind: 'web', os: 'web', ocrEngine: 'fake', devices: null, pickFile: async () => file('mysugr-style.csv', 'text/csv'), captureReport: async () => null, extractors: {} });
  const store = createGlucoseStore({ supabaseUrl: null, supabaseAnonKey: null, demo: true }); await store.start();
  let s = initialExpansionState(); const routes: string[] = []; const sheets: { title: string; choices?: { label: string; action: () => void }[] }[] = [];
  const ctx = () => ({ s, setState: (fn: (x: typeof s) => typeof s) => { s = fn(s); }, store, go: (r: string) => routes.push(r), back: () => {}, open: (sh: never) => sheets.push(sh) }) as never;
  assert.equal(importAction('import-file', ctx()), true);
  for (let i = 0; i < 50 && !routes.includes('import-review'); i++) await new Promise(r => setTimeout(r, 10));
  assert.deepEqual(routes, ['import-review']); assert.equal(s.glucoseImport!.batch!.candidates.length, 4);
  importAction('import-save', ctx()); assert.equal(sheets.at(-1)!.title, 'Check reading'); assert.equal(store.getSnapshot().readings.length, 0, 'nothing auto-saves');
  importAction('import-bulk:confirm-clean', ctx());
  const view = buildImportView(s.glucoseImport, [], 'web'); assert.equal(view.confirmed, 4); assert.equal(view.saveLabel, 'Save 4 readings');
  s = { ...s, glucoseImportView: view }; const scene = buildScene('import-review', s);
  assert.ok(scene.layers.some(l => l.action === 'import-save' && !l.disabled)); assert.ok(scene.layers.some(l => l.action?.startsWith('import-row:')));
  importAction('import-save', ctx());
  for (let i = 0; i < 50 && store.getSnapshot().readings.length < 4; i++) await new Promise(r => setTimeout(r, 10));
  assert.equal(store.getSnapshot().readings.length, 4); assert.equal(store.getSnapshot().readings[0].source.type, 'file'); assert.equal(s.glucoseImport!.batch, null);
  importAction('import-device:ble_meter', ctx()); assert.match(sheets.at(-1)!.title, /available in the mobile app/);
  setImportPlatform(null);
});
