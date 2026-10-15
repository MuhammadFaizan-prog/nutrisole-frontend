import test from 'node:test';
import assert from 'node:assert/strict';
import { reconcileImport } from '../../src/nutrisole/glucose/adapters/reconcile.ts';
import { decodeSfloat, parseGlucoseMeasurement, bleGlucoseAdapter } from '../../src/nutrisole/glucose/adapters/bleGlucoseService.ts';
import { mapHealthConnectRecord, healthConnectAdapter } from '../../src/nutrisole/glucose/adapters/healthConnect.ts';
import { glucoseAdapters } from '../../src/nutrisole/glucose/adapters/index.ts';
import type { ImportedSample, GlucoseReading } from '../../src/nutrisole/glucose/types.ts';

const now = new Date('2026-10-16T12:00:00Z');
const sample = (id: string, extra: Partial<ImportedSample> = {}): ImportedSample => ({ sourceRecordId: id, provider: 'com.example.meterapp', device: null, measuredAt: '2026-10-15T03:00:00Z', tzOffsetMinutes: 300, value: '104', unit: 'mg/dL', specimen: 'capillary_blood', ...extra });

test('every import adapter is disabled and reports research-only (no counterfeit connected state)', async () => {
  assert.equal(glucoseAdapters.length, 4);
  for (const a of glucoseAdapters) { assert.equal(a.enabled, false); const st = await a.status(); assert.equal(st.state, 'research-only'); await assert.rejects(a.readSince(null)); }
  assert.equal(bleGlucoseAdapter.evidence, 'REQUIRES HARDWARE TEST'); assert.equal(healthConnectAdapter.evidence, 'UNVERIFIED');
});

test('reconcile: idempotent re-import, out-of-order safe, CGM rejected, units preserved', () => {
  const first = reconcileImport('health_connect', [sample('b'), sample('a', { value: '5.9', unit: 'mmol/L' })], [], now);
  assert.equal(first.result.imported, 2); assert.equal(first.drafts[1].unitOriginal, 'mmol/L'); assert.equal(first.drafts[1].valueOriginal, '5.9'); assert.equal(first.drafts[1].valueMgDl, 106.31);
  const stored: GlucoseReading[] = first.drafts.map((d, i) => ({ ...d, id: `r${i}`, userId: 'u', createdAt: now.toISOString(), updatedAt: now.toISOString() }));
  const again = reconcileImport('health_connect', [sample('a'), sample('b'), sample('a')], stored, now);
  assert.equal(again.result.imported, 0); assert.equal(again.result.skippedDuplicates, 3);
  const mixed = reconcileImport('health_connect', [sample('c', { specimen: 'interstitial_fluid' }), sample('d', { specimen: 'unknown' }), sample('e', { value: '400', unit: 'mmol/L' }), sample('f', { measuredAt: '2027-01-01T00:00:00Z' }), sample('', {})], [], now);
  assert.equal(mixed.result.imported, 0); assert.equal(mixed.result.rejected.length, 5); assert.match(mixed.result.rejected[0].reason, /CGM/);
  // Same instant + same value from two distinct source records stays two records (not collapsed).
  const twins = reconcileImport('ble_meter', [sample('seq-1'), sample('seq-2')], [], now); assert.equal(twins.result.imported, 2);
});

test('BLE GLS 0x2A18 parser decodes SFLOAT, units, time offset and control solution', () => {
  assert.equal(decodeSfloat(0x07ff), null); assert.equal(decodeSfloat(0xb06e), 110e-5); assert.equal(decodeSfloat(0xd03d), 61e-3);
  // flags: time offset + concentration (kg/L); seq 7; 2026-10-16 08:15:00; offset +0; 110 mg/dL (0xB06E); capillary whole blood, finger
  const mg = parseGlucoseMeasurement(new Uint8Array([0x03, 0x07, 0x00, 0xea, 0x07, 10, 16, 8, 15, 0, 0x00, 0x00, 0x6e, 0xb0, 0x11]));
  assert.deepEqual([mg.sequence, mg.value, mg.unit, mg.specimen, mg.controlSolution, mg.baseTime], [7, '110', 'mg/dL', 'capillary_blood', false, '2026-10-16T08:15:00.000']);
  // mol/L flag (bit 2): 6.1 mmol/L = 0.0061 mol/L = 61e-4 → SFLOAT exponent -4 (0xC03D); type 10 = control solution
  const ctl = parseGlucoseMeasurement(new Uint8Array([0x06, 0x08, 0x00, 0xea, 0x07, 10, 16, 8, 15, 0, 0x3d, 0xc0, 0x1a]));
  assert.deepEqual([ctl.value, ctl.unit, ctl.controlSolution], ['6.1', 'mmol/L', true]);
  assert.throws(() => parseGlucoseMeasurement(new Uint8Array([1, 2, 3])));
});

test('Health Connect mapper keeps provenance and separates finger-prick from CGM', () => {
  const s = mapHealthConnectRecord({ metadata: { id: 'hc-1', dataOrigin: 'com.lifescan.reveal' }, time: '2026-10-15T03:00:00Z', zoneOffsetSeconds: 18000, level: { inMilligramsPerDeciliter: 104 }, specimenSource: 2, relationToMeal: 2 });
  assert.deepEqual([s.sourceRecordId, s.provider, s.unit, s.value, s.specimen, s.mealContext, s.tzOffsetMinutes], ['hc-1', 'com.lifescan.reveal', 'mg/dL', '104', 'capillary_blood', 'fasting', 300]);
  assert.equal(mapHealthConnectRecord({ metadata: { id: 'x', dataOrigin: 'cgm' }, time: '2026-10-15T03:00:00Z', level: { inMilligramsPerDeciliter: 99 }, specimenSource: 1, relationToMeal: 0 }).specimen, 'interstitial_fluid');
});
