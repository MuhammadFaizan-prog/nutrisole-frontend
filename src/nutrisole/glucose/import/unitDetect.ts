// Unit detection and plausibility for imported values. A unit is never converted silently:
// when it is not written next to the value it is inferred and flagged for review.
import type { GlucoseUnit, MealContext } from '../types';
import { normalizeDecimal, toMgDl } from '../units';
import type { CandidateFlag, UnitSource } from './types';

/** Plausible strip-meter range for review flags (brief: outside 10–600 mg/dL is implausible). */
export const PLAUSIBLE_MG_DL: [number, number] = [10, 600];

export function unitFromText(text: string | null | undefined): GlucoseUnit | null {
  if (!text) return null;
  const t = text.toLowerCase().replace(/\s+/g, '');
  if (/mmol\/?l|mmol\b|mmo1\/?l/.test(t)) return 'mmol/L';
  if (/mg\/?d[l1i]|mg%|mgdl|mg\/dl/.test(t)) return 'mg/dL';
  return null;
}

/** Infer a unit from the number alone. Decimals ≤ 35 read as mmol/L; whole numbers ≥ 40 as mg/dL. */
export function inferUnit(value: string): { unit: GlucoseUnit; ambiguous: boolean; confidence: number } {
  const n = Number(value); const decimal = value.includes('.');
  if (decimal && n <= 35) return { unit: 'mmol/L', ambiguous: false, confidence: 0.75 };
  if (!decimal && n >= 40) return { unit: 'mg/dL', ambiguous: false, confidence: 0.75 };
  if (!decimal && n < 40) return { unit: 'mmol/L', ambiguous: true, confidence: 0.4 };
  return { unit: 'mg/dL', ambiguous: true, confidence: 0.4 };
}

/** Column-level unit from many values: mostly decimals under 35 → mmol/L. */
export function inferColumnUnit(values: string[]): GlucoseUnit | null {
  const nums = values.map(v => normalizeDecimal(v)).filter((v): v is string => v !== null);
  if (!nums.length) return null;
  const mmol = nums.filter(v => v.includes('.') && Number(v) <= 35).length;
  const mg = nums.filter(v => !v.includes('.') && Number(v) >= 40).length;
  if (mmol / nums.length >= 0.6) return 'mmol/L';
  if (mg / nums.length >= 0.6) return 'mg/dL';
  return null;
}

export function resolveUnit(value: string, explicit: GlucoseUnit | null, fallback: { unit: GlucoseUnit; source: UnitSource } | null): { unit: GlucoseUnit; source: UnitSource; flags: CandidateFlag[]; confidence: number } {
  if (explicit) return { unit: explicit, source: 'explicit', flags: [], confidence: 1 };
  if (fallback) return { unit: fallback.unit, source: fallback.source, flags: fallback.source === 'inferred' ? ['unit-inferred'] : [], confidence: fallback.source === 'inferred' ? 0.75 : 0.95 };
  const g = inferUnit(value);
  return { unit: g.unit, source: 'inferred', flags: g.ambiguous ? ['unit-inferred', 'unit-ambiguous'] : ['unit-inferred'], confidence: g.confidence };
}

/** mg/dL equivalent, or null when the value cannot be represented in that unit. */
export function mgDlOf(value: string, unit: GlucoseUnit): number | null {
  const v = normalizeDecimal(value); if (v === null) return null;
  try { return toMgDl(unit === 'mmol/L' ? (Math.round(Number(v) * 100) / 100).toString() : v, unit); } catch { return null; }
}

export function plausibilityFlags(value: string, unit: GlucoseUnit | null): CandidateFlag[] {
  if (!unit) return [];
  const mg = mgDlOf(value, unit);
  if (mg === null) return ['invalid'];
  return mg < PLAUSIBLE_MG_DL[0] || mg > PLAUSIBLE_MG_DL[1] ? ['implausible'] : [];
}

/** Meal/context words from meters, apps and lab reports → MealContext. */
export function contextFromText(text: string | null | undefined): MealContext {
  const t = (text || '').toLowerCase();
  if (!t.trim()) return 'unspecified';
  if (/\bfast(ing|ed)?\b|\bfbs\b|\bfpg\b|nüchtern|empty stomach/.test(t)) return 'fasting';
  if (/post|after|\bpp\b|ppbs|2\s*-?\s*h(ou)?r|postprandial|nach/.test(t)) return 'after_meal';
  if (/before|pre[-\s]?meal|pre[-\s]?prandial|\bac\b|vor dem/.test(t)) return 'before_meal';
  if (/bed|night|sleep/.test(t)) return 'bedtime';
  if (/random|\brbs\b|\brbg\b|casual/.test(t)) return 'random';
  return 'unspecified';
}
