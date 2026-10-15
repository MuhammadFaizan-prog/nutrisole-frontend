// Pure helpers for history filters and the trend chart. Charts plot the canonical
// mg/dL value converted only for display; nothing is labelled high/low clinically.
import type { GlucoseReading, GlucoseUnit } from './types';
import { displayValue, fromMgDl } from './units';
import { formatDisplayDate, formatDisplayTime, instantToWallClock } from './time';

export type GlucoseRange = '7d' | '30d' | '90d' | 'all';
export const rangeLabels: Record<GlucoseRange, string> = { '7d': 'Last 7 days', '30d': 'Last 30 days', '90d': 'Last 90 days', all: 'All readings' };
export function rangeFromLabel(label: string): GlucoseRange { return (Object.keys(rangeLabels) as GlucoseRange[]).find(k => rangeLabels[k] === label) || '7d'; }

export function filterReadings(readings: GlucoseReading[], range: GlucoseRange, now = new Date()): GlucoseReading[] {
  if (range === 'all') return readings;
  const days = range === '7d' ? 7 : range === '30d' ? 30 : 90;
  const from = now.getTime() - days * 86_400_000;
  return readings.filter(r => Date.parse(r.measuredAt) >= from && Date.parse(r.measuredAt) <= now.getTime() + 5 * 60_000);
}

export function readingWhen(r: GlucoseReading) {
  const c = instantToWallClock(r.measuredAt, r.tzOffsetMinutes);
  return { date: formatDisplayDate(c), time: formatDisplayTime(c), short: `${['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][c.month]} ${c.day}` };
}

export type ChartBar = { id: string; value: string; heightRatio: number; label: string };
export type ChartModel = { bars: ChartBar[]; min: string; max: string; latest: string; count: number; first: string; last: string; unit: GlucoseUnit; summary: string };

/** Up to `maxBars` most recent readings, oldest→newest, scaled between 0.15 and 1 of the plot height. */
export function chartModel(readings: GlucoseReading[], unit: GlucoseUnit, maxBars = 12): ChartModel | null {
  if (!readings.length) return null;
  const shown = readings.slice(-maxBars);
  const values = readings.map(r => r.valueMgDl);
  const lo = Math.min(...shown.map(r => r.valueMgDl)); const hi = Math.max(...shown.map(r => r.valueMgDl));
  const fmt = (mg: number) => unit === 'mmol/L' ? fromMgDl(mg, unit).toFixed(1) : String(fromMgDl(mg, unit));
  const bars = shown.map(r => ({ id: r.id, value: displayValue(r, unit), heightRatio: hi === lo ? .6 : .15 + .85 * (r.valueMgDl - lo) / (hi - lo), label: readingWhen(r).short }));
  const latest = readings[readings.length - 1];
  const min = fmt(Math.min(...values)); const max = fmt(Math.max(...values));
  const latestText = displayValue(latest, unit);
  return { bars, min, max, latest: latestText, count: readings.length, first: readingWhen(readings[0]).short, last: readingWhen(latest).short, unit, summary: `${readings.length} reading${readings.length === 1 ? '' : 's'} · lowest ${min}, highest ${max} ${unit} · latest ${latestText} ${unit}` };
}
