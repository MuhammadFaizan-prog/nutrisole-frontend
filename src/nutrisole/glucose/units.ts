import type { GlucoseUnit } from './types';

/** mg/dL per mmol/L for glucose (molar mass 180.16 g/mol ÷ 10). */
export const MG_DL_PER_MMOL_L = 18.0182;
const FACTOR_MILLIONTHS = 18_018_200; // 18.0182 × 10^6, exact integer

/** Allowed decimal places per unit for entered values (meters display ≤1). */
export const maxDecimals: Record<GlucoseUnit, number> = { 'mg/dL': 1, 'mmol/L': 2 };
/** Hard entry limits: outside these a value cannot be a valid meter reading in that unit. */
export const hardRange: Record<GlucoseUnit, [number, number]> = { 'mg/dL': [10, 1000], 'mmol/L': [0.6, 55.5] };
/** Typical strip-meter display range; values outside need explicit confirmation (not a clinical judgement). */
export const typicalMeterRange: Record<GlucoseUnit, [number, number]> = { 'mg/dL': [20, 600], 'mmol/L': [1.1, 33.3] };

/**
 * Normalize a typed decimal ("5,6", " 110 ", "5.60") into a canonical decimal string.
 * Returns null for anything that is not a plain positive decimal (signs, exponents,
 * thousands separators, multiple separators, NaN/Infinity, empty).
 */
export function normalizeDecimal(raw: string): string | null {
  const text = raw.trim().replace(',', '.');
  if (!/^\d{1,5}(\.\d{1,4})?$/.test(text)) return null;
  const [int, frac = ''] = text.split('.');
  const intPart = int.replace(/^0+(?=\d)/, '');
  const fracPart = frac.replace(/0+$/, '');
  return fracPart ? `${intPart}.${fracPart}` : intPart;
}

export function decimalPlaces(value: string) { const i = value.indexOf('.'); return i < 0 ? 0 : value.length - i - 1; }

/** Exact scaled integer of a canonical decimal string (e.g. "5.6", 2 → 560). */
function scaled(value: string, places: number): number {
  const [int, frac = ''] = value.split('.');
  return Number(int) * 10 ** places + Number((frac + '0'.repeat(places)).slice(0, places) || '0');
}

/**
 * Canonical mg/dL for an entered value, rounded half-up to 2 decimals using integer
 * arithmetic. Matches the database generated column
 * `round(value_original * 18.0182, 2)` for every value with ≤2 decimals.
 * mg/dL inputs are returned unchanged, so a stored value is never converted twice.
 */
export function toMgDl(value: string, unit: GlucoseUnit): number {
  const canonical = normalizeDecimal(value);
  if (canonical === null) throw new RangeError('Glucose value must be a positive decimal.');
  if (unit === 'mg/dL') return Number(canonical);
  if (decimalPlaces(canonical) > 2) throw new RangeError('mmol/L values support at most 2 decimals.');
  const hundredths = scaled(canonical, 2); // value × 100
  // value × 18.0182 × 100 = hundredths × 18018200 / 10^6 ; round half up
  const product = hundredths * FACTOR_MILLIONTHS; // < 2^53 for every allowed value
  const roundedHundredths = Math.floor((product + 500_000) / 1_000_000);
  return roundedHundredths / 100;
}

/** Display a canonical mg/dL value in a unit. mmol/L shows 1 decimal, mg/dL whole numbers. */
export function fromMgDl(mgDl: number, unit: GlucoseUnit): number {
  if (!Number.isFinite(mgDl) || mgDl <= 0) throw new RangeError('Canonical value must be positive.');
  if (unit === 'mg/dL') return Math.round(mgDl);
  return Math.round((mgDl / MG_DL_PER_MMOL_L) * 10) / 10;
}

/**
 * The number to show for a reading in the requested unit. When the requested unit is
 * the unit the reading was entered in, the original text is shown exactly (no round trip).
 */
export function displayValue(reading: { valueOriginal: string; unitOriginal: GlucoseUnit; valueMgDl: number }, unit: GlucoseUnit): string {
  if (unit === reading.unitOriginal) return reading.valueOriginal;
  const v = fromMgDl(reading.valueMgDl, unit);
  return unit === 'mmol/L' ? v.toFixed(1) : String(v);
}

export function formatWithUnit(value: string, unit: GlucoseUnit) { return `${value} ${unit}`; }
