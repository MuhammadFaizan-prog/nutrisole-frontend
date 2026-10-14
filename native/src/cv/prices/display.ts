// G9 Stage G price display contract. EXACT mirror of ml/prices/display.py (parity: native/tests/cvCloseup.test.ts replays
// ml/eval/fixtures/closeup_parity.json "price" cases). Built on the G4.6 module (reference.ts); it never computes a price itself.
//  - A price is shown only for a VERIFIED category (identification policy passed) with a CURRENT (non-stale) official row.
//  - Every shown price carries source, list date, location and unit, and is labelled an official reference, never a seller's
//    price and never a grade-adjusted value of this item.
//  - Wide scan: category reference = official list range across list grades for that class.
//    After a visual grade: grade A/B show the official list-grade row (grade 1 / grade 2) as "official list price for list grade N";
//    C / Reject / Not graded keep the category reference line only, with no grade-specific price.
import { priceReference, type PriceSource, type PriceReferenceOk } from './reference.ts';

export const PRICE_LOCATION: Record<string, string> = {
  'Market Committee Lahore / PAMRA retail rate list': 'Lahore',
  'Punjab AMIS (amis.pk) average wholesale prices': 'Lahore (Punjab AMIS wholesale)',
  'PBS weekly SPI (national weekly average)': 'Pakistan (national average)',
};
export const PRICE_LABEL = 'Official reference price, not this seller\'s price';

export type PriceLine = {
  kind: 'category_reference' | 'list_grade_reference';
  text: string; source: string; sourceUrl: string; listDate: string; location: string; unit: string; minRs: number; maxRs: number;
  listGrade: 'grade 1' | 'grade 2' | null; label: string;
};
export type PriceDisplay = { show: true; line: PriceLine } | { show: false; reason: 'not_identified' | 'no_current_official_price' | 'grade_below_list' | 'unknown_location' };

function fmt(r: PriceReferenceOk, kind: PriceLine['kind'], loc: string, minRs: number, maxRs: number, listGrade: PriceLine['listGrade']): PriceLine {
  const range = minRs === maxRs ? `Rs ${minRs}` : `Rs ${minRs}-${maxRs}`;
  const what = kind === 'category_reference' ? 'official list range' : `official list price, ${listGrade}`;
  return {
    kind, text: `${range} per ${r.unit} (${what}; ${r.source}, ${loc}, ${r.list_date})`, source: r.source, sourceUrl: r.source_url,
    listDate: r.list_date as string, location: loc, unit: r.unit, minRs, maxRs, listGrade, label: PRICE_LABEL,
  };
}

/** Wide-scan line for a verified category (no grade). */
export function categoryPrice(identified: boolean, appClass: string, sources: PriceSource[], today: string): PriceDisplay {
  if (!identified) return { show: false, reason: 'not_identified' };
  const a = priceReference(appClass, 'A', sources, today); const b = priceReference(appClass, 'B', sources, today);
  const ok = [a, b].filter((r): r is PriceReferenceOk => r.status === 'ok' && !r.stale && r.list_date !== null);
  const cur = ok.filter((r) => r.source === ok[0]?.source);
  if (!cur.length) return { show: false, reason: 'no_current_official_price' };
  const loc = PRICE_LOCATION[cur[0].source];
  if (!loc) return { show: false, reason: 'unknown_location' };
  return { show: true, line: fmt(cur[0], 'category_reference', loc, Math.min(...cur.map((r) => r.min_rs)), Math.max(...cur.map((r) => r.max_rs)), null) };
}

/** Close-up line after the gate. grade = gate output ('A' | 'B' | 'C' | 'Reject') or null when Not graded. */
export function gradedPrice(identified: boolean, appClass: string, grade: string | null, sources: PriceSource[], today: string): PriceDisplay {
  if (!identified) return { show: false, reason: 'not_identified' };
  if (grade !== 'A' && grade !== 'B') return grade === null ? categoryPrice(identified, appClass, sources, today) : { show: false, reason: 'grade_below_list' };
  const r = priceReference(appClass, grade, sources, today);
  if (r.status !== 'ok' || r.stale || r.list_date === null) return { show: false, reason: 'no_current_official_price' };
  const loc = PRICE_LOCATION[r.source];
  if (!loc) return { show: false, reason: 'unknown_location' };
  return { show: true, line: fmt(r, 'list_grade_reference', loc, r.min_rs, r.max_rs, r.list_grade) };
}
