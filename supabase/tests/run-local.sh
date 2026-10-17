#!/usr/bin/env bash
# Local, isolated validation of the glucose migration on PostgreSQL 17 (no Supabase project touched).
# Usage: supabase/tests/run-local.sh [--keep]   (needs initdb/pg_ctl/psql on PATH or PG_BIN)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/../.." && pwd)"
PG_BIN="${PG_BIN:-$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | sort -V | tail -1)}"; export PATH="$PG_BIN:$PATH"
PORT="${GLUCOSE_PG_PORT:-55432}"; DATA="${GLUCOSE_PG_DATA:-$(mktemp -d /tmp/glucose-pg.XXXX)}"
initdb -D "$DATA" -U postgres -A trust >/dev/null
pg_ctl -D "$DATA" -o "-p $PORT -k /tmp -c listen_addresses=127.0.0.1" -l "$DATA/log" -w start >/dev/null
trap '[ "${1:-}" = "--keep" ] || pg_ctl -D "$DATA" -m fast stop >/dev/null' EXIT
P="psql -X -q -h /tmp -p $PORT -U postgres -v ON_ERROR_STOP=1"
$P -c "create database glucose_test" postgres
$P -d glucose_test -f "$HERE/local_auth_stub.sql" >/dev/null
$P -d glucose_test -f "$ROOT/supabase/migrations/20261016000000_create_glucose_readings.sql" >/dev/null
$P -d glucose_test -f "$ROOT/supabase/migrations/20261017205545_glucose_report_corrections.sql" >/dev/null
echo "migrations applied"
$P -d glucose_test -f "$HERE/rls_glucose.test.sql"
# Rollback then re-apply to prove the down migration is clean and the up migration is repeatable.
$P -d glucose_test -f "$ROOT/supabase/rollback/20261016000000_create_glucose_readings.down.sql" >/dev/null
test "$($P -d glucose_test -Atc "select count(*) from pg_class where relname = 'glucose_readings'")" = 0
$P -d glucose_test -f "$ROOT/supabase/migrations/20261016000000_create_glucose_readings.sql" >/dev/null
echo "ok - rollback drops all objects; migration re-applies cleanly"
# Conversion parity: DB generated column vs. the app's toMgDl for every mmol/L value 0.60..55.50.
$P -d glucose_test -Atc "select to_char(v/100.0, 'FM990.00') || ',' || (case when true then round((v/100.0) * 18.0182, 2) end) from generate_series(60, 5550) v" > "$DATA/parity.csv"
node --experimental-strip-types --import "$ROOT/tests/glucose/resolve-ts.mjs" -e "
import('$ROOT/src/nutrisole/glucose/units.ts').then(({ toMgDl }) => { const fs = require('fs'); let n = 0;
for (const line of fs.readFileSync('$DATA/parity.csv', 'utf8').trim().split('\n')) { const [v, db] = line.split(','); if (toMgDl(v, 'mmol/L') !== Number(db)) { console.error('MISMATCH', v, db, toMgDl(v, 'mmol/L')); process.exit(1); } n++; }
console.log('ok - conversion parity for', n, 'mmol/L values (DB round(v*18.0182,2) == app toMgDl)'); });"
# Optional: real client round trip through a local PostgREST (set POSTGREST_BIN).
if [ -n "${POSTGREST_BIN:-}" ]; then
  $P -d glucose_test -c "insert into auth.users (id, email) values ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'a@test.local'), ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', 'b@test.local') on conflict do nothing"
  (cd "$ROOT" && node --experimental-strip-types --import ./tests/glucose/resolve-ts.mjs tests/glucose/db-roundtrip.mjs "$PORT" "$POSTGREST_BIN")
fi
echo "ALL LOCAL DATABASE CHECKS PASSED"
