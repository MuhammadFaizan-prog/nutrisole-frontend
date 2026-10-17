import test from 'node:test';
import assert from 'node:assert/strict';
import { GlucoseStore } from '../../src/nutrisole/glucose/store.ts';
import { SupabaseRest } from '../../src/nutrisole/glucose/supabaseRest.ts';
import { DemoGlucoseRepository } from '../../src/nutrisole/glucose/repository.ts';
import { validateGlucoseInput } from '../../src/nutrisole/glucose/validation.ts';
import type { GlucoseDraft, GlucoseReading } from '../../src/nutrisole/glucose/types.ts';

const input = validateGlucoseInput({ value: '110', unit: 'mg/dL', date: 'Oct 15, 2026', time: '8:15 AM', mealContext: 'fasting' });
if (!input.ok) throw new Error(input.error);
const draft = input.draft;
const session = () => { const client = new SupabaseRest('https://example.supabase.co', 'anon'); client.adoptSession({ accessToken: 'test', refreshToken: 'test', userId: 'A', email: null, expiresAt: Date.now() + 60_000 }); return client; };

test('a late cloud save cannot repopulate history after sign-out', async () => {
  let release!: () => void;
  class Delayed extends DemoGlucoseRepository {
    async create(d: GlucoseDraft) { await new Promise<void>(r => { release = r; }); return super.create(d); }
  }
  const client = session(); const store = new GlucoseStore(new Delayed(), client); await store.start();
  const pending = store.save(draft); client.adoptSession(null); release(); await pending;
  assert.equal(store.getSnapshot().readings.length, 0); assert.equal(store.getSnapshot().status, 'signed-out'); assert.equal(store.getSnapshot().busy, null);
});

test('an older history request cannot erase a newly saved reading', async () => {
  let release!: (rows: GlucoseReading[]) => void;
  class DelayedList extends DemoGlucoseRepository {
    delay = false;
    async list() { return this.delay ? new Promise<GlucoseReading[]>(r => { release = r; }) : super.list(); }
  }
  const repo = new DelayedList(); const store = new GlucoseStore(repo); await store.start(); repo.delay = true;
  const pending = store.reload(); assert.ok((await store.save(draft)).ok); release([]); await pending;
  assert.equal(store.getSnapshot().readings.length, 1);
});

test('a save during the first load also retains older previously unseen history', async () => {
  let release!: (rows: GlucoseReading[]) => void;
  class FirstLoad extends DemoGlucoseRepository {
    async list() { return new Promise<GlucoseReading[]>(r => { release = r; }); }
  }
  const repo = new FirstLoad(); const previous = await repo.create(draft);
  const store = new GlucoseStore(repo); const pending = store.start();
  assert.ok((await store.save({ ...draft, valueOriginal: '111', valueMgDl: 111 })).ok);
  release([previous]); await pending;
  assert.equal(store.getSnapshot().readings.length, 2);
});
