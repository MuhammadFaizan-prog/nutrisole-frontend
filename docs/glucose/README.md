# NutriSole glucose monitoring (feature/glucose-monitoring)

Scope: finger-prick / test-strip (SMBG) glucose readings only. Manual logging, history, charts and a gated import architecture. **Not** CGM, not diagnosis, not insulin or treatment advice, not a medical device. Matches the approved FYP proposal (manual entry; compatible health-data/device integration where available; history and visualization).

Status (2026-10-16): manual flow implemented on web and native and verified against an **isolated local** PostgreSQL 17 + PostgREST with the real migration and RLS. The live Supabase project `nutrisole` (`zlxefqhzceiloplyszje`) is **unchanged**: the migration awaits owner approval. All device import adapters are disabled and research-only.

## Architecture

```text
Manual entry (Add reading) ─┐
Health Connect (disabled) ──┤→ validateGlucoseInput / reconcileImport (units.ts: ×18.0182, exact decimals)
HealthKit (disabled) ───────┤            ↓
BLE 0x1808 (disabled) ──────┤   GlucoseStore (status machine, optimistic update/delete with rollback, double-submit guard)
Vendor CSV (unsupported) ───┘            ↓
                     GlucoseRepository: Supabase (fetch → PostgREST, user JWT, RLS) | Demo (explicit flag) | Unconfigured
                                         ↓
                     viewModel.ts → extensions/model.ts scenes (glucose-overview, add-reading, reading-detail, health-connections)
                                         ↓
                     web: ExpansionScreen/Viewport (absolute layers)   native: ExpandedScreen/sceneFlow (flowing layout)
```

| File | Responsibility |
|---|---|
| `src/nutrisole/glucose/types.ts` | `GlucoseReading`, `GlucoseInput`, `GlucoseDraft`, `GlucoseSource`, `GlucoseRepository`, `GlucoseImportAdapter`, `ConnectionStatus`, `ImportResult`, `GlucoseConfig` |
| `units.ts` | 18.0182 conversion with integer arithmetic; ranges; display that shows the original text in its own unit |
| `time.ts` | wall clock ↔ UTC instant with stored offset; time-zone labels; stable chronological sort |
| `validation.ts` | the single validation boundary: decimals (comma accepted), hard ranges, unit-mismatch and unusual-value warnings (confirm, never auto-convert), future dates, notes ≤500, possible-duplicate warning |
| `supabaseRest.ts` | minimal Supabase Auth (password grant, refresh, logout) + PostgREST client on `fetch`; tokens in memory only; typed errors that never echo values |
| `repository.ts` | `SupabaseGlucoseRepository`, `DemoGlucoseRepository` (explicit flag), `UnconfiguredGlucoseRepository`; row mapping |
| `store.ts` | `GlucoseStore` snapshot/subscribe; statuses `unconfigured · signed-out · loading · ready · offline · schema-missing · error`; `stale` flag |
| `history.ts`, `viewModel.ts` | range filters (7/30/90 days/all), chart model, list rows, detail strings, truthful banners |
| `actions.ts` | screen actions (add, review, confirm, edit, delete with confirmation, unit, range, provider info) |
| `adapters/` | `reconcile.ts` (idempotent, capillary-only), `bleGlucoseService.ts` (GLS 0x2A18 parser, disabled), `healthConnect.ts` (BloodGlucoseRecord mapper, disabled), `healthKit.ts`, `vendorImport.ts` (disabled) |
| `config.ts` / `config.native.ts` | web reads `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_GLUCOSE_DEMO` / `?glucoseDemo`; native constants (null = unconfigured) |
| `supabase/migrations/20261016000000_create_glucose_readings.sql` | table, generated `value_mg_dl`, constraints, indexes, guard trigger, RLS, grants |
| `supabase/rollback/…down.sql` | rollback |
| `supabase/tests/` | local auth stub, two-user RLS suite, runner (`npm run test:glucose:db`) |
| `tests/glucose/` | unit/property tests, scene tests, PostgREST round trip, local QA stack |

Shared screens: the existing Figma-derived layer scenes were kept (same components, colours, type). Glucose-scoped visual changes: the fixed "Sep 28 – Oct 4" week strip on Glucose history became the existing segmented control for 7/30/90 days/All; the empty card now hosts the trend chart or the honest state; a readings list follows; Add reading gained a Notes field and a time-zone line; Reading details gained Notes and "Entered in NutriSole"; Health connections lists the research-only sources. Long glucose screens now scroll (their primary button is no longer pinned).

Demo fixtures: only behind `?glucoseDemo` / `VITE_GLUCOSE_DEMO=1` (web) or `GLUCOSE_DEMO` (native), labelled "Demo mode · not saved" on every glucose screen. `?glucoseDemo=seed` adds six "Sample" readings for screenshots. No other path shows sample readings.

## Setup

1. Approve and apply the migration (see `supabase-approval.md`).
2. Web: copy `.env.example` to `.env.local` and set `VITE_SUPABASE_URL=https://zlxefqhzceiloplyszje.supabase.co` and the project's **publishable/anon** key. Never a service-role key.
3. Native: set `SUPABASE_URL` / `SUPABASE_ANON_KEY` in `src/nutrisole/glucose/config.native.ts` (public values only) and rebuild.
4. Create a test user in Supabase Auth (dashboard) and sign in from the app's Sign in screen.

Sessions are memory-only: after a restart the user signs in again; readings persist in Postgres. There are no offline drafts (no secure local store exists): when offline, nothing is saved, the form keeps the entry and the UI says so.

## Verification commands

```bash
npm run test:glucose        # 29 unit/property/scene/client tests (no network)
npm run test:glucose:db     # local Postgres 17: migration, 9 two-user RLS checks, rollback, 5,491-value conversion parity
POSTGREST_BIN=/path/to/postgrest npm run test:glucose:db   # + real client round trip through local PostgREST
npm run typecheck && npm run test:expansion && npm test && npm run check:runtime
npm --prefix native run typecheck && npm --prefix native test
```

## Device / API findings (summary of `meter-research.md`)

- Route A, manual: works with every meter. Implemented.
- Route B, BLE Glucose Service 0x1808: most realistic auto-import for a Pakistan-available meter. Candidate **Accu-Chek Instant (Bluetooth model, not "Instant S")**: REQUIRES HARDWARE TEST (passkey bonding; no Context characteristic; vendor decoy RACP UUID, so resolve 0x2A52 inside service 0x1808 only). Parser prototype only; no BLE package added.
- Route C, Health Connect: platform SUPPORTED (`BloodGlucoseRecord`, `READ_BLOOD_GLUCOSE`, `specimenSource` separates capillary from CGM). No Pakistan-available meter app is documented to write to it (mySugr documents Google Fit/Apple Health). UNVERIFIED end to end. Mapper only; `react-native-health-connect` 4.1.3 would need a build test on RN 0.86.3 before adding.
- Route D, HealthKit: mySugr, Contour Diabetes and OneTouch Reveal document Apple Health writes. iOS later.
- Route E, vendor API/CSV: no public SMBG API found; OneTouch Reveal CSV exists, but its meters are grey imports in Pakistan. UNSUPPORTED.
- Lowest strip cost: On Call Plus ≈ Rs 26.5/test, Sinocare Safe AQ ≈ Rs 32/test, Accu-Chek Instant ≈ Rs 40.2/test (manual only for the first two).
- Safest FYP demo: manual entry + a hardware GLS test on Accu-Chek Instant (≈ Rs 6,350–6,760 with 50 strips). **Purchase needs the owner's approval.**

## HARDWARE-BLOCKED validations

BLE pairing/bonding, RACP record download, sequence-number dedupe, control-solution filtering on a real meter; any meter → Health Connect chain; HealthKit permissions on an iPhone. None were run; nothing claims "connected".
