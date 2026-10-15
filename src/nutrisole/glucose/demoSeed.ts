// Sample fixtures for the explicit demo flag `?glucoseDemo=seed` only (screenshots/QA).
// They are synthetic, labelled "Sample" in the UI and never written to a database.
import type { GlucoseReading } from './types';
import { toMgDl } from './units';

export function demoSeed(now = new Date()): GlucoseReading[] {
  const offset = -now.getTimezoneOffset();
  const samples: [number, number, string, 'mg/dL' | 'mmol/L', GlucoseReading['mealContext']][] = [
    [6, 8, '96', 'mg/dL', 'fasting'], [5, 14, '7.4', 'mmol/L', 'after_meal'], [4, 8, '102', 'mg/dL', 'fasting'],
    [3, 21, '118', 'mg/dL', 'bedtime'], [2, 13, '141', 'mg/dL', 'after_meal'], [1, 8, '5.6', 'mmol/L', 'fasting'],
  ];
  return samples.map(([daysAgo, hour, value, unit, context], i) => {
    const local = new Date(now.getFullYear(), now.getMonth(), now.getDate() - daysAgo, hour, 15);
    const iso = local.toISOString();
    return { id: `sample-${i + 1}`, userId: 'demo-session', measuredAt: iso, tzOffsetMinutes: offset, tzName: null, valueOriginal: value, unitOriginal: unit, valueMgDl: toMgDl(value, unit), mealContext: context, note: 'Sample reading (demo flag)', source: { type: 'manual', provider: null, device: null, recordId: null }, createdAt: iso, updatedAt: iso };
  });
}
