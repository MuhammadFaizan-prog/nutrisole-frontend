// G9 Stage J4: typed nutrition contract for the five showcase classes (additive; not wired to any screen).
// Values come only from nutritionFdc.ts, which is GENERATED from the official USDA FoodData Central SR Legacy release
// (see FDC_SOURCE). Anything not in that release is 'missing' with a reason; nothing is estimated or typed in by hand.
// Glycemic index / glycemic load are NOT in FoodData Central: they stay missing until a cited source is added.
import { FDC_SHOWCASE, FDC_SOURCE, NUTRIENT_UNITS, FDC_NUTRIENT_IDS } from './nutritionFdc.ts';
import { domainIdForCvClass } from '../domainMap.ts';

export type ShowcaseClass = 'apple' | 'banana' | 'citrus_orange' | 'tomato' | 'carrot';
export const SHOWCASE: readonly ShowcaseClass[] = ['apple', 'banana', 'citrus_orange', 'tomato', 'carrot'];
export type NutrientKey = keyof typeof NUTRIENT_UNITS;
export type NutrientValue =
  | { status: 'sourced'; value: number; unit: string; fdcNutrientId: number }
  | { status: 'missing'; reason: string };
export type NutritionSource = { name: string; dataset: string; fdcId: number; foodUrl: string; datasetUrl: string; datasetSha256: string; publicationDate: string };
export type NutritionRecord = {
  produceType: ShowcaseClass; description: string; basis: 'per 100 g raw edible portion'; matchNote: string;
  source: NutritionSource;
  nutrients: Record<NutrientKey, NutrientValue>;
  glycemicIndex: NutrientValue;
  typicalPortion: { label: string; grams: number; source: 'USDA FoodData Central food_portion' } | null;
};

export const fdcFoodUrl = (fdcId: number) => `https://fdc.nal.usda.gov/food-details/${fdcId}/nutrients`;
const GI_MISSING: NutrientValue = { status: 'missing', reason: 'glycemic index is not published in USDA FoodData Central; no cited source added yet' };

export function nutritionFor(produceType: string): NutritionRecord | null {
  const r = (FDC_SHOWCASE as Record<string, (typeof FDC_SHOWCASE)[ShowcaseClass]>)[produceType];
  if (!r) return null;
  const nutrients = {} as Record<NutrientKey, NutrientValue>;
  for (const k of Object.keys(NUTRIENT_UNITS) as NutrientKey[]) {
    const v = (r.nutrients as Record<string, number | null>)[k];
    nutrients[k] = typeof v === 'number' && Number.isFinite(v)
      ? { status: 'sourced', value: v, unit: NUTRIENT_UNITS[k], fdcNutrientId: FDC_NUTRIENT_IDS[k] }
      : { status: 'missing', reason: 'not present in the FDC SR Legacy record' };
  }
  return {
    produceType: produceType as ShowcaseClass, description: r.description, basis: 'per 100 g raw edible portion', matchNote: r.matchNote,
    source: { name: FDC_SOURCE.name, dataset: FDC_SOURCE.dataset, fdcId: r.fdcId, foodUrl: fdcFoodUrl(r.fdcId), datasetUrl: FDC_SOURCE.datasetUrl,
      datasetSha256: FDC_SOURCE.datasetSha256, publicationDate: r.publicationDate },
    nutrients, glycemicIndex: GI_MISSING,
    typicalPortion: r.portion ? { label: r.portion.label, grams: r.portion.grams, source: 'USDA FoodData Central food_portion' } : null,
  };
}

/** J6: nutrition for a CV recognition output (CV class string, e.g. `citrus` -> citrus_orange record). Goes through domainMap.ts only;
 *  a class with no domain id (lemon_lime, mango, H2 unknown, ...) returns null. Per 100 g; portion grams come from the user, never the image. */
export function nutritionForCv(cvClass: string | null): NutritionRecord | null {
  const d = domainIdForCvClass(cvClass);
  return d ? nutritionFor(d) : null;
}

/** Scale sourced per-100 g values to a portion in grams. Missing stays missing (never zero). Rounded to 0.1. */
export function forPortion(rec: NutritionRecord, grams: number): Record<NutrientKey, NutrientValue> {
  if (!(grams > 0)) throw new Error('grams must be positive');
  const out = {} as Record<NutrientKey, NutrientValue>;
  for (const [k, v] of Object.entries(rec.nutrients) as [NutrientKey, NutrientValue][]) {
    out[k] = v.status === 'sourced' ? { ...v, value: Math.round(v.value * grams / 10) / 10 } : v;
  }
  return out;
}

/** Contract check: every sourced value has an FDC id + URL; nothing unsourced is presented as a number. Empty list = valid. */
export function checkNutrition(rec: NutritionRecord): string[] {
  const e: string[] = [];
  if (!SHOWCASE.includes(rec.produceType)) e.push('not a showcase class');
  if (!(rec.source.fdcId > 0) || !rec.source.foodUrl.endsWith(`/${rec.source.fdcId}/nutrients`)) e.push('FDC id / URL required');
  if (!/^[0-9a-f]{64}$/.test(rec.source.datasetSha256)) e.push('dataset sha256 required');
  for (const [k, v] of Object.entries(rec.nutrients)) {
    if (v.status === 'sourced' && !(Number.isFinite(v.value) && v.value >= 0)) e.push(`${k}: invalid value`);
    if (v.status === 'missing' && !v.reason) e.push(`${k}: missing needs a reason`);
  }
  if (rec.glycemicIndex.status === 'sourced') e.push('glycemic index has no cited source in this contract');
  return e;
}
