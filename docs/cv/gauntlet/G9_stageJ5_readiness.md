# G9 Stage J5: H3 readiness report (2026-10-15 PKT)

**Verdict: NOT READY. H3 guard REFUSED** (`ml/runs/G9/stageJ/out/j5/h3_guard_report_j5.json`: no verified human manifests, no user go).
Human-verified images (independent double annotation + adjudication): **0**. Kappa: **not computable** (only one label set exists per item).
The J5 human-review record (one non-blind reviewer confirming AI-assisted labels, provenance `HUMAN_REVIEWED_AI_ASSISTED`) is kept and
reported, but the frozen gates do not accept a single-reviewer tier, so it unlocks nothing. No gate was loosened.

| Gate | Status | Why / what clears it |
|---|---|---|
| R1 κ ≥ 0.85 / 0.80 on pilot + pilot2 | **FAIL** | needs two independent blind annotators; the reviewed AI labels are one non-independent set |
| R2 eval counts | **FAIL** (not verified) | if the reviewed labels were verified they would give clean supported apple 55, banana 41, citrus 52, tomato 40, carrot 41 (229 total) and 168 negatives, **but packaging 4 < 10 and occluded 3 < 10** — informational only, never a gate value |
| R3 completeness + third-human adjudication | **FAIL** | no annotator exports, no adjudicator; 203 `uncertain` rows (84 + 119) + P729 would need adjudication |
| R4 frozen verified manifest | **FAIL** | no verified manifest exists (the J5 reviewed-label tables are hash-frozen but are not verified manifests) |
| T1 ≥ 150 verified train / class, ≥ 2 sources | **FAIL** | 0 verified; projected after training packs: apple 85, banana 146, citrus 142, tomato 142, carrot 151; + 162 unverified Commons candidates + team photos |
| T2 ≥ 150 real negatives | **FAIL** | 0 verified (projected 152) |
| T3 ≥ 10 J-dev per class | **FAIL** | 0 verified (79 J-dev items await labels) |
| T4 κ on training batches | **FAIL** | no training labels |
| T5 separation / licence | structurally clean for the reviewed eval items | 0 key overlap, 0 Commons uploader overlap, 0 shared datasets, no eval-only source in training, 0 pHash ≤ 10 pairs among 467 eval × 900 train images on disk (340 images not on local disk; J2 audit covered all at ingestion) |
| GO | **absent** | only the user writes `h3/USER_TRAINING_GO.json`, after R1–R4/T1–T5 pass |

**Training-label use of the reviewed AI labels: no.** Frozen T1 counts only *human-verified* J-train images; T4 needs κ on the training
batch; and every reviewed item is in **J-eval** (pilot / pilot2), which T5 forbids in training. The rule is unchanged.

## Blockers, in order
1. Two independent annotators + one adjudicator for pilot (265) and pilot2 (335): packs and guides are ready in the handoff folder.
2. Team eval photos for the packaging (need ≥ 10) and occluded (≥ 10) sub-quotas.
3. Training labels for train 461 + train2 646 (+ team training photos incl. orange, + the J5 candidate pool once packed).
4. The user's training go, naming plan v2 (or a user-frozen v3) and the verified manifest hashes.
