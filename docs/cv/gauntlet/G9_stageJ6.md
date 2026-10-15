# G9 Stage J6 (no training): P729 amendment, Android P1 host checks, CV→data mapping, human-eval gaps, training candidates, H3 plan

Written 2026-10-16 (PKT). Continues J5 (local `02e6f76` = remote `cv-gauntlet` `dedb110`; device `ca521e3` = remote `f4fbc41`; both remote
heads were authored by the sync script only, so there were no user commits to mirror). The user's brief of 2026-10-16 00:06 PKT is
authoritative. **Unchanged:** G3 champion, H2 v2 experimental, grades blocked, M-TEST sealed, `h3_guard` unchanged and REFUSED, frozen gates
and frozen plan v2 untouched. No Kaggle, no training, nothing deleted, `main` (`0bac361`) untouched.

## 1. P729 (approved)
Amendment `G9J5-HRAI-v1/amendment_001` → record **v2** = v1 + amendment, in `ml/runs/G9/stageJ/out/j5/human_review_ai_assisted_v2/`
(`amendment_001_P729.json`, `reviewed_labels_pilot2.csv`, `.sha256` files, README; script `scripts/j6_p729_amendment.py`, `--check` verifies).
P729: `uncertain` → **carrot**, bag=1, multi=1, cut=0, rotten=0, not occluded (in this schema `occluded` is a label) → role `supported_packaged`
(must-not-grade). Approval source: M Faizan's chat message, Fri 2026-10-16 12:06 AM PKT; his evidence: real orange carrots in
transparent wrapping, sufficiently visible. Matches the Hark v2 row exactly. v1 record/tables and the original AI CSV (`6c17debf…`) are
byte-identical (re-checked). Tier stays `HUMAN_REVIEWED_AI_ASSISTED`: never blind, kappa, verified manifest, training label or H3 unlock
(the amended table is still refused by `j_agree agree`). pilot2 uncertain 119 → 118; disputed rows 1 → 0.

## 2. Android (cv-gauntlet-device) — see `G9_stageJ6_ANDROID_P1_ADDENDUM.md` on that branch
P0 env verified (RN 0.86.3, VisionCamera 5.2.3, worklets 0.12.2, onnxruntime-react-native 1.24.3 installed). Host checks, all **host-side**:
G3 + H2 ONNX I/O equal `MODEL_IO` with real runtime metadata (onnxruntime Python 1.31 and onnxruntime-node 1.24.3; sha256 = `models.ts`);
TS vs Python preprocessing parity on 16 real stills + 3 synthetic: detector tensor max abs 0.0051 (tol 2/255), H2 tensor 0, H2 top-1 16/16,
detector class sets 13/16 identical at the 0.25 decode floor; harness end-to-end 26 simulated taps: 2 named + Not graded, 24 Unable to
identify, 0 contract errors, 0 grades; host init h2 71 ms / g3 29 ms, RSS +36 MB; G3 p50 45 ms, H2 p50 4.5 ms, 3-still pipeline p50 158 ms
(2 vCPU sandbox). Debug camera now shows **REAL INFERENCE** (green, only with loaded sessions + a pipeline result) vs **PLACEHOLDER**
(orange); init/latency/UI-lag/domain NSCV lines. Gradle debug build **not feasible in the sandbox** (no JDK/SDK/NDK; background processes do
not survive; 120 s command cap; 2 vCPU/7 GB). Metro bundle re-run timed out twice (J5 bundle OK). Phone performance: none claimed.
Demo: `files/g9/stageJ/handoff/G9_stageJ6_demo.mp4` (1280×720, ~2 min), rendered from the real host run, labelled host-side, not a phone.

## 3. CV → data mapping
`native/src/cv/domainMap.ts` (one module; committed on cv-gauntlet and cherry-picked onto the device branch). Details and the remaining
connections: `G9_stageJ5_pipeline_connection_audit.md` § "J6 update". Missing: Scan screen does not consume CV; no verified price-list
ingestion in the app; UI nutrition uses the demo catalog; grading blocked by design; glucose/diet/footwear/assistant not linked to CV.

## 4. Remaining human-evaluation requirements (frozen gates, unchanged)
- **R1** κ(class) ≥ 0.85 and κ(supported) ≥ 0.80 between **two independent annotators** on **pilot (265) + pilot2 (335)** — the gate names these packs.
- **R3** both annotators label 100 %; every disagreement / uncertain / cut-bag mismatch adjudicated by a **third human**.
- **R2** among adjudicated J-eval: ≥ 20 clean supported per class, ≥ 100 total, ≥ 60 negatives; sub-quotas unsupported ≥ 25, printed ≥ 10,
  **packaging ≥ 10, occluded ≥ 10** (guard checks both).
- **R4** verified manifest + sha256 committed before any model sees a J-eval image (no CV model has been run on pilot/pilot2).
- **Exposure:** the 600 pilot/pilot2 images whose AI labels M Faizan reviewed **cannot be claimed blind for him**; he cannot be annotator A
  or B on them. The frozen gates do **not** require unexposed *images*; they require *independent, blind annotators*. The existing blind
  packs (`NutriSole_G9J_ANNOTATOR_A/B.zip`, no AI labels inside, hashes verified in J4) still qualify if both annotators are people who have
  not seen the AI labels or the post-hoc zip (e.g. the two FYP teammates). Adjudicator: any third human per the letter of R3; we recommend
  someone other than M Faizan because of his exposure (if he adjudicates, record it).
- **Genuinely unexposed pool needed for the sub-quotas:** if pilot+pilot2 verified exactly as reviewed (informational only), packaging
  would be 5 (incl. P729) and occluded 3 → at least **5 more verified packaging and 7 more verified occluded** items, which only the
  `team_eval` photos (not yet taken; quota 46 bagged + 46 partly hidden, J5 quota sheet) can supply. Plus 202 `uncertain` rows (84 + 118) go to adjudication.

## 5. Training data (all unverified candidates; J-train/J-dev/J-eval and sealed M-TEST separation preserved)
J6 batch `scripts/j6_candidate_pool.py` (reuses j5 filters): **267 new candidates** from Wikimedia Commons per-file CC/PD (93 dropped as
pHash ≤ 10 to the 57,575 reference hashes incl. M-TEST stored hashes, or ≤ 6 to the J5 pool): apple 73, orange 41, tomato 45, banana 21,
hard negatives 87 (objects 59, printed 18, persimmon 10). No Pexels/Pixabay/Mixkit/Unsplash. Zenodo: none added. Coverage
(`out/j6/candidates/j6_coverage_vs_quota.json`, exploratory 0.55 Commons yield, human-verified now 0, T1 = 150 verified/class):
| Class | J2 shortfall | J5 + J6 candidates | Expected | Projected remaining |
|---|---|---|---|---|
| apple | 65 | 42 + 73 | 63.3 | **≈ 2** (borderline; team phone apples ≥ 75 still recommended) |
| orange | 8 | 53 + 41 | 51.8 | 0 |
| tomato | 8 | 39 + 45 | 46.3 | 0 |
| banana | 4 | 28 + 21 | 27.0 | 0 |
None of it counts until two annotators + adjudicator label it.

## 6. H3
`G9_stageJ5_H3_plan_v3_DRAFT.md` updated in place (§5 balanced sampling + phone-camera augmentations from H2 v2 weights, same architecture;
§6 baselines G3 46/99, H2 v2 9/99 accepted, 0 wrong; §7 comparison incl. per-class accuracy, abstention, grading eligibility, latency;
§8 preregistered criteria). Not frozen, not launched. Blockers: no human-verified labels (R1–R4, T1–T4), no user go.

## 7. Tests
ML 161/161 (92 stageJ incl. 5 `test_j6.py` + 69 eval/grading/prices/autolabel), native 161/161 on cv-gauntlet (+6 `cvDomainMap`) and
178/178 on the device branch (+6 `cvDomainMap`, +6 `cvDeviceJ6`), web 5/5, expansion 8/8, runtime 28 OK, `native/src/cv` tsc clean; app
code 0 tsc errors (45 pre-existing errors only in older tests, unchanged).

## 8. Needs the user
1. P1 on your phone (addendum), then send the log, three meminfo files, recording and screenshots.
2. Two annotators who have not seen the AI labels (pilot + pilot2 blind zips) and a third-human adjudicator; team eval photos (bagged / partly hidden).
3. Later: whether to freeze the H3 v3 draft; any training go only after every gate passes.
