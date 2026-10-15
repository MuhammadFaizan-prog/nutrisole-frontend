// G9 Stage J4: official Lahore price lookup BY PRODUCE TYPE (no grade split). Additive; reference.ts / display.ts unchanged.
// Contract:
//  - input: a showcase produce type + official sources already parsed by ml/prices (rate_list.py / amis.py; same PriceSource shape);
//  - only Lahore sources count (Market Committee Lahore / PAMRA retail list first, then Punjab AMIS Lahore wholesale);
//    the PBS national weekly average is never presented as a Lahore price;
//  - one range per type: retail rows combine the list's grade-1 and grade-2 columns, wholesale rows use the wholesale column,
//    so the app never ties a price to a visual grade of the scanned item;
//  - a stale or missing list returns 'unavailable' with a reason; a value is never invented, carried over or interpolated.
// Not wired to any screen in Stage J4.
import { STALE_DAYS, type PriceSource, type PriceType, type PriceUnit, type PriceRow } from './reference.ts';
import { PRICE_LOCATION } from './display.ts';

export type ShowcaseClass = 'apple' | 'banana' | 'citrus_orange' | 'tomato' | 'carrot';
export const SHOWCASE_CLASSES: readonly ShowcaseClass[] = ['apple', 'banana', 'citrus_orange', 'tomato', 'carrot'];
/** Showcase label -> app/price class used by ml/prices (class_map). */
export const SHOWCASE_APP_CLASS: Record<ShowcaseClass, string> = { apple: 'apple', banana: 'banana', citrus_orange: 'citrus', tomato: 'tomato', carrot: 'carrot' };
export const LAHORE_SOURCES = Object.keys(PRICE_LOCATION).filter((s) => PRICE_LOCATION[s].startsWith('Lahore'));
export const PRICE_LOOKUP_LABEL = 'Official Lahore reference price for this produce type, not a seller\'s price and not tied to a grade';

export type ProducePriceOk = {
  status: 'ok'; produceType: ShowcaseClass; appClass: string; location: string; priceType: PriceType;
  minRs: number; maxRs: number; unit: PriceUnit; varieties: Array<string | null>;
  source: string; sourceUrl: string; listDate: string; ageDays: number; gradeSplit: false; label: string;
};
export type ProducePriceUnavailable = {
  status: 'unavailable'; produceType: string;
  reason: 'unknown_produce_type' | 'no_lahore_source' | 'not_listed' | 'stale';
  lastListDate: string | null; note: string;
};
export type ProducePrice = ProducePriceOk | ProducePriceUnavailable;

const age = (d: string, today: string) => Math.round((Date.parse(`${today}T00:00:00Z`) - Date.parse(`${d}T00:00:00Z`)) / 86400000);
const cols = (t: PriceType): (keyof PriceRow)[] => (t === 'retail' ? ['grade1_rs', 'grade2_rs'] : ['wholesale_rs']);

export function lahoreProducePrice(produceType: string, sources: PriceSource[], today: string): ProducePrice {
  const appClass = (SHOWCASE_APP_CLASS as Record<string, string>)[produceType];
  if (!appClass) return { status: 'unavailable', produceType, reason: 'unknown_produce_type', lastListDate: null, note: 'Not a showcase produce type.' };
  const lahore = sources.filter((s) => LAHORE_SOURCES.includes(s.source));
  if (!lahore.length) return { status: 'unavailable', produceType, reason: 'no_lahore_source', lastListDate: null, note: 'No official Lahore list was supplied.' };
  let lastStale: string | null = null;
  for (const src of lahore) {
    const t: PriceType = src.price_type ?? 'retail';
    const rows = src.rows.filter((r) => r.app_class === appClass && cols(t).some((c) => typeof r[c] === 'number'));
    if (!rows.length) continue;
    if (!src.list_date) continue;
    const a = age(src.list_date, today);
    if (a < 0 || a > (STALE_DAYS[t] ?? 2)) { lastStale = lastStale ?? src.list_date; continue; }
    const unit = rows[0].unit; const same = rows.filter((r) => r.unit === unit);
    const vals = same.flatMap((r) => cols(t).map((c) => r[c]).filter((v): v is number => typeof v === 'number'));
    return {
      status: 'ok', produceType: produceType as ShowcaseClass, appClass, location: PRICE_LOCATION[src.source], priceType: t,
      minRs: Math.min(...vals), maxRs: Math.max(...vals), unit, varieties: same.map((r) => r.item_en ?? null),
      source: src.source, sourceUrl: src.source_url, listDate: src.list_date, ageDays: a, gradeSplit: false, label: PRICE_LOOKUP_LABEL,
    };
  }
  return lastStale
    ? { status: 'unavailable', produceType, reason: 'stale', lastListDate: lastStale, note: `The latest official Lahore list (${lastStale}) is out of date; no price shown.` }
    : { status: 'unavailable', produceType, reason: 'not_listed', lastListDate: null, note: 'This produce type is not on the supplied official Lahore lists.' };
}

/** Contract check for any ProducePrice handed to a screen. Empty list = valid. */
export function checkProducePrice(p: ProducePrice): string[] {
  const e: string[] = [];
  if (p.status === 'unavailable') { if (!p.note) e.push('unavailable needs a note'); return e; }
  if (p.gradeSplit !== false) e.push('gradeSplit must be false');
  if (!p.location.startsWith('Lahore')) e.push('location must be Lahore');
  if (!(p.minRs > 0 && p.maxRs >= p.minRs)) e.push('price range invalid');
  if (!/^https?:\/\//.test(p.sourceUrl)) e.push('sourceUrl required');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(p.listDate)) e.push('listDate required');
  if (/grade\s*[12ABC]\b/i.test(p.label)) e.push('label must not name a grade');
  return e;
}
