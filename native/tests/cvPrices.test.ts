import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { priceReference, type AppGrade, type PriceSource } from '../src/cv/prices/reference.ts';

type Fixture = { sources: PriceSource[]; cases: Array<{ app_class: string; app_grade: AppGrade; today: string; expected: unknown }> };
const fx = JSON.parse(readFileSync(new URL('../../ml/prices/fixtures/reference_parity.json', import.meta.url), 'utf8')) as Fixture;

test('TypeScript priceReference reproduces the Python reference case by case', () => {
  assert.ok(fx.cases.length >= 100);
  for (const c of fx.cases) {
    assert.deepStrictEqual(priceReference(c.app_class, c.app_grade, fx.sources, c.today), c.expected, `${c.app_class} ${c.app_grade} ${c.today}`);
  }
});

test('grade C and Reject never get a price', () => {
  for (const g of ['C', 'Reject'] as AppGrade[]) {
    const r = priceReference('apple', g, fx.sources, '2026-10-12');
    assert.equal(r.status, 'no_price');
  }
});

test('an old list is flagged stale, a missing class gets no price', () => {
  const r = priceReference('tomato', 'A', fx.sources, '2026-10-20');
  assert.equal(r.status, 'ok');
  if (r.status === 'ok') assert.equal(r.stale, true);
  assert.equal(priceReference('dragonfruit', 'A', fx.sources, '2026-10-12').status, 'no_price');
});
