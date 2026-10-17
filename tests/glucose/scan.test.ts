import test from 'node:test';
import assert from 'node:assert/strict';
import { scanGlucoseMeters } from '../../src/nutrisole/glucose/import/scan.ts';

test('Bluetooth discovery publishes each device immediately without waiting for the scan deadline', async () => {
  let found: ((d: { id: string; name: string | null; rssi: number | null }) => void) | undefined; let stopped = 0;
  const signal = new AbortController(); const seen: string[] = [];
  const result = scanGlucoseMeters({ start: fn => { found = fn; }, stop: () => { stopped++; } }, { timeoutMs: 5000, signal: signal.signal, onFound: d => seen.push(d.id) });
  found!({ id: 'meter-A', name: 'Strip meter', rssi: -40 });
  assert.deepEqual(seen, ['meter-A']);
  signal.abort(); const meters = await result;
  assert.equal(meters.length, 1); assert.equal(stopped, 1);
});

test('duplicate advertisements update one meter and scan errors stop the radio', async () => {
  let stopped = 0;
  await assert.rejects(scanGlucoseMeters({ start: (fn, fail) => { fn({ id: 'a', name: null, rssi: -50 }); fn({ id: 'a', name: 'Meter', rssi: -40 }); fail(new Error('Bluetooth off')); }, stop: () => { stopped++; } }, { timeoutMs: 20 }), /Bluetooth off/);
  assert.equal(stopped, 1);
});

test('asynchronous BLE startup rejection is surfaced and the radio is stopped', async () => {
  let stopped = 0;
  await assert.rejects(scanGlucoseMeters({ start: async () => { throw new Error('scan denied'); }, stop: async () => { stopped++; } }, { timeoutMs: 30 }), /scan denied/);
  assert.equal(stopped, 1);
});
