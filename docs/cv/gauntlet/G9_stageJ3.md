# G9 Stage J3: phone-photo ingestion, original-image review, human handoff and guarded H3 plan (2026-10-15 PKT)

**No training, no GPU, no grades, no main, no deploy. Backend/Supabase and other FYP modules stay queued.** Human-verified CV
images: **0**. Independent human exports: **0**. H3: **BLOCKED** (launch guard refuses). G3, H2, all weights, checkpoints, datasets,
results, frozen gates and the project lead's AI reviews are unchanged. The full FYP scope is preserved (see `G9_FYP_requirement_status.md`).

## Step 1. State
Remote `cv-gauntlet` head was `d337188` (unchanged since the last sync); local `4e8bc47` mirrored it. No reconcile needed.

## Step 2. Team phone ingestion (`ml/runs/G9/stageJ/scripts/j_team_phone.py`)
- **Earlier-reference check on by default.** New committed manifest `out/j3_reference_hashes.json` (+ `.sha256`): **41 sets, 57,575 unique
  64-bit pHashes, hashes only** (no paths, names or pixels). Built by `j3_ref_hashes.py` from G0–G7 data folders (109,437 files hashed),
  G3 train / DEV val / DEV clips, G7 keyframes, Stage D/E/F pools, CU, Stage H set and in-kernel list, Stage I candidates, Stage J/J2
  candidates, and the **stored M-DEV + M-TEST hashes (M-TEST pixels never opened; `/workspace/work/cv/g9e` skipped)**. Each set has a role
  (train_source / earlier_eval / mixed→treated as training). Missing manifest = refusal, not a silent skip.
- **Eval photos are now checked too:** an eval photo within Hamming ≤ 10 of an earlier **training source** is quarantined; one that
  repeats an earlier eval/holdout set is quarantined as not-new evidence. Train photos: unchanged rule (near any eval photo or reference).
- **Provenance record per photo:** sha256, session, photographer, date, place, purpose, licence, consent, ingested_at.
- Photos must sit in their own session folder; byte-identical files are recorded (`exact_duplicate_of`) and grouped.
- **Blind packs:** `--out-dir DIR --packs` writes the lead-only manifest, provenance CSV and `team_blind_key.csv`, then builds
  annotator packs `team_eval` (Q###) / `team_train` (R###) with `j2_pack.build_from` (same tool, guide, seeds 101/202, fallback CSV,
  contact sheets as Pilot 1/2; EXIF rotation applied, all metadata dropped). Blind ids follow sha256 order, so they encode neither class
  nor condition; packs contain no file names, session ids, photographer names or intent fields (tested by grep).
- `j_agree.py` accepts `--batch team_eval|team_train --key DIR/team_blind_key.csv`; `j2_pack.py` is import-safe (CLI unchanged).
- Note: the shot list's §8 still shows the older `--ref-hashes` command and stub caveat; `SUBMISSION_STEPS.md` in the team zip and this
  section describe the current behaviour (his shot list file was left as he wrote it).

## Step 3. Recovered originals, AI review v2 (`out/handoff/20261015_pilot2_visual_review_v2_hark/`, AI_ASSISTED_NOT_HUMAN)
New versioned review; his `20261015_pilot2_visual_review/` (CSV `6c17deb…d2aa`, SHA256SUMS, revision log) is byte-identical (71 files checked).

| Item | Original | v1 (his) | v2 (Hark) | Finding |
|---|---|---|---|---|
| P729 | 3333×2138 | uncertain, B M | **carrot, B M** | Only whole real carrots, most fully visible in an open clear bag; the opaque object is a cling-wrapped non-produce package on top. Same-kind pile + clear-bag rules → carrot+B+M. Adjudicator may still choose uncertain/exclude (frame centre falls on the package); with B it is a must-not-grade packaged negative either way. |
| P756 | 1600×902 | other_produce / other | unchanged (confidence → high) | Ridged orange fruit (Jacaratia spinosa) in a hand, > half visible; not a carrot, not occluded. |
| P773 | 536×471 | apple, B M | unchanged | The "original" is the same size as the package (no extra resolution). Apples individually clear-wrapped plus one unwrapped apple; visible, not occluded. |

The full 335-row v2 CSV sits under `AI_ASSISTED_NOT_HUMAN/`, so `validate_human_pair` refuses it (exact and ≥ 95% near-copy) — tested.

## Step 4. Human handoff (zips not in git; `files/g9/stageJ/handoff/`)
Built by `j3_handoff_build.py`; every inner pack sha256 re-verified against `out/j_packs.json` / `out/gaps/j2_packs.json`; AI-leak grep of
every annotator and team zip (recursing into inner zips) = clean. See `G9_stageJ3_missing_inputs_checklist.md`.

| Zip | For | Contents |
|---|---|---|
| `NutriSole_G9J_ANNOTATOR_A.zip` (43.6 MB) | annotator 1 | pilot + pilot2 annotator1 packs, guide, one-page instructions, blank self-attestation |
| `NutriSole_G9J_ANNOTATOR_B.zip` (43.6 MB) | annotator 2 | same with annotator2 packs |
| `NutriSole_G9J_ANNOTATOR_A_training.zip` / `_B_training.zip` (63.9 MB each) | phase 2 | train + train2 packs, guide, instructions, attestation |
| `NutriSole_G9J_TEAM_PHOTOS.zip` | photographers | shot list, `sessions_TEMPLATE.csv`, submission steps |
| `NutriSole_G9J_ADJUDICATOR.zip` (8.1 MB) | third person | 18 recovered originals (≤ 2048 px), adjudication instructions, guide, readiness gates. No AI labels. |
| `NutriSole_G9J_ADJUDICATOR_AI_POSTHOC_release_after_exports.zip` | adjudicator, **after** both exports | v1 265 + v1 335 AI reviews, v2 corrections |

`j3_merge_evidence.py` turns the two self-filled attestation files into the evidence JSON `j_agree.py agree --evidence` needs, binding the
exact CSV sha256 (nothing is filled in for a person).

## Step 5. H3 (prepared, not run)
- Frozen plan v2: `G9_stageJ3_H3_frozen_plan_v2.md` (existing H2 v2 `.pt` `02b402a1…bd82` as the start; G3 E224 detector frozen; baseline
  table for recognition, genuine acceptance, wrong ID, unsupported, occlusion leakage, grading safety and full latency).
- Kernel `h3/kernel/run_h3.py`: dry run on a synthetic set, CPU, ~7 s, `.pt` saved before ONNX, J-eval rows refused.
- `h3/h3_guard.py`: PASS only if the verified human manifests pass R1–R4/T1–T5 (recomputed, hash-checked) **and** the user's own
  `USER_TRAINING_GO.json` names the plan sha256 and the manifest hashes. Today: **REFUSED** (no manifests, no go file).
- `h3/h3_launch.py` (guard first; `--dry-run` for the local smoke test), `h3/h3_compare.py` (E1–E8 table via `j_gates`, dry run marked
  synthetic).

## Tests (2026-10-15, sandbox)
ML pytest **141/141** (120 + 12 Stage J3 ingestion/review/evidence + 9 H3), native `node --test` **122/122**, web `npm test` **5/5**,
`npm run test:expansion` **8/8**, `npm run check:runtime` **28 protected files OK**.
