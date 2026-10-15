// G9 Stage J6: THE canonical mapping between CV class ids and the domain ids used by nutrition and pricing.
//
// Why: recognition emits model class ids (G3 detector 0-11 = V1_CLASSES, H2 close-up 0-12 = H2_CLASSES with 12 = unknown), the price
// pipeline (ml/prices, prices/reference.ts, prices/display.ts) keys rows by the CV class string (`citrus`), and the nutrition contract
// (data/nutrition.ts, generated from USDA FDC) plus the Lahore produce-type lookup (prices/lookup.ts) key by the showcase domain id
// (`citrus_orange`). Before J6, `nutritionFor('citrus')` returned null. Every CV -> nutrition/price hop must go through this file:
// no scattered string replaces, and model output indexes are NEVER changed here (they are asserted against labels.ts / verify.ts).
//
// Rules:
//  - Price rows (ml/prices lexicon) are keyed by the CV class string itself for all 12 classes.
//  - Only the five showcase classes have a domain id. `lemon_lime` (id 6) is NOT orange and maps to no domain id; mango, guava, etc.
//    are recognised classes with no nutrition / showcase-lookup contract yet; category price rows may exist (domainId null => callers show "not available", never a guess).
//  - H2 `unknown` (12) and anything out of range map to null.
//  - The mapping carries no weight, no grade and no price value. Weight is never inferred from an image: nutrition is per 100 g or a
//    portion the user selects; prices come only from supplied official sources (with source, location, date, unit).
import { V1_CLASSES } from './models/labels.ts';
import { H2_CLASSES } from './pipeline/verify.ts';

export type DomainId = 'apple' | 'banana' | 'citrus_orange' | 'tomato' | 'carrot';
export const DOMAIN_IDS: readonly DomainId[] = ['apple', 'banana', 'citrus_orange', 'tomato', 'carrot'];
export type CvModel = 'g3' | 'h2';

export type CvDomainEntry = {
  cvClass: string;            // model class string (labels.ts classId / H2_CLASSES), also the ml/prices `app_class`
  domainId: DomainId | null;  // nutrition + Lahore produce-type key; null = no contract (show "not available")
  priceAppClass: string;      // key into PriceSource.rows[].app_class (ml/prices lexicon uses the CV class string for all 12)
  note: string;
};

/** Keyed by CV class string. Single source of truth. */
export const CV_DOMAIN: Readonly<Record<string, CvDomainEntry>> = Object.freeze({
  banana: { cvClass: 'banana', domainId: 'banana', priceAppClass: 'banana', note: '' },
  apple: { cvClass: 'apple', domainId: 'apple', priceAppClass: 'apple', note: '' },
  mango: { cvClass: 'mango', domainId: null, priceAppClass: 'mango', note: 'recognised class; no nutrition / showcase-lookup contract yet; category price rows may exist' },
  citrus: { cvClass: 'citrus', domainId: 'citrus_orange', priceAppClass: 'citrus', note: 'orange / kinnow / mosambi; FDC record is raw orange' },
  guava: { cvClass: 'guava', domainId: null, priceAppClass: 'guava', note: 'recognised class; no nutrition / showcase-lookup contract yet; category price rows may exist' },
  pomegranate: { cvClass: 'pomegranate', domainId: null, priceAppClass: 'pomegranate', note: 'recognised class; no nutrition / showcase-lookup contract yet; category price rows may exist' },
  lemon_lime: { cvClass: 'lemon_lime', domainId: null, priceAppClass: 'lemon_lime', note: 'NOT orange: never mapped to citrus_orange (own price rows only)' },
  tomato: { cvClass: 'tomato', domainId: 'tomato', priceAppClass: 'tomato', note: '' },
  potato: { cvClass: 'potato', domainId: null, priceAppClass: 'potato', note: 'recognised class; no nutrition / showcase-lookup contract yet; category price rows may exist' },
  cucumber: { cvClass: 'cucumber', domainId: null, priceAppClass: 'cucumber', note: 'recognised class; no nutrition / showcase-lookup contract yet; category price rows may exist' },
  carrot: { cvClass: 'carrot', domainId: 'carrot', priceAppClass: 'carrot', note: '' },
  capsicum: { cvClass: 'capsicum', domainId: null, priceAppClass: 'capsicum', note: 'recognised class; no nutrition / showcase-lookup contract yet; category price rows may exist' },
});

const CLASSES: Record<CvModel, readonly string[]> = { g3: V1_CLASSES.map((c) => c.classId), h2: H2_CLASSES };

/** Model class index -> CV class string (unchanged model order). null for H2 `unknown` or out of range. */
export function cvClassOf(model: CvModel, classIndex: number): string | null {
  if (!Number.isInteger(classIndex)) return null;
  const c = CLASSES[model][classIndex];
  return c && c !== 'unknown' ? c : null;
}

export function entryForCvClass(cvClass: string | null | undefined): CvDomainEntry | null {
  return cvClass ? CV_DOMAIN[cvClass] ?? null : null;
}

export function domainIdForCvClass(cvClass: string | null | undefined): DomainId | null {
  return entryForCvClass(cvClass)?.domainId ?? null;
}

export function domainIdForClassIndex(model: CvModel, classIndex: number): DomainId | null {
  return domainIdForCvClass(cvClassOf(model, classIndex));
}

/** Domain id -> the CV class string that represents it (inverse; total over DOMAIN_IDS). */
export function cvClassForDomain(domainId: string): string | null {
  const e = Object.values(CV_DOMAIN).find((v) => v.domainId === domainId);
  return e ? e.cvClass : null;
}

/** Price-pipeline app_class for a CV class (ml/prices rows). null = not a CV class. */
export function priceAppClassForCvClass(cvClass: string | null | undefined): string | null {
  return entryForCvClass(cvClass)?.priceAppClass ?? null;
}

/** Contract check of the table itself. Empty list = valid. */
export function checkDomainMap(): string[] {
  const e: string[] = [];
  const g3 = CLASSES.g3; const h2 = CLASSES.h2;
  if (Object.keys(CV_DOMAIN).length !== g3.length) e.push('every G3 class needs exactly one entry');
  for (const c of g3) if (!CV_DOMAIN[c]) e.push(`missing entry ${c}`);
  for (let i = 0; i < g3.length; i++) if (h2[i] !== g3[i]) e.push(`H2 index ${i} differs from G3`);
  if (h2[h2.length - 1] !== 'unknown') e.push('H2 last class must be unknown');
  for (const d of DOMAIN_IDS) if (Object.values(CV_DOMAIN).filter((v) => v.domainId === d).length !== 1) e.push(`domain ${d} must map from exactly one CV class`);
  if (CV_DOMAIN.lemon_lime.domainId !== null) e.push('lemon_lime must not map to a domain');
  for (const v of Object.values(CV_DOMAIN)) if (v.priceAppClass !== v.cvClass) e.push(`${v.cvClass}: price app_class must equal the CV class (ml/prices lexicon)`);
  return e;
}
