# NutriSole FYP requirement status audit (G9 Stage J)

Written **2026-10-15**, following the instruction in [G9_stageJ_FYP_scope_alignment.md](G9_stageJ_FYP_scope_alignment.md):
*"Report each FYP requirement as verified, partial, pending or blocked with the evidence needed for its actual user workflow."*
Proposal: **FYP-proposal edit one.docx** (SHA256 `c76c8a6e…aa5438`, unchanged, not edited). Repo state audited: `cv-gauntlet` at the
user's `38e6b0a` plus this commit. Nothing was trained, no GPU, main untouched, nothing deployed.

## Status definitions (strict)

| Status | Meaning |
|---|---|
| **verified** | The requirement works in its **real user workflow** (real inputs, in the app a user would run, on a phone where the proposal implies one), with independent evidence. |
| **partial** | Real, tested building blocks exist, but the user workflow is incomplete, runs on synthetic/sample data, or lacks independent or device evidence. |
| **pending** | Only UI mock-ups, static sample screens or plans exist; the logic the proposal describes is not built yet. |
| **blocked** | Work exists but cannot progress until a named external prerequisite is met (human labels, a failed frozen gate, etc.). |

Synthetic or demo data never counts as verified. Sandbox-only numbers (2-core CPU, no phone, no emulator) are not device evidence.

## Facts that apply to every row

- **The app is a frontend demo with synthetic data.** `README.md` line 13: "Authentication, food recognition, camera capture, health
  connections, prices, notifications, and staff permissions are simulated." `Schema.md`: "No database … synthetic data only"
  (`localStorage` on web, `AsyncStorage` on native, key `nutrisole.demo.v1`). `Techspec.md`: "No REST handlers, database, secrets,
  network data service, or background jobs."
- **No backend exists in the repo.** The proposal's backend (NestJS, REST, Pydantic) and database (Supabase) are absent: no `supabase`
  reference anywhere in `src/`, `native/` or `worker/`; `worker/index.js` only serves static assets with an SPA fallback. A Supabase
  project named "nutrisole" was created on 2026-10-12 (project notes), but no schema, migrations or client code is in the repo.
- **The CV pipeline is not wired into any screen.** `native/src/cv/**` is imported only by `native/tests/cv*.test.ts`. `native/package.json`
  has no camera or inference runtime (dependencies: async-storage, lucide, react, react-native, safe-area-context, svg). The Stage I
  runtime set (vision-camera 5.2.3, executorch 0.10.5, …) is documented in `G9_stageI_android_test.md` but not installed; the `.pte`
  export of H2 is not done. Nothing has run on a phone or emulator (`G6_device_validation_pending.md`).
- **Demo screens hard-code CV outputs that the gates forbid.** `native/responsive/ScanScreen.tsx` and `src/nutrisole/Scan.tsx` show a fixed
  "Apple · Confidence 97%"; `src/nutrisole/extensions/model.ts` (`analysis-result`, `market-reference`, also rendered by native
  `ExpandedScreen.tsx`) shows "VISIBLE GRADE **A**" and "Grade A" for a "Sample analysis". These are labelled as samples, but they
  contradict the Stage G/H decision that no A/B/C grade is shown to users. They must not be presented as model results.
- **Test counts reproduced on 2026-10-15 (sandbox):** ML pytest **120/120** (117 + 3 new `j_team_phone` tests), native `node --test`
  **122/122**, web `npm test` (domain) **5/5**, `npm run test:expansion` **8/8**, `npm run check:runtime` **28 protected files OK**.
  These prove code contracts and parity, not label correctness, product completion or device behaviour.
- **Human-verified CV labels: 0.** The 265 + 335 pilot reviews remain `AI_ASSISTED_NOT_HUMAN`; H3 is **BLOCKED**
  (`G9_stageJ_gaps.md`, `G9_stageJ_readiness.md`).

## Requirement-by-requirement status

### 1. Supported fruit/vegetable recognition (objective 1, §6.1) — **BLOCKED**

| | |
|---|---|
| Code | Detector G3 yolo11n@480 + scene guard + IouTracker (`ml/`, TS mirror `native/src/cv/pipeline/{postprocess,tracker}.ts`); 12-class map `native/src/cv/models/labels.ts`; close-up identity H2 (MobileNetV3-S + unknown) and verify/occlusion rules `native/src/cv/pipeline/{closeup,verify}.ts`; camera/tap/tensor mapping `camera.ts` with Python parity. |
| Evidence | `DASHBOARD.md`: G3 pooled mAP50 **0.314** (n=829) vs target ≥0.85 (FAIL); FA 1.25/min on the G1 negative clip (target ≤1). `G9_stageG.md`: in the close-up approach G3 named 19/29 items, **6 correctly**. `G9_stageH.md`: NOT ACCEPTED (4/8 criteria); correct-item acceptance **0.14** vs 0.60 floor (abstains on ~90%). Stage I: post-hoc diagnostics only. Stages B–E: no promotion. |
| Data | Public web datasets (Roboflow/OIV7/LVIS/Commons) with locked splits; all G9 close-up labels are agent/source labels (exploratory). No real Lahore or phone footage labelled. In-app scan is a static image with a hard-coded "Confidence 97%". |
| Blocked by | 0 human-verified labels (two blind annotators + third adjudicator per `G9_stageJ_annotation_guide.md`); apple training short by a projected ~65 usable images (`G9_stageJ_gaps.md`); team phone photos not yet collected (`G9_stageJ_team_photo_shotlist.md`). |
| Needed for the real workflow | (a) Human-verified J-eval set and H3 passing the frozen gates (genuine acceptance ≥0.60 **and** wrong ID ≤2%); (b) camera + model bundled in the native app; (c) on-phone run on the five showcase classes with per-item results, unsupported items shown as "unable to identify"; (d) a Lahore/phone field set scored per `G6_device_validation_pending.md` #3. |

### 2. Visible ripeness, defects, colour, shape and surface condition (objective 2) — **PARTIAL**

| | |
|---|---|
| Code | Fresh/rotten condition classifier E224 (`MODEL_IO.condition` in `camera.ts`); measurement rules `ml/grading/{measure,rules}.py`, `colour_bands.json`; ripeness head `ml/grading/ripeness.py` ↔ `native/src/cv/pipeline/ripeness.ts` (170-case parity); assessments schema with `unable_to_assess`. |
| Evidence | `DASHBOARD.md`: E224 rotten recall **0.983** on the locked public test (n=270), 0.941 on synthetic low light (gate 0.95: FAIL); G7 per-fruit ripeness head stage accuracy 0.989 on single-fruit web photos, **wired OFF**; rubric thresholds "still untuned (no human graders)". Stage G: gated fresh/rotten correctness 0.727 on CU-check. |
| Data | Public curated photos, not market/Lahore/phone, not human-graded. Not visible in the app except the hard-coded sample rows "Even colour / Minor marks". |
| Needed | Human condition labels (ripeness stage, visible defects) on real phone close-ups; calibration set for the 0.6/0.15 abstain thresholds; in-situ shop-light check (`G6_device_validation_pending.md` #6); condition assessed only after identity passes (depends on row 1). |

### 3. Understandable quality grade (objective 3, figure 7.2) — **BLOCKED**

| | |
|---|---|
| Code | Rubric `ml/grading/rubric_v0.json`, `golden_rules.json`, `rules.ts`; Stage G close-up gate (96 px, 3-frame) and grade-flip control. |
| Evidence | `G9_stageG.md`: **Not accepted** — 8 of 11 grades issued on a wrong identity; G-A1, G-A2, G-A5 FAIL. `G9_stageH.md`: no A/B/C grade and no grade-specific price shown. Grading proxy TEST 0.981 is a weak proxy with no human kappa (`DASHBOARD.md`). |
| Data | No human grading panel. The app's "VISIBLE GRADE A" is a static mock. |
| Blocked by | Row 1 (identity) and the failed Stage G gates; no human graders to tune the rubric. |
| Needed | Accepted identity (row 1); human grading panel with agreement (kappa) on A/B/C for the showcase classes; grade explanation shown in the app from real model outputs; removal of the hard-coded sample grade until then. |

### 4. Grade plus verified market-price reference (objective 4) — **PARTIAL**

| | |
|---|---|
| Code | `ml/prices/` (rate-list index parser, Tesseract grid OCR, Urdu lexicon, AMIS wholesale ticker, `build_daily.py`, `reference.py`), exact TS mirror `native/src/cv/prices/{reference,display}.ts`; `ml/prices/tests/test_prices.py`; `native/tests/cvPrices.test.ts` (120-case parity). SPI is interface-only (always no rows). |
| Evidence | `docs/cv/prices.md`: official Lahore retail lists (lahore.punjab.gov.pk) OCR on 4 hand-checked lists — kept cells **254/254** correct, priced-row recall **0.89**, 0 wrong rows (2026-10-12 lists are in-sample for the lexicon). Stage G G-A8 price contract PASS. |
| Data | **Real** official lists, but only fixtures dated 2026-10-10 and 2026-10-12 (`ml/prices/fixtures/parsed_*`); no scheduled daily fetch, no store, nothing served to the app. The app's market screen shows a static "No verified price yet" with a hard-coded "Grade A". Kinnow not on the October lists. |
| Needed | A daily job (backend/cron) that fetches and stores lists with source/date/staleness; the app calling it for the **confirmed class** (class-level reference, no grade split, while grades are blocked); per-row human check for the first weeks (as `prices.md` requires); grade-specific price only after row 3 passes; the user's unit/weight entered explicitly. |

### 5. Food recognition linked to nutrition and portions (§6.1, figure 7.1) — **PARTIAL**

| | |
|---|---|
| Code | `src/nutrisole/domain.ts` (edible mass, energy, idempotent meal recording), `extensions/model.ts` `foodInfo` + `extensions/domain.ts` `mealResult` (amount / weight / size portions, 0–5000 g limits); food selector and nutrition/portion screens (web + native). |
| Evidence | `tests/domain.test.ts` 5/5 (positive portions, idempotent saves, drafts); `tests/expansion.test.mjs` "portion calculations use the selected food and preserve drafts". |
| Data | **Synthetic**: a 3-food "Demo catalog v1 · Sample values only" (Apple, Banana, Tomato; per-100 g kcal/macros with no cited source). Carrot and orange-type citrus (showcase classes) are missing. The scan always resolves to the Apple demo; no CV output feeds nutrition. |
| Needed | A sourced nutrient table (e.g. USDA FoodData Central or a Pakistani food-composition table, cited per row) for all five showcase classes; identity from row 1 confirmed by the user before nutrition is shown; meals stored per user in the backend; stated portion assumptions in the UI. |

### 6. Glucose records: manual or supported source, history and visualisation (objective 5, §6.1/6.3) — **PARTIAL**

| | |
|---|---|
| Code | `extensions/domain.ts` `readingResult` / `saveReading` (numeric, unit-aware limit 1000 mg/dL or 55.5 mmol/L, date/time validation, duplicate rejection); screens glucose-overview, add-reading, reading-detail, health-connections. |
| Evidence | `tests/expansion.test.mjs` "manual readings validate values and deduplicate a reviewed record". |
| Data | History and week chart are **sample** data; time zone fixed to "Pacific Time"; README: "expanded-flow records reset on reload" (not persisted). Apple Health / device connection is simulated ("Not connected"). |
| Needed | Readings persisted per user (Supabase table with source = manual/import), history and chart drawn from the user's own records in Asia/Karachi, edit/delete audited; at least one real supported import path *or* an explicit decision that v1 is manual-only (the proposal allows manual entry); a test on a phone with real entered readings. |

### 7. Personalised weekly diet and exercise guidance (objective 6) — **PENDING**

| | |
|---|---|
| Code | `WeeklyPlan.tsx`, `native/responsive/WeeklyScreen.tsx`, plan-generation / plan-rationale / activity-plan screens; `create-plan` in `useExpansion.ts` only increments `planVersion` and navigates. One real rule: a recorded foot concern or limited mobility defers activity. |
| Evidence | `tests/expansion.test.mjs` "recorded foot concerns visibly defer activity and substitution"; meal accept/substitute state in the demo store. |
| Data | **Synthetic** fixed plan (week "Sep 28 – Oct 4", profile "Alex Chen", fixed diet/allergens). Glucose is shown as "None" in the rationale; no nutrition or glucose input drives the plan. "Rule set v1" is a label, not a rule engine. |
| Needed | A documented plan rule set (calorie/macro targets, allergen exclusion, glucose-aware meal choices within non-clinical bounds, activity by mobility) implemented and unit-tested; the plan generated from the user's stored profile, meals and glucose; supervisor review of the rules' safety wording. |

### 8. Basic footwear and injury-prevention guidance (objective 7) — **PARTIAL**

| | |
|---|---|
| Code | foot-questionnaire (shoe fit, comfort concern, mobility) and foot-guidance screens in `extensions/model.ts`; concern/limited → "seek a qualified assessment", activity deferred. |
| Evidence | Same expansion test as row 7. Boundary text "not a diagnosis" present. |
| Data | Three generic static tips labelled "SAMPLE RESPONSE"; answers not persisted except a "Save this session" toggle in demo state. |
| Needed | A written, cited footwear rule table (fit, activity, warning signs → referral) reviewed by the supervisor; guidance generated from the answers by those rules with tests per rule; answers stored in the user profile and used by row 7. No smart-shoe/sensor scope (excluded in §6.2). |

### 9. Conversational assistant within safety boundaries (objective 8) — **PENDING**

| | |
|---|---|
| Code | `assistantReply()` in `extensions/domain.ts`: three canned replies chosen by regex (dose/diagnosis refusal, plan/allergen hint, generic). Assistant screen with "View sources" and "Report a concern" demo buttons. |
| Evidence | `tests/expansion.test.mjs` "assistant dose questions remain within the stated support boundary" (the refusal boundary is real and tested). |
| Data | Canned text ("This is a general demo response"); no language model, no knowledge source, no user context. |
| Needed | A real assistant service (backend-held API key, system prompt with the §6.2 exclusions, optional user context with consent), a red-team test set (insulin dosing, diagnosis, equipment control, unsafe diets) with refusal pass rates, source citation for food facts, and logging of reported concerns. |

### 10. User management, feedback, progress, uncertainty handling and data protection (objective 9) — **PARTIAL**

| | |
|---|---|
| Code | Sign-in / create-account / verify / recover / reset screens with form validation only (`accountError`); profile, privacy & consent toggles, reminders, report-a-concern and staff evidence screens; demo store with version/shape checks and reset. CV side: `unknown`/abstain contracts, Stage H/I abstention, `AI_ASSISTED_NOT_HUMAN` separation enforced by `j_agree.py` (refuses AI CSVs, exact and ≥95% near-copy), consent/licence/GPS/photographer-leak checks in `j_team_phone.py`. |
| Evidence | `tests/expansion.test.mjs` account validation test; ML tests for `j_agree`, `j_handoff`, `j_team_phone` (in the 120); Stage H H-A2/H-A3 (unsupported/abstention criteria) pass. |
| Data | No authentication or accounts exist; profile is a fixed synthetic user; data lives only on the device. Uncertainty handling in CV is real but sandbox-only. |
| Needed | Real auth (Supabase Auth) with row-level security per user; profile/history stored server-side; consent records and data-deletion/export that actually act on stored data; the app showing "unable to identify / uncertain" from real model outputs; a short privacy note for photos and health data. |

### 11. Modular mobile / backend / data integration (figures 7.1/7.3, §8) — **PENDING**

| | |
|---|---|
| Code | React Native 0.86.3 app (`native/`, typecheck/lint/export scripts), web preview (`src/`), protected runtime shell (`check:runtime`, 28 files), pure-TS CV pipeline with Python parity fixtures. |
| Evidence | Native tests 122/122; ONNX export parity PASS (`DASHBOARD.md`); `G9_stageI_android_test.md` steps written. No Gradle build with camera/inference dependencies, no device run, no FPS/latency on a phone. |
| Data | All app data synthetic and local; no backend, database, API contracts or network services. |
| Needed | NestJS (or agreed) backend + Supabase schema and API contracts for profiles, meals, glucose, plans, prices and CV results (with provenance fields); camera + inference runtime installed and the CV pipeline wired into the Scan screen behind a flag; an end-to-end scripted test on his Android phone: scan → identity → (condition) → nutrition → log meal → price reference, with screenshots/video and timings (`G6_device_validation_pending.md` #1, #2, #7). |

## Summary table

| # | Requirement | Status | Key evidence | What is needed for the real workflow |
|---|---|---|---|---|
| 1 | Supported recognition | **blocked** | G3 pooled mAP50 0.314 (<0.85); Stage G 6/19 correct; Stage H not accepted (acceptance 0.14) | human-verified labels → H3 passing gates; model in app; on-phone showcase test |
| 2 | Visible ripeness/defects | **partial** | E224 rotten recall 0.983 (public test); ripeness head OFF; rubric untuned | human condition labels on phone close-ups; calibration; in-situ light test |
| 3 | Quality grade | **blocked** | Stage G not accepted (8/11 grades on wrong ID); app "Grade A" is a mock | accepted identity + human grading panel (kappa); remove mock grade |
| 4 | Grade + verified price | **partial** | real official Lahore OCR 254/254 cells, recall 0.89; 120-case parity; fixtures only | daily fetch + store + app wiring at class level; grade price after row 3 |
| 5 | Nutrition/portions | **partial** | portion logic tested (5 + 1 tests); 3-food unsourced sample catalog | sourced table for 5 classes; CV-confirmed identity → nutrition; per-user storage |
| 6 | Glucose records | **partial** | manual-entry validation + dedupe tested; sample history; not persisted | persisted per-user readings + real chart; import path or manual-only decision |
| 7 | Weekly diet/exercise | **pending** | static sample plan; only the foot-concern deferral rule is real | documented, tested rule engine using profile, meals, glucose |
| 8 | Footwear guidance | **partial** | questionnaire + referral/deferral rule tested; generic static tips | cited rule table reviewed by supervisor; per-rule tests; stored answers |
| 9 | Assistant | **pending** | 3 regex canned replies; dose/diagnosis refusal tested | real assistant service + guardrail red-team set + sources |
| 10 | User mgmt/uncertainty/data protection | **partial** | form validation only, no auth; CV abstention + AI/human separation + consent checks real | Supabase Auth + RLS; server-side history; working consent/delete/export |
| 11 | Modular mobile/backend integration | **pending** | RN app + TS CV pipeline + parity; no backend, no camera/model, no device run | backend + schema; CV wired into Scan; scripted end-to-end phone test |

**Verified: 0 of 11.** No requirement yet meets the verified bar for its real user workflow. Sandbox-verified components exist
(price OCR on 4 lists, Python/TS parity, condition classifier on a public test, validation and refusal rules), but each still depends on
synthetic data, missing integration or missing human/device evidence.

## Prioritised next actions (whole FYP)

1. **Human labels for CV (unblocks rows 1–3).** Faizi + teammate label the Stage J blind packs with the offline tool; a third person adjudicates;
   run `j_agree.py`. Without this, H3 and every grade stay blocked.
2. **Team phone collection** per the revised shot list (~80 eval candidates, ~70 whole-apple training candidates, `sessions.csv`), ingested with
   `j_team_phone.py --ref-hashes …`, then packed blind. Closes the packaging/occlusion eval gap and the apple training gap.
3. **Backend + database skeleton (rows 5, 6, 10, 11).** Supabase schema + Auth/RLS for profiles, meals, glucose readings, plans, prices and CV
   results with provenance; move the demo store to it; NestJS (or a documented Supabase-only decision) for the price job and assistant.
4. **Device integration spike (rows 1, 11).** Install the Stage I runtime set, wire `native/src/cv` into the Scan screen behind a flag, and run
   `G6_device_validation_pending.md` #1, #2, #7 on his Android phone. Replace the hard-coded "Confidence 97%" / "Grade A" with real or
   clearly "not available" states (protected UI: needs his approval).
5. **Daily price job + sourced nutrition (rows 4, 5).** Schedule the Lahore rate-list fetch into the prices table and show a class-level
   reference with source/date/staleness; build a cited nutrient table for the five showcase classes linked to confirmed identity.
6. Then: plan rule engine (row 7), footwear rule table (row 8), real assistant with guardrail tests (row 9), and one scripted end-to-end
   demo recording for the viva.
