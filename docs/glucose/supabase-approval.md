# Approval request: apply the glucose migration to Supabase `nutrisole`

**Do not apply without the project owner's explicit approval.** Nothing below has been run against the live project.

## Discovered (read-only, 2026-10-16 via Supabase MCP)

- Project `nutrisole`, ref `zlxefqhzceiloplyszje`, region ap-south-1, status ACTIVE_HEALTHY, Postgres 17.11.
- Public tables: 0. Recorded migrations: 0. Branches: 0. `auth.users`: 0 rows. `auth.uid()` exists.
- Extensions installed: plpgsql, supabase_vault, pg_stat_statements, pgcrypto, uuid-ossp. Security advisors: no lints.
- Auth provider settings (email confirmation, sign-ups enabled) are not exposed by the MCP tools: **unverified**. Check them in the dashboard before testing sign-in.

## What would change

| Object | Change |
|---|---|
| `public.glucose_readings` | new table (RLS enabled; 4 owner-only policies for `authenticated`) |
| `public.glucose_readings_guard()` + trigger | new function/trigger (updated_at, no future readings, immutable owner/provenance, read-only imported values) |
| `glucose_readings_user_measured_idx`, `glucose_readings_import_uid` | new indexes |
| Grants | `anon`: none. `authenticated`: select, delete; insert/update on listed columns only (not `user_id`, not `value_mg_dl`) |

No existing data is touched (there is none). No edge functions, storage or secrets.

- **SQL:** `supabase/migrations/20261016000000_create_glucose_readings.sql`
- **Rollback:** `supabase/rollback/20261016000000_create_glucose_readings.down.sql` (drops the table; export first if real readings exist)
- **Cost:** free. Runs inside the existing project; no new project, no branch, no paid add-on.
- **Risk:** low. New, isolated objects. Main risk: health data starts being stored, so privacy obligations begin; the table is owner-only by RLS.
- **Evidence:** `npm run test:glucose:db` on local PostgreSQL 17 with a Supabase-compatible `auth.uid()` stub: 9 RLS/integrity checks (anon blocked; user A cannot read/update/delete/forge B rows; RLS WITH CHECK holds even if a `user_id` grant were added; null identity sees nothing; constraints; idempotent imports; cascade on user deletion), clean rollback + re-apply, DB/app conversion parity for 5,491 values, and an app-client round trip through local PostgREST 16.4 with two JWT identities.

## After approval (owner or agent with approval)

1. Apply the migration (Supabase SQL editor or `apply_migration` with name `create_glucose_readings`).
2. Run `get_advisors` (security + performance) and `list_tables` to confirm RLS.
3. Create two test users in Auth and repeat the two-user checks against the project, using the anon key from the app (not SQL as postgres).
4. Set the public URL + publishable key in `.env.local` (web) / `config.native.ts` (native). Never commit a service-role key.
5. Regenerate types with `generate_typescript_types` and compare with `GlucoseRow` in `src/nutrisole/glucose/repository.ts`.
