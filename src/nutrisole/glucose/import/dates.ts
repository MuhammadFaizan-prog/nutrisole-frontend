// Tolerant date/time parsing for imported files and OCR text. Output is the wall clock the
// source shows; the review screen renders it in the manual-entry formats.
import { formatDisplayDate, formatDisplayTime } from '../time';

export type DateOrder = 'DMY' | 'MDY' | 'YMD';
export type DateParts = { year: number; month: number; day: number };
export type TimeParts = { hour: number; minute: number };

const monthNames = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
const monthIndex = (name: string) => monthNames.indexOf(name.slice(0, 3).toLowerCase());

function valid(year: number, month: number, day: number): DateParts | null {
  if (year < 100) year += 2000;
  if (year < 2000 || year > 2100 || month < 0 || month > 11 || day < 1 || day > 31) return null;
  const probe = new Date(Date.UTC(year, month, day));
  return probe.getUTCMonth() === month && probe.getUTCDate() === day ? { year, month, day } : null;
}

const numericDate = /(\d{1,4})[./\-](\d{1,2})[./\-](\d{2,4})/;
const textDate1 = /(\d{1,2})[\s\-./]*([A-Za-z]{3,9})[\s\-./,]*(\d{2,4})/; // 16-Oct-2026, 16 October 2026
const textDate2 = /([A-Za-z]{3,9})[\s\-./]*(\d{1,2}),?[\s\-./]*(\d{4})/; // Oct 16, 2026

/** Finds the first date in free text. `order` resolves 03/04/2026 (default DMY, the Pakistani convention). */
export function findDate(text: string, order: DateOrder = 'DMY'): { date: DateParts; index: number; length: number } | null {
  const candidates: { date: DateParts | null; index: number; length: number }[] = [];
  const n = numericDate.exec(text);
  if (n) {
    const [a, b, c] = [n[1], n[2], n[3]].map(Number);
    let d: DateParts | null = null;
    if (n[1].length === 4) d = valid(a, b - 1, c);
    else if (order === 'MDY' && a <= 12) d = valid(c, a - 1, b) || valid(c, b - 1, a);
    else d = a > 12 ? valid(c, b - 1, a) : b > 12 ? valid(c, a - 1, b) : valid(c, b - 1, a);
    candidates.push({ date: d, index: n.index, length: n[0].length });
  }
  const t1 = textDate1.exec(text);
  if (t1 && monthIndex(t1[2]) >= 0) candidates.push({ date: valid(Number(t1[3]), monthIndex(t1[2]), Number(t1[1])), index: t1.index, length: t1[0].length });
  const t2 = textDate2.exec(text);
  if (t2 && monthIndex(t2[1]) >= 0) candidates.push({ date: valid(Number(t2[3]), monthIndex(t2[1]), Number(t2[2])), index: t2.index, length: t2[0].length });
  const best = candidates.filter(c => c.date).sort((x, y) => x.index - y.index)[0];
  return best ? { date: best.date!, index: best.index, length: best.length } : null;
}

const timeRe = /(?:^|[^\d:])([01]?\d|2[0-3])[:.]([0-5]\d)(?::[0-5]\d(?:\.\d+)?)?\s*([AaPp]\.?\s?[Mm]\.?)?(?![\d])/;
export function findTime(text: string): { time: TimeParts; index: number } | null {
  const m = timeRe.exec(text);
  if (!m) return null;
  let hour = Number(m[1]); const minute = Number(m[2]);
  const ampm = m[3]?.replace(/[\s.]/g, '').toUpperCase();
  if (ampm) { if (hour < 1 || hour > 12) return null; hour = (hour % 12) + (ampm === 'PM' ? 12 : 0); }
  return { time: { hour, minute }, index: m.index };
}

/** Decide DMY vs MDY for a whole column: any first part > 12 means DMY; any second part > 12 means MDY. */
export function detectDateOrder(samples: string[]): DateOrder {
  let dmy = 0, mdy = 0, ymd = 0;
  for (const s of samples) {
    const m = numericDate.exec(s); if (!m) continue;
    if (m[1].length === 4) { ymd++; continue; }
    if (Number(m[1]) > 12) dmy++; else if (Number(m[2]) > 12) mdy++;
  }
  return ymd && !dmy && !mdy ? 'YMD' : mdy > dmy ? 'MDY' : 'DMY';
}

/** Excel serial day number (1900 system) → wall clock. */
export function excelSerialToParts(serial: number): DateParts & TimeParts {
  const ms = Math.round((serial - 25569) * 86_400_000);
  const d = new Date(ms);
  const minute = Math.round((d.getUTCSeconds() + d.getUTCMinutes() * 60) / 60);
  return { year: d.getUTCFullYear(), month: d.getUTCMonth(), day: d.getUTCDate(), hour: d.getUTCHours() + (minute === 60 ? 1 : 0), minute: minute % 60 };
}

export const displayDate = (d: DateParts) => formatDisplayDate(d);
export const displayTime = (t: TimeParts) => formatDisplayTime(t);
