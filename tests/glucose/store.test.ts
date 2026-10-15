import test from 'node:test';
import assert from 'node:assert/strict';
import { GlucoseStore, createGlucoseStore } from '../../src/nutrisole/glucose/store.ts';
import { DemoGlucoseRepository, UnconfiguredGlucoseRepository, SupabaseGlucoseRepository } from '../../src/nutrisole/glucose/repository.ts';
import { SupabaseRest } from '../../src/nutrisole/glucose/supabaseRest.ts';
import { validateGlucoseInput } from '../../src/nutrisole/glucose/validation.ts';
import { GlucoseRepositoryError, type GlucoseDraft, type GlucoseRepository, type GlucoseReading } from '../../src/nutrisole/glucose/types.ts';

const now = new Date('2026-10-16T12:00:00Z');
const draft = (value = '110', unit: 'mg/dL' | 'mmol/L' = 'mg/dL', time = '8:15 AM'): GlucoseDraft => { const r = validateGlucoseInput({ value, unit, date: 'Oct 16, 2026', time, tzOffsetMinutes: 300, tzName: 'Asia/Karachi', mealContext: 'fasting' }, { now }); if (!r.ok) throw new Error(r.error); return r.draft; };

test('unconfigured build shows an honest state and cannot save', async () => {
  const store = createGlucoseStore({ supabaseUrl: null, supabaseAnonKey: null, demo: false });
  assert.equal(store.getSnapshot().status, 'unconfigured'); assert.equal(store.repository.mode, 'unconfigured');
  const res = await store.save(draft()); assert.equal(res.ok, false); assert.equal(store.getSnapshot().readings.length, 0);
  assert.ok(store.repository instanceof UnconfiguredGlucoseRepository);
});

test('configured Supabase build starts signed-out (no fake readings) and never uses demo data', async () => {
  const store = createGlucoseStore({ supabaseUrl: 'https://example.supabase.co', supabaseAnonKey: 'anon', demo: false });
  assert.ok(store.repository instanceof SupabaseGlucoseRepository); assert.equal(store.getSnapshot().status, 'signed-out');
  const res = await store.reload(); assert.equal(res.ok, false); assert.equal(store.getSnapshot().readings.length, 0);
});

test('demo flag CRUD: create → list → update (keeps unit) → delete, chronologically sorted', async () => {
  const store = new GlucoseStore(new DemoGlucoseRepository()); await store.start();
  assert.equal(store.getSnapshot().status, 'ready');
  const a = await store.save(draft('110', 'mg/dL', '9:00 AM')); const b = await store.save(draft('5.6', 'mmol/L', '7:00 AM'));
  assert.ok(a.ok && b.ok); assert.deepEqual(store.getSnapshot().readings.map(r => r.valueOriginal), ['5.6', '110']);
  const id = (b as { reading: GlucoseReading }).reading.id;
  const u = await store.save(draft('6.2', 'mmol/L', '7:00 AM'), id); assert.ok(u.ok);
  const edited = store.getSnapshot().readings.find(r => r.id === id)!; assert.equal(edited.unitOriginal, 'mmol/L'); assert.equal(edited.valueOriginal, '6.2'); assert.equal(edited.valueMgDl, 111.71);
  assert.ok((await store.remove(id)).ok); assert.equal(store.getSnapshot().readings.length, 1);
});

class FlakyRepo implements GlucoseRepository {
  readonly mode = 'supabase' as const; rows: GlucoseReading[] = []; failNext: GlucoseRepositoryError | null = null; calls = 0;
  async list() { return this.rows; }
  async create(d: GlucoseDraft) { this.calls++; await new Promise(r => setTimeout(r, 5)); if (this.failNext) { const e = this.failNext; this.failNext = null; throw e; } const r = { ...d, id: `r${this.calls}`, userId: 'u', createdAt: now.toISOString(), updatedAt: now.toISOString() }; this.rows.push(r); return r; }
  async update(id: string, d: GlucoseDraft) { if (this.failNext) { const e = this.failNext; this.failNext = null; throw e; } const r = { ...this.rows.find(x => x.id === id)!, ...d }; return r; }
  async remove() { if (this.failNext) { const e = this.failNext; this.failNext = null; throw e; } }
}

test('rapid double submission saves once; failures roll back with honest offline state', async () => {
  const repo = new FlakyRepo(); const client = new SupabaseRest('https://x.supabase.co', 'anon'); client.adoptSession({ accessToken: 't', refreshToken: 'r', expiresAt: Date.now() + 1e6, userId: 'u', email: null });
  const store = new GlucoseStore(repo, client); await store.reload();
  const [first, second] = await Promise.all([store.save(draft()), store.save(draft())]);
  assert.equal(first.ok, true); assert.equal(second.ok, false); assert.equal(repo.calls, 1); assert.equal(store.getSnapshot().readings.length, 1);
  const before = store.getSnapshot().readings;
  repo.failNext = new GlucoseRepositoryError('offline', 'offline');
  const del = await store.remove(before[0].id); assert.equal(del.ok, false); assert.deepEqual(store.getSnapshot().readings, before, 'optimistic delete rolled back');
  assert.equal(store.getSnapshot().status, 'offline'); assert.equal(store.getSnapshot().stale, true);
  repo.failNext = new GlucoseRepositoryError('server', 'boom');
  const upd = await store.save(draft('120'), before[0].id); assert.equal(upd.ok, false); assert.equal(store.getSnapshot().readings[0].valueOriginal, '110', 'optimistic update rolled back');
  repo.failNext = new GlucoseRepositoryError('server', 'boom');
  const created = await store.save(draft('130')); assert.equal(created.ok, false); assert.equal(store.getSnapshot().readings.length, 1, 'failed create is never shown as saved');
});

test('sign-out clears readings from memory', async () => {
  const repo = new FlakyRepo(); const client = new SupabaseRest('https://x.supabase.co', 'anon'); client.adoptSession({ accessToken: 't', refreshToken: 'r', expiresAt: 0, userId: 'u', email: null });
  const store = new GlucoseStore(repo, client); await store.reload(); await store.save(draft());
  client.adoptSession(null); assert.equal(store.getSnapshot().status, 'signed-out'); assert.equal(store.getSnapshot().readings.length, 0);
});
