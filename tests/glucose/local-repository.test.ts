import test from 'node:test';
import assert from 'node:assert/strict';
import { LocalGlucoseRepository } from '../../src/nutrisole/glucose/localRepository.ts';
import { GlucoseStore } from '../../src/nutrisole/glucose/store.ts';
import { validateGlucoseInput } from '../../src/nutrisole/glucose/validation.ts';
import type { GlucoseDraft, GlucoseStorage } from '../../src/nutrisole/glucose/types.ts';

const draft = (value = '110', unit: 'mg/dL' | 'mmol/L' = 'mg/dL'): GlucoseDraft => {
  const r = validateGlucoseInput({ value, unit, date: 'Oct 15, 2026', time: '8:15 AM', mealContext: 'fasting', tzOffsetMinutes: 300 });
  if (!r.ok) throw new Error(r.error); return r.draft;
};
const memory = () => { let data: string | null = null; let writes = 0; return { read: async () => data, write: async (next: string) => { data = next; writes++; }, get writes() { return writes; } }; };

test('real local readings survive a new repository and store instance', async () => {
  const disk = memory(); const first = new GlucoseStore(new LocalGlucoseRepository(disk)); await first.start();
  assert.equal(first.getSnapshot().status, 'ready');
  const result = await first.save(draft('6.2', 'mmol/L')); assert.ok(result.ok);
  const restart = new GlucoseStore(new LocalGlucoseRepository(disk)); await restart.start();
  assert.equal(restart.getSnapshot().readings.length, 1);
  const r = restart.getSnapshot().readings[0]; assert.equal(r.valueOriginal, '6.2'); assert.equal(r.unitOriginal, 'mmol/L'); assert.equal(r.valueMgDl, 111.71);
  assert.equal(r.userId, 'this-device');
  await restart.save(draft('111'), r.id); const afterEdit = new LocalGlucoseRepository(disk);
  assert.equal((await afterEdit.list())[0].valueOriginal, '111');
  await afterEdit.remove(r.id); assert.equal((await new LocalGlucoseRepository(disk).list()).length, 0);
});

test('a confirmed import is one durable write, source-record duplicates are skipped', async () => {
  const disk = memory(); const repo = new LocalGlucoseRepository(disk); const store = new GlucoseStore(repo); await store.start();
  const d = draft(); d.source = { type: 'ble_meter', provider: 'ble:gls', device: 'meter-A', recordId: 'seq1@2026-10-15T08:15:00' };
  const many = await store.importMany([d, d, { ...d, source: { ...d.source, recordId: 'seq2@2026-10-15T08:15:00' } }]);
  assert.equal(many.saved.length, 2); assert.equal(many.skipped, 1); assert.equal(disk.writes, 1);
  assert.equal((await new LocalGlucoseRepository(disk).list()).length, 2);
});

test('a failed durable write never leaks an unsaved reading into history', async () => {
  const disk: GlucoseStorage = { read: async () => null, write: async () => { throw new Error('storage full'); } };
  const repo = new LocalGlucoseRepository(disk); const store = new GlucoseStore(repo); await store.start();
  assert.equal((await store.save(draft())).ok, false);
  assert.equal(store.getSnapshot().readings.length, 0); assert.equal((await repo.list()).length, 0);
});

test('concurrent durable mutations cannot lose an earlier reading', async () => {
  const disk = memory(); const repo = new LocalGlucoseRepository(disk);
  await Promise.all(Array.from({ length: 20 }, (_, i) => repo.create(draft(String(100 + i)))));
  assert.equal((await new LocalGlucoseRepository(disk).list()).length, 20);
});

test('corrupt storage is reported and never replaced with an empty history', async () => {
  const disk = { read: async () => '{broken', write: async () => { throw new Error('must not overwrite'); } };
  await assert.rejects(new LocalGlucoseRepository(disk).list(), /stored glucose history could not be read/i);
});

test('a caller cannot persist a draft with a mismatched canonical value', async () => {
  const disk = memory(); const repo = new LocalGlucoseRepository(disk);
  await assert.rejects(repo.create({ ...draft('6.2', 'mmol/L'), valueMgDl: 6.2 }), /value|conversion/i);
  assert.equal(disk.writes, 0);
});

test('a phone restart retains every reading beyond the old 1000-row cloud page limit', async () => {
  const disk = memory(); const store = new GlucoseStore(new LocalGlucoseRepository(disk)); await store.start();
  assert.equal((await store.importMany(Array.from({ length: 1001 }, () => draft()))).saved.length, 1001);
  const restarted = new GlucoseStore(new LocalGlucoseRepository(disk)); await restarted.start();
  assert.equal(restarted.getSnapshot().readings.length, 1001);
});

test('correcting a phone clock backwards does not make its saved history unreadable', async () => {
  const validation = validateGlucoseInput({ value: '110', unit: 'mg/dL', date: 'Oct 15, 2030', time: '8:15 AM', mealContext: 'fasting', tzOffsetMinutes: 300 }, { now: new Date('2030-10-16T12:00:00Z') });
  assert.ok(validation.ok);
  const row = { ...validation.draft, id: 'clock-drift', userId: 'this-device', createdAt: '2030-10-15T03:15:00Z', updatedAt: '2030-10-15T03:15:00Z' };
  const disk = { read: async () => JSON.stringify({ version: 1, readings: [row] }), write: async () => {} };
  const repo = new LocalGlucoseRepository(disk);
  assert.equal((await repo.list())[0].id, 'clock-drift');
  await assert.rejects(repo.create(validation.draft), /future/);
});

test('editing a stored device reading preserves its seconds when the displayed minute is unchanged', async () => {
  const disk = memory(); const store = new GlucoseStore(new LocalGlucoseRepository(disk)); await store.start();
  const d = { ...draft(), measuredAt: '2026-10-15T03:15:42.123Z', source: { type: 'health_connect' as const, provider: 'meter.app', device: null, recordId: 'exact' } };
  const saved = await store.save(d); assert.ok(saved.ok);
  assert.ok((await store.save(draft('111'), saved.reading.id)).ok);
  assert.equal((await new LocalGlucoseRepository(disk).list())[0].measuredAt, d.measuredAt);
});
