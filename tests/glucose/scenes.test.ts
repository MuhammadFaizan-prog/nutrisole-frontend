import test from 'node:test';
import assert from 'node:assert/strict';
import { buildScene, initialExpansionState, type ExpansionState } from '../../src/nutrisole/extensions/model.ts';
import { compileScene, type FlowNode } from '../../native/responsive/sceneFlow.ts';
import { GlucoseStore } from '../../src/nutrisole/glucose/store.ts';
import { DemoGlucoseRepository } from '../../src/nutrisole/glucose/repository.ts';
import { buildGlucoseView } from '../../src/nutrisole/glucose/viewModel.ts';
import { validateGlucoseInput } from '../../src/nutrisole/glucose/validation.ts';
import { initialGlucoseSnapshot } from '../../src/nutrisole/glucose/store.ts';

const now = new Date();
const yesterday = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(now.getTime() - 86_400_000));
const flatten = (nodes: FlowNode[]): FlowNode[] => nodes.flatMap(n => [n, ...flatten(n.children)]);
async function withReadings() {
  const store = new GlucoseStore(new DemoGlucoseRepository()); await store.start();
  for (const [value, unit, time] of [['96', 'mg/dL', '12:05 AM'], ['6.1', 'mmol/L', '12:10 AM'], ['141', 'mg/dL', '12:20 AM']] as const) {
    const r = validateGlucoseInput({ value, unit, date: yesterday, time, mealContext: 'before_meal', note: 'n' }, { now }); if (!r.ok) throw new Error(r.error); await store.save(r.draft);
  }
  return store;
}
const state = (store: GlucoseStore, patch: Partial<ExpansionState> = {}): ExpansionState => {
  const s = { ...initialExpansionState(), ...patch };
  return { ...s, glucose: buildGlucoseView(store.getSnapshot(), { displayUnit: 'mg/dL', range: '7d', currentId: s.glucoseCurrentId, removed: s.glucoseRemoved, editingId: s.glucoseEditingId, editOffset: null }) };
};

test('overview renders a chart, a newest-first list and a demo banner from repository data', async () => {
  const store = await withReadings(); const scene = buildScene('glucose-overview', state(store));
  const texts = scene.layers.map(l => l.text || '');
  assert.ok(texts.some(t => t.startsWith('Demo mode')), 'demo data is labelled');
  assert.ok(texts.includes('Trend')); assert.equal(scene.layers.filter(l => l.kind === 'surface' && l.fill === '#123f2c' && l.w <= 18).length, 3, 'one bar per reading');
  const rows = scene.layers.filter(l => l.action?.startsWith('open-reading:')); assert.equal(rows.length, 3);
  assert.ok(texts.includes('141 mg/dL') && texts.includes('110 mg/dL'), 'mmol/L reading displayed in chosen unit');
  for (const l of scene.layers) { assert.ok(l.x >= 0 && l.x + l.w <= 393 && l.w > 0 && l.h > 0 && l.y >= 54, `${l.kind} ${l.text}`); }
  const flow = compileScene(scene); const all = flatten([...flow.header, ...flow.body, ...flow.footer]);
  const actions = new Set(all.flatMap(n => [n.layer.action, n.actionLayer?.action]));
  for (const l of scene.layers) if (l.action) assert.ok(actions.has(l.action), `native lost ${l.action}`);
});

test('detail shows the original value and unit with provenance; edit/remove enabled only with a reading', async () => {
  const store = await withReadings(); const mmol = store.getSnapshot().readings.find(r => r.unitOriginal === 'mmol/L')!;
  const scene = buildScene('reading-detail', state(store, { glucoseCurrentId: mmol.id }));
  const texts = scene.layers.map(l => l.text || '');
  assert.ok(texts.includes('6.1') && texts.includes('mmol/L') && texts.some(t => t.startsWith('≈ 110 mg/dL')));
  assert.ok(texts.includes('Demo session · not saved')); assert.ok(texts.includes('Manual meter entry')); assert.ok(texts.includes('Before a meal'));
  assert.ok(scene.layers.some(l => l.action === 'edit-reading' && !l.disabled));
  const removed = buildScene('reading-detail', state(store, { glucoseRemoved: true })); assert.ok(removed.layers.some(l => l.action === 'remove-reading' && l.disabled));
});

test('each non-ready status renders its own honest message (no fake readings)', () => {
  const statuses = ['unconfigured', 'signed-out', 'loading', 'offline', 'schema-missing', 'error'] as const;
  const seen = new Set<string>();
  for (const status of statuses) {
    const snap = { ...initialGlucoseSnapshot('supabase'), status, error: status === 'offline' ? 'NutriSole could not reach the database.' : null };
    const s = { ...initialExpansionState(), glucose: buildGlucoseView(snap, { displayUnit: 'mg/dL', range: '7d', currentId: null, removed: false, editingId: null, editOffset: null }) };
    const scene = buildScene('glucose-overview', s); const title = s.glucose.stateTitle; seen.add(title);
    assert.ok(scene.layers.some(l => l.text === title)); assert.ok(!scene.layers.some(l => l.action?.startsWith('open-reading:')));
  }
  assert.equal(seen.size, statuses.length);
});

test('add-reading form exposes notes, context, time zone and a truthful save note', async () => {
  const unconfigured = buildScene('add-reading', { ...initialExpansionState(), glucose: buildGlucoseView(initialGlucoseSnapshot('unconfigured'), { displayUnit: 'mg/dL', range: '7d', currentId: null, removed: false, editingId: null, editOffset: null }) });
  assert.ok(unconfigured.layers.some(l => l.field === 'readingNote' && l.multiline)); assert.ok(unconfigured.layers.some(l => l.action === 'reading-context'));
  assert.ok(unconfigured.layers.some(l => (l.text || '').startsWith('Database not configured')));
  assert.ok(unconfigured.layers.some(l => /UTC[+−]\d\d:\d\d/.test(l.text || '')), 'time zone label shown');
});
