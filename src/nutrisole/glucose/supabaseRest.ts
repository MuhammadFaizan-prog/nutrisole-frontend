// Minimal Supabase Auth + PostgREST client built on fetch (no new dependency).
// Session tokens live in memory only: nothing sensitive is written to localStorage,
// AsyncStorage or logs. After an app restart the user signs in again; the readings
// themselves persist in Postgres.
import { GlucoseRepositoryError } from './types';

export type Session = { accessToken: string; refreshToken: string; expiresAt: number; userId: string; email: string | null };
export type FetchLike = (input: string, init?: { method?: string; headers?: Record<string, string>; body?: string }) => Promise<{ ok: boolean; status: number; json(): Promise<unknown>; text(): Promise<string> }>;

export class SupabaseRest {
  readonly url: string;
  private readonly anonKey: string;
  private readonly fetcher: FetchLike;
  private session: Session | null = null;
  private listeners = new Set<(s: Session | null) => void>();
  constructor(url: string, anonKey: string, fetcher?: FetchLike) {
    this.url = url.replace(/\/$/, ''); this.anonKey = anonKey;
    this.fetcher = fetcher ?? ((input, init) => fetch(input, init) as unknown as ReturnType<FetchLike>);
  }
  currentSession() { return this.session; }
  onSession(listener: (s: Session | null) => void) { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; }
  private setSession(s: Session | null) { this.session = s; this.listeners.forEach(l => l(s)); }
  /** For tests / isolated harnesses that mint a token outside GoTrue. */
  adoptSession(s: Session | null) { this.setSession(s); }

  private async send(path: string, init: { method?: string; headers?: Record<string, string>; body?: string }) {
    try { return await this.fetcher(`${this.url}${path}`, init); }
    catch { throw new GlucoseRepositoryError('offline', 'NutriSole could not reach the database. Check your connection and retry.'); }
  }

  async signInWithPassword(email: string, password: string): Promise<Session> {
    const res = await this.send('/auth/v1/token?grant_type=password', { method: 'POST', headers: { apikey: this.anonKey, 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) });
    if (!res.ok) throw new GlucoseRepositoryError(res.status === 400 || res.status === 401 ? 'unauthenticated' : 'server', res.status === 400 || res.status === 401 ? 'Email or password is incorrect, or the email is not confirmed yet.' : 'Sign-in is unavailable right now.');
    const session = toSession(await res.json());
    this.setSession(session); return session;
  }

  async refresh(): Promise<boolean> {
    if (!this.session) return false;
    const res = await this.send('/auth/v1/token?grant_type=refresh_token', { method: 'POST', headers: { apikey: this.anonKey, 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: this.session.refreshToken }) });
    if (!res.ok) { this.setSession(null); return false; }
    this.setSession(toSession(await res.json())); return true;
  }

  async signOut() {
    const s = this.session; this.setSession(null);
    if (s) { try { await this.fetcher(`${this.url}/auth/v1/logout`, { method: 'POST', headers: { apikey: this.anonKey, Authorization: `Bearer ${s.accessToken}` } }); } catch { /* local sign-out already done */ } }
  }

  /** PostgREST request as the signed-in user. Retries once after a token refresh. */
  async rest(path: string, init: { method?: string; body?: unknown; prefer?: string } = {}, retried = false): Promise<unknown> {
    if (!this.session) throw new GlucoseRepositoryError('unauthenticated', 'Sign in to view and save your glucose readings.');
    const headers: Record<string, string> = { apikey: this.anonKey, Authorization: `Bearer ${this.session.accessToken}`, Accept: 'application/json' };
    if (init.body !== undefined) headers['Content-Type'] = 'application/json';
    if (init.prefer) headers.Prefer = init.prefer;
    const res = await this.send(`/rest/v1${path}`, { method: init.method || 'GET', headers, body: init.body === undefined ? undefined : JSON.stringify(init.body) });
    if (res.status === 401 && !retried) { if (await this.refresh()) return this.rest(path, init, true); throw new GlucoseRepositoryError('unauthenticated', 'Your session ended. Sign in again.'); }
    if (!res.ok) throw await restError(res);
    if (res.status === 204) return null;
    const text = await res.text(); return text ? JSON.parse(text) : null;
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
