import type { GlucoseDraft, GlucoseQuery, GlucoseReading, GlucoseRepository, GlucoseUnit, MealContext, GlucoseSourceType } from './types';
import { GlucoseRepositoryError } from './types';
import type { SupabaseRest } from './supabaseRest';
import { compareChronological } from './time';
import { toMgDl } from './units';

/** Row shape of public.glucose_readings (see supabase/migrations/*_glucose_readings.sql). */
export type GlucoseRow = {
  id: string; user_id: string; measured_at: string; tz_offset_minutes: number; tz_name: string | null;
  value_original: number | string; unit_original: GlucoseUnit; value_mg_dl: number | string;
  meal_context: MealContext; note: string | null; source_type: GlucoseSourceType; source_provider: string | null;
  source_device: string | null; source_record_id: string | null; source_meta?: Record<string, unknown> | null; import_batch_id?: string | null; dedupe_key?: string | null; created_at: string; updated_at: string;
};
const columns = 'id,user_id,measured_at,tz_offset_minutes,tz_name,value_original,unit_original,value_mg_dl,meal_context,note,source_type,source_provider,source_device,source_record_id,source_meta,import_batch_id,dedupe_key,created_at,updated_at';

export function rowToReading(row: GlucoseRow): GlucoseReading {
  return {
    id: row.id, userId: row.user_id, measuredAt: new Date(row.measured_at).toISOString(), tzOffsetMinutes: row.tz_offset_minutes, tzName: row.tz_name,
    valueOriginal: String(row.value_original), unitOriginal: row.unit_original, valueMgDl: Number(row.value_mg_dl), mealContext: row.meal_context, note: row.note,
    source: { type: row.source_type, provider: row.source_provider, device: row.source_device, recordId: row.source_record_id, meta: row.source_meta ?? null, batchId: row.import_batch_id ?? null, dedupeKey: row.dedupe_key ?? null },
    createdAt: new Date(row.created_at).toISOString(), updatedAt: new Date(row.updated_at).toISOString(),
  };
}

/** Insert/update payload. user_id comes from auth.uid() in the database default + RLS check. */
export function draftToRow(draft: GlucoseDraft) {
  return {
    measured_at: draft.measuredAt, tz_offset_minutes: draft.tzOffsetMinutes, tz_name: draft.tzName,
    value_original: draft.valueOriginal, unit_original: draft.unitOriginal, // value_mg_dl is a generated column
    meal_context: draft.mealContext, note: draft.note,
    source_type: draft.source.type, source_provider: draft.source.provider, source_device: draft.source.device, source_record_id: draft.source.recordId,
    ...(draft.source.type === 'manual' ? {} : { source_meta: draft.source.meta ?? null, import_batch_id: draft.source.batchId ?? null, dedupe_key: draft.source.dedupeKey ?? null }),
  };
}

export class SupabaseGlucoseRepository implements GlucoseRepository {
  readonly mode = 'supabase' as const;
  private readonly client: SupabaseRest;
  constructor(client: SupabaseRest) { this.client = client; }
  async list(query: GlucoseQuery = {}) {
    const params = [`select=${columns}`, 'order=measured_at.desc,created_at.desc,id.desc', `limit=${Math.min(Math.max(query.limit || 500, 1), 1000)}`];
    if (query.from) params.push(`measured_at=gte.${encodeURIComponent(query.from)}`);
    if (query.to) params.push(`measured_at=lt.${encodeURIComponent(query.to)}`);
    const rows = await this.client.rest(`/glucose_readings?${params.join('&')}`) as GlucoseRow[];
    return rows.map(rowToReading);
  }
  async create(draft: GlucoseDraft) {
    const rows = await this.client.rest(`/glucose_readings?select=${columns}`, { method: 'POST', body: draftToRow(draft), prefer: 'return=representation' }) as GlucoseRow[];
    if (!rows?.[0]) throw new GlucoseRepositoryError('server', 'The reading was not returned after saving.');
    return rowToReading(rows[0]);
  }
  async update(id: string, draft: GlucoseDraft) {
    const { source_type: _t, source_provider: _p, source_device: _d, source_record_id: _r, source_meta: _m, import_batch_id: _b, dedupe_key: _k, ...editable } = draftToRow(draft) as ReturnType<typeof draftToRow> & { source_meta?: unknown; import_batch_id?: unknown; dedupe_key?: unknown };
    const rows = await this.client.rest(`/glucose_readings?id=eq.${encodeURIComponent(id)}&select=${columns}`, { method: 'PATCH', body: editable, prefer: 'return=representation' }) as GlucoseRow[];
    if (!rows?.[0]) throw new GlucoseRepositoryError('not-found', 'This reading no longer exists or belongs to another account.');
    return rowToReading(rows[0]);
  }
  async remove(id: string) {
    const rows = await this.client.rest(`/glucose_readings?id=eq.${encodeURIComponent(id)}&select=id`, { method: 'DELETE', prefer: 'return=representation' }) as { id: string }[];
    if (!rows?.length) throw new GlucoseRepositoryError('not-found', 'This reading no longer exists or belongs to another account.');
  }
}

/**
 * Explicit demo flag only (VITE_GLUCOSE_DEMO=1 or ?glucoseDemo). Records live in memory
 * for this session and the UI labels them "Demo · not saved". Never used as a fallback.
 */
export class DemoGlucoseRepository implements GlucoseRepository {
  readonly mode = 'demo' as const;
  private rows: GlucoseReading[] = [];
  private serial = 0;
  constructor(seed: GlucoseReading[] = []) { this.rows = [...seed]; }
  async list(query: GlucoseQuery = {}) {
    return this.rows.filter(r => (!query.from || r.measuredAt >= query.from) && (!query.to || r.measuredAt < query.to)).sort((a, b) => compareChronological(b, a)).slice(0, query.limit || 500).map(r => ({ ...r, source: { ...r.source } }));
  }
  async create(draft: GlucoseDraft) {
    const now = new Date().toISOString();
    const reading: GlucoseReading = { ...draft, source: { ...draft.source }, id: `demo-${++this.serial}-${Date.now().toString(36)}`, userId: 'demo-session', valueMgDl: toMgDl(draft.valueOriginal, draft.unitOriginal), createdAt: now, updatedAt: now };
    this.rows.push(reading); return { ...reading };
  }
  async update(id: string, draft: GlucoseDraft) {
    const i = this.rows.findIndex(r => r.id === id); if (i < 0) throw new GlucoseRepositoryError('not-found', 'This demo reading no longer exists.');
    const old = this.rows[i];
    const next: GlucoseReading = { ...old, ...draft, source: old.source, valueMgDl: toMgDl(draft.valueOriginal, draft.unitOriginal), updatedAt: new Date().toISOString() };
    this.rows[i] = next; return { ...next };
  }
  async remove(id: string) {
    const before = this.rows.length; this.rows = this.rows.filter(r => r.id !== id);
    if (this.rows.length === before) throw new GlucoseRepositoryError('not-found', 'This demo reading no longer exists.');
  }
}

/** Used when no database is configured: every call reports the honest state. */
export class UnconfiguredGlucoseRepository implements GlucoseRepository {
  readonly mode = 'unconfigured' as const;
  private fail(): never { throw new GlucoseRepositoryError('unconfigured', 'The NutriSole database is not configured in this build, so readings cannot be saved.'); }
  async list(): Promise<GlucoseReading[]> { return this.fail(); }
  async create(): Promise<GlucoseReading> { return this.fail(); }
  async update(): Promise<GlucoseReading> { return this.fail(); }
  async remove(): Promise<void> { return this.fail(); }
}
