import type { GlucoseDraft, GlucoseInput, GlucoseReading, GlucoseSource, GlucoseValidation, GlucoseWarning, MealContext } from './types';
import { mealContexts } from './types';
import { decimalPlaces, hardRange, maxDecimals, normalizeDecimal, toMgDl, typicalMeterRange } from './units';
import { deviceOffsetMinutes, deviceTimeZoneName, parseDisplayDate, parseDisplayTime, wallClockToInstant } from './time';

export const NOTE_MAX = 500;
/** Readings dated further than this into the future are rejected (meter clock drift allowance). */
export const FUTURE_TOLERANCE_MS = 5 * 60_000;
const manualSource: GlucoseSource = { type: 'manual', provider: null, device: null, recordId: null };

export function contextLabel(value: MealContext) { return mealContexts.find(c => c.value === value)?.label || 'Not specified'; }
export function contextFromLabel(label: string): MealContext { return mealContexts.find(c => c.label === label)?.value || 'unspecified'; }

/**
 * The single validation boundary for manual entry (and, later, adapters).
 * Never converts a value into another unit silently: a likely unit mix-up is either a
 * hard error (impossible in the chosen unit) or a warning the user must confirm.
 */
export function validateGlucoseInput(input: GlucoseInput, options: { now?: Date; existing?: GlucoseReading[]; editingId?: string | null; source?: GlucoseSource } = {}): GlucoseValidation {
  const now = options.now ?? new Date();
  if (input.unit !== 'mg/dL' && input.unit !== 'mmol/L') return { ok: false, field: 'unit', error: 'Choose mg/dL or mmol/L, exactly as your meter shows.' };
  const value = normalizeDecimal(input.value || '');
  if (value === null || Number(value) <= 0) return { ok: false, field: 'value', error: 'Enter a positive numeric meter reading, such as 110 or 6.1.' };
  if (decimalPlaces(value) > maxDecimals[input.unit]) return { ok: false, field: 'value', error: input.unit === 'mg/dL' ? 'mg/dL readings use whole numbers (at most 1 decimal). Check the unit on your meter.' : 'mmol/L readings use at most 2 decimals.' };
  const numeric = Number(value);
  const [min, max] = hardRange[input.unit];
  if (numeric < min || numeric > max) {
    const hint = input.unit === 'mmol/L' && numeric > max ? ' If your meter shows mg/dL, switch the unit to mg/dL.' : input.unit === 'mg/dL' && numeric < min ? ' If your meter shows mmol/L, switch the unit to mmol/L.' : '';
    return { ok: false, field: 'value', error: `This value is outside the possible entry range for ${input.unit} (${min}–${max}).${hint}` };
  }
  const date = parseDisplayDate(input.date || '');
  if (!date) return { ok: false, field: 'date', error: 'Enter a valid measurement date, such as Oct 16, 2026.' };
  const time = parseDisplayTime(input.time || '');
  if (!time) return { ok: false, field: 'time', error: 'Enter a valid time, such as 8:15 AM.' };
  const clock = { ...date, ...time };
  const offset = input.tzOffsetMinutes ?? deviceOffsetMinutes(clock);
  if (!Number.isInteger(offset) || offset < -840 || offset > 840) return { ok: false, field: 'time', error: 'The time zone offset is not valid.' };
  const measuredAt = wallClockToInstant(clock, offset);
  if (Date.parse(measuredAt) > now.getTime() + FUTURE_TOLERANCE_MS) return { ok: false, field: 'date', error: 'The measurement time is in the future. Check the date and time on your meter.' };
  if (!mealContexts.some(c => c.value === input.mealContext) && input.mealContext !== 'unspecified') return { ok: false, field: 'context', error: 'Choose a measurement context.' };
  const note = (input.note || '').trim();
  if (note.length > NOTE_MAX) return { ok: false, field: 'note', error: `Notes can be up to ${NOTE_MAX} characters.` };

  const draft: GlucoseDraft = {
    measuredAt, tzOffsetMinutes: offset, tzName: input.tzName === undefined ? deviceTimeZoneName() : input.tzName,
    valueOriginal: value, unitOriginal: input.unit, valueMgDl: toMgDl(value, input.unit),
    mealContext: input.mealContext, note: note || null, source: options.source ?? manualSource,
  };
  const warnings: GlucoseWarning[] = [];
  const [typicalMin, typicalMax] = typicalMeterRange[input.unit];
  if (input.unit === 'mmol/L' && numeric > typicalMax) warnings.push({ code: 'possible-unit-mismatch', message: `${value} mmol/L is above what most strip meters display. If your meter shows mg/dL, change the unit before saving.` });
  else if (input.unit === 'mg/dL' && numeric < typicalMin) warnings.push({ code: 'possible-unit-mismatch', message: `${value} mg/dL is below what most strip meters display. If your meter shows mmol/L, change the unit before saving.` });
  else if (numeric < typicalMin) warnings.push({ code: 'unusual-low', message: `This value is below the range most strip meters display (${typicalMin}–${typicalMax} ${input.unit}). Check the meter display and unit.` });
  else if (numeric > typicalMax) warnings.push({ code: 'unusual-high', message: `This value is above the range most strip meters display (${typicalMin}–${typicalMax} ${input.unit}). Check the meter display and unit.` });
  const duplicate = (options.existing || []).find(r => r.id !== options.editingId && r.source.type === 'manual' && r.measuredAt === draft.measuredAt && r.valueMgDl === draft.valueMgDl);
  if (duplicate) warnings.push({ code: 'possible-duplicate', message: 'A manual reading with the same value and time is already in your history. Save again only if you measured twice.' });
  return { ok: true, draft, warnings };
}

/** Edit preserves the unit and value the reading was entered with. */
export function inputFromReading(reading: GlucoseReading, format: { date: string; time: string }): GlucoseInput {
  return { value: reading.valueOriginal, unit: reading.unitOriginal, date: format.date, time: format.time, tzOffsetMinutes: reading.tzOffsetMinutes, tzName: reading.tzName, mealContext: reading.mealContext, note: reading.note || '' };
}
