// Real on-device readings, separate from a signed-in cloud account and demo data.
// The Android adapter encrypts the snapshot with a non-exportable Keystore key.
import type { GlucoseDraft, GlucoseQuery, GlucoseReading, GlucoseRepository, GlucoseStorage } from './types';
import { GlucoseRepositoryError } from './types';
import { toMgDl } from './units';
import { compareChronological, formatDisplayDate, formatDisplayTime, instantToWallClock } from './time';
import { validateGlucoseInput } from './validation';

const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value));
const sourceKey = (d: GlucoseDraft) => d.source.type === 'manual' || !d.source.recordId ? null : JSON.stringify([d.source.type, d.source.provider, d.source.device, d.source.recordId]);

function checkDraft(draft: GlucoseDraft, persisted = false) {
  if (!Number.isFinite(Date.parse(draft.measuredAt))) throw new GlucoseRepositoryError('validation', 'The measurement date is invalid.');
  const wall = instantToWallClock(draft.measuredAt, draft.tzOffsetMinutes);
  // Correcting a phone clock must not invalidate previously accepted history.
  // New entries still use the current-time check at the write boundary.
  const now = persisted ? new Date(Math.max(Date.now(), Date.parse(draft.measuredAt))) : undefined;
  const result = validateGlucoseInput({ value: draft.valueOriginal, unit: draft.unitOriginal, date: formatDisplayDate(wall), time: formatDisplayTime(wall), tzOffsetMinutes: draft.tzOffsetMinutes, tzName: draft.tzName, mealContext: draft.mealContext, note: draft.note || '' }, { now });
  if (!result.ok) throw new GlucoseRepositoryError('validation', result.error);
  if (draft.valueMgDl !== toMgDl(draft.valueOriginal, draft.unitOriginal)) throw new GlucoseRepositoryError('validation', 'The original value and canonical glucose conversion do not match.');
  if (!draft.source || !['manual', 'file', 'ocr', 'ble_meter', 'health_connect', 'healthkit', 'vendor_import'].includes(draft.source.type)) throw new GlucoseRepositoryError('validation', 'The reading source is invalid.');
}

export class LocalGlucoseRepository implements GlucoseRepository {
  readonly mode = 'local' as const;
  private rows: GlucoseReading[] | null = null;
  private queue: Promise<unknown> = Promise.resolve();
  private serial = 0;
  private storage: GlucoseStorage;
  constructor(storage: GlucoseStorage) { this.storage = storage; }

  private transaction<T>(work: () => Promise<T>): Promise<T> {
    const next = this.queue.then(work);
    this.queue = next.catch(() => undefined);
    return next;
  }
  private async load(): Promise<GlucoseReading[]> {
    if (this.rows) return this.rows;
    try {
      const text = await this.storage.read();
      if (text === null) return (this.rows = []);
      const data = JSON.parse(text);
      if (data.version !== 1 || !Array.isArray(data.readings) || data.readings.length > 20_000) throw new Error('invalid history format');
      const ids = new Set<string>();
      for (const row of data.readings) {
        if (typeof row.id !== 'string' || ids.has(row.id) || row.userId !== 'this-device' || !Number.isFinite(Date.parse(row.createdAt)) || !Number.isFinite(Date.parse(row.updatedAt))) throw new Error('invalid reading');
        checkDraft(row, true); ids.add(row.id);
      }
      return (this.rows = data.readings);
    } catch { throw new GlucoseRepositoryError('server', 'Your stored glucose history could not be read. It has not been overwritten. Retry or export/recover the app data before clearing storage.'); }
  }
  private async commit(rows: GlucoseReading[]) {
    try { await this.storage.write(JSON.stringify({ version: 1, readings: rows })); }
    catch { throw new GlucoseRepositoryError('server', 'The reading could not be saved on this phone. Check available storage and retry. Your previous history is unchanged.'); }
    this.rows = rows;
  }
  list(query: GlucoseQuery = {}): Promise<GlucoseReading[]> {
    return this.transaction(async () => clone((await this.load()).filter(r => (!query.from || r.measuredAt >= query.from) && (!query.to || r.measuredAt < query.to)).sort((a, b) => compareChronological(b, a)).slice(0, query.limit || 1000)));
  }
  create(draft: GlucoseDraft): Promise<GlucoseReading> {
    return this.createMany([draft]).then(r => {
      if (!r.saved.length) throw new GlucoseRepositoryError('conflict', 'This source reading has already been imported.');
      return r.saved[0];
    });
  }
  createMany(drafts: GlucoseDraft[]): Promise<{ saved: GlucoseReading[]; skipped: number }> {
    return this.transaction(async () => {
      const rows = await this.load(); const saved: GlucoseReading[] = []; let skipped = 0;
      const keys = new Set(rows.map(sourceKey).filter((k): k is string => k !== null));
      for (const d of drafts) {
        checkDraft(d); const key = sourceKey(d);
        if (key && keys.has(key)) { skipped++; continue; }
        const timestamp = new Date().toISOString();
        saved.push({ ...clone(d), id: `phone-${Date.now().toString(36)}-${(++this.serial).toString(36)}-${Math.random().toString(36).slice(2, 10)}`, userId: 'this-device', createdAt: timestamp, updatedAt: timestamp });
        if (key) keys.add(key);
      }
      if (rows.length + saved.length > 20_000) throw new GlucoseRepositoryError('validation', 'This phone history has reached 20,000 readings. Export older readings before adding more.');
      if (saved.length) await this.commit([...rows, ...saved]);
      return { saved: clone(saved), skipped };
    });
  }
  update(id: string, draft: GlucoseDraft): Promise<GlucoseReading> {
    return this.transaction(async () => {
      checkDraft(draft); const rows = await this.load(); const old = rows.find(r => r.id === id);
      if (!old) throw new GlucoseRepositoryError('not-found', 'This phone reading no longer exists.');
      const saved = { ...old, ...clone(draft), source: old.source, updatedAt: new Date().toISOString() };
      await this.commit(rows.map(r => r.id === id ? saved : r)); return clone(saved);
    });
  }
  remove(id: string): Promise<void> {
    return this.transaction(async () => {
      const rows = await this.load();
      if (!rows.some(r => r.id === id)) throw new GlucoseRepositoryError('not-found', 'This phone reading no longer exists.');
      await this.commit(rows.filter(r => r.id !== id));
    });
  }
}
