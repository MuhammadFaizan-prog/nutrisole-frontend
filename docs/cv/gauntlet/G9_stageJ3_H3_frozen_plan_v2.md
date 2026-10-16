# G9 H3: frozen, ready-to-run fine-tune plan, version 2 (Stage J3, written 2026-10-15 PKT, NOT RUN)

**Status: FROZEN, NOT RUN, BLOCKED.** This is a new versioned document. It does not edit or replace
`G9_stageI_finetune_prereg.md` (v1) or `G9_stageJ_readiness.md`; it turns them into an executable plan. Where they differ, the
stricter rule applies. Human-verified images today: **0**, so the launch guard refuses. **No GPU, no training, no grades.**

## 1. Preconditions (all enforced by `ml/runs/G9/stageJ/h3/h3_guard.py`)

| Gate | Rule (from `G9_stageJ_readiness.md`) | How the guard checks it |
|---|---|---|
| R1 | κ(class) ≥ 0.85 and κ(supported) ≥ 0.80 on pilot and pilot2 | `agreement.json` (hash-checked) of each batch |
| R2 | ≥ 20 clean supported per priority class, ≥ 100 total, ≥ 60 negatives (sub-quotas reported) on pilot + pilot2 (+ team_eval) | recomputed with `j_agree.readiness_counts` from the verified manifests |
| R3 | 100% coverage, every disagreement adjudicated by a third human | `verified_summary_*.json: complete = true` |
| R4 | verified eval manifests frozen (`.sha256`) before any model sees a J-eval image | `.sha256` present and matching |
| T1 | ≥ 150 verified clean training images per priority class from ≥ 2 sources | recomputed from train + train2 (+ team_train) |
| T2 | ≥ 150 verified real-photo negatives in J-train | recomputed |
| T3 | ≥ 10 verified clean J-dev items per priority class | recomputed |
| T4 | κ(class) ≥ 0.85 on the training batches | `agreement.json` |
| T5 | no eval item / eval-only source (FruitNet, carrot_m, tomato_m) in training; splits J-train/J-dev only; pHash ≤ 10 against the complete reference manifest `out/j3_reference_hashes.json` (57,575 hashes, incl. M-TEST stored hashes) | key/source overlap in the guard; pHash at ingestion (`j_team_phone.py`, `j2_audit.py`) and again in-kernel (`--eval-hashes`) |
| GO | the user's own `h3/USER_TRAINING_GO.json`: `go: true`, `experiment: "H3"`, `given_by`, ISO `given_at`, `plan_sha256` = sha256 of this file, `manifest_sha256` = the verified manifest hashes | `check_go()`; the agent never writes this file |

The guard exits 2 (REFUSED) on any miss. `h3_launch.py` calls the guard before it prepares anything.

## 2. Model and initial weights (existing, unchanged)

- **H3 arm:** timm `mobilenetv3_small_100`, 13 outputs (12 classes + `unknown`), initialised from the existing Stage H v2 weights
  `/workspace/work/g9h/h2v2/h2_mnv3s.pt` (sha256 `02b402a1302a437cab59c8ddecae1cfd117fbc4a511529cdb9e7be6a7b09bd82`). The kernel refuses
  any other initial file in a real run. No class is dropped or merged.
- **Detector:** the G3 champion (E224) stays frozen as the detection front end; it is not retrained. Full-pipeline latency is measured
  with it in the loop.
- **Baselines:** G3 (E224 detector + its class head) and H2 v2 as they are today; both are re-run on exactly the same J-eval items.

## 3. Training data and recipe (fixed now)

- Human-verified **J-train** (pilot training packs 1 + 2, team_train) plus the legacy Kaggle pools capped at ≤ 30% of draws; thresholds
  tuned on **J-dev** only. J-eval, M-TEST, FruitNet, carrot_m, tomato_m never enter training. In-kernel pHash drop (Hamming ≤ 10)
  against all J-eval and stored M-TEST hashes.
- Crops made the way the pipeline crops (detector box / tap-ROI, sides 96–400 px); `unknown` gets real-photo negatives in the same
  proportion as each supported class.
- Sampler: priority classes 2× weight, others ≥ 1× class-balanced. AdamW, head lr 3e-4, backbone lr 1e-4, weight decay 0.05, batch 64,
  ≤ 12 epochs, early stop (patience 3) on J-dev priority-class macro accuracy, seed 0.
- Free Kaggle GPU only; **one attempt plus at most one infrastructure retry** (no change of data, code or criteria between them).
  `.pt` saved **before** ONNX export. Kernel: `ml/runs/G9/stageJ/h3/kernel/run_h3.py` (dry-run verified locally on a synthetic set, CPU,
  ~7 s; that run is not a result).

## 4. Evaluation (each eval split opened once, human labels, same items for every arm)

Policy thresholds frozen on J-dev, then `h3_compare.py` computes the table below with `j_gates.py` (Wilson PASS / FAIL / UNCERTAIN).
**A model cannot pass by abstaining:** E1 and E2 must hold together. UNCERTAIN is reported as uncertain, never as a pass.

## 5. Baseline comparison table (template; filled only after a guarded run)

| Metric (same human-verified J-eval items) | G3 (E224) | H2 v2 | H3 | Threshold |
|---|---|---|---|---|
| Recognition: top-1 on clean supported items | | | | report |
| **E1** genuine acceptance (accepted with the correct class), pooled / I-eval-A / I-eval-B | | | | ≥ 0.60 / ≥ 0.60 / ≥ 0.50 |
| E1 per priority class (apple, banana, citrus, tomato, carrot) | | | | each ≥ 0.40 |
| **E2** wrong ID (supported accepted as another class) | | | | ≤ 2%, 0 graded, 0 priority wrong-ID on I-eval-A |
| **E3** unsupported / printed / packaging / cut accepted | | | | ≤ 2%, 0 graded |
| **E4** other produce accepted as a priority class | | | | ≤ 3% |
| **E5** occlusion leakage: Stage H synthetic suite (n ≥ 900) / human-tagged real occluded | | | | ≤ 3% overall, ≤ 5% per type / 0 graded |
| Grading safety: items shown any A/B/C grade | | | | **0** (grades blocked) |
| **E6** full-pipeline latency p50 / p95 (detector + crop + classifier, sandbox CPU) | | | | p95 ≤ 60 ms; close-up path vs 700 ms |
| **E7** H3 better than G3 and H2 (genuine acceptance higher, wrong ID not higher) | – | – | | PASS required |
| **E8** TS/Python/native tests, e2e CV flow, Android tests preserved; grades blocked | | | | all pass |

Synthetic dry run of the table generator: `h3_compare.py --dry-run` (clearly marked "SYNTHETIC DRY RUN - not results").

## 6. What a pass does not mean

Passing E1–E8 does not promote H3 to users and does not enable grades. Grade display needs its own frozen criteria and an independent
human grading panel. The hard-coded UI demo values ("Confidence 97%", "Grade A") are never evidence and never an input to this table.

## 7. Run order once humans have delivered

1. `j3_merge_evidence.py` → `j_agree.py agree` → adjudication → `j_agree.py verify` for pilot, pilot2, train, train2 (+ team batches).
2. Lead writes `h3/h3_inputs.json` (paths only). `h3_guard.py` → must PASS on gates; send the readiness report to the user.
3. The user writes `h3/USER_TRAINING_GO.json` himself (template in `h3/USER_TRAINING_GO.TEMPLATE.json`).
4. `h3_launch.py --prepare` (guard again) → `kaggle kernels push` once.
5. Run G3, H2 and H3 on the frozen J-eval; `h3_compare.py` → table above, committed with the predictions CSV and hashes.
