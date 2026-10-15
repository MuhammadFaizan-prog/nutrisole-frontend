# G9 Stage J4 (no training): handoff verified, labelling/ingestion runbooks, readiness work, placeholder audit

Written 2026-10-15 (PKT). Continues J3 (local 9374ed8 = remote cv-gauntlet 74c963c; remote unchanged at start, nothing to mirror).
**Unchanged:** G3, H2 experimental, user-facing automatic grades blocked, M-TEST sealed, H3 BLOCKED (0 human manifests, no user go).
No training, no GPU, nothing deleted. Scope: five showcase classes (apple, banana, citrus/orange, tomato, carrot) inside the full FYP.

## 1. Handoff integrity (read-only; nothing regenerated)
`ml/runs/G9/stageJ/scripts/j4_verify_handoff.py` checked the 7 zips in `files/g9/stageJ/handoff/` against
`ml/runs/G9/stageJ/out/handoff/j3_handoff_manifest.json`: **PASS**. Outer zip sha256 + member lists match; all 8 inner packs match their
recorded sha256 and item counts (265/335/461/646 × 2 copies); `HANDOFF_MANIFEST.json` copy equals the repo manifest; recursive AI-leak grep
(13 markers incl. `AI_ASSISTED`, `G9J_AI_`, `j_blind_key`, `source_label`, `pred_label`): annotator A/B, both training zips and team zip
**clean**; adjudicator zip mentions the marker only in its instruction text (expected). Report: `ml/runs/G9/stageJ/out/j4/j4_handoff_verify.json`.
Note: the files re-uploaded to `files/uploads/` on 2026-10-15 22:23 PKT are byte-identical to the blank packs (no human exports yet).

## 2–4. Human runbooks (also copied to the handoff folder as plain files)
- `G9_stageJ4_WINDOWS_LABELLING_GUIDE.md`: annotators (Edge/Chrome offline tool, exact export names, PowerShell `Get-FileHash`,
  attestation in Notepad + validity check, send by Drive/email), lead PowerShell commands (`j3_merge_evidence` → `j_agree agree` →
  adjudication → `j_agree verify`), adjudicator columns.
- `G9_stageJ4_PHASE2_TRAINING_SCHEDULE.md`: D0-relative plan for train 461 + train2 646, team packs, and 7 frozen leakage rules.
- `G9_stageJ4_TEAM_PHOTO_INGESTION_RUNBOOK.md`: priority quotas (eval: apple/banana/tomato 20 each, citrus/carrot 16 each, bagged + partly
  hidden; train: apple ≥ 75, tomato ≥ 15, banana ≥ 10), consent/licence, PowerShell bulk rename, ingestion and what to commit.
- `G9_stageJ4_ANDROID_FIRST_PHONE_TEST.md`: P0 (today, no new dependency) and P1 (device branch after approval) for the Figure 7.2 flow.

**Script gap fixed (real):** `j_team_phone.py` refused every non-apple training session, but the identified shortages include tomato and
banana. Training sessions now accept apple/banana/tomato (`TRAIN_CLASSES`) and refuse packaging/hidden conditions in training; existing
test regex updated to the new message (same assertion: `none` still refused). Checked but **not** a gap: the attestation timestamp format
(files contain ISO 8601 with offset; the human-readable form seen earlier was a display artefact), so `j3_merge_evidence.py` is unchanged.

## 5. Independent non-training readiness work (native/src/cv; not wired to live screens)
| Added | What | Tests |
|---|---|---|
| `pipeline/cropmap.ts` | crop ↔ original, H2 224-window → crop, frame box → display orientation (rotation + mirror), `boxInside` | `cvCropMap.test.ts` (7): letterbox round-trip + pad clamp + `detectorToFrame` agreement, rotation inverses, on-screen box ↔ tap consistency for 4 rotations × mirror, 16:9→4:3 still, crop/H2 window inside crop, end-to-end tap→still crop |
| `pipeline/result.ts` | explicit **Unknown / Not graded / Poor capture** states; no graded state; `USER_GRADES_ENABLED = false`; grade/confidence never copied to the display result; demo results labelled | `cvResult.test.ts` (4) |
| `runtimeCheck.ts` + `scripts/check-cv-runtime.ts` | read-only presence check of the pinned camera/inference packages, the 3 weight files, CAMERA permission; MISSING/MISMATCH with exact fixes. Today: **NOT READY** | `cvRuntimeCheck.test.ts` (4) |
| `prices/lookup.ts` | official **Lahore** price by produce type, one range combining list grade 1+2 (no grade split), PBS national excluded, stale → unavailable, never invented | `cvDataContracts.test.ts` |
| `data/nutrition.ts` + generated `data/nutritionFdc.ts` | per-100 g values for the 5 classes from USDA FoodData Central SR Legacy (fdc 171688 apple, 173944 banana, 169097 orange, 170457 tomato, 170393 carrot), FDC nutrient ids, food URLs, dataset sha256; glycemic index **missing** (not in FDC); citrus flagged as closest match (kinnow not a separate FDC food) | `cvDataContracts.test.ts` (6 total) |
| `debug.ts` | phone-test debug flag (default off) + NSCV lines that match `g9i-device-check.ps1` | `cvDebug.test.ts` (2) |
| `ml/.../j4_nutrition_extract.py` | regenerates `nutritionFdc.ts` from the official zip (sha256-checked) | — |

Nutrition source: <https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip>
(sha256 `b80817294b8850530aaedf2e515c02593b1824f763a0ff356e5c2081643e6fd0`, retrieved 2026-10-15); food pages
`https://fdc.nal.usda.gov/food-details/<fdc_id>/nutrients`. The existing demo catalog values in `extensions/model.ts` (`foods`) are not
touched; they are not cited in the UI.

## 6. Placeholder audit (confidence / grade / identity)
| # | File:line (before J4) | Placeholder | Action |
|---|---|---|---|
| 1 | `src/nutrisole/Scan.tsx:26` | `Confidence 97%` on the scan banner | **Needs approval** (file protected by `artifacts/expansion/six-screen-baseline.json`; AGENTS.md forbids changing or re-baselining it). Proposed diff: §6.1 |
| 2 | `src/nutrisole/Scan.tsx:9`, `:25` | default identity `'Apple'` shown as the detected item | demo sample (gallery sheet says no AI analysis occurs); same approval as #1 |
| 3 | `native/responsive/ScanScreen.tsx:28` | `Confidence 97%` (native scan banner) | **Changed** → `demoConfidenceText()` = "Demo data · not a model result" |
| 4 | `native/responsive/ScanScreen.tsx:13`; `native/responsive/NutriSole.tsx:32,70` | default/sample identity `Apple` | kept (demo flow); every downstream screen now carries "Demo data" |
| 5 | `src/nutrisole/extensions/model.ts:117` | `Apple` + `Sample analysis` | **Changed** → `DEMO_PLACEHOLDER.identity` + "Demo data · sample" |
| 6 | `src/nutrisole/extensions/model.ts:118` | `VISIBLE GRADE` **`A`** + "Good visible condition" | **Changed** → `gradeDisplay()`: "—" + "Not graded · Demo data" (grade only if flag on **and** a real model grade is passed) |
| 7 | `src/nutrisole/extensions/model.ts:119` | Ripeness "Even colour", Surface "Minor marks" | kept (sample evidence text under the "Demo data" header); component preserved |
| 8 | `src/nutrisole/extensions/model.ts:120` | `Model v1.0 · Rubric v1.0` | **Changed** → "Demo data · no model was run" |
| 9 | `src/nutrisole/extensions/model.ts:124` | market reference `Grade A` | **Changed** → "Not graded · Demo data" |
| 10 | `src/nutrisole/extensions/useExpansion.ts:29` | evidence notice `Confidence: 97%. Model v1.0 · Rubric v1.0` | **Changed** → title "Assessment evidence · Demo data", text `DEMO_PLACEHOLDER.note` |
| 11 | `artifacts/figma/scenes.json:1326`, `artifacts/figma-expansion/scene-manifest.json:29772`, `ui.html` | generated design exports containing the old strings | not regenerated (design artefacts; `figma:build` would rewrite them): needs user decision |
| 12 | `UI_BUILD_PROMPT.md:13`, `artifacts/screen-coverage/*` | design spec / coverage text "Apple / Confidence 97%" | documentation of the original design; untouched |
| — | `native/src/cv/pipeline/rules.ts:88-106`, `closeup.ts:175`, `prices/display.ts:37-49`, `reference.ts` | real grading/price engine code paths | functional components, preserved; never displayed (`GRADE_DISPLAY_ENABLED = false`, `result.ts`) |

Central source: `DEMO_PLACEHOLDER`, `DEMO_FLAGS { showDemoPlaceholders: true, gradeDisplayEnabled: false }`, `demoConfidenceText`,
`demoBadge`, `gradeDisplay`, `NOT_GRADED` at the end of `src/nutrisole/extensions/model.ts` (kept there because model.ts is imported
directly by node tests and the Figma importer and has no imports). Test: `native/tests/demoPlaceholder.test.ts` (4). `check:runtime`
(28 protected files) and the six-screen baseline test are untouched and pass; nothing was bypassed or re-baselined.

### 6.1 Proposed diff needing approval (protected original screen)
```diff
--- a/src/nutrisole/Scan.tsx
+++ b/src/nutrisole/Scan.tsx
@@ -2,6 +2,7 @@
 import ScenePhoto, { CameraFrame } from './ScenePhoto';
+import { demoBadge } from './extensions/model';
@@ -23,7 +24,7 @@
     <Txt x={395} y={447} w={330} fs={40} bold color="#fff">{selected}</Txt>
-    <Txt x={395} y={497} w={340} fs={38} color="#fff">Confidence 97%</Txt>
+    <Txt x={395} y={497} w={340} fs={38} color="#fff">{demoBadge()}</Txt>
```
Applying it also requires updating the `src/nutrisole/Scan.tsx` hash in `artifacts/expansion/six-screen-baseline.json`, which AGENTS.md
reserves for the user. Say "apply the Scan.tsx demo-label diff" to approve; until then the web preview's Scan screen still shows the
original 97% design text (not CV evidence).

## 7–8. Status and tests (2026-10-15)
ML pytest **148/148** (141 + 7 `test_j4.py`), native `node --test` **149/149** (122 + 27), web `npm test` **5/5**, `test:expansion` **8/8**,
`check:runtime` **28 protected files OK**, root `tsc --noEmit` and `native/src/cv` `tsc` clean. Full native app `tsc -p native/tsconfig.json`
cannot run in the sandbox (native React Native type packages not installed); not a J4 regression.

## 10. Who does what
**Agent (autonomous, no approval needed):** re-verify received files; run merge/agree/verify when exports arrive and commit outputs to
cv-gauntlet; ingest team drops and build blind packs; report R1–R4/T1–T5; non-training app work (contracts, tests, runbooks); write the
P1 device-branch code once approved.
**User (M Faizan):** pick the three people and send each only their zip; receive exports + attestations and upload them; approve
(a) the Scan.tsx diff + baseline update, (b) regenerating the Figma artefacts, (c) a device branch with the camera/inference packages,
CAMERA permission and bundled weights; run P0/P1 on the phone; decide citrus training sessions; later, the H3 go (only if every gate passes).
**Annotators A and B:** label pilot 265 + pilot2 335 independently, export, self-attest; then train 461 + train2 646; then team packs.
**Adjudicator:** settle every disagreement/uncertain/tag mismatch for each batch; sees AI post-hoc material only after both exports.
**Team photographers:** shoot to the quotas with location off, fill their own `sessions.csv` row (licence + consent).
