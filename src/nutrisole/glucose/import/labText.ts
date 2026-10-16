// Parses text from a PDF text layer or OCR into glucose candidates. Tuned to common
// Pakistani lab report layouts (Chughtai, Shaukat Khanum, Excel Labs, IDC style: "Glucose
// Fasting", "Random Blood Sugar", "FBS", "RBS", mg/dL, "Collected on") and to meter
// screen photos. HbA1c, eAG and urine sugar are reported separately, never as readings.
import type { GlucoseUnit, MealContext } from '../types';
import { normalizeDecimal } from '../units';
import type { CandidateFlag, ImportCandidate, ImportFormat, NonGlucoseFinding } from './types';
import { displayDate, displayTime, findDate, findTime, type DateParts, type TimeParts } from './dates';
import { plausibilityFlags, resolveUnit, unitFromText } from './unitDetect';

/** One OCR box on a row; x0/x1 are positions along the text direction (pixels). */
export type TextCell = { text: string; x0: number; x1: number; confidence: number; h?: number };
export type TextLine = { text: string; confidence?: number | null; locator: string; cells?: TextCell[] };
export type LabParseResult = { kind: 'lab-report' | 'meter-screen' | 'none'; candidates: ImportCandidate[]; nonGlucose: NonGlucoseFinding[]; notes: string[]; collected: { date: DateParts | null; time: TimeParts | null; label: string | null } };

/** OCR clean-up that only touches number-like tokens and unit spellings. */
export function normalizeOcrLine(text: string): string {
  return text
    .replace(/[|¦]/g, ' ')
    .replace(/m\s*g\s*[/l1I|]\s*d\s*[lL1I|]\b\.?/g, 'mg/dL').replace(/mg\s*\/\s*dl/gi, 'mg/dL').replace(/mgdl\b/gi, 'mg/dL')
    .replace(/m\s*m\s*o\s*[l1I]\s*[/l1I|]\s*[lL1I]\b/gi, 'mmol/L')
    .replace(/(?<=\d)[oO](?=\d|\b)/g, '0').replace(/(?<=\d[.,])[oO]/g, '0')
    .replace(/(?<=\s)[oO](?=[.,]?\d)/g, '0')
    .replace(/(\d),(\d{1,2})(?!\d)/g, '$1.$2')
    .replace(/\b0ct\b/g, 'Oct').replace(/\bN0v\b/g, 'Nov')
    .replace(/\s{2,}/g, ' ').trim();
}

const NON_GLUCOSE: { kind: NonGlucoseFinding['kind']; re: RegExp; label: string }[] = [
  { kind: 'hba1c', re: /(hb\s*a\s*[1lI]\s*c|hba[1lI]c|\ba1c\b|glyc(?:at|osyl)ated\s*h(?:a)?emoglobin|glycohemoglobin)/i, label: 'HbA1c' },
  { kind: 'eag', re: /(estimated\s*average\s*glucose|\beag\b|mean\s*(?:plasma|blood)\s*glucose)/i, label: 'Estimated average glucose' },
  { kind: 'urine', re: /(urine|urinary)\s*(?:\w+\s*){0,2}(sugar|glucose)|(sugar|glucose)\s*\(?\s*urine/i, label: 'Urine sugar' },
];
const TESTS: { re: RegExp; context: MealContext; label: string }[] = [
  { re: /(fasting\s*(?:blood|plasma|serum)?\s*(?:sugar|glucose)|(?:blood|plasma|serum)?\s*(?:sugar|glucose)\s*[,\-–(]*\s*fasting|\bf\.?\s?b\.?\s?s\b\.?|\bfpg\b|\bfbg\b|(?:glucose|sugar)\s*\(\s*f\s*\)|\bbsf\b)/i, context: 'fasting', label: 'Fasting' },
  { re: /(random\s*(?:blood|plasma|serum)?\s*(?:sugar|glucose)|(?:blood|plasma|serum)?\s*(?:sugar|glucose)\s*[,\-–(]*\s*random|\br\.?\s?b\.?\s?s\b\.?|\brbg\b|(?:glucose|sugar)\s*\(\s*r\s*\)|\bbsr\b)/i, context: 'random', label: 'Random' },
  { re: /(post\s*-?\s*prandial|\bp\.?\s?p\.?\s?b\.?\s?s\b|\b2\s*-?\s*h(?:ou)?rs?\.?\s*(?:after|pp|post|abf)|\bpp\b\s*(?:blood)?\s*(?:sugar|glucose)|(?:sugar|glucose)\s*[,\-–(]*\s*(?:2\s*hrs?\s*)?p\.?p\b|after\s*(?:meal|breakfast|lunch|dinner))/i, context: 'after_meal', label: 'After a meal (PP)' },
  { re: /(?<!urine\s)(?<!urinary\s)\b(?:blood|plasma|serum|capillary)?\s*(?:sugar|glucose)\b/i, context: 'unspecified', label: 'Glucose' },
];
const COMMENTARY = /(normal|impaired|diabet|pre-?diabet|reference|interpretation|desirable|\bada\b|criteria|recommend|guideline|method|hexokinase|god-?pod|enzymatic|specimen|comment|note:|range|units?\b\s*$|test\s*name|result\s*unit)/i;
const COLLECTION_LABELS: { re: RegExp; label: string; rank: number }[] = [
  { re: /(collect(?:ed|ion)\s*(?:on|date|at|time|date\s*[/&]\s*time)?|sample\s*(?:collection|taken|drawn|date)|specimen\s*collected|drawn\s*on)/i, label: 'Collected', rank: 1 },
  { re: /(registered\s*(?:on|date)?|registration\s*date|received\s*(?:on|date)?|booking\s*date|visit\s*date)/i, label: 'Registered', rank: 2 },
  { re: /(report(?:ed)?\s*(?:on|date|time)?|print(?:ed)?\s*(?:on|date)|verified\s*on|validated\s*on)/i, label: 'Reported', rank: 3 },
];

/** Numbers on a line that are results, not reference ranges, comparators, percentages or ids. */
export function resultNumbers(text: string): string[] {
  const out: string[] = [];
  const re = /(\d{1,4}(?:\.\d{1,2})?)/g; let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    const before = text.slice(0, m.index); const after = text.slice(m.index + m[0].length);
    if (/[-–~]\s*$/.test(before) && /\d\s*[-–~]\s*$/.test(before)) continue; // end of range "70 - 110"
    if (/^\s*[-–~]\s*\d/.test(after) || /^\s*to\s*\d/i.test(after)) continue; // start of range
    if (/[<>≤≥]\s*=?\s*$/.test(before) || /(upto|up to|less than|more than|above|below)\s*$/i.test(before)) continue;
    if (/^\s*%/.test(after) || /^\s*(?:hrs?|hours?|mins?|g\b|gm\b|years?|yrs?|y\b)/i.test(after)) continue;
    if (/[/:.]\s*$/.test(before) && /\d\s*[/:.]\s*$/.test(before)) continue; // part of a date/time
    if (/^\s*[/:]\s*\d/.test(after)) continue;
    if (/[A-Za-z]$/.test(before)) continue; // A1c, ID12
    out.push(m[1]);
  }
  return out;
}

function findCollection(lines: TextLine[]): LabParseResult['collected'] {
  let best: { rank: number; date: DateParts | null; time: TimeParts | null; label: string } | null = null;
  lines.forEach((line, i) => {
    for (const l of COLLECTION_LABELS) {
      const m = l.re.exec(line.text); if (!m) continue;
      const rest = line.text.slice(m.index + m[0].length);
      const nextText = lines[i + 1]?.text || '';
      const d = findDate(rest) || findDate(nextText);
      if (!d) continue;
      const source = findDate(rest) ? rest : nextText;
      const t = findTime(source.slice(d.index + d.length)) || findTime(source.slice(0, d.index));
      if (!best || l.rank < best.rank) best = { rank: l.rank, date: d.date, time: t?.time || null, label: l.label };
    }
  });
  if (best) { const b = best as { date: DateParts | null; time: TimeParts | null; label: string }; return { date: b.date, time: b.time, label: b.label }; }
  for (const line of lines) { const d = findDate(line.text); if (d) { const t = findTime(line.text.slice(d.index + d.length)); return { date: d.date, time: t?.time || null, label: null }; } }
  return { date: null, time: null, label: null };
}

const RANGE_CELL = /^\s*(?:[<>≤≥]|upto|up\s*to|less|more|below|above|normal|ref)|\d\s*[-–~]\s*\d|\d\s+to\s+\d/i;
type Columns = { result: number | null; range: [number, number] | null; unit: number | null; headerRow: number };
const mid = (c: TextCell) => (c.x0 + c.x1) / 2;
/** Table header ("Test | Result | Unit | Reference Range") → x-centre of each column. */
function findColumns(lines: TextLine[]): Columns | null {
  for (const [i, l] of lines.entries()) {
    if (!l.cells || l.cells.length < 2) continue;
    let result: number | null = null, unit: number | null = null, range: [number, number] | null = null; let hits = 0;
    for (const c of l.cells) {
      const t = c.text.toLowerCase();
      if (/\b(results?|observed\s*value|value|observation)\b/.test(t) && result === null) { result = mid(c); hits++; }
      else if (/\bunits?\b/.test(t) && unit === null) { unit = mid(c); hits++; }
      else if (/(range|reference|normal|interval|ref\.)/.test(t) && range === null) { range = [c.x0, c.x1]; hits++; }
      else if (/(test|investigation|parameter|examination)/.test(t)) hits++;
    }
    if (hits >= 2 && result !== null) return { result, unit, range, headerRow: i };
  }
  return null;
}
type CellPick = { value: string; unitText: GlucoseUnit | null; conf: number; raw: string };
/** Pair a test-name cell with the value (and unit) printed on the same row. */
function pickFromCells(line: TextLine, labelIdx: number, labelTail: string, cols: Columns | null): CellPick | null | 'skip' {
  const cells = line.cells!;
  if (cells[labelIdx].text.split(/\s+/).length > 7) return 'skip'; // a sentence (interpretation note), not a table row
  const options: { cell: TextCell; nums: string[]; idx: number }[] = [];
  const tailNums = resultNumbers(labelTail.replace(/\d+\s*[-–]\s*\d+.*$/, ''));
  if (tailNums.length && !RANGE_CELL.test(labelTail)) options.push({ cell: { ...cells[labelIdx], text: labelTail }, nums: tailNums, idx: labelIdx });
  for (let k = labelIdx + 1; k < cells.length; k++) {
    const c = cells[k]; const t = normalizeOcrLine(c.text);
    if (RANGE_CELL.test(t)) continue;
    if (cols?.range && mid(c) >= cols.range[0] - 4 && mid(c) <= cols.range[1] + 4 && (cols.result === null || Math.abs(mid(c) - cols.result) > Math.abs(mid(c) - (cols.range[0] + cols.range[1]) / 2))) continue;
    const nums = resultNumbers(t); if (nums.length) options.push({ cell: { ...c, text: t }, nums, idx: k });
  }
  if (!options.length) return null;
  let best = options[0];
  if (cols?.result != null) best = options.slice().sort((a, b) => Math.abs(mid(a.cell) - cols.result!) - Math.abs(mid(b.cell) - cols.result!))[0];
  const value = normalizeDecimal(best.nums[0]); if (!value) return null;
  let unitText: GlucoseUnit | null = unitFromText(best.cell.text);
  if (!unitText) {
    const after = cells.slice(best.idx + 1).map(c => normalizeOcrLine(c.text));
    const byCol = cols?.unit != null ? cells.slice(best.idx + 1).find(c => Math.abs(mid(c) - cols.unit!) < (c.x1 - c.x0) + 40) : undefined;
    unitText = (byCol && unitFromText(normalizeOcrLine(byCol.text))) || after.map(t => unitFromText(t)).find(Boolean) || null;
  }
  return { value, unitText, conf: best.cell.confidence, raw: cells.map(c => c.text).join(' | ') };
}

type Meta = { format: ImportFormat; method: 'file' | 'ocr'; fileName: string | null; fileSha256: string | null; batchId: string; engine: string | null; now?: Date };

export function parseReportText(input: TextLine[], meta: Meta): LabParseResult {
  const lines = input.map(l => ({ ...l, text: normalizeOcrLine(l.text) })).filter(l => l.text);
  const notes: string[] = []; const nonGlucose: NonGlucoseFinding[] = []; const found: { line: number; value: string; unitText: GlucoseUnit | null; context: MealContext; label: string; conf: number; raw: string; locator: string }[] = [];
  const collected = findCollection(lines);
  const cols = findColumns(lines);
  lines.forEach((line, i) => {
    const text = line.text;
    const ng = NON_GLUCOSE.find(n => n.re.test(text));
    if (ng) {
      const after = text.slice(text.search(ng.re));
      const nums = resultNumbers(after.replace(ng.re, ' '));
      const pct = /(\d{1,2}(?:\.\d{1,2})?)\s*%/.exec(after.replace(ng.re, ' '));
      const value = ng.kind === 'hba1c' ? (nums[0] || pct?.[1]) : nums[0]; // nums excludes a range end like "4.0 - 5.6 %"
      if (value && !COMMENTARY.test(text.replace(ng.re, ''))) nonGlucose.push({ kind: ng.kind, label: ng.label, value, unit: ng.kind === 'hba1c' ? (/mmol\s*\/\s*mol/i.test(after) ? 'mmol/mol' : '%') : unitFromText(after) || '', raw: text.slice(0, 200), locator: line.locator });
      return;
    }
    const test = TESTS.find(t => t.re.test(text));
    if (!test) return;
    const match = test.re.exec(text)!;
    const tail = text.slice(match.index + match[0].length);
    if (COMMENTARY.test(tail) && !resultNumbers(tail.replace(/\d+\s*[-–]\s*\d+.*$/, '')).length) return;
    if (/^\s*(test|investigation|parameter)/i.test(text)) return;
    // Section heading ("BLOOD GLUCOSE", "DIABETIC PROFILE") on its own row: not a result.
    if (line.cells && line.cells.length === 1 && !/\d/.test(text) && text === text.toUpperCase()) return;
    if (line.cells && line.cells.length) {
      const idx = line.cells.findIndex(c => test.re.test(normalizeOcrLine(c.text)));
      if (idx >= 0) {
        const lt = normalizeOcrLine(line.cells[idx].text); const lm = test.re.exec(lt)!;
        const pick = pickFromCells(line, idx, lt.slice(lm.index + lm[0].length), cols);
        if (pick === 'skip') return;
        if (pick) {
          const confBase = Math.max(0.2, Math.min(1, pick.conf)) * 0.97;
          found.push({ line: i, value: pick.value, unitText: pick.unitText, context: test.context, label: test.label, conf: test.context === 'unspecified' ? confBase - 0.05 : confBase, raw: pick.raw.slice(0, 200), locator: line.locator });
          return;
        }
      }
    }
    let nums = resultNumbers(tail); let raw = text; let unitLine = tail;
    if (!nums.length) {
      // Table layouts split by OCR: result on one of the next two lines.
      for (const next of lines.slice(i + 1, i + 3)) {
        if (TESTS.some(t => t.re.test(next.text)) || NON_GLUCOSE.some(n => n.re.test(next.text))) break;
        // With geometry, a next row that starts with its own name is a different test, not our result.
        if (next.cells?.length && /[A-Za-z]{2,}/.test(next.cells[0].text) && !resultNumbers(normalizeOcrLine(next.cells[0].text)).length) break;
        const n = resultNumbers(next.text); if (n.length && !COMMENTARY.test(next.text)) { nums = n; raw = `${text} / ${next.text}`; unitLine = next.text; break; }
      }
    }
    if (!nums.length) return;
    const value = normalizeDecimal(nums[0]); if (!value) return;
    const confBase = line.confidence == null ? 0.95 : Math.max(0.2, Math.min(1, line.confidence)) * 0.95;
    found.push({ line: i, value, unitText: unitFromText(unitLine) || unitFromText(text), context: test.context, label: test.label, conf: test.context === 'unspecified' ? confBase - 0.05 : confBase, raw: raw.slice(0, 200), locator: line.locator });
  });
  // Same test printed twice (summary + detail page) → keep the first.
  const unique = found.filter((f, i) => found.findIndex(g => g.value === f.value && g.context === f.context) === i);
  const reportUnits = unique.map(f => f.unitText).filter(Boolean) as GlucoseUnit[];
  const reportUnit: GlucoseUnit | null = reportUnits.length ? (reportUnits.filter(u => u === 'mmol/L').length > reportUnits.length / 2 ? 'mmol/L' : 'mg/dL') : null;
  let kind: LabParseResult['kind'] = unique.length || nonGlucose.length ? 'lab-report' : 'none';
  let parsed = unique.map(f => ({ ...f, reportUnit }));
  if (kind === 'none') {
    const meter = parseMeterScreen(lines, meta);
    if (meter) return { kind: 'meter-screen', candidates: [meter], nonGlucose, notes: ['Read as a meter screen photo. Check the value, unit, date and time against the meter.'], collected };
  }
  if (!collected.date && parsed.length) notes.push('No collection date was found on the report. Enter the date before confirming.');
  else if (collected.date && collected.label !== 'Collected' && parsed.length) notes.push(`Date taken from the "${collected.label || 'first date on the'}" ${collected.label ? 'field' : 'report'}; check it matches the sample collection time.`);
  if (nonGlucose.length) notes.push(`${nonGlucose.length} non-glucose lab value${nonGlucose.length === 1 ? '' : 's'} (${[...new Set(nonGlucose.map(n => n.label))].join(', ')}) shown separately and not imported as readings.`);
  const candidates: ImportCandidate[] = parsed.map((f, n) => {
    const flags: CandidateFlag[] = [];
    const u = resolveUnit(f.value, f.unitText, f.reportUnit ? { unit: f.reportUnit, source: 'report' } : null);
    flags.push(...u.flags, ...plausibilityFlags(f.value, u.unit));
    if (!collected.date) flags.push('missing-date'); if (!collected.time) flags.push('missing-time');
    const conf = Math.max(0, Math.min(1, f.conf * (u.source === 'explicit' ? 1 : u.source === 'report' ? 0.92 : 0.75) * (collected.date ? 1 : 0.8)));
    return {
      id: `${meta.batchId}-t${n + 1}`, value: f.value, unit: u.unit, unitSource: u.source,
      date: collected.date ? displayDate(collected.date) : '', time: collected.time ? displayTime(collected.time) : '', tzOffsetMinutes: null,
      mealContext: f.context, note: `Lab report · ${f.label}`, confidence: Math.round(conf * 100) / 100, flags,
      original: { value: f.value, unit: f.unitText },
      provenance: { method: meta.method, format: meta.format, provider: meta.method === 'ocr' ? `ocr:${meta.engine || 'unknown'}` : `file:${meta.format}`, recordId: `${(meta.fileSha256 || 'nohash').slice(0, 16)}:${f.locator.replace(/\s+/g, '')}`, device: null, fileName: meta.fileName, fileSha256: meta.fileSha256, locator: f.locator, raw: f.raw, engine: meta.engine },
      decision: 'pending', edited: false,
    };
  });
  if (!candidates.length && !nonGlucose.length) { kind = 'none'; notes.push('No glucose result was recognised in this text.'); }
  return { kind, candidates, nonGlucose, notes, collected };
}

/** Meter screen photo: one big number (+unit), optional "16-10 08:15" style date/time. */
export function parseMeterScreen(lines: TextLine[], meta: Meta): ImportCandidate | null {
  const text = lines.map(l => l.text).join('\n');
  const conf = lines.length ? lines.reduce((s, l) => s + (l.confidence ?? 0.7), 0) / lines.length : 0.5;
  const withUnit = /(?<![\d:./-])(\d{1,3}(?:\.\d)?)[ \t]*(mg\/dL|mmol\/L)/.exec(text);
  let value: string | null = null; let unit: GlucoseUnit | null = null;
  // Geometry first: on a meter the reading is by far the tallest number on the screen.
  const plausibleNum = (n: string) => (n.includes('.') && Number(n) >= 1.1 && Number(n) <= 33.3) || (!n.includes('.') && Number(n) >= 20 && Number(n) <= 600);
  const tall = lines.flatMap(l => l.cells || []).filter(c => c.h && /^\d{2,3}(?:\.\d)?$/.test(normalizeOcrLine(c.text).replace(/\s/g, '')) && plausibleNum(normalizeOcrLine(c.text).replace(/\s/g, '')))
    .sort((a, b) => (b.h || 0) - (a.h || 0));
  const allH = lines.flatMap(l => l.cells || []).map(c => c.h || 0).sort((a, b) => a - b); const medH = allH[Math.floor(allH.length / 2)] || 0;
  if (tall.length && (tall[0].h || 0) >= 1.6 * medH) { value = normalizeDecimal(normalizeOcrLine(tall[0].text).replace(/\s/g, '')); unit = unitFromText(text); }
  else if (withUnit) { value = normalizeDecimal(withUnit[1]); unit = unitFromText(withUnit[2]); }
  else {
    const nums = lines.flatMap(l => resultNumbers(l.text.replace(/\d{1,2}[:.]\d{2}(\s*[AP]M)?/gi, ' ').replace(/\d{1,4}[/-]\d{1,2}([/-]\d{2,4})?|\d{1,2}\.\d{1,2}\.\d{2,4}/g, ' ')));
    const plausible = nums.map(n => normalizeDecimal(n)).filter((n): n is string => !!n && ((n.includes('.') && Number(n) >= 1.1 && Number(n) <= 33.3) || (!n.includes('.') && Number(n) >= 20 && Number(n) <= 600)));
    value = plausible.sort((a, b) => b.length - a.length)[0] || null;
  }
  if (!value) return null;
  const flags: CandidateFlag[] = [];
  const now = meta.now ?? new Date();
  let date: DateParts | null = findDate(text)?.date || null;
  if (!date) {
    const dm = /(?:^|\s)(\d{1,2})[./-](\d{1,2})(?![./-]?\d)/.exec(text.replace(/\d{1,2}:\d{2}/g, ' '));
    if (dm) { const d = Number(dm[1]), m = Number(dm[2]); const probe = new Date(Date.UTC(now.getFullYear(), m - 1, d)); if (m >= 1 && m <= 12 && probe.getUTCDate() === d) { date = { year: now.getFullYear(), month: m - 1, day: d }; flags.push('year-assumed'); } }
  }
  const time = findTime(text)?.time || null;
  const u = resolveUnit(value, unit, null);
  flags.push(...u.flags, ...plausibilityFlags(value, u.unit));
  if (!date) flags.push('missing-date'); if (!time) flags.push('missing-time');
  // Capped below LOW_CONFIDENCE (0.6): meter photos read 5 of 9 right on the blind held-out set,
  // so every meter reading is flagged for a look against the meter before it can be saved.
  const confidence = Math.round(Math.max(0.1, Math.min(0.55, conf * 0.7 * (unit ? 1 : 0.8))) * 100) / 100;
  return {
    id: `${meta.batchId}-m1`, value, unit: u.unit, unitSource: u.source, date: date ? displayDate(date) : '', time: time ? displayTime(time) : '', tzOffsetMinutes: null,
    mealContext: 'unspecified', note: 'Meter screen photo', confidence, flags, original: { value, unit },
    provenance: { method: meta.method, format: meta.format, provider: meta.method === 'ocr' ? `ocr:${meta.engine || 'unknown'}` : `file:${meta.format}`, recordId: `${(meta.fileSha256 || 'nohash').slice(0, 16)}:meter`, device: null, fileName: meta.fileName, fileSha256: meta.fileSha256, locator: 'whole image', raw: text.slice(0, 200), engine: meta.engine },
    decision: 'pending', edited: false,
  };
}
