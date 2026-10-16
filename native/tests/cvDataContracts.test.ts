// G9 Stage J4: official Lahore price lookup by produce type (no grade split) + sourced nutrition per showcase class.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { lahoreProducePrice, checkProducePrice, SHOWCASE_CLASSES, LAHORE_SOURCES } from '../src/cv/prices/lookup.ts';
import { priceReference, type PriceSource } from '../src/cv/prices/reference.ts';
import { nutritionFor, forPortion, checkNutrition, SHOWCASE } from '../src/cv/data/nutrition.ts';
import { FDC_SHOWCASE } from '../src/cv/data/nutritionFdc.ts';

const F = JSON.parse(readFileSync(new URL('../../ml/prices/fixtures/reference_parity.json', import.meta.url), 'utf8'));
const SRC: PriceSource[] = F.sources;
const TODAY = '2026-10-12';

test('only Lahore sources count; PBS national average is excluded', () => {
  assert.ok(LAHORE_SOURCES.includes('Market Committee Lahore / PAMRA retail rate list'));
  assert.ok(!LAHORE_SOURCES.some((s) => s.startsWith('PBS')));
  const pbs: PriceSource = { source: 'PBS weekly SPI (national weekly average)', source_url: 'https://www.pbs.gov.pk/', price_type: 'national weekly average', list_date: TODAY,
    rows: [{ item_en: 'Banana', app_class: 'banana', unit: 'dozen', grade1_rs: null, grade2_rs: null, wholesale_rs: 150 }] };
  const r = lahoreProducePrice('banana', [pbs], TODAY); assert.equal(r.status, 'unavailable'); assert.equal((r as { reason: string }).reason, 'no_lahore_source');
});

test('type-level range combines list grade 1 and 2 (no grade split) and agrees with the existing reference module', () => {
  const r = lahoreProducePrice('apple', SRC, TODAY);
  assert.equal(r.status, 'ok');
  if (r.status !== 'ok') return;
  const a = priceReference('apple', 'A', SRC, TODAY); const b = priceReference('apple', 'B', SRC, TODAY);
  assert.ok(a.status === 'ok' && b.status === 'ok');
  if (a.status === 'ok' && b.status === 'ok') { assert.equal(r.minRs, Math.min(a.min_rs, b.min_rs)); assert.equal(r.maxRs, Math.max(a.max_rs, b.max_rs)); }
  assert.equal(r.gradeSplit, false); assert.equal(r.location, 'Lahore'); assert.equal(r.listDate, TODAY);
  assert.doesNotMatch(JSON.stringify(r), /grade 1|grade 2|grade1|grade2/);
});

test('citrus_orange maps to the citrus price class; every showcase type gives ok or an explicit unavailable', () => {
  for (const c of SHOWCASE_CLASSES) {
    const r = lahoreProducePrice(c, SRC, TODAY);
    assert.ok(r.status === 'ok' || (r.status === 'unavailable' && r.note.length > 0), c);
    if (r.status === 'ok') assert.ok(r.minRs > 0 && r.maxRs >= r.minRs);
  }
  assert.equal(lahoreProducePrice('mango', SRC, TODAY).status, 'unavailable');
});

test('stale lists are never shown; contract check rejects non-http sources (fixture file:// is test data, not a verified source)', () => {
  const stale = lahoreProducePrice('apple', SRC, '2026-10-20');
  assert.equal(stale.status, 'unavailable'); assert.equal((stale as { reason: string }).reason, 'stale');
  const ok = lahoreProducePrice('apple', SRC, TODAY);
  assert.ok(checkProducePrice(ok).some((e) => /sourceUrl/.test(e)));
  const live = SRC.map((s) => ({ ...s, source_url: 'https://lahore.punjab.gov.pk/rate-list' }));
  assert.deepEqual(checkProducePrice(lahoreProducePrice('apple', live, TODAY)), []);
});

test('nutrition: five sourced records with FDC ids and URLs; glycemic index explicitly missing', () => {
  const ids: Record<string, number> = { apple: 171688, banana: 173944, citrus_orange: 169097, tomato: 170457, carrot: 170393 };
  for (const c of SHOWCASE) {
    const r = nutritionFor(c)!; assert.ok(r, c);
    assert.equal(r.source.fdcId, ids[c]); assert.equal(r.source.foodUrl, `https://fdc.nal.usda.gov/food-details/${ids[c]}/nutrients`);
    assert.deepEqual(checkNutrition(r), []);
    assert.equal(r.glycemicIndex.status, 'missing');
    assert.equal(r.nutrients.energy_kcal.status, 'sourced');
  }
  assert.equal(nutritionFor('mango'), null);
});

test('nutrition values are exactly the generated FDC values (spot checks) and portions scale without inventing missing values', () => {
  const apple = nutritionFor('apple')!;
  const e = apple.nutrients.energy_kcal; assert.ok(e.status === 'sourced' && e.value === 52 && e.unit === 'kcal');
  const k = nutritionFor('banana')!.nutrients.potassium_mg; assert.ok(k.status === 'sourced' && k.value === 358);
  const c = nutritionFor('citrus_orange')!.nutrients.vitamin_c_mg; assert.ok(c.status === 'sourced' && c.value === 53.2);
  assert.equal(apple.typicalPortion?.grams, 182);
  const p = forPortion(apple, 182); const pe = p.energy_kcal; assert.ok(pe.status === 'sourced' && pe.value === 94.6);
  const fake = { ...apple, nutrients: { ...apple.nutrients, sugars_g: { status: 'missing' as const, reason: 'test' } } };
  assert.equal(forPortion(fake, 100).sugars_g.status, 'missing');
  assert.match(FDC_SHOWCASE.citrus_orange.matchNote, /kinnow/);
});
