// LOCAL QA HARNESS ONLY (never deployed): exposes a local PostgREST + a minimal
// GoTrue-compatible password grant on one port, shaped like a Supabase project URL, so
// the real web app can be exercised against the local Postgres with the glucose
// migration and RLS. Users: a@test.local / b@test.local, password "local-test-password".
// Usage: node tests/glucose/local-stack.mjs <pgPort> <postgrestBin> <port>
import { spawn } from 'node:child_process';
import http from 'node:http';
import crypto from 'node:crypto';
import fs from 'node:fs';
const [pgPort, postgrestBin, port] = process.argv.slice(2);
const secret = crypto.randomBytes(32).toString('hex'); const restPort = Number(port) + 1;
const conf = `/tmp/glucose-stack-${port}.conf`;
fs.writeFileSync(conf, `db-uri = "postgres://authenticator:local-test-only@127.0.0.1:${pgPort}/glucose_test"\ndb-schemas = "public"\ndb-anon-role = "anon"\njwt-secret = "${secret}"\nserver-port = ${restPort}\nserver-host = "127.0.0.1"\nlog-level = "error"\n`);
const pgrst = spawn(postgrestBin, [conf], { stdio: ['ignore', 'ignore', 'inherit'] });
const users = { 'a@test.local': 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'b@test.local': 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb' };
const b64 = o => Buffer.from(JSON.stringify(o)).toString('base64url');
const jwt = sub => { const h = b64({ alg: 'HS256', typ: 'JWT' }); const p = b64({ sub, role: 'authenticated', aud: 'authenticated', exp: Math.floor(Date.now() / 1000) + 3600 }); return `${h}.${p}.${crypto.createHmac('sha256', secret).update(`${h}.${p}`).digest('base64url')}`; };
const cors = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'authorization, apikey, content-type, prefer, accept', 'Access-Control-Allow-Methods': 'GET, POST, PATCH, DELETE, OPTIONS', 'Access-Control-Expose-Headers': 'content-range' };
http.createServer((req, res) => {
  if (req.method === 'OPTIONS') { res.writeHead(204, cors); return res.end(); }
  if (req.url.startsWith('/auth/v1/token')) {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      const { email, password, refresh_token } = JSON.parse(body || '{}'); const sub = users[email] || (refresh_token && refresh_token.split(':')[1]);
      if (!sub || (email && password !== 'local-test-password')) { res.writeHead(400, { ...cors, 'Content-Type': 'application/json' }); return res.end('{"error":"invalid_grant"}'); }
      res.writeHead(200, { ...cors, 'Content-Type': 'application/json' }); res.end(JSON.stringify({ access_token: jwt(sub), refresh_token: `local:${sub}`, expires_in: 3600, user: { id: sub, email: email || null } }));
    }); return;
  }
  if (req.url.startsWith('/auth/v1/logout')) { res.writeHead(204, cors); return res.end(); }
  const up = http.request({ host: '127.0.0.1', port: restPort, path: req.url.replace(/^\/rest\/v1/, ''), method: req.method, headers: req.headers }, r => { const headers = Object.fromEntries(Object.entries(r.headers).filter(([k]) => !k.startsWith('access-control-'))); res.writeHead(r.statusCode, { ...headers, ...cors }); r.pipe(res); });
  req.pipe(up); up.on('error', () => { res.writeHead(502, cors); res.end(); });
}).listen(Number(port), '127.0.0.1', () => console.log(`local stack on http://127.0.0.1:${port}`));
process.on('SIGTERM', () => { pgrst.kill(); fs.rmSync(conf, { force: true }); process.exit(0); });
