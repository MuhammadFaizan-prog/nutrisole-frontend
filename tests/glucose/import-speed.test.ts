import test from 'node:test';
import assert from 'node:assert/strict';
import { GlucoseStore } from '../../src/nutrisole/glucose/store.ts';
import { DemoGlucoseRepository } from '../../src/nutrisole/glucose/repository.ts';
import { validateGlucoseInput } from '../../src/nutrisole/glucose/validation.ts';

test('imports use bounded requests and publish saved rows before the last request completes', async () => {
  let active = 0, peak = 0, complete = 0; const seen: number[] = [];
  class Network extends DemoGlucoseRepository {
    async create(d: Parameters<DemoGlucoseRepository['create']>[0]) { active++; peak = Math.max(peak, active); await new Promise(r => setTimeout(r, 10)); const row = await super.create(d); active--; complete++; return row; }
  }
  const store = new GlucoseStore(new Network()); await store.start();
  store.subscribe(() => { if (complete < 12 && store.getSnapshot().readings.length) seen.push(store.getSnapshot().readings.length); });
  const d = validateGlucoseInput({ value: '110', unit: 'mg/dL', date: 'Oct 15, 2026', time: '8:15 AM', mealContext: 'fasting' }); if (!d.ok) throw new Error(d.error);
  const result = await store.importMany(Array.from({ length: 12 }, () => d.draft));
  assert.equal(result.saved.length, 12); assert.ok(peak > 1 && peak <= 4, `peak concurrent requests ${peak}`); assert.ok(seen.length > 0);
});
