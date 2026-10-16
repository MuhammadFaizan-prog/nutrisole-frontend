import test from 'node:test';
import assert from 'node:assert/strict';
import { buildImportView, initialImportState } from '../../src/nutrisole/glucose/import/view.ts';
import { healthConnectToBatch } from '../../src/nutrisole/glucose/import/devices.ts';
import { initialExpansionState, buildScene } from '../../src/nutrisole/extensions/model.ts';
import { importAction } from '../../src/nutrisole/glucose/importActions.ts';
import { createGlucoseStore } from '../../src/nutrisole/glucose/store.ts';

const now = new Date('2026-10-16T12:00:00Z');
const batch = () => healthConnectToBatch(Array.from({ length: 95 }, (_, i) => ({ metadata: { id: `record-${i}`, dataOrigin: 'test.meter.app' }, time: new Date(Date.parse('2026-10-15T03:00:00Z') + i * 60_000).toISOString(), zoneOffset: { totalSeconds: 18000 }, level: { inMilligramsPerDeciliter: 110 + i }, specimenSource: 2 })), now);

test('every imported row is reachable in bounded pages, including the last flagged row', () => {
  const b = batch();
  const base = { ...initialImportState(), batch: b };
  const pages = [0, 1, 2].map(page => buildImportView({ ...base, page }, [], 'native', now));
  assert.deepEqual(pages.map(p => p.rows.length), [40, 40, 15]);
  assert.deepEqual(pages.flatMap(p => p.rows.map(r => r.id)), b.candidates.map(c => c.id));
  assert.deepEqual(pages.map(p => [p.pageStart, p.pageEnd]), [[0, 40], [40, 80], [80, 95]]);
  const scene = buildScene('import-review', { ...initialExpansionState(), glucoseImportView: pages[0] });
  assert.ok(scene.layers.some(l => l.action === 'import-page:next' && !l.disabled));
  assert.ok(scene.layers.some(l => l.action === 'import-page:previous' && l.disabled));
});

test('pagination clamps after a new mapping reduces the number of candidates', () => {
  const b = batch(); b.candidates = b.candidates.slice(0, 3);
  const view = buildImportView({ ...initialImportState(), batch: b, page: 2 }, [], 'native', now);
  assert.equal(view.page, 0); assert.equal(view.pageCount, 1); assert.equal(view.rows.length, 3);
});

test('the last page supports confirmation and saving through the actual import actions', async () => {
  const store = createGlucoseStore({ supabaseUrl: null, supabaseAnonKey: null, demo: true }); await store.start();
  let s = { ...initialExpansionState(), glucoseImport: { ...initialImportState(), batch: batch() } };
  let sheet: { choices?: { label: string; action: () => void }[] } | null = null;
  const ctx = () => ({ s, setState: (fn: (x: typeof s) => typeof s) => { s = fn(s); }, store, go: () => {}, back: () => {}, open: (sh: never) => { sheet = sh; } }) as never;
  importAction('import-page:next', ctx()); importAction('import-page:next', ctx());
  const last = buildImportView(s.glucoseImport, [], 'native', now).rows.at(-1)!;
  importAction(`import-row:${last.id}`, ctx());
  const confirm = (sheet as { choices?: { label: string; action: () => void }[] } | null)?.choices?.find(c => /Confirm/.test(c.label));
  assert.ok(confirm); confirm.action();
  importAction('import-save', ctx());
  const save = (sheet as { choices?: { label: string; action: () => void }[] } | null)?.choices?.find(c => /^Save 1 reading/.test(c.label));
  assert.ok(save); save.action();
  for (let i = 0; i < 20 && !store.getSnapshot().readings.length; i++) await new Promise(r => setTimeout(r, 5));
  assert.equal(store.getSnapshot().readings[0].source.recordId, 'record-94');
});
