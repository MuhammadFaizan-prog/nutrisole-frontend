// Framework-free glucose state machine shared by web and native. React subscribes via
// useSyncExternalStore. Every state shown to the user comes from a real repository
// result; there is no fake "saved" path.
import type { GlucoseDraft, GlucoseReading, GlucoseRepository } from './types';
import { GlucoseRepositoryError } from './types';
import { DemoGlucoseRepository, SupabaseGlucoseRepository, UnconfiguredGlucoseRepository } from './repository';
import { SupabaseRest } from './supabaseRest';
import { compareChronological } from './time';
import type { GlucoseConfig } from './types';
import { demoSeed } from './demoSeed';
import { LocalGlucoseRepository } from './localRepository';

export type GlucoseStatus = 'unconfigured' | 'signed-out' | 'loading' | 'ready' | 'offline' | 'schema-missing' | 'error';
export type GlucoseBusy = null | 'signing-in' | 'saving' | 'deleting';
export type GlucoseSnapshot = {
  mode: GlucoseRepository['mode'];
  status: GlucoseStatus;
  /** Chronological ascending (oldest first). */
  readings: GlucoseReading[];
  error: string | null;
  busy: GlucoseBusy;
  email: string | null;
  lastLoadedAt: string | null;
  /** True when the visible list may be out of date (failed refresh after a successful load). */
  stale: boolean;
};
export type MutationResult = { ok: true; reading?: GlucoseReading } | { ok: false; error: string; kind: string };

export const initialGlucoseSnapshot = (mode: GlucoseSnapshot['mode'] = 'unconfigured'): GlucoseSnapshot => ({ mode, status: mode === 'unconfigured' ? 'unconfigured' : mode === 'demo' || mode === 'local' ? 'loading' : 'signed-out', readings: [], error: null, busy: null, email: null, lastLoadedAt: null, stale: false });

export class GlucoseStore {
  private snapshot: GlucoseSnapshot;
  private listeners = new Set<() => void>();
  private generation = 0;
  private revision = 0;
  private request = 0;
  readonly repository: GlucoseRepository;
  readonly client: SupabaseRest | null;
  constructor(repository: GlucoseRepository, client: SupabaseRest | null = null) {
    this.repository = repository; this.client = client;
    this.snapshot = initialGlucoseSnapshot(repository.mode);
    let userId = client?.currentSession()?.userId ?? null;
    client?.onSession(session => {
      const next = session?.userId ?? null;
      if (next !== userId || !session) { this.generation++; this.request++; userId = next; this.set({ status: 'signed-out', readings: [], email: session?.email ?? null, busy: null, error: null, lastLoadedAt: null, stale: false }); }
    });
  }
  getSnapshot = () => this.snapshot;
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; };
  private set(patch: Partial<GlucoseSnapshot>) { this.snapshot = { ...this.snapshot, ...patch }; this.listeners.forEach(l => l()); }
  private fail(error: unknown, keepReadings = true): MutationResult {
    const e = error instanceof GlucoseRepositoryError ? error : new GlucoseRepositoryError('server', 'Something went wrong. Please retry.');
    const status: GlucoseStatus = e.kind === 'offline' ? 'offline' : e.kind === 'unauthenticated' ? 'signed-out' : e.kind === 'schema-missing' ? 'schema-missing' : e.kind === 'unconfigured' ? 'unconfigured' : this.snapshot.status === 'ready' ? 'ready' : 'error';
    this.set({ status, error: e.message, stale: keepReadings && this.snapshot.readings.length > 0 && status !== 'ready' ? true : this.snapshot.stale, readings: status === 'signed-out' ? [] : this.snapshot.readings });
    return { ok: false, error: e.message, kind: e.kind };
  }

  async start() { if (this.repository.mode === 'demo' || this.repository.mode === 'local') return this.reload(); }

  async reload(): Promise<MutationResult> {
    if (this.repository.mode === 'unconfigured') { this.set({ status: 'unconfigured', error: null }); return { ok: false, error: 'unconfigured', kind: 'unconfigured' }; }
    if (this.repository.mode === 'supabase' && !this.client?.currentSession()) { this.set({ status: 'signed-out' }); return { ok: false, error: 'Sign in to view your readings.', kind: 'unauthenticated' }; }
    const generation = this.generation, revision = this.revision, request = ++this.request;
    const before = new Map(this.snapshot.readings.map(r => [r.id, r]));
    this.set({ status: this.snapshot.lastLoadedAt ? this.snapshot.status : 'loading', error: null });
    try {
      const rows = await this.repository.list({ limit: this.repository.mode === 'local' ? 20_000 : 1000 });
      if (generation !== this.generation || request !== this.request) return { ok: true };
      const merged = new Map(rows.map(r => [r.id, r]));
      if (revision !== this.revision) {
        const current = new Map(this.snapshot.readings.map(r => [r.id, r]));
        for (const id of before.keys()) if (!current.has(id)) merged.delete(id);
        for (const [id, row] of current) if (before.get(id) !== row) merged.set(id, row);
      }
      this.set({ status: 'ready', readings: [...merged.values()].sort(compareChronological), lastLoadedAt: new Date().toISOString(), stale: false, error: null });
      return { ok: true };
    } catch (error) { return generation !== this.generation || request !== this.request ? { ok: false, kind: 'unauthenticated', error: 'The account changed during this request.' } : this.fail(error); }
  }

  async signIn(email: string, password: string): Promise<MutationResult> {
    if (!this.client) return { ok: false, error: 'The database is not configured in this build.', kind: 'unconfigured' };
    if (this.snapshot.busy) return { ok: false, error: 'Please wait for the current action to finish.', kind: 'busy' };
    this.set({ busy: 'signing-in', error: null });
    try { const s = await this.client.signInWithPassword(email, password); this.set({ busy: null, email: s.email }); }
    catch (error) { this.set({ busy: null }); return this.fail(error); }
    return this.reload();
  }
  async signOut() { await this.client?.signOut(); }

  /** Create (editingId null) or update. Create waits for the server; update is optimistic with rollback. */
  async save(draft: GlucoseDraft, editingId: string | null = null): Promise<MutationResult> {
    if (this.snapshot.busy) return { ok: false, error: 'This reading is already being saved.', kind: 'busy' };
    this.set({ busy: 'saving', error: null });
    const generation = this.generation; this.revision++;
    const before = this.snapshot.readings;
    try {
      if (editingId) {
        const old = before.find(r => r.id === editingId);
        if (!old) throw new GlucoseRepositoryError('not-found', 'This reading is no longer in your history.');
        if (Math.floor(Date.parse(old.measuredAt) / 60_000) === Math.floor(Date.parse(draft.measuredAt) / 60_000)) draft = { ...draft, measuredAt: old.measuredAt };
        this.set({ readings: before.map(r => r.id === editingId ? { ...r, ...draft, source: r.source } : r).sort(compareChronological) });
      }
      const saved = editingId ? await this.repository.update(editingId, draft) : await this.repository.create(draft);
      if (generation !== this.generation) return { ok: false, kind: 'unauthenticated', error: 'The account changed during this action. Reload its history before retrying.' };
      this.revision++;
      this.set({ busy: null, readings: [...this.snapshot.readings.filter(r => r.id !== saved.id), saved].sort(compareChronological), status: 'ready' });
      return { ok: true, reading: saved };
    } catch (error) {
      if (generation !== this.generation) return { ok: false, kind: 'unauthenticated', error: 'The account changed during this action.' };
      this.set({ busy: null, readings: before });
      return this.fail(error);
    }
  }

  /**
   * Save reviewed imports atomically on the phone or with up to four cloud requests. A unique-index
   * conflict means the row was already imported and is counted as skipped, never retried.
   */
  async importMany(drafts: GlucoseDraft[]): Promise<{ saved: GlucoseReading[]; skipped: number; failed: { index: number; error: string }[]; stoppedEarly: string | null }> {
    if (this.snapshot.busy) return { saved: [], skipped: 0, failed: [], stoppedEarly: 'Please wait for the current action to finish.' };
    this.set({ busy: 'saving', error: null });
    const generation = this.generation; this.revision++;
    const saved: GlucoseReading[] = []; const failed: { index: number; error: string }[] = []; let skipped = 0; let stoppedEarly: string | null = null;
    if (this.repository.createMany) {
      try {
        const result = await this.repository.createMany(drafts);
        if (generation !== this.generation) return { saved: [], skipped: 0, failed: [], stoppedEarly: 'The account changed during this action.' };
        this.revision++;
        this.set({ busy: null, readings: [...this.snapshot.readings, ...result.saved].sort(compareChronological), status: 'ready', error: null });
        return { ...result, failed, stoppedEarly };
      } catch (error) {
        if (generation !== this.generation) return { saved: [], skipped: 0, failed: [], stoppedEarly: 'The account changed during this action.' };
        const result = this.fail(error); this.set({ busy: null });
        const message = result.ok ? 'Could not save readings.' : result.error;
        return { saved: [], skipped: 0, failed: drafts.map((_, index) => ({ index, error: message })), stoppedEarly: message };
      }
    }
    let next = 0;
    const worker = async () => {
      while (next < drafts.length && !stoppedEarly && generation === this.generation) {
        const index = next++;
        try {
          const row = await this.repository.create(drafts[index]);
          if (generation !== this.generation) return;
          saved.push(row); this.revision++;
          this.set({ readings: [...this.snapshot.readings.filter(r => r.id !== row.id), row].sort(compareChronological), status: 'ready' });
        } catch (error) {
          const e = error instanceof GlucoseRepositoryError ? error : new GlucoseRepositoryError('server', 'Something went wrong.');
          if (e.kind === 'conflict') { skipped++; continue; }
          failed.push({ index, error: e.message });
          if (['offline', 'unauthenticated', 'unconfigured', 'schema-missing', 'forbidden'].includes(e.kind)) stoppedEarly = e.message;
        }
      }
    };
    await Promise.all(Array.from({ length: Math.min(4, drafts.length) }, worker));
    failed.sort((a, b) => a.index - b.index);
    if (generation !== this.generation) return { saved: [], skipped, failed, stoppedEarly: 'The account changed during this action.' };
    this.revision++;
    this.set({ busy: null, readings: [...this.snapshot.readings.filter(r => !saved.some(n => n.id === r.id)), ...saved].sort(compareChronological), status: saved.length ? 'ready' : this.snapshot.status });
    return { saved, skipped, failed, stoppedEarly };
  }

  /** Optimistic delete with rollback on failure. */
  async remove(id: string): Promise<MutationResult> {
    if (this.snapshot.busy) return { ok: false, error: 'Please wait for the current action to finish.', kind: 'busy' };
    const before = this.snapshot.readings;
    const generation = this.generation; this.revision++;
    this.set({ busy: 'deleting', error: null, readings: before.filter(r => r.id !== id) });
    try { await this.repository.remove(id); if (generation !== this.generation) return { ok: false, kind: 'unauthenticated', error: 'The account changed during this action.' }; this.revision++; this.set({ busy: null }); return { ok: true }; }
    catch (error) { if (generation !== this.generation) return { ok: false, kind: 'unauthenticated', error: 'The account changed during this action.' }; this.set({ busy: null, readings: before }); return this.fail(error); }
  }
}

export function createGlucoseStore(config: GlucoseConfig): GlucoseStore {
  if (config.demo) return new GlucoseStore(new DemoGlucoseRepository(config.demoSeed ? demoSeed() : []));
  if (config.localStorage) return new GlucoseStore(new LocalGlucoseRepository(config.localStorage));
  if (config.supabaseUrl && config.supabaseAnonKey) { const client = new SupabaseRest(config.supabaseUrl, config.supabaseAnonKey); return new GlucoseStore(new SupabaseGlucoseRepository(client), client); }
  return new GlucoseStore(new UnconfiguredGlucoseRepository());
}
