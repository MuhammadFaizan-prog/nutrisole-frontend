// Bluetooth SIG Glucose Profile (GLP 1.0 / GLS 1.0.1) for strip meters: 0x2A18 Glucose
// Measurement, 0x2A34 Glucose Measurement Context and 0x2A52 Record Access Control Point.
// Transport-agnostic: the native adapter (react-native-ble-plx) and the simulated meter
// used by the tests both drive GlsSession through the GlsTransport interface.
// HARDWARE-UNVERIFIED: checked against spec byte vectors and a simulator only.
import type { MealContext } from '../types';
import { decodeSfloat } from '../adapters/bleGlucoseService';

export const GLS_SERVICE_UUID = '00001808-0000-1000-8000-00805f9b34fb';
export const GLS_MEASUREMENT_UUID = '00002a18-0000-1000-8000-00805f9b34fb';
export const GLS_CONTEXT_UUID = '00002a34-0000-1000-8000-00805f9b34fb';
export const GLS_FEATURE_UUID = '00002a51-0000-1000-8000-00805f9b34fb';
export const GLS_RACP_UUID = '00002a52-0000-1000-8000-00805f9b34fb';

export type GlsSpecimen = 'capillary_whole_blood' | 'capillary_plasma' | 'venous_whole_blood' | 'venous_plasma' | 'arterial_whole_blood' | 'arterial_plasma' | 'undetermined_whole_blood' | 'undetermined_plasma' | 'interstitial_fluid' | 'control_solution' | 'unknown';
const TYPES: Record<number, GlsSpecimen> = { 1: 'capillary_whole_blood', 2: 'capillary_plasma', 3: 'venous_whole_blood', 4: 'venous_plasma', 5: 'arterial_whole_blood', 6: 'arterial_plasma', 7: 'undetermined_whole_blood', 8: 'undetermined_plasma', 9: 'interstitial_fluid', 10: 'control_solution' };
const LOCATIONS: Record<number, string> = { 1: 'finger', 2: 'alternate site test', 3: 'earlobe', 4: 'control solution', 15: 'not available' };
const STATUS_BITS = ['device battery low', 'sensor malfunction', 'sample size insufficient', 'strip insertion error', 'strip type incorrect for device', 'result higher than the device can process', 'result lower than the device can process', 'temperature too high', 'temperature too low', 'read interrupted (strip pulled too soon)', 'general device fault', 'time fault'];

export type GlsRecord = {
  sequence: number;
  /** Meter wall clock (Base Time + Time Offset), no zone: "YYYY-MM-DDTHH:MM:SS". */
  wallClock: string;
  timeOffsetMinutes: number;
  /** As displayed by meters: whole mg/dL, or mmol/L with one decimal. Null when absent/NaN. */
  value: string | null;
  unit: 'mg/dL' | 'mmol/L';
  specimen: GlsSpecimen;
  location: string;
  sensorStatus: string[];
  contextFollows: boolean;
  raw: string;
};
export type GlsContext = { sequence: number; meal: MealContext | null; carbsGrams: number | null; tester: string | null; health: string | null; exerciseSeconds: number | null; medication: string | null; hba1cPercent: number | null; raw: string };

const hex = (b: Uint8Array) => Array.from(b, x => x.toString(16).padStart(2, '0')).join(' ');
const pad = (n: number) => String(n).padStart(2, '0');

export function parseGlsMeasurement(bytes: Uint8Array): GlsRecord {
  if (bytes.length < 10) throw new RangeError('Glucose Measurement is shorter than 10 bytes.');
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const flags = dv.getUint8(0); let i = 1;
  const need = (n: number) => { if (i + n > bytes.length) throw new RangeError('Glucose Measurement is truncated.'); };
  const sequence = dv.getUint16(i, true); i += 2;
  const year = dv.getUint16(i, true), month = dv.getUint8(i + 2), day = dv.getUint8(i + 3), hour = dv.getUint8(i + 4), minute = dv.getUint8(i + 5), second = dv.getUint8(i + 6); i += 7;
  if (!year || !month || !day) throw new RangeError('Glucose Measurement has no base time.');
  const baseTime = new Date(Date.UTC(year, month - 1, day, hour, minute, second));
  if (year < 1900 || year > 9999 || month < 1 || month > 12 || day < 1 || day > 31 || hour > 23 || minute > 59 || second > 59 || baseTime.getUTCDate() !== day || baseTime.getUTCMonth() !== month - 1) throw new RangeError('Glucose Measurement has an invalid meter date or time.');
  let timeOffsetMinutes = 0; if (flags & 0x01) { need(2); timeOffsetMinutes = dv.getInt16(i, true); i += 2; }
  const unit = flags & 0x04 ? 'mmol/L' as const : 'mg/dL' as const;
  let value: string | null = null; let specimen: GlsSpecimen = 'unknown'; let location = 'not available';
  if (flags & 0x02) {
    need(3);
    const conc = decodeSfloat(dv.getUint16(i, true)); const tl = dv.getUint8(i + 2); i += 3;
    specimen = TYPES[tl & 0x0f] || 'unknown'; location = LOCATIONS[tl >> 4] || 'reserved';
    if (conc !== null) value = unit === 'mg/dL' ? String(Math.round(conc * 1e5)) : (Math.round(conc * 1e4) / 10).toFixed(1);
  }
  const sensorStatus: string[] = [];
  if (flags & 0x08) { need(2); const s = dv.getUint16(i, true); i += 2; STATUS_BITS.forEach((label, b) => { if (s & (1 << b)) sensorStatus.push(label); }); }
  const wall = new Date(Date.UTC(year, month - 1, day, hour, minute, second) + timeOffsetMinutes * 60_000);
  const wallClock = `${wall.getUTCFullYear()}-${pad(wall.getUTCMonth() + 1)}-${pad(wall.getUTCDate())}T${pad(wall.getUTCHours())}:${pad(wall.getUTCMinutes())}:${pad(wall.getUTCSeconds())}`;
  return { sequence, wallClock, timeOffsetMinutes, value, unit, specimen, location, sensorStatus, contextFollows: Boolean(flags & 0x10), raw: hex(bytes) };
}

const MEALS: Record<number, MealContext> = { 1: 'before_meal', 2: 'after_meal', 3: 'fasting', 4: 'random', 5: 'bedtime' };
const TESTERS: Record<number, string> = { 1: 'self', 2: 'health care professional', 3: 'lab test', 15: 'not available' };
const HEALTH: Record<number, string> = { 1: 'minor health issues', 2: 'major health issues', 3: 'during menses', 4: 'under stress', 5: 'no health issues', 15: 'not available' };
const MEDS: Record<number, string> = { 1: 'rapid acting insulin', 2: 'short acting insulin', 3: 'intermediate acting insulin', 4: 'long acting insulin', 5: 'pre-mixed insulin' };

export function parseGlsContext(bytes: Uint8Array): GlsContext {
  if (bytes.length < 3) throw new RangeError('Glucose Measurement Context is shorter than 3 bytes.');
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const flags = dv.getUint8(0); let i = 1;
  const sequence = dv.getUint16(i, true); i += 2;
  const need = (n: number) => { if (i + n > bytes.length) throw new RangeError('Glucose Measurement Context is truncated.'); };
  if (flags & 0x80) { need(1); i += 1; } // extended flags (reserved)
  let carbsGrams: number | null = null, meal: MealContext | null = null, tester: string | null = null, health: string | null = null, exerciseSeconds: number | null = null, medication: string | null = null, hba1cPercent: number | null = null;
  if (flags & 0x01) { need(3); const kg = decodeSfloat(dv.getUint16(i + 1, true)); carbsGrams = kg === null ? null : Math.round(kg * 1000 * 10) / 10; i += 3; }
  if (flags & 0x02) { need(1); meal = MEALS[dv.getUint8(i)] || null; i += 1; }
  if (flags & 0x04) { need(1); const th = dv.getUint8(i); tester = TESTERS[th & 0x0f] || null; health = HEALTH[th >> 4] || null; i += 1; }
  if (flags & 0x08) { need(3); const s = dv.getUint16(i, true); exerciseSeconds = s === 0xffff ? null : s; i += 3; }
  if (flags & 0x10) { need(3); const id = dv.getUint8(i); const amount = decodeSfloat(dv.getUint16(i + 1, true)); medication = `${MEDS[id] || 'medication'}${amount === null ? '' : flags & 0x20 ? ` ${Math.round(amount * 1e3 * 10) / 10} mL` : ` ${Math.round(amount * 1e6 * 10) / 10} mg`}`; i += 3; }
  if (flags & 0x40) { need(2); hba1cPercent = decodeSfloat(dv.getUint16(i, true)); i += 2; }
  return { sequence, meal, carbsGrams, tester, health, exerciseSeconds, medication, hba1cPercent, raw: hex(bytes) };
}

// ---- Record Access Control Point (0x2A52) ----
export const RACP = { REPORT_STORED: 0x01, DELETE: 0x02, ABORT: 0x03, REPORT_COUNT: 0x04, COUNT_RESPONSE: 0x05, RESPONSE: 0x06 } as const;
export const RACP_OPERATOR = { NULL: 0x00, ALL: 0x01, LESS_EQ: 0x02, GREATER_EQ: 0x03, RANGE: 0x04, FIRST: 0x05, LAST: 0x06 } as const;
export const RACP_FILTER_SEQUENCE = 0x01;
const RESPONSE_CODES: Record<number, string> = { 1: 'success', 2: 'op code not supported', 3: 'invalid operator', 4: 'operator not supported', 5: 'invalid operand', 6: 'no records found', 7: 'abort unsuccessful', 8: 'procedure not completed', 9: 'operand not supported' };

export const racpReportAll = () => new Uint8Array([RACP.REPORT_STORED, RACP_OPERATOR.ALL]);
export const racpReportSince = (sequence: number) => new Uint8Array([RACP.REPORT_STORED, RACP_OPERATOR.GREATER_EQ, RACP_FILTER_SEQUENCE, sequence & 0xff, (sequence >> 8) & 0xff]);
export const racpCountAll = () => new Uint8Array([RACP.REPORT_COUNT, RACP_OPERATOR.ALL]);
export const racpAbort = () => new Uint8Array([RACP.ABORT, RACP_OPERATOR.NULL]);

export type RacpIndication = { kind: 'response'; requestOpCode: number; code: number; message: string } | { kind: 'count'; count: number } | { kind: 'unknown'; raw: string };
export function parseRacp(bytes: Uint8Array): RacpIndication {
  if (bytes[0] === RACP.RESPONSE && bytes.length >= 4) return { kind: 'response', requestOpCode: bytes[2], code: bytes[3], message: RESPONSE_CODES[bytes[3]] || 'reserved' };
  if (bytes[0] === RACP.COUNT_RESPONSE && bytes.length >= 4) return { kind: 'count', count: bytes[2] | (bytes[3] << 8) };
  return { kind: 'unknown', raw: hex(bytes) };
}

// ---- Download session ----
export interface GlsTransport {
  /** Subscribe to notifications (0x2A18, 0x2A34) or indications (0x2A52). Returns an unsubscribe. */
  subscribe(characteristic: 'measurement' | 'context' | 'racp', onValue: (bytes: Uint8Array) => void, onError?: (error: Error) => void): Promise<() => void>;
  /** Measurement Context is optional in the Bluetooth Glucose Service. */
  supportsContext?: boolean;
  writeRacp(bytes: Uint8Array): Promise<void>;
}
export type GlsDownload = { records: (GlsRecord & { context: GlsContext | null })[]; lastSequence: number | null; outcome: 'success' | 'no-records' | 'failed'; message: string; parseErrors: string[] };

/** Report all stored records, or only those with sequence ≥ `sinceSequence` ("since last sync"). */
export async function downloadRecords(transport: GlsTransport, opts: { sinceSequence?: number | null; timeoutMs?: number; signal?: AbortSignal; onProgress?: (partial: GlsDownload) => void } = {}): Promise<GlsDownload> {
  const records = new Map<number, GlsRecord>(); const contexts = new Map<number, GlsContext>(); const parseErrors: string[] = [];
  const unsubs: (() => void)[] = [];
  let finish: (r: RacpIndication | null) => void = () => {};
  const done = new Promise<RacpIndication | null>(resolve => { finish = resolve; });
  let failure: string | null = null; let timer: ReturnType<typeof setTimeout> | undefined;
  const listRecords = () => [...records.values()].sort((a, b) => a.sequence - b.sequence).map(r => ({ ...r, context: contexts.get(r.sequence) || null }));
  let lastPublished = -Infinity;
  const progress = () => {
    if (!opts.onProgress || Date.now() - lastPublished < 50) return;
    lastPublished = Date.now(); const list = listRecords();
    opts.onProgress({ records: list, lastSequence: list.at(-1)?.sequence ?? null, outcome: 'success', message: `${list.length} received · transfer in progress`, parseErrors: [...parseErrors] });
  };
  const failed = (error: Error) => { failure = error.message; finish(null); };
  const abort = () => { failure = 'Transfer cancelled. Received readings have not been saved.'; void transport.writeRacp(racpAbort()).catch(() => undefined); finish(null); };
  try {
    if (opts.signal?.aborted) throw new Error('Transfer cancelled.');
    unsubs.push(await transport.subscribe('measurement', b => { try { const r = parseGlsMeasurement(b); records.set(r.sequence, r); progress(); } catch (e) { parseErrors.push((e as Error).message); } }, failed));
    if (transport.supportsContext !== false) unsubs.push(await transport.subscribe('context', b => { try { const c = parseGlsContext(b); contexts.set(c.sequence, c); progress(); } catch (e) { parseErrors.push((e as Error).message); } }, failed));
    unsubs.push(await transport.subscribe('racp', b => { const r = parseRacp(b); if (r.kind === 'response' && r.requestOpCode === RACP.REPORT_STORED) finish(r); }, failed));
    opts.signal?.addEventListener('abort', abort, { once: true });
    if (opts.signal?.aborted) throw new Error('Transfer cancelled.');
    timer = setTimeout(() => finish(null), opts.timeoutMs ?? 30_000);
    await transport.writeRacp(opts.sinceSequence != null ? racpReportSince(opts.sinceSequence) : racpReportAll());
    const response = await done;
    const list = listRecords();
    const lastSequence = list.length ? list[list.length - 1].sequence : null;
    if (!response) return { records: list, lastSequence, outcome: 'failed', message: failure || 'The meter stopped responding before the transfer finished.', parseErrors };
    if (response.kind === 'response' && response.code === 6) return { records: list, lastSequence, outcome: 'no-records', message: 'The meter has no stored readings in that range.', parseErrors };
    if (response.kind === 'response' && response.code !== 1) return { records: list, lastSequence, outcome: 'failed', message: `The meter refused the request (${response.message}).`, parseErrors };
    return { records: list, lastSequence, outcome: 'success', message: `${list.length} record${list.length === 1 ? '' : 's'} received.`, parseErrors };
  } finally { clearTimeout(timer); opts.signal?.removeEventListener('abort', abort); unsubs.forEach(u => u()); }
}

// ---- Encoders (simulator + spec byte vectors) ----
export function encodeSfloat(value: number, exponent: number): number {
  const mantissa = Math.round(value / 10 ** exponent);
  if (mantissa < -2048 || mantissa > 2047 || exponent < -8 || exponent > 7) throw new RangeError('SFLOAT out of range');
  return ((exponent & 0x0f) << 12) | (mantissa & 0x0fff);
}
export type SimRecord = { sequence: number; wall: [number, number, number, number, number, number]; offsetMinutes?: number; mgDl?: number; mmolL?: number; type?: number; location?: number; status?: number; meal?: number; hba1c?: number };
export function encodeMeasurement(r: SimRecord): Uint8Array {
  const out: number[] = []; let flags = 0x02;
  if (r.offsetMinutes !== undefined) flags |= 0x01;
  if (r.mmolL !== undefined) flags |= 0x04;
  if (r.status !== undefined) flags |= 0x08;
  if (r.meal !== undefined || r.hba1c !== undefined) flags |= 0x10;
  const u16 = (v: number) => out.push(v & 0xff, (v >> 8) & 0xff);
  out.push(flags); u16(r.sequence); u16(r.wall[0]); out.push(r.wall[1], r.wall[2], r.wall[3], r.wall[4], r.wall[5]);
  if (r.offsetMinutes !== undefined) u16(r.offsetMinutes & 0xffff);
  u16(r.mmolL !== undefined ? encodeSfloat(r.mmolL / 1000, -4) : encodeSfloat((r.mgDl ?? 0) / 1e5, -5));
  out.push(((r.location ?? 1) << 4) | (r.type ?? 1));
  if (r.status !== undefined) u16(r.status);
  return new Uint8Array(out);
}
export function encodeContext(r: SimRecord): Uint8Array {
  const out: number[] = []; let flags = 0;
  if (r.meal !== undefined) flags |= 0x02; if (r.hba1c !== undefined) flags |= 0x40;
  out.push(flags, r.sequence & 0xff, (r.sequence >> 8) & 0xff);
  if (r.meal !== undefined) out.push(r.meal);
  if (r.hba1c !== undefined) { const s = encodeSfloat(r.hba1c, -1); out.push(s & 0xff, s >> 8); }
  return new Uint8Array(out);
}

/** In-memory meter for tests and the QA "simulated meter" path. Behaves like a GLS server. */
export class SimulatedGlucoseMeter implements GlsTransport {
  private handlers: Record<'measurement' | 'context' | 'racp', ((b: Uint8Array) => void)[]> = { measurement: [], context: [], racp: [] };
  records: SimRecord[]; supportsSince: boolean; dropBeforeResponse: boolean;
  constructor(records: SimRecord[], opts: { supportsSince?: boolean; dropBeforeResponse?: boolean } = {}) { this.records = records; this.supportsSince = opts.supportsSince ?? true; this.dropBeforeResponse = opts.dropBeforeResponse ?? false; }
  async subscribe(c: 'measurement' | 'context' | 'racp', h: (b: Uint8Array) => void) { this.handlers[c].push(h); return () => { this.handlers[c] = this.handlers[c].filter(x => x !== h); }; }
  private emit(c: 'measurement' | 'context' | 'racp', b: Uint8Array) { this.handlers[c].forEach(h => h(b)); }
  async writeRacp(cmd: Uint8Array) {
    const respond = (code: number) => this.emit('racp', new Uint8Array([RACP.RESPONSE, 0x00, cmd[0], code]));
    if (cmd[0] !== RACP.REPORT_STORED) return void setTimeout(() => respond(2), 0);
    let list = this.records;
    if (cmd[1] === RACP_OPERATOR.GREATER_EQ) { if (!this.supportsSince) return void setTimeout(() => respond(4), 0); const since = cmd[3] | (cmd[4] << 8); list = list.filter(r => r.sequence >= since); }
    else if (cmd[1] !== RACP_OPERATOR.ALL) return void setTimeout(() => respond(4), 0);
    setTimeout(() => {
      for (const r of list) { this.emit('measurement', encodeMeasurement(r)); if (r.meal !== undefined || r.hba1c !== undefined) this.emit('context', encodeContext(r)); }
      if (!this.dropBeforeResponse) respond(list.length ? 1 : 6);
    }, 0);
  }
}
