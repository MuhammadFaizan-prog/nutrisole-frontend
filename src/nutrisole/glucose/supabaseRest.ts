// Auth + PostgREST. Native sessions use Android Keystore-backed encrypted storage.
import { GlucoseRepositoryError, type GlucoseStorage } from './types';

export type Session = { accessToken: string; refreshToken: string; expiresAt: number; userId: string; email: string | null };
export type FetchLike = (input: string, init?: { method?: string; headers?: Record<string, string>; body?: string }) => Promise<{ ok: boolean; status: number; json(): Promise<unknown>; text(): Promise<string> }>;

export class SupabaseRest {
  readonly url: string;
  private readonly anonKey: string;
  private readonly fetcher: FetchLike;
  private session: Session | null = null;
  private generation = 0;
  private refreshing: { generation: number; promise: Promise<boolean> } | null = null;
  private listeners = new Set<(s: Session | null) => void>();
  private readonly storage?: GlucoseStorage;
  private persisting: Promise<void> = Promise.resolve();
  private initialized: Promise<void> | null = null;
  constructor(url: string, anonKey: string, fetcher?: FetchLike, storage?: GlucoseStorage) {
    this.url = url.replace(/\/$/, ''); this.anonKey = anonKey;
    this.fetcher = fetcher ?? ((input, init) => fetch(input, init) as unknown as ReturnType<FetchLike>);
    this.storage = storage;
  }
  currentSession() { return this.session; }
  onSession(listener: (s: Session | null) => void) { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; }
  private setSession(s: Session | null, preserveGeneration = false) {
    if (!preserveGeneration) this.generation++; this.session = s;
    if (this.storage) {
      const value = s ? JSON.stringify(s) : '';
      this.persisting = this.persisting.catch(() => {}).then(() => this.storage!.write(value));
      // Consumers await flushSession to surface storage failure; avoid an unhandled rejection.
      void this.persisting.catch(() => {});
    }
    this.listeners.forEach(l => l(s));
  }
  async flushSession() { await this.persisting; }
  async initialize() {
    return this.initialized ??= (async () => {
      if (!this.storage) return;
      const generation = this.generation;
      const raw = await this.storage.read();
      if (!raw || generation !== this.generation) return;
      let saved: Session;
      try {
        saved = JSON.parse(raw) as Session;
        if (!saved.accessToken || !saved.refreshToken || !saved.userId || !Number.isFinite(saved.expiresAt)) throw new Error();
      } catch { await this.storage.write(''); return; }
      this.setSession(saved);
      await this.maintainSession();
    })();
  }
  async maintainSession() { if (this.session && this.session.expiresAt < Date.now() + 90_000) await this.refresh(); }
  /** For tests / isolated harnesses that mint a token outside GoTrue. */
  adoptSession(s: Session | null) { this.setSession(s); }

  private async send(path: string, init: { method?: string; headers?: Record<string, string>; body?: string }) {
    try { return await this.fetcher(`${this.url}${path}`, init); }
    catch { throw new GlucoseRepositoryError('offline', 'NutriSole could not reach the database. Check your connection and retry.'); }
  }

  async signInWithPassword(email: string, password: string): Promise<Session> {
    const generation = ++this.generation;
    const res = await this.send('/auth/v1/token?grant_type=password', { method: 'POST', headers: { apikey: this.anonKey, 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) });
    if (!res.ok) throw new GlucoseRepositoryError(res.status === 400 || res.status === 401 ? 'unauthenticated' : 'server', res.status === 400 || res.status === 401 ? 'Email or password is incorrect, or the email is not confirmed yet.' : 'Sign-in is unavailable right now.');
    const session = toSession(await res.json());
    if (generation !== this.generation) throw new GlucoseRepositoryError('unauthenticated', 'This sign-in attempt was cancelled by an account change.');
    this.setSession(session, true); await this.flushSession(); return session;
  }

  async signUp(email: string, password: string, name: string): Promise<boolean> {
    const generation = ++this.generation;
    const res = await this.send('/auth/v1/signup', { method: 'POST', headers: { apikey: this.anonKey, 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password, data: { full_name: name } }) });
    if (!res.ok) throw new GlucoseRepositoryError('server', res.status === 429 ? 'Too many attempts. Please try again shortly.' : 'Could not create the account. Check your email and password, then retry.');
    const body = await res.json() as { access_token?: string };
    if (generation !== this.generation) throw new GlucoseRepositoryError('unauthenticated', 'The account changed. Please try again.');
    if (body.access_token) { this.setSession(toSession(body), true); await this.flushSession(); return true; }
    return false;
  }

  async requestEmail(email: string, kind: 'recover' | 'resend') {
    const res = await this.send(`/auth/v1/${kind}`, { method: 'POST', headers: { apikey: this.anonKey, 'Content-Type': 'application/json' }, body: JSON.stringify(kind === 'resend' ? { email, type: 'signup' } : { email }) });
    if (!res.ok) throw new GlucoseRepositoryError('server', res.status === 429 ? 'Please wait before requesting another email.' : 'Could not send the email. Please retry.');
  }

  async refresh(): Promise<boolean> {
    const session = this.session, generation = this.generation;
    if (!session) return false;
    if (this.refreshing?.generation === generation) return this.refreshing.promise;
    const promise = (async () => {
      const res = await this.send('/auth/v1/token?grant_type=refresh_token', { method: 'POST', headers: { apikey: this.anonKey, 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: session.refreshToken }) });
      if (generation !== this.generation) return false;
      if (!res.ok) { if (res.status === 400 || res.status === 401) { this.setSession(null); await this.flushSession(); return false; } throw new GlucoseRepositoryError('server', 'Could not refresh sign-in. Please retry.'); }
      const fresh = toSession(await res.json());
      if (generation !== this.generation) return false;
      if (fresh.userId !== session.userId) throw new GlucoseRepositoryError('unauthenticated', 'The refresh response belongs to a different account. Sign in again.');
      this.setSession(fresh, true); await this.flushSession(); return true;
    })();
    this.refreshing = { generation, promise };
    try { return await promise; }
    finally { if (this.refreshing?.promise === promise) this.refreshing = null; }
  }

  async signOut() {
    const s = this.session; this.setSession(null);
    await this.flushSession();
    if (s) { try { await this.fetcher(`${this.url}/auth/v1/logout`, { method: 'POST', headers: { apikey: this.anonKey, Authorization: `Bearer ${s.accessToken}` } }); } catch { /* local sign-out already done */ } }
  }

  /** Private account topic carries only invalidations, never health values. */
  watchChanges(changed: () => void, connection: (ready: boolean) => void): () => void {
    let disposed = false; let stop: (() => void) | undefined;
    void import('@supabase/realtime-js').then(({ RealtimeClient }) => {
      if (disposed || !this.session) return;
      const userId = this.session.userId;
      const realtime = new RealtimeClient(`${this.url}/realtime/v1`, { params: { apikey: this.anonKey }, accessToken: async () => this.session?.userId === userId ? this.session.accessToken : null });
      const off = this.onSession(s => { if (s?.userId === userId) void realtime.setAuth().catch(() => connection(false)); else { void realtime.disconnect(); connection(false); } });
      const channel = realtime.channel(`glucose:${userId}`, { config: { private: true } }).on('broadcast', { event: 'changed' }, changed);
      channel.subscribe(status => { if (disposed) return; connection(status === 'SUBSCRIBED'); if (status === 'SUBSCRIBED') changed(); });
      stop = () => { off(); void realtime.removeChannel(channel); void realtime.disconnect(); };
      if (disposed) stop();
    }).catch(() => connection(false));
    return () => { disposed = true; stop?.(); };
  }

  /** PostgREST request as the signed-in user. Retries once after a token refresh. */
  async rest(path: string, init: { method?: string; body?: unknown; prefer?: string } = {}): Promise<unknown> {
    return this.requestRest(path, init, this.generation, false);
  }
  private async requestRest(path: string, init: { method?: string; body?: unknown; prefer?: string }, generation: number, retried: boolean): Promise<unknown> {
    if (!this.session || generation !== this.generation) throw new GlucoseRepositoryError('unauthenticated', 'Your account or session changed. Sign in and reload before retrying.');
    const headers: Record<string, string> = { apikey: this.anonKey, Authorization: `Bearer ${this.session.accessToken}`, Accept: 'application/json' };
    if (init.body !== undefined) headers['Content-Type'] = 'application/json';
    if (init.prefer) headers.Prefer = init.prefer;
    const res = await this.send(`/rest/v1${path}`, { method: init.method || 'GET', headers, body: init.body === undefined ? undefined : JSON.stringify(init.body) });
    if (generation !== this.generation) throw new GlucoseRepositoryError('unauthenticated', 'The account changed during this request. Reload its history before retrying.');
    if (res.status === 401 && !retried) { if (await this.refresh()) return this.requestRest(path, init, generation, true); throw new GlucoseRepositoryError('unauthenticated', 'Your session ended. Sign in again.'); }
    if (!res.ok) throw await restError(res);
    if (res.status === 204) return null;
    const text = await res.text();
    if (generation !== this.generation) throw new GlucoseRepositoryError('unauthenticated', 'The account changed during this request.');
    return text ? JSON.parse(text) : null;
  }
}

function toSession(body: unknown): Session {
  const b = body as { access_token?: string; refresh_token?: string; expires_in?: number; user?: { id?: string; email?: string } };
  if (!b?.access_token || !b.refresh_token || !b.user?.id) throw new GlucoseRepositoryError('server', 'Unexpected sign-in response.');
  return { accessToken: b.access_token, refreshToken: b.refresh_token, expiresAt: Date.now() + (b.expires_in || 3600) * 1000, userId: b.user.id, email: b.user.email || null };
}

async function restError(res: { status: number; text(): Promise<string> }) {
  let code = ''; try { code = (JSON.parse(await res.text()) as { code?: string }).code || ''; } catch { /* body not JSON */ }
  // Error messages never echo request bodies (they may contain health values).
  if (code === '42P01' || code === 'PGRST205' || res.status === 404 && code.startsWith('PGRST')) return new GlucoseRepositoryError('schema-missing', 'The glucose table is not set up in the database yet (migration pending approval).');
  if (code === '42501' || res.status === 403) return new GlucoseRepositoryError('forbidden', 'This account is not allowed to change that reading.');
  if (code === '23505' || res.status === 409) return new GlucoseRepositoryError('conflict', 'This reading was already imported.');
  if (code === '23514' || code === '22P02' || code === 'P0001' || res.status === 400) return new GlucoseRepositoryError('validation', 'The database rejected this reading. Check the value, unit and time.');
  return new GlucoseRepositoryError('server', 'The database returned an error. Please retry.');
}
