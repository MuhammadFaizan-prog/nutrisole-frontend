import test from 'node:test';
import assert from 'node:assert/strict';
import { SupabaseRest, type FetchLike } from '../../src/nutrisole/glucose/supabaseRest.ts';
import { SupabaseGlucoseRepository, draftToRow } from '../../src/nutrisole/glucose/repository.ts';
import { validateGlucoseInput } from '../../src/nutrisole/glucose/validation.ts';

type Call = { url: string; method: string; headers: Record<string, string>; body?: string };
function fakeFetch(responses: { status: number; body?: unknown }[], calls: Call[]): FetchLike {
  return async (url, init = {}) => { calls.push({ url, method: init.method || 'GET', headers: init.headers || {}, body: init.body }); const r = responses.shift() || { status: 500 }; return { ok: r.status < 300, status: r.status, json: async () => r.body, text: async () => r.body === undefined ? '' : JSON.stringify(r.body) }; };
}
const row = { id: '11111111-1111-1111-1111-111111111111', user_id: 'u1', measured_at: '2026-10-16T03:15:00+00:00', tz_offset_minutes: 300, tz_name: 'Asia/Karachi', value_original: 6.1, unit_original: 'mmol/L', value_mg_dl: 109.91, meal_context: 'fasting', note: null, source_type: 'manual', source_provider: null, source_device: null, source_record_id: null, created_at: '2026-10-16T04:00:00+00:00', updated_at: '2026-10-16T04:00:00+00:00' };
const d = (() => { const r = validateGlucoseInput({ value: '6.1', unit: 'mmol/L', date: 'Oct 16, 2026', time: '8:15 AM', tzOffsetMinutes: 300, tzName: 'Asia/Karachi', mealContext: 'fasting' }, { now: new Date('2026-10-17T00:00:00Z') }); if (!r.ok) throw new Error(); return r.draft; })();

test('sign-in uses the anon key only; REST calls carry the user JWT; payload never sets user_id or value_mg_dl', async () => {
  const calls: Call[] = [];
  const client = new SupabaseRest('https://abc.supabase.co', 'anon-key', fakeFetch([{ status: 200, body: { access_token: 'jwt-a', refresh_token: 'ref', expires_in: 3600, user: { id: 'u1', email: 'a@example.org' } } }, { status: 201, body: [row] }, { status: 200, body: [row] }], calls));
  await client.signInWithPassword('a@example.org', 'pw-123456');
  const repo = new SupabaseGlucoseRepository(client);
  const saved = await repo.create(d); assert.equal(saved.valueOriginal, '6.1'); assert.equal(saved.unitOriginal, 'mmol/L'); assert.equal(saved.valueMgDl, 109.91);
  const list = await repo.list({ from: '2026-10-01T00:00:00.000Z' });
  assert.equal(list.length, 1);
  assert.equal(calls[0].headers.apikey, 'anon-key'); assert.ok(!('Authorization' in calls[0].headers));
  assert.equal(calls[1].headers.Authorization, 'Bearer jwt-a'); assert.equal(calls[1].headers.Prefer, 'return=representation');
  const body = JSON.parse(calls[1].body!); assert.ok(!('user_id' in body)); assert.ok(!('value_mg_dl' in body)); assert.equal(body.value_original, '6.1');
  assert.match(calls[2].url, /order=measured_at\.desc/); assert.match(calls[2].url, /measured_at=gte\./);
  assert.deepEqual(Object.keys(draftToRow(d)).sort(), ['meal_context', 'measured_at', 'note', 'source_device', 'source_provider', 'source_record_id', 'source_type', 'tz_name', 'tz_offset_minutes', 'unit_original', 'value_original']);
});

test('expired token refreshes once, then a missing table and RLS denials map to honest errors', async () => {
  const calls: Call[] = [];
  const client = new SupabaseRest('https://abc.supabase.co', 'anon', fakeFetch([{ status: 401 }, { status: 200, body: { access_token: 'jwt-b', refresh_token: 'ref2', user: { id: 'u1' } } }, { status: 404, body: { code: 'PGRST205' } }, { status: 403, body: { code: '42501' } }, { status: 200, body: [] }], calls));
  client.adoptSession({ accessToken: 'old', refreshToken: 'ref', expiresAt: 0, userId: 'u1', email: null });
  const repo = new SupabaseGlucoseRepository(client);
  await assert.rejects(repo.list(), (e: Error & { kind?: string }) => e.kind === 'schema-missing');
  assert.equal(calls[2].headers.Authorization, 'Bearer jwt-b');
  await assert.rejects(repo.create(d), (e: Error & { kind?: string }) => e.kind === 'forbidden');
  await assert.rejects(repo.remove('other-users-row'), (e: Error & { kind?: string }) => e.kind === 'not-found', 'RLS-hidden rows delete nothing');
});

test('network failure is reported as offline and error text never echoes health values', async () => {
  const client = new SupabaseRest('https://abc.supabase.co', 'anon', async () => { throw new TypeError('Failed to fetch'); });
  client.adoptSession({ accessToken: 't', refreshToken: 'r', expiresAt: 0, userId: 'u1', email: null });
  await assert.rejects(new SupabaseGlucoseRepository(client).create(d), (e: Error & { kind?: string }) => e.kind === 'offline' && !e.message.includes('6.1'));
});
