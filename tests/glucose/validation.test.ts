import test from 'node:test';
import assert from 'node:assert/strict';
import { validateGlucoseInput } from '../../src/nutrisole/glucose/validation.ts';
import type { GlucoseInput, GlucoseReading } from '../../src/nutrisole/glucose/types.ts';

const now = new Date('2026-10-16T12:00:00Z');
const base: GlucoseInput = { value: '110', unit: 'mg/dL', date: 'Oct 16, 2026', time: '8:15 AM', tzOffsetMinutes: 300, tzName: 'Asia/Karachi', mealContext: 'fasting', note: '' };
const ok = (i: Partial<GlucoseInput>) => { const r = validateGlucoseInput({ ...base, ...i }, { now }); if (!r.ok) throw new Error(r.error); return r; };
const err = (i: Partial<GlucoseInput>) => { const r = validateGlucoseInput({ ...base, ...i }, { now }); assert.equal(r.ok, false); return r.ok ? '' : r.error; };

test('valid manual reading keeps original value/unit and stores a separate measured instant', () => {
  const r = ok({}); assert.equal(r.draft.valueOriginal, '110'); assert.equal(r.draft.unitOriginal, 'mg/dL'); assert.equal(r.draft.valueMgDl, 110);
  assert.equal(r.draft.measuredAt, '2026-10-16T03:15:00.000Z'); assert.equal(r.draft.tzOffsetMinutes, 300); assert.equal(r.draft.source.type, 'manual'); assert.equal(r.warnings.length, 0);
  const m = ok({ value: '6,1', unit: 'mmol/L' }); assert.equal(m.draft.valueOriginal, '6.1'); assert.equal(m.draft.valueMgDl, 109.91);
});

test('non-numbers, non-positive, NaN and impossible values are rejected', () => {
  for (const value of ['', 'abc', '-5', '0', '0.0', 'NaN', 'Infinity', '1e2', '5..1']) assert.match(err({ value }), /positive numeric/, value);
  assert.match(err({ value: '5' }), /possible entry range/); assert.match(err({ value: '5' }), /mmol\/L/);
  assert.match(err({ value: '1200' }), /possible entry range/);
  assert.match(err({ value: '110', unit: 'mmol/L' }), /switch the unit to mg\/dL/);
  assert.match(err({ value: '110.25' }), /whole numbers/);
  assert.match(err({ value: '5.555', unit: 'mmol/L' }), /2 decimals/);
});

test('likely unit mix-ups and unusual values need explicit confirmation (warnings, never auto-convert)', () => {
  const lowMg = ok({ value: '15' }); assert.equal(lowMg.warnings[0].code, 'possible-unit-mismatch'); assert.equal(lowMg.draft.unitOriginal, 'mg/dL'); assert.equal(lowMg.draft.valueMgDl, 15);
  const highMmol = ok({ value: '40', unit: 'mmol/L' }); assert.equal(highMmol.warnings[0].code, 'possible-unit-mismatch');
  assert.equal(ok({ value: '700' }).warnings[0].code, 'unusual-high');
  assert.equal(ok({ value: '1', unit: 'mmol/L' }).warnings[0].code, 'unusual-low');
});

test('dates, times, future readings, offsets and notes are validated', () => {
  assert.match(err({ date: 'Sep 31, 2026' }), /date/); assert.match(err({ date: '2026-10-16' }), /date/); assert.match(err({ time: '13:00 PM' }), /time/);
  assert.match(err({ date: 'Oct 17, 2026' }), /future/);
  assert.match(err({ tzOffsetMinutes: 900 }), /offset/);
  assert.match(err({ note: 'x'.repeat(501) }), /500/);
  assert.equal(ok({ note: '  after a walk  ' }).draft.note, 'after a walk'); assert.equal(ok({ note: '   ' }).draft.note, null);
});

test('same wall clock in different zones is a different instant (timezone safe)', () => {
  assert.equal(ok({ tzOffsetMinutes: 0 }).draft.measuredAt, '2026-10-16T08:15:00.000Z');
  assert.equal(ok({ tzOffsetMinutes: -420, date: 'Oct 15, 2026' }).draft.measuredAt, '2026-10-15T15:15:00.000Z');
});

test('possible manual duplicate is a non-destructive warning; editing itself is not a duplicate', () => {
  const first = ok({});
  const existing: GlucoseReading[] = [{ ...first.draft, id: 'r1', userId: 'u', createdAt: now.toISOString(), updatedAt: now.toISOString() }];
  const again = validateGlucoseInput(base, { now, existing }); assert.ok(again.ok && again.warnings.some(w => w.code === 'possible-duplicate'));
  const edit = validateGlucoseInput(base, { now, existing, editingId: 'r1' }); assert.ok(edit.ok && !edit.warnings.length);
});
