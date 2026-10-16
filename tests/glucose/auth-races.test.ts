import test from 'node:test';
import assert from 'node:assert/strict';
import { SupabaseRest, type FetchLike, type Session } from '../../src/nutrisole/glucose/supabaseRest.ts';
const session = (id: string): Session => ({ userId: id, accessToken: id, refreshToken: `refresh-${id}`, expiresAt: 0, email: null });
const response = (status: number, body: unknown) => ({ ok: status < 400, status, json: async () => body, text: async () => JSON.stringify(body) });

test('a late 401 for account A never replays its write as account B', async () => {
  let release!: () => void; const calls: string[] = [];
  const fetcher: FetchLike = async (url, init) => {
    calls.push(`${url}|${init?.headers?.Authorization}`);
    if (calls.length === 1) { await new Promise<void>(r => { release = r; }); return response(401, {}); }
    return response(200, { access_token: 'B2', refresh_token: 'B-r2', user: { id: 'B' } });
  };
  const client = new SupabaseRest('https://example.supabase.co', 'anon', fetcher); client.adoptSession(session('A'));
  const pending = client.rest('/glucose_readings', { method: 'POST', body: { value_original: 110 } });
  client.adoptSession(session('B')); release(); await assert.rejects(pending, /account|session/i);
  assert.equal(calls.length, 1);
});

test('concurrent expired requests share one refresh and cannot invalidate each other', async () => {
  let refreshes = 0;
  const fetcher: FetchLike = async (url, init) => {
    if (url.includes('refresh_token')) { refreshes++; await new Promise(r => setTimeout(r, 5)); return response(200, { access_token: 'fresh', refresh_token: 'rotated', user: { id: 'A' } }); }
    return response(init?.headers?.Authorization === 'Bearer fresh' ? 200 : 401, []);
  };
  const client = new SupabaseRest('https://example.supabase.co', 'anon', fetcher); client.adoptSession(session('A'));
  await Promise.all(Array.from({ length: 4 }, () => client.rest('/glucose_readings')));
  assert.equal(refreshes, 1); assert.equal(client.currentSession()?.accessToken, 'fresh');
});

test('signing out during refresh cannot restore the old account', async () => {
  let release!: () => void;
  const fetcher: FetchLike = async () => { await new Promise<void>(r => { release = r; }); return response(200, { access_token: 'fresh', refresh_token: 'rotated', user: { id: 'A' } }); };
  const client = new SupabaseRest('https://example.supabase.co', 'anon', fetcher); client.adoptSession(session('A'));
  const refresh = client.refresh(); client.adoptSession(null); release(); await refresh;
  assert.equal(client.currentSession(), null);
});
