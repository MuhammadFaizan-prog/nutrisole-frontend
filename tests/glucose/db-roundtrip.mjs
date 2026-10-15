// Isolated end-to-end round trip: the app's real SupabaseRest + SupabaseGlucoseRepository
// against a LOCAL PostgREST in front of the LOCAL Postgres with the glucose migration + RLS.
// Two users are identified by locally signed HS256 JWTs (Supabase's own JWT shape).
// This proves the client ↔ PostgREST ↔ RLS contract; it is not a test of the live project.
// Usage: node --experimental-strip-types --import ./tests/glucose/resolve-ts.mjs tests/glucose/db-roundtrip.mjs <pgPort> <postgrestBin>
import { spawn } from 'node:child_process';
import http from 'node:http';
import crypto from 'node:crypto';
import fs from 'node:fs';
import assert from 'node:assert/strict';
const [pgPort, postgrestBin] = process.argv.slice(2);
const secret = crypto.randomBytes(32).toString('hex');
const restPort = 53000 + Math.floor(Math.random() * 1000); const proxyPort = restPort + 1;
const conf = `/tmp/glucose-postgrest-${restPort}.conf`;
fs.writeFileSync(conf, `db-uri = "postgres://authenticator:local-test-only@127.0.0.1:${pgPort}/glucose_test"\ndb-schemas = "public"\ndb-anon-role = "anon"\njwt-secret = "${secret}"\nserver-port = ${restPort}\nserver-host = "127.0.0.1"\nlog-level = "error"\n`);
const pgrst = spawn(postgrestBin, [conf], { stdio: ['ignore', 'ignore', 'inherit'] });
const b64 = o => Buffer.from(JSON.stringify(o)).toString('base64url');
const jwt = sub => { const h = b64({ alg: 'HS256', typ: 'JWT' }); const p = b64({ sub, role: 'authenticated', aud: 'authenticated', exp: Math.floor(Date.now() / 1000) + 600 }); return `${h}.${p}.${crypto.createHmac('sha256', secret).update(`${h}.${p}`).digest('base64url')}`; };
// Supabase serves PostgREST under /rest/v1; strip it for the local server.
const proxy = http.createServer((req, res) => { const up = http.request({ host: '127.0.0.1', port: restPort, path: req.url.replace(/^\/rest\/v1/, ''), method: req.method, headers: req.headers }, r => { res.writeHead(r.statusCode, r.headers); r.pipe(res); }); req.pipe(up); up.on('error', () => { res.writeHead(502); res.end(); }); }).listen(proxyPort);
const { SupabaseRest } = await import('../../src/nutrisole/glucose/supabaseRest.ts');
const { SupabaseGlucoseRepository } = await import('../../src/nutrisole/glucose/repository.ts');
const { GlucoseStore } = await import('../../src/nutrisole/glucose/store.ts');
const { validateGlucoseInput } = await import('../../src/nutrisole/glucose/validation.ts');
const A = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', B = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
const session = sub => ({ accessToken: jwt(sub), refreshToken: 'n/a', expiresAt: Date.now() + 6e5, userId: sub, email: null });
const client = sub => { const c = new SupabaseRest(`http://127.0.0.1:${proxyPort}`, 'local-anon-placeholder'); c.adoptSession(session(sub)); return c; };
const draft = (value, unit, time) => { const r = validateGlucoseInput({ value, unit, date: 'Oct 15, 2026', time, tzOffsetMinutes: 300, tzName: 'Asia/Karachi', mealContext: 'before_meal', note: 'roundtrip' }); if (!r.ok) throw new Error(r.error); return r.draft; };
try {
  for (let i = 0; i < 40; i++) { try { await fetch(`http://127.0.0.1:${restPort}/`); break; } catch { await new Promise(r => setTimeout(r, 250)); } }
  const ca = client(A); const sa = new GlucoseStore(new SupabaseGlucoseRepository(ca), ca);
  assert.equal((await sa.reload()).ok, true); assert.equal(sa.getSnapshot().readings.length, 0);
  const c1 = await sa.save(draft('110', 'mg/dL', '8:15 AM')); const c2 = await sa.save(draft('6.1', 'mmol/L', '1:30 PM'));
  assert.ok(c1.ok && c2.ok, JSON.stringify([c1, c2]));
  assert.equal(c2.reading.valueMgDl, 109.91); assert.equal(c2.reading.unitOriginal, 'mmol/L'); assert.equal(c2.reading.valueOriginal, '6.1'); assert.equal(c2.reading.userId, A);
  assert.notEqual(c1.reading.measuredAt, c1.reading.createdAt);
  console.log('ok - A created 2 readings through PostgREST; user_id from JWT; mg/dL generated server-side');
  // "Restart": a brand-new client/store loads the persisted rows.
  const ca2 = client(A); const sa2 = new GlucoseStore(new SupabaseGlucoseRepository(ca2), ca2); await sa2.reload();
  assert.deepEqual(sa2.getSnapshot().readings.map(r => r.valueOriginal), ['110', '6.1']);
  console.log('ok - a fresh client (simulated restart) reloads the persisted readings in chronological order');
  const u = await sa2.save(draft('6.4', 'mmol/L', '1:30 PM'), c2.reading.id); assert.ok(u.ok); assert.equal(u.reading.valueMgDl, 115.32); assert.equal(u.reading.unitOriginal, 'mmol/L');
  console.log('ok - A edited a reading; unit preserved; canonical value regenerated');
  const cb = client(B); const sb = new GlucoseStore(new SupabaseGlucoseRepository(cb), cb); await sb.reload();
  assert.equal(sb.getSnapshot().readings.length, 0);
  const repoB = new SupabaseGlucoseRepository(cb);
  await assert.rejects(repoB.update(c1.reading.id, draft('300', 'mg/dL', '8:15 AM')), e => e.kind === 'not-found');
  await assert.rejects(repoB.remove(c1.reading.id), e => e.kind === 'not-found');
  const forged = await fetch(`http://127.0.0.1:${proxyPort}/rest/v1/glucose_readings`, { method: 'POST', headers: { Authorization: `Bearer ${jwt(B)}`, 'Content-Type': 'application/json', apikey: 'x' }, body: JSON.stringify({ user_id: A, measured_at: '2026-10-15T03:00:00Z', tz_offset_minutes: 0, value_original: 100, unit_original: 'mg/dL' }) });
  assert.ok([401, 403].includes(forged.status), `forged insert status ${forged.status}`);
  const anon = await fetch(`http://127.0.0.1:${proxyPort}/rest/v1/glucose_readings?select=id`, { headers: { apikey: 'x' } });
  assert.ok([401, 403].includes(anon.status), `anon status ${anon.status}`);
  console.log('ok - B cannot see, edit, delete or forge A rows; anonymous requests are refused');
  assert.equal((await sa2.remove(c1.reading.id)).ok, true); await sa2.reload(); assert.equal(sa2.getSnapshot().readings.length, 1);
  console.log('ok - A deleted a reading; deletion persisted');
  console.log('ROUNDTRIP PASSED');
} finally { pgrst.kill(); proxy.close(); fs.rmSync(conf, { force: true }); }
