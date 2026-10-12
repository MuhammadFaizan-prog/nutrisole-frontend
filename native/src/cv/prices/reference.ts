/**
 * Official price reference for one graded item (G4). EXACT mirror of ml/prices/reference.py
 * (parity: native/tests/cvPrices.test.ts replays ml/prices/fixtures/reference_parity.json).
 * Grade A -> grade-1 retail, B -> grade-2 retail, C / Reject / ungradable -> no price.
 * Sources in priority order: Lahore Market Committee / PAMRA retail list -> AMIS wholesale -> PBS SPI.
 * A reference only, never an offer or a valuation. Always carries source, URL, list date and staleness.
 */
export type AppGrade = 'A' | 'B' | 'C' | 'Reject' | 'ungradable';
export type PriceType = 'retail' | 'wholesale' | 'national weekly average';
export type PriceUnit = 'kg' | 'dozen' | 'piece';

export interface PriceRow {
  item_en: string | null;
  app_class: string | null;
  unit: PriceUnit;
  grade1_rs?: number | null;
  grade2_rs?: number | null;
  wholesale_rs?: number | null;
}

export interface PriceSource {
  source: string;
  source_url: string;
  price_type: PriceType;
  list_date: string | null; // YYYY-MM-DD
  rows: PriceRow[];
}

export interface PriceReferenceOk {
  status: 'ok';
  app_class: string;
  app_grade: 'A' | 'B';
  price_type: PriceType;
  list_grade: 'grade 1' | 'grade 2' | null;
  min_rs: number;
  max_rs: number;
  unit: PriceUnit;
  varieties: Array<string | null>;
  other_unit_rows: Array<{ item_en: string | null; unit: PriceUnit; rs: number }>;
  source: string;
  source_url: string;
  list_date: string | null;
  age_days: number | null;
  stale: boolean;
  disclaimer: string;
}

export interface PriceReferenceNone {
  status: 'no_price';
  reason: 'grade_below_market' | 'ungradable' | 'class_not_listed';
  note: string;
}

export type PriceReference = PriceReferenceOk | PriceReferenceNone;

export const STALE_DAYS: Record<PriceType, number> = { retail: 2, wholesale: 2, 'national weekly average': 7 };
const NOTE_LOW = 'Below market grade; expect a discount. No reference price shown.';

function ageDays(listDate: string | null, today: string): number | null {
  if (!listDate) return null;
  const ms = Date.parse(`${today}T00:00:00Z`) - Date.parse(`${listDate}T00:00:00Z`);
  return Math.round(ms / 86400000);
}

export function priceReference(appClass: string, appGrade: AppGrade, sources: PriceSource[], today: string): PriceReference {
  if (appGrade !== 'A' && appGrade !== 'B') {
    const low = appGrade === 'C' || appGrade === 'Reject';
    return { status: 'no_price', reason: low ? 'grade_below_market' : 'ungradable', note: low ? NOTE_LOW : 'No grade, so no reference price.' };
  }
  let fallback: PriceReferenceOk | null = null;
  for (const src of sources) {
    const ptype: PriceType = src.price_type ?? 'retail';
    const age = ageDays(src.list_date, today);
    const stale = age === null || age > (STALE_DAYS[ptype] ?? 2);
    const col: keyof PriceRow = ptype === 'retail' ? (appGrade === 'A' ? 'grade1_rs' : 'grade2_rs') : 'wholesale_rs';
    const rows = src.rows.filter((r) => r.app_class === appClass && r[col] !== null && r[col] !== undefined);
    if (rows.length === 0) continue;
    const unit = rows[0].unit;
    const same = rows.filter((r) => r.unit === unit);
    const vals = same.map((r) => r[col] as number);
    const ref: PriceReferenceOk = {
      status: 'ok', app_class: appClass, app_grade: appGrade, price_type: ptype,
      list_grade: ptype === 'retail' ? (appGrade === 'A' ? 'grade 1' : 'grade 2') : null,
      min_rs: Math.min(...vals), max_rs: Math.max(...vals), unit,
      varieties: same.map((r) => r.item_en ?? null),
      other_unit_rows: rows.filter((r) => r.unit !== unit).map((r) => ({ item_en: r.item_en ?? null, unit: r.unit, rs: r[col] as number })),
      source: src.source, source_url: src.source_url, list_date: src.list_date, age_days: age, stale,
      disclaimer: 'Official reference price, not an offer or a valuation.',
    };
    if (!stale) return ref;
    fallback = fallback ?? ref;
  }
  return fallback ?? { status: 'no_price', reason: 'class_not_listed', note: "This item is not on today's official lists." };
}
