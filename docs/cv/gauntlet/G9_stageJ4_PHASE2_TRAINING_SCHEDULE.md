# NutriSole G9 Stage J4: Phase 2 labelling schedule (training batches 461 + 646)

Written 2026-10-15 (PKT). **No training is scheduled.** This plan only gets human labels for the training batches, without any
evaluation label leaking into training. H3 stays **BLOCKED** until R1–R4 and T1–T5 (`G9_stageJ_readiness.md`) pass **and** the user
gives the training go. M-TEST stays sealed. User-facing grades stay blocked.

**Day 0 (D0)** = the day the lead has received **both** annotators' Phase 1 exports (pilot 265 + pilot2 335) **and** both attestations,
and `j3_merge_evidence.py` + `j_agree.py agree` ran without refusal. Dates below are counted from D0, not from today.

## 1. Schedule

| Day | Who | What | Output |
|---|---|---|---|
| D0 | Lead | Merge evidence + agreement for `pilot` and `pilot2` (Windows guide, Part 2). Send adjudication sheets. **Then** release the training zips: `NutriSole_G9J_ANNOTATOR_A_training.zip` to A, `..._B_training.zip` to B | `agree_pilot`, `agree_pilot2` |
| D0–D1 | Adjudicator | Phase 1 adjudication (every disagreement, `uncertain`, cut/bag mismatch) | 2 completed sheets |
| D1 | Lead | `j_agree.py verify` for pilot and pilot2 → `verified_manifest_*.csv` + `.sha256` committed to `cv-gauntlet` (**R4 freeze**: before any model sees a J-eval photo). Agent reports R1–R3 | eval labels frozen |
| D1–D2 | A, B | **Train** batch (461): about 2 × 45-minute sittings; export after each sitting as backup; final export `G9J-train_annotator1_<Name>_461of461.csv` | 2 CSVs |
| D3–D4 | A, B | **Train 2** batch (646): about 3 × 45 minutes; final `G9J-train2_annotator1_<Name>_646of646.csv` | 2 CSVs |
| D4 | A, B | Fill and send `attestation_annotator1_training.json` / `..._annotator2_training.json` (same format as Phase 1; batches `train`, `train2`) | 2 attestations |
| D5 | Lead | Merge evidence + `j_agree.py agree` for `train` and `train2`; send sheets to the adjudicator | `agree_train`, `agree_train2` |
| D5–D6 | Adjudicator | Phase 2 adjudication | 2 completed sheets |
| D7 | Lead / agent | `j_agree.py verify` for train, train2; agent writes the T1–T5 status (per-class verified counts, sources, agreement) | readiness report |
| D0–D7 (parallel) | Team photographers | Team phone sessions (`G9_stageJ4_TEAM_PHOTO_INGESTION_RUNBOOK.md`); lead ingests each drop on arrival | `team_eval`, `team_train` packs |
| D8–D10 | A, B, Adjudicator | Label + adjudicate `team_eval` (first) and `team_train` packs, same procedure | verified team manifests |
| after D10 | User | Only if every R and T gate passes: decide on the H3 training go. Not before, and never implied by this schedule | — |

If a person is slower, everything after their step moves by the same number of days. Nothing is skipped to keep a date.

## 2. Leakage rules (frozen; apply to every batch)

1. **Order.** Training zips are released only after both Phase 1 exports are received (D0). Evaluation labels are frozen and committed
   (D1) before any training label is merged, and before any model runs on a J-eval photo.
2. **Separate items.** Evaluation batches (`pilot`, `pilot2`, `team_eval`) and training batches (`train`, `train2`, `team_train`) share no
   photo, no blind id, no Commons uploader and no team photographer. Checked now by `test_j4.py::test_frozen_eval_and_training_keys_are_disjoint`
   (600 eval keys vs 1,107 training keys: 0 shared) and at H3 time by `h3_guard.py` gate T5 (key overlap must be 0).
3. **Labels flow one way.** A training manifest is built only from `verified_manifest_train*.csv` / `team_train`. An evaluation CSV,
   evaluation adjudication sheet or `verified_manifest_pilot*.csv` is **never** an input to anything that trains, tunes or selects a model.
   Thresholds are tuned on J-dev only (the 79 `train`-batch items marked J-dev).
4. **No AI labels anywhere.** The `AI_ASSISTED_NOT_HUMAN` files are post-hoc reference for the evaluation adjudicator only; they are
   never sent to annotators and never merged into any training or evaluation label. `j_agree.py` refuses known AI CSVs, including
   near-copies.
5. **Same annotators, separate sittings.** A and B may label both phases, but they do not re-open Phase 1 photos or exports while doing
   Phase 2, and they still do not discuss photos with each other until both have exported.
6. **Team photos.** The split is fixed per session by `sessions.csv`; a photographer is either eval or train. Any training photo within
   pHash Hamming ≤ 10 of an eval photo or of the committed reference hashes (incl. M-TEST stored hashes) is quarantined by `j_team_phone.py`.
7. **M-TEST** stays sealed: not opened, not labelled, not used for any decision.

## 3. What the agent does meanwhile (no labels, no training)
Re-run the integrity check of every received file, run `merge` / `agree` / `verify` when the lead uploads files, commit outputs to
`cv-gauntlet` only, report R/T gate status, and keep the non-training app work (camera checks, runtime checks, data contracts) moving.
