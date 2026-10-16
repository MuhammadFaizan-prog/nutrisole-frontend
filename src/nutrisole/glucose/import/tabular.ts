// CSV/XLSX → review candidates. Auto-detects the header row, delimiter, date order and
// which column holds what; the user can override every column in the mapper.
import type { GlucoseUnit } from '../types';
import { normalizeDecimal } from '../units';
import type { CandidateFlag, ImportCandidate, ImportFormat, TabularMapping } from './types';
import { MAX_IMPORT_ROWS } from './types';
import { detectDateOrder, displayDate, displayTime, findDate, findTime } from './dates';
import { contextFromText, inferColumnUnit, plausibilityFlags, resolveUnit, unitFromText } from './unitDetect';

/** RFC 4180-style parser with delimiter sniffing (, ; tab |) and quoted fields. */
export function parseDelimited(text: string): string[][] {
  const clean = text.replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n');
  const sample = clean.split('\n').slice(0, 40).filter(l => l.trim());
  const delims = [',', ';', '\t', '|'];
  const score = (d: string) => { const counts = sample.map(l => l.split(d).length - 1).filter(c => c > 0); if (!counts.length) return 0; const mode = counts.sort((a, b) => counts.filter(x => x === b).length - counts.filter(x => x === a).length)[0]; return counts.filter(c => c === mode).length * Math.min(mode, 12); };
  const delim = delims.reduce((best, d) => score(d) > score(best) ? d : best, ',');
  const rows: string[][] = []; let row: string[] = []; let cell = ''; let quoted = false;
  for (let i = 0; i < clean.length; i++) {
    const ch = clean[i];
    if (quoted) { if (ch === '"') { if (clean[i + 1] === '"') { cell += '"'; i++; } else quoted = false; } else cell += ch; continue; }
    if (ch === '"' && cell.trim() === '') { quoted = true; cell = ''; continue; }
    if (ch === delim) { row.push(cell.trim()); cell = ''; continue; }
    if (ch === '\n') { row.push(cell.trim()); rows.push(row); row = []; cell = ''; continue; }
    cell += ch;
  }
  if (cell.length || row.length) { row.push(cell.trim()); rows.push(row); }
  return rows.filter(r => r.some(c => c !== ''));
}

const H = {
  exclude: /hba1c|a1c|target|carb|insulin|ketone|bolus|basal|unit|temp|serial|sensor|cgm|scan|strip|lot|id$|^id|weight|steps|blood pressure|systolic|diastolic|pulse|medication|food|kcal|duration/i,
  value: /(blood\s*(sugar|glucose)|^bg\b|\bbg\b|^bz\b|glucose|sugar|reading|result|messwert|value|level|wert)/i,
  datetime: /(date\s*[/&-]?\s*time|time\s*stamp|timestamp|datetime|date\s*and\s*time|recorded|measured\s*at|zeit\s*stempel)/i,
  date: /(^|\b)(date|day|datum)(\b|$)/i,
  time: /(^|\b)(time|uhrzeit|zeit)(\b|$)/i,
  unit: /unit|einheit/i,
  context: /(meal|context|tag|event|marker|flag|before|after|period|relation|mahlzeit)/i,
  note: /(note|comment|remark|notiz|description)/i,
};

const isNumericCell = (c: string) => normalizeDecimal(c) !== null;

/** Header row = first row (within 30) with ≥ 2 header-like cells followed by data rows. */
export function findHeaderRow(rows: string[][]): number {
  for (let i = 0; i < Math.min(rows.length - 1, 30); i++) {
    const r = rows[i]; const hits = r.filter(c => H.value.test(c) || H.date.test(c) || H.time.test(c) || H.datetime.test(c)).length;
    const numericCells = r.filter(isNumericCell).length;
    if (hits >= 2 && numericCells === 0 && rows.slice(i + 1, i + 6).some(next => next.some(isNumericCell))) return i;
  }
  return 0;
}

export function autoMap(rows: string[][]): TabularMapping {
  const headerRow = findHeaderRow(rows);
  const header = rows[headerRow] || [];
  const data = rows.slice(headerRow + 1, headerRow + 60);
  const reasons: string[] = [];
  const pick = (re: RegExp, taken: (number | null)[], guard: (h: string, i: number) => boolean = () => true) => {
    const i = header.findIndex((h, idx) => re.test(h) && !taken.includes(idx) && guard(h, idx));
    return i >= 0 ? i : null;
  };
  const datetime = pick(H.datetime, []);
  const date = datetime === null ? pick(H.date, []) : null;
  const time = datetime === null ? pick(H.time, [date]) : null;
  const numericShare = (i: number) => data.filter(r => isNumericCell(r[i] || '')).length / Math.max(1, data.filter(r => (r[i] || '') !== '').length);
  let value = pick(H.value, [datetime, date, time], h => !H.exclude.test(h.replace(/\((mg\/dl|mmol\/l)\)|\[(mg\/dl|mmol\/l)\]/i, '')) || /blood\s*(sugar|glucose)|glucose/i.test(h));
  if (value !== null && /blood\s*(sugar|glucose)|glucose|\bbg\b/i.test(header[value]) === false) {
    // Prefer an explicit glucose column over a generic "value"/"result" one when both exist.
    const better = pick(/blood\s*(sugar|glucose)|glucose|\bbg\b/i, [datetime, date, time], h => !/hba1c|a1c|target|cgm|sensor/i.test(h));
    if (better !== null) value = better;
  }
  if (value === null) {
    const numericCols = header.map((_, i) => i).filter(i => ![datetime, date, time].includes(i) && numericShare(i) > 0.6 && !H.exclude.test(header[i] || ''));
    value = numericCols[0] ?? null; if (value !== null) reasons.push(`Value: "${header[value] || `column ${value + 1}`}" is the first mostly-numeric column (guessed).`);
  } else reasons.push(`Value: "${header[value]}" matches a glucose column name.`);
  const unit = pick(H.unit, [datetime, date, time, value]);
  const context = pick(H.context, [datetime, date, time, value, unit], h => !H.exclude.test(h) || /meal/i.test(h));
  const note = pick(H.note, [datetime, date, time, value, unit, context]);
  const columnUnit = value !== null ? unitFromText(header[value]) : null;
  if (datetime !== null) reasons.push(`Date & time: "${header[datetime]}".`);
  if (date !== null) reasons.push(`Date: "${header[date]}".`);
  if (time !== null) reasons.push(`Time: "${header[time]}".`);
  if (columnUnit) reasons.push(`Unit: ${columnUnit} from the "${header[value!]}" header.`);
  else if (unit !== null) reasons.push(`Unit: per-row from "${header[unit]}".`);
  const dateCol = datetime ?? date;
  const dateOrder = dateCol !== null ? detectDateOrder(data.map(r => r[dateCol] || '')) : 'DMY';
  return { header, headerRow, datetime, date, time, value, unit, context, note, columnUnit, dateOrder, auto: true, reasons };
}

export function rowsToCandidates(rows: string[][], mapping: TabularMapping, meta: { format: ImportFormat; fileName: string | null; fileSha256: string | null; batchId: string }): { candidates: ImportCandidate[]; skipped: number; notes: string[] } {
  const notes: string[] = []; const candidates: ImportCandidate[] = []; let skipped = 0;
  if (mapping.value === null) return { candidates, skipped: rows.length, notes: ['No glucose value column found. Choose the value column in the column mapper.'] };
  const data = rows.slice(mapping.headerRow + 1);
  if (data.length > MAX_IMPORT_ROWS) notes.push(`Only the first ${MAX_IMPORT_ROWS} rows are read.`);
  const valueCol = mapping.value;
  const columnUnit = mapping.columnUnit ?? (mapping.unit === null ? inferColumnUnit(data.map(r => r[valueCol] || '')) : null);
  const columnUnitSource = mapping.columnUnit ? 'column' as const : 'inferred' as const;
  data.slice(0, MAX_IMPORT_ROWS).forEach((r, i) => {
    const rowNo = mapping.headerRow + i + 2; // 1-based file row
    const rawValue = (r[valueCol] || '').trim();
    const value = normalizeDecimal(rawValue.replace(/\s*(mg\/?dl|mmol\/?l)\s*$/i, ''));
    if (!rawValue) { skipped++; return; } // other log entries (insulin, food) in the same export
    const flags: CandidateFlag[] = [];
    const rowUnit = mapping.unit !== null ? unitFromText(r[mapping.unit]) : unitFromText(rawValue);
    if (value === null) { skipped++; return; }
    const u = resolveUnit(value, rowUnit, columnUnit ? { unit: columnUnit, source: columnUnitSource } : null);
    flags.push(...u.flags, ...plausibilityFlags(value, u.unit));
    const dtText = mapping.datetime !== null ? r[mapping.datetime] || '' : `${mapping.date !== null ? r[mapping.date] || '' : ''} ${mapping.time !== null ? r[mapping.time] || '' : ''}`;
    const d = findDate(dtText, mapping.dateOrder);
    const timeText = mapping.datetime !== null ? (d ? dtText.slice(0, d.index) + ' ' + dtText.slice(d.index + d.length) : dtText) : (mapping.time !== null ? r[mapping.time] || '' : '');
    const t = findTime(timeText);
    if (!d) flags.push('missing-date'); if (!t) flags.push('missing-time');
    const contextText = mapping.context !== null ? r[mapping.context] || '' : '';
    if (/control/i.test(contextText) || r.some((c, idx) => idx !== valueCol && /^control( test| solution)?$|^(yes|x|1)$/i.test(c) && /control/i.test(mapping.header[idx] || c))) flags.push('control-solution');
    const mealContext = contextFromText(contextText);
    const noteParts = [mapping.note !== null ? r[mapping.note] || '' : '', mealContext === 'unspecified' && contextText ? contextText : ''].filter(Boolean);
    const confidence = Math.min(u.confidence, d && t ? 1 : 0.7) * (mapping.auto ? 1 : 1);
    candidates.push({
      id: `${meta.batchId}-r${rowNo}`, value, unit: u.unit, unitSource: u.source,
      date: d ? displayDate(d.date) : '', time: t ? displayTime(t.time) : '', tzOffsetMinutes: null,
      mealContext, note: noteParts.join(' · ').slice(0, 500), confidence, flags,
      original: { value: rawValue, unit: rowUnit ?? mapping.columnUnit ?? null },
      provenance: { method: 'file', format: meta.format, provider: `file:${meta.format}`, recordId: `${(meta.fileSha256 || 'nohash').slice(0, 16)}:row${rowNo}`, device: null, fileName: meta.fileName, fileSha256: meta.fileSha256, locator: `row ${rowNo}`, raw: r.join(' | ').slice(0, 200), engine: null },
      decision: 'pending', edited: false,
    });
  });
  if (skipped) notes.push(`${skipped} row${skipped === 1 ? '' : 's'} had no glucose value (other log entries) and ${skipped === 1 ? 'was' : 'were'} skipped.`);
  return { candidates, skipped, notes };
}

/** Manual mapper: set one role to a column index (or null). Clears the auto flag. */
export function remap(mapping: TabularMapping, role: 'datetime' | 'date' | 'time' | 'value' | 'unit' | 'context' | 'note', column: number | null): TabularMapping {
  const next: TabularMapping = { ...mapping, [role]: column, auto: false };
  if (role === 'datetime' && column !== null) { next.date = null; next.time = null; }
  if ((role === 'date' || role === 'time') && column !== null) next.datetime = null;
  if (role === 'value') next.columnUnit = column !== null ? unitFromText(mapping.header[column]) : null;
  return next;
}
export function setColumnUnit(mapping: TabularMapping, unit: GlucoseUnit | null): TabularMapping { return { ...mapping, columnUnit: unit, auto: false }; }
export function setDateOrder(mapping: TabularMapping, order: TabularMapping['dateOrder']): TabularMapping { return { ...mapping, dateOrder: order, auto: false }; }
