import test from 'node:test';
import assert from 'node:assert/strict';
import { parseReportText, type TextLine } from '../../src/nutrisole/glucose/import/labText.ts';
import { downloadRecords, encodeMeasurement, parseGlsMeasurement, RACP, type GlsTransport } from '../../src/nutrisole/glucose/import/gls.ts';

const meta = { format: 'image-ocr' as const, method: 'ocr' as const, fileName: 'report.jpg', fileSha256: 'a'.repeat(64), batchId: 'review', engine: 'test', now: new Date('2026-10-16T12:00:00Z') };
const lines = (text: string, page = 1): TextLine[] => text.split('\n').map((text, i) => ({ text, locator: `page ${page} line ${i + 1}` }));

test('an unrelated invoice with a plausible number is not a meter reading', () => {
  const result = parseReportText(lines('STORE RECEIPT\nTotal 154\nOct 15, 2026 8:15 AM'), meta);
  assert.equal(result.candidates.length, 0);
});

test('a lipid report with mg/dL but no glucose result is not a meter screen', () => {
  const result = parseReportText(lines('Test Result Unit Reference\nTotal Cholesterol 154 mg/dL\nTriglycerides 128 mg/dL\nCollected Oct 15, 2026 8:15 AM'), meta);
  assert.equal(result.candidates.length, 0);
});

test('abbreviated lipid analytes and an unlabeled unit-bearing result are not meter evidence', () => {
  for (const text of ['LIPID PROFILE\nHDL 54 mg/dL\nLDL 130 mg/dL\nCollected: Oct 15, 2026 8:15 AM', 'Serum result: 54 mg/dL']) {
    assert.equal(parseReportText(lines(text), meta).candidates.length, 0);
  }
});

test('separate meter photos in one PDF have different source record identifiers', () => {
  const result = parseReportText([...lines('126\nmg/dL\n15-10 08:15', 1), ...lines('126\nmg/dL\n15-10 09:15', 2)], meta);
  assert.equal(result.candidates.length, 2);
  assert.notEqual(result.candidates[0].provenance.recordId, result.candidates[1].provenance.recordId);
});

test('equal glucose values on different report pages keep their own collection dates', () => {
  const result = parseReportText([...lines('Collected: Oct 13, 2026 8:15 AM\nFasting Glucose 110 mg/dL', 1), ...lines('Collected: Oct 14, 2026 9:30 AM\nFasting Glucose 110 mg/dL', 2)], meta);
  assert.deepEqual(result.candidates.map(c => [c.value, c.date, c.time]), [['110', 'Oct 13, 2026', '8:15 AM'], ['110', 'Oct 14, 2026', '9:30 AM']]);
  assert.notEqual(result.candidates[0].id, result.candidates[1].id);
});

test('meter transfer ignores a response for a different RACP operation', async () => {
  const handlers = new Map<string, (b: Uint8Array) => void>();
  const transport: GlsTransport = {
    async subscribe(c, fn) { handlers.set(c, fn); return () => { handlers.delete(c); }; },
    async writeRacp() {
      handlers.get('racp')!(new Uint8Array([RACP.RESPONSE, 0, RACP.REPORT_COUNT, 1]));
      setTimeout(() => {
        handlers.get('measurement')?.(encodeMeasurement({ sequence: 1, wall: [2026, 10, 16, 8, 15, 0], mgDl: 110 }));
        handlers.get('racp')?.(new Uint8Array([RACP.RESPONSE, 0, RACP.REPORT_STORED, 1]));
      }, 5);
    },
  };
  const result = await downloadRecords(transport, { timeoutMs: 100 });
  assert.equal(result.records.length, 1);
  assert.equal(handlers.size, 0);
});

test('a failed subscription releases earlier subscriptions', async () => {
  let active = 0;
  const transport: GlsTransport = {
    async subscribe(c) { if (c === 'racp') throw new Error('disconnected'); active++; return () => { active--; }; },
    async writeRacp() {},
  };
  await assert.rejects(downloadRecords(transport, { timeoutMs: 50 }), /disconnected/);
  assert.equal(active, 0);
});

test('readings reach review progressively before transfer completion and context is optional', async () => {
  const events: string[] = []; const handlers = new Map<string, (b: Uint8Array) => void>();
  const transport: GlsTransport = {
    supportsContext: false,
    async subscribe(c, fn) { assert.notEqual(c, 'context'); handlers.set(c, fn); return () => { handlers.delete(c); }; },
    async writeRacp() {
      handlers.get('measurement')!(encodeMeasurement({ sequence: 1, wall: [2026, 10, 16, 8, 15, 0], mgDl: 110 }));
      assert.deepEqual(events, ['received 1']);
      handlers.get('racp')!(new Uint8Array([RACP.RESPONSE, 0, RACP.REPORT_STORED, 1]));
    },
  };
  const result = await downloadRecords(transport, { onProgress: r => events.push(`received ${r.records.length}`) });
  assert.equal(result.records.length, 1); assert.equal(handlers.size, 0);
});

test('cancelling a meter transfer releases listeners and returns its unsaved partial records', async () => {
  const control = new AbortController(); let active = 0;
  const transport: GlsTransport = {
    async subscribe() { active++; return () => { active--; }; },
    async writeRacp(bytes) { if (bytes[0] === RACP.REPORT_STORED) control.abort(); },
  };
  const result = await downloadRecords(transport, { signal: control.signal, timeoutMs: 100 });
  assert.equal(active, 0); assert.equal(result.outcome, 'failed'); assert.match(result.message, /cancelled/);
});

test('invalid meter dates are rejected instead of rolling over into another month', () => {
  assert.throws(() => parseGlsMeasurement(encodeMeasurement({ sequence: 1, wall: [2026, 2, 31, 8, 15, 0], mgDl: 110 })), /invalid/);
});

test('a burst of stored meter records does not rebuild the whole history for every packet', async () => {
  const handlers = new Map<string, (b: Uint8Array) => void>(); let snapshots = 0;
  const transport: GlsTransport = {
    supportsContext: false,
    async subscribe(c, fn) { handlers.set(c, fn); return () => handlers.delete(c); },
    async writeRacp() {
      for (let sequence = 1; sequence <= 5000; sequence++) handlers.get('measurement')!(encodeMeasurement({ sequence, wall: [2026, 10, 15, 8, 15, 0], mgDl: 110 }));
      handlers.get('racp')!(new Uint8Array([RACP.RESPONSE, 0, RACP.REPORT_STORED, 1]));
    },
  };
  const result = await downloadRecords(transport, { onProgress: () => { snapshots++; } });
  assert.equal(result.records.length, 5000);
  assert.ok(snapshots < 100, `Expected throttled progress; received ${snapshots} snapshots`);
});
