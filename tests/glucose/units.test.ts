import test from 'node:test';
import assert from 'node:assert/strict';
import { MG_DL_PER_MMOL_L, displayValue, fromMgDl, normalizeDecimal, toMgDl } from '../../src/nutrisole/glucose/units.ts';

// Deterministic PRNG so property tests are reproducible (no new dependency).
function rng(seed: number) { return () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 2 ** 32; }; }

test('conversion uses 18.0182 and documented examples', () => {
  assert.equal(MG_DL_PER_MMOL_L, 18.0182);
  assert.equal(toMgDl('5.6', 'mmol/L'), 100.9);   // 100.90192
  assert.equal(toMgDl('7', 'mmol/L'), 126.13);    // 126.1274
  assert.equal(toMgDl('10', 'mmol/L'), 180.18);
  assert.equal(toMgDl('1.1', 'mmol/L'), 19.82);
  assert.equal(toMgDl('110', 'mg/dL'), 110);
  assert.equal(toMgDl('110.5', 'mg/dL'), 110.5);
  assert.equal(fromMgDl(126.13, 'mmol/L'), 7);
  assert.equal(fromMgDl(100.9, 'mg/dL'), 101);
});

test('7 mmol/L is never treated as 7 mg/dL and mg/dL input is never converted twice', () => {
  assert.notEqual(toMgDl('7', 'mmol/L'), 7);
  for (const v of ['20', '99', '110', '600']) assert.equal(toMgDl(String(toMgDl(v, 'mg/dL')), 'mg/dL'), Number(v));
});

test('decimal normalization accepts locale commas and rejects non-numbers', () => {
  assert.equal(normalizeDecimal(' 5,6 '), '5.6'); assert.equal(normalizeDecimal('05.60'), '5.6'); assert.equal(normalizeDecimal('110'), '110');
  for (const bad of ['', ' ', '-5', '+5', '1e3', 'NaN', 'Infinity', '5..6', '5.6.1', '1,000.5', 'abc', '0x10', '١٢٣']) assert.equal(normalizeDecimal(bad), null, bad);
});

test('property: mmol→mg/dL is exact half-up rounding of v × 18.0182 to 2 decimals', () => {
  const r = rng(42);
  for (let i = 0; i < 5000; i++) {
    const hundredths = 60 + Math.floor(r() * (5550 - 60)); // 0.60 … 55.50 mmol/L
    const v = (hundredths / 100).toFixed(2);
    // Independent BigInt reference: hundredths × 180182 / 10000, rounded half up.
    const expected = Number((BigInt(hundredths) * 180182n + 5000n) / 10000n) / 100;
    assert.equal(toMgDl(v, 'mmol/L'), expected, v);
  }
});

test('property: conversion is monotonic and round-trips within display precision', () => {
  const r = rng(7); let prev = -Infinity; const values = Array.from({ length: 2000 }, () => 60 + Math.floor(r() * 5490)).sort((a, b) => a - b);
  for (const h of values) {
    const v = (h / 100).toFixed(2); const mg = toMgDl(v, 'mmol/L');
    assert.ok(mg >= prev); prev = mg;
    assert.ok(Math.abs(fromMgDl(mg, 'mmol/L') - Number(v)) <= 0.051, `${v} round trip`);
  }
});

test('display shows the original text in the entered unit (no round-trip drift)', () => {
  const reading = { valueOriginal: '5.6', unitOriginal: 'mmol/L' as const, valueMgDl: toMgDl('5.6', 'mmol/L') };
  assert.equal(displayValue(reading, 'mmol/L'), '5.6'); assert.equal(displayValue(reading, 'mg/dL'), '101');
  const mg = { valueOriginal: '126', unitOriginal: 'mg/dL' as const, valueMgDl: 126 };
  assert.equal(displayValue(mg, 'mmol/L'), '7.0'); assert.equal(displayValue(mg, 'mg/dL'), '126');
});

test('invalid canonical inputs throw rather than produce plausible values', () => {
  for (const bad of ['0x1', '-1', '', 'abc']) assert.throws(() => toMgDl(bad, 'mmol/L'));
  assert.throws(() => toMgDl('5.555', 'mmol/L')); for (const v of [0, -1, NaN, Infinity]) assert.throws(() => fromMgDl(v, 'mg/dL'));
});
