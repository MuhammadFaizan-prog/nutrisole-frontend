import test from 'node:test';
import assert from 'node:assert/strict';
import { healthConnectToBatch, glsToBatch } from '../../src/nutrisole/glucose/import/devices.ts';
import { assessBatch, draftsToSave, editCandidate } from '../../src/nutrisole/glucose/import/review.ts';
import type { GlucoseReading } from '../../src/nutrisole/glucose/types.ts';

const now = new Date('2026-10-16T12:00:00Z');
test('Health Connect import preserves the exact measurement instant including seconds', () => {
  const batch = healthConnectToBatch([{ metadata: { id: 'record', dataOrigin: 'meter.app' }, time: '2026-10-15T03:00:42.123Z', zoneOffset: { totalSeconds: 18000 }, level: { inMilligramsPerDeciliter: 110 }, specimenSource: 2 }], now);
  batch.candidates[0].decision = 'confirmed';
  const result = draftsToSave(batch, [], now);
  assert.equal(result.drafts[0].measuredAt, '2026-10-15T03:00:42.123Z');
  const changedValue = editCandidate(batch, batch.candidates[0].id, { value: '111' });
  assert.equal(draftsToSave(changedValue, [], now).drafts[0].measuredAt, '2026-10-15T03:00:42.123Z');
  const uiEdit = editCandidate(batch, batch.candidates[0].id, { value: '111', date: batch.candidates[0].date, time: batch.candidates[0].time });
  assert.equal(draftsToSave(uiEdit, [], now).drafts[0].measuredAt, '2026-10-15T03:00:42.123Z');
  const changedTime = editCandidate(batch, batch.candidates[0].id, { time: '9:00 AM' });
  assert.equal(draftsToSave(changedTime, [], now).drafts[0].measuredAt, '2026-10-15T04:00:00.000Z');
});

test('the same sequence and clock from two different meters is not the same source record', () => {
  const download = { records: [{ sequence: 1, wallClock: '2026-10-15T08:15:00', timeOffsetMinutes: 0, value: '110', unit: 'mg/dL' as const, specimen: 'capillary_whole_blood' as const, location: 'finger', sensorStatus: [], contextFollows: false, context: null, raw: '' }], lastSequence: 1, outcome: 'success' as const, message: '', parseErrors: [] };
  const a = glsToBatch(download, { id: 'A', name: 'Meter' }, now); a.candidates[0].decision = 'confirmed';
  const draft = draftsToSave(a, [], now).drafts[0];
  const row: GlucoseReading = { ...draft, id: 'saved-A', userId: 'u', createdAt: now.toISOString(), updatedAt: now.toISOString() };
  const b = glsToBatch(download, { id: 'B', name: 'Meter' }, now);
  assert.ok(!assessBatch(b, [row], now)[0].allFlags.includes('already-imported'));
  assert.ok(assessBatch(a, [row], now)[0].allFlags.includes('already-imported'));
});
