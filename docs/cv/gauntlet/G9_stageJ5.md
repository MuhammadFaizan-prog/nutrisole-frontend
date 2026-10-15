# G9 Stage J5 (no training): human-review record, approved UI corrections, isolated device branch, data and readiness

Written 2026-10-15 (PKT). Continues J4 (local 83090a0 = remote cv-gauntlet 293d075; remote unchanged at start, nothing to mirror).
The user's brief of 2026-10-15 22:53 PKT is authoritative. **Unchanged:** G3, H2 v2 experimental, grades blocked for users, M-TEST sealed,
H3 BLOCKED. No training, no GPU, nothing deleted, frozen gates and frozen plan v2 untouched.

## 1. Human verification (honest result)
**Inputs found:** no human CSV exports and no attestations. The five annotator zips uploaded at 22:23 PKT are byte-identical to the blank
packs (pilot a1 `d1af6dfa…`, pilot a2 `261f74f0…`, pilot2 a1 `ab5d4f31…` ×2, pilot2 a2 `e5f15438…`). `files/uploads/` holds no CSV or JSON.
So `j3_merge_evidence → j_agree agree → adjudication → j_agree verify` has nothing to run on; nothing was fabricated.

**The user's statement** ("I have manually reviewed the AI annotation files against the images and confirm that the labels match my
assessment …", verbatim in the record) is recorded as a NEW versioned record, `ml/runs/G9/stageJ/out/j5/human_review_ai_assisted_v1/`:
- `human_review_record.json` (+ `.sha256`): provenance **`HUMAN_REVIEWED_AI_ASSISTED`**, reviewer **M Faizan (1 reviewer)**, **non-blind**
  (he reviewed pre-filled AI labels), not independent double annotation, stated 2026-10-15 22:53 PKT, source = his chat statement;
  sha256 of the reviewed files, which are **unmodified**: pilot `4bf78b68f478…6b6ef9` (265 rows), pilot2 `6c17debff4bb…48d2aa` (335 rows);
  Hark v2 corrections `09ad0c9d…6b7c` (CSV) / `c78d96a8…fefc6` (change list).
- `reviewed_labels_pilot.csv`, `reviewed_labels_pilot2.csv` (+ `.sha256`): the AI labels and image IDs exactly as reviewed, each row tagged
  with the tier, reviewer, `blind=no`, `independent=no`.
- Script: `ml/runs/G9/stageJ/scripts/j5_human_review.py` (`--check` re-verifies without writing; refuses to overwrite).

| Check | Result |
|---|---|
| Image IDs (both pilots) | pilot 265/265 and pilot2 335/335 equal the frozen blind keys; 0 duplicates, 0 blanks, 0 invalid labels |
| Reviewed count | 600 items by one reviewer (his statement covers "the AI annotation files"; per-item review times are not recorded) |
| Independence | **not independent**: one non-blind reviewer of AI-prefilled labels |
| Completeness / class balance (if accepted, informational) | pilot: 84 uncertain; clean supported apple 12, banana 18, citrus 15, tomato 18, carrot 22. pilot2: 119 uncertain; apple 43, banana 23, citrus 37, tomato 22, carrot 19. Negatives 96 + 72; **packaging 4, occluded 3** in total |
| Kappa vs the frozen requirement (κ ≥ 0.85 / 0.80) | **not computable**: one label set per item; a reviewer confirming AI labels is not a second annotator |
| Disputed labels | **P729**: Hark v2 changed `uncertain` → `carrot` (B M); his statement does not say whether he accepted v2, so the record keeps his v1 label and marks P729 **UNCONFIRMED** (needs his answer). Plus 203 `uncertain` rows (84 + 119) that would go to adjudication |
| Adjudication | none possible (no second annotator, no third-human adjudicator) |
| Train/eval independence | 0 candidate-key overlap, 0 Commons uploader overlap, 0 shared datasets, no eval-only source (FruitNet, carrot_m, tomato_m) in J-train/J-dev; pHash: 0 pairs ≤ 10 between 467 eval and 900 train/dev images on disk (340 not on local disk; the J2 audit covered all at ingestion) |

**Provenance tier added explicitly** (`j_agree.PROVENANCE_TIERS`, `j_agree.tier_allows`, `j_gates.FROZEN_GATES`, `j_gates.tier_gate_report`,
`h3_guard.load_batch`): only `HUMAN_INDEPENDENT` is double annotation / kappa evidence / verified manifest. `HUMAN_REVIEWED_AI_ASSISTED`
and `AI_ASSISTED_NOT_HUMAN` allow none of these. `j_agree agree` now refuses any CSV whose rows declare a non-independent tier, and
`h3_guard` names the tier when it refuses. The frozen gates were checked: **none admits a single-reviewer tier** (R1/T4 need κ between two
annotators, R3 needs both annotators + a third-human adjudicator, R2/T1–T3 count only verified manifests). Nothing was loosened.

**Gates with this record:** R1 FAIL, R2 FAIL, R3 FAIL, R4 FAIL, T1 FAIL, T2 FAIL, T3 FAIL, T4 FAIL, T5 not provenance-dependent (data
checks above clean), GO absent, E1–E8 not run. `can_unlock_h3_eval_gate = false`.
**Training-label source? No.** Frozen T1 counts only human-verified J-train images, T4 needs κ on the training batch, and all 600 reviewed
items are J-eval, which T5 bars from training. Rule unchanged.

## 2. Approved: Scan.tsx demo-label diff (applied)
Approval: the user's 22:53 PKT message. `src/nutrisole/Scan.tsx`: `Confidence 97%` → `{demoBadge()}` ("Demo data"); default / sample
identity `'Apple'` → `DEMO_PLACEHOLDER.identity` (same text, central source). Same coordinates, font sizes, colours, assets, sheets, hit
areas and actions; no grade. Native `ScanScreen.tsx` default identity also uses `DEMO_PLACEHOLDER.identity`. Baseline: only the Scan.tsx entry
of `artifacts/expansion/six-screen-baseline.json` changed (`2a13b255…` → `725ab709…`), recorded with the approval in
`artifacts/expansion/six-screen-baseline.CHANGES.md` (the repo has no baseline script; AGENTS.md reserves this for the user, who approved it).
Regression tests `native/tests/demoPlaceholderScan.test.ts` (6): badge in the exact slot, no `%`/grade/`Model v1.0` in any screen source,
baseline hash = file + approval logged, frozen `DEMO_PLACEHOLDER` cannot be given a confidence, demo results relabelled as model output or
carrying `97%` are refused by `checkDisplayResult`, Figma exports clean. "Grade A" / "97%" no longer appear in any screen source or Figma export (design-coverage documents keep the original brief text).

## 3. Approved: isolated Android device branch
Branch **`cv-gauntlet-device`** (remote created at cv-gauntlet `bbd1bd4`, device commit synced; local `ca521e3`). Draft PR **#2**
`cv-gauntlet-device → cv-gauntlet` (draft, do not merge). Details, P0 results and the P1 phone steps: `G9_stageJ5_ANDROID_P1.md` on that
branch (copied to the handoff folder). Summary: Stage H/I pinned VisionCamera 5.2.3 family + worklets 0.12.2 + onnxruntime-react-native
1.24.3 (ExecuTorch optional, no H2 `.pte`), CAMERA permission, debug layer behind `CV_DEBUG_PIPELINE = false`, frozen pipeline title only,
weights pushed by a sha256-checked script (not in Git/APK; zip in handoff). P0 in the sandbox: `npm ci` OK, app `tsc` 0 errors against
the real package types, Metro Android bundle OK, native tests 166/166. Gradle/APK/phone: P1 on his PC. No FPS claims.

## 4. Data
- `j_team_phone.py`: **orange (`citrus_orange`) training sessions enabled** (approved); carrot / `none` training still refused; test added.
- Quota sheet: `G9_stageJ5_TEAM_PHOTO_QUOTA.md` + `.csv` (train: apple ≥ 75, orange ≥ 20, tomato ≥ 15, banana ≥ 10; eval bagged/hidden
  quotas unchanged from J4, needed for R2 packaging/occluded).
- Candidate pool: `j5_candidate_pool.py` → **162 unverified J-train candidates** from Wikimedia Commons per-file CC BY / BY-SA / CC0 / PD
  (orange 53, apple 42, tomato 39, banana 28); 10 dropped as pHash ≤ 10 near-duplicates of earlier sets (57,575 reference hashes incl.
  M-TEST stored hashes) or of each other; uploaders/artists owning any J-eval/J-dev item excluded; Pexels/Pixabay/Mixkit/Unsplash and
  stock credits refused. Attribution: `out/j5/candidates/j5_candidate_pool.csv`; pixels outside Git. Never eval; unlabeled until
  annotated. Zenodo: none added this run.
- H3: `G9_stageJ5_H3_plan_v3_DRAFT.md` (prepared, not frozen, not launched): H2 v2 weights, same architecture, controlled arms vs G3
  and H2 baselines on recall, genuine acceptance, wrong IDs, unsupported rejection, occlusion safety and latency. Guard unchanged and
  REFUSED. Readiness: `G9_stageJ5_readiness.md`.

## 5. Recognition → grading → price → nutrition
Report only: `G9_stageJ5_pipeline_connection_audit.md`. Every module kept. Main findings: the CV chain is not consumed by any app
screen (only the device-branch debug layer); `citrus` (recognition) vs `citrus_orange` (nutrition, Lahore lookup) key mismatch
(`nutritionFor('citrus')` = null); no price-source feed in the app; UI nutrition uses the demo catalog, not FDC; grading connected
internally only (blocked by design).

## 6. Figma demo exports (approved)
`artifacts/figma-expansion/*` and `artifacts/expansion/scene-manifest.json` **regenerated** with `npm run figma:build` (the evidence
dialog string in `scripts/build-expansion-figma.mjs` now uses `DEMO_LABEL` / `DEMO_PLACEHOLDER.note`); `artifacts/figma/scenes*.json` and
`source-markup.json` **edited** (one string each: "Confidence 97%" → "Demo data") because a full six-screen re-export would also rewrite
masked photo assets. The live Figma file was not touched from the sandbox. Log: `artifacts/figma/DEMO_LABEL_CHANGES.md`. No redesign.

## 7. Tests and Git
ML pytest **156/156** (148 + 8 `test_j5.py`; note: `test_h3.py::test_kernel_dry_run…` has a 60 s wall-clock assertion that failed once
under CPU contention and passes alone/re-run, pre-existing), native **155/155** on cv-gauntlet (149 + 6) and **166/166** on the device
branch (+ 11 `cvDevice.test.ts`), web 5/5, `test:expansion` 8/8, `check:runtime` 28 OK, root `tsc` and `native/src/cv` `tsc` clean.
No deletions. Remote cv-gauntlet `293d075` → `bbd1bd4` (J5 core, 31/31 blobs verified) → J5 docs commit; device branch as above.

## 8. Preserved models (nothing retrained or moved): `ml/runs/G9/stageJ/out/j5/model_inventory.json`
H2 v2 `.pt` `02b402a1` / `.onnx` `20898d7c` (`/workspace/work/g9h/h2v2/`; the `h2/` ONNX is byte-identical); G3 detector `best.pt`
`29cc5212` / ONNX `c6fcb32a` / `.pte` `edb7623f`; G3 E224 `best.pt` `320b84b0` / ONNX `c51d2199` / `.pte` `44f7bc5f`; device zip `e18fa4c4`.

## 9. Next justified camera-model improvement
H3 = fine-tune **H2 v2** (same MobileNetV3-Small, same 13 outputs) on human-verified real phone-style crops made exactly as the pipeline
crops them. Justification: Stage H/I showed H2's errors are **domain mismatch** (studio-trained, 1–46 real photos per class; correct-item
acceptance 0.14 vs the 0.60 floor while wrong IDs stay ~0), and crop geometry changes were not confirmed out of sample. It stays blocked
until independent labels exist. The improvement that needs no labels is P1: real phone crops and mapping logs from the debug build
(tap-ROI vs detector-box crop rate, orientation, parity), which feed the H3 crop recipe. Not justified now: grade display, new
architectures, or training on the reviewed AI labels.

## 10. Needs the user
1. Did you accept the Hark v2 P729 correction (uncertain → carrot, bagged, many)? Yes / no.
2. Two independent annotators + one adjudicator (zips ready); team eval photos for bagged/hidden quotas; training photos per the quota sheet.
3. P1 on your phone (`G9_stageJ5_ANDROID_P1.md`), then send the log + screenshots; device zip `NutriSole_G9J5_device_models.zip`.
4. Later, only if every gate passes: the H3 training go (and whether to freeze plan v3).
