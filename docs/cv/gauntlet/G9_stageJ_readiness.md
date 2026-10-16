# G9 Stage J: frozen readiness criteria for H3 (written 2026-10-15, before any human label exists)

**Status: FROZEN.** These gates decide when the H3 fine-tune (`G9_stageI_finetune_prereg.md`) may be assessed and run, and how its
evaluation is judged. They are written before any label, model output or GPU run, and they change only by a dated addendum that says
why, never after seeing a result. Where this document and the Stage I prereg differ, **the stricter rule applies** (notably wrong ID:
≤ 2% here vs ≤ 3% in the prereg).

**Today's verdict: NOT READY.** No human labels exist yet (R1-R4 open), and the training pool is far below T1 for apple, banana and
tomato. **No GPU is requested and nothing is trained.**

Decision helpers: `ml/runs/G9/stageJ/scripts/j_agree.py` (agreement, adjudication, verified manifest, count gates) and
`ml/runs/G9/stageJ/scripts/j_gates.py` (Wilson-interval PASS / FAIL / UNCERTAIN rules). Both are covered by `test_j_agree.py`.

---

## 1. Labelling gates (R): the human-verified evaluation set

| ID | Gate | Rule |
|---|---|---|
| **R1** | Agreement | On the pilot batch: Cohen's κ(class, 9 labels) **≥ 0.85** and κ(supported: one of the 5 priority classes vs not) **≥ 0.80**, computed by `j_agree.py agree` on items both annotators labelled. If either floor is missed: the annotators re-read the guide together **with the adjudicator on 20 J-dev items** (never eval items), then relabel only the disagreeing pilot items, once. If the floor is still missed, the class definitions are revised by addendum before anything else happens. |
| **R2** | Eval counts | Adjudicated pilot items (J-eval only): **≥ 20 clean supported items per priority class** (apple, banana, citrus/orange, tomato, carrot; "clean" = whole, not cut, not in packaging, not occluded) and **≥ 100 in total**, plus **≥ 60 negatives**, of which unsupported/other produce ≥ 25, printed/screen ≥ 10, packaging ≥ 10, occluded ≥ 10. A sub-quota that is not met blocks only the metrics that depend on it (packaging/occluded → E3/E5), and more items for it are collected from an **eval-only** source (for example the team's own phone photos as a new source with its own session ids). |
| **R3** | Completeness | 100% of pilot items labelled by both annotators; every disagreement, every `uncertain` and every cut/bag tag mismatch adjudicated (`verified_summary_pilot.json: complete = true`). Final `uncertain`/`exclude` items are dropped, never guessed. |
| **R4** | Freeze | `verified_manifest_pilot.csv` and its `.sha256` are committed **before** any model (G3, H2, H3) is run on a J-eval image. The adjudicator may see the source page but not any model output. |

## 2. Training-data gates (T): the human-verified training set

| ID | Gate | Rule |
|---|---|---|
| **T1** | Volume | **≥ 150 human-verified clean training images per priority class** in J-train, from **≥ 2 independent sources per class**, at least one of them hand-held/phone-style. *(Target chosen by the agent: Stage H learnt from only 1-46 real photos per class and collapsed into `unknown`; 150 per class is a modest, reachable floor for fine-tuning a pretrained head, not a guarantee of success.)* |
| **T2** | Real-photo negatives | **≥ 150 verified real-photo negatives** (unsupported produce, printed/screen, packaging, occluded) in J-train for the `unknown` class, so "real photo → unknown" stops being a shortcut. |
| **T3** | Dev set | **≥ 10 verified clean items per priority class in J-dev** (thresholds are tuned on J-dev only). |
| **T4** | Training agreement | κ(class) ≥ 0.85 on the training batch, disagreements adjudicated the same way as R3. |
| **T5** | Separation and licence | Every J-train/J-dev image passes the licence audit (no NC/ND, no Pexels/Pixabay/Mixkit or other stock-site origin), and the partition audit: no uploader, artist, dataset or session in two splits; no pHash near-duplicate (Hamming ≤ 10) across splits or against any earlier set, including the stored M-TEST hashes. Training never uses J-eval, M-TEST, FruitNet, carrot_m or tomato_m. |

## 3. When H3 may run

H3 may be **assessed** (prereg re-read, compute and data budget written down) only when **R1-R4 and T1-T5 are all met**, and the
annotation completeness, class balance, diversity and agreement report has been sent to the user. It may **run** only with the user's
go, under the prereg's frozen design (free GPU, one attempt plus one infrastructure retry, `.pt` saved before export).

## 4. Evaluation gates (E): how an H3 result is judged

Measured on J-eval with human labels, policy thresholds frozen on J-dev, each eval split opened once. Every arm (G3, H2, H3) is
reported on exactly the same items. **A model cannot pass by abstaining:** E1 and E2 must hold together.

| ID | Gate | Threshold | Statistical rule (`j_gates.py`) |
|---|---|---|---|
| **E1** | **Genuine acceptance** = clean supported priority items verified with the **correct** class | **≥ 0.60** pooled and on the Commons part (I-eval-A); **≥ 0.50** on the phone-dataset part (I-eval-B); and **≥ 0.40 for every priority class** separately | `at_least`: PASS if the point estimate meets the threshold **and** the 95% Wilson lower bound ≥ threshold − 0.10; FAIL if the upper bound is below the threshold; otherwise UNCERTAIN |
| **E2** | **Wrong ID** = supported items accepted as a different class | **≤ 2%** of supported items pooled, **0** wrong-ID grades, and 0 wrong ID among the 5 priority classes on I-eval-A | `at_most(thr 0.02, upper cap 0.06)` + `zero_required` |
| **E3** | Unsupported / printed / packaging / cut acceptance | **≤ 2%** and **0 graded** | `at_most(0.02, 0.06)` + `zero_required` |
| **E4** | Other produce (lime, guava, pomegranate, ...) accepted as a priority class | **≤ 3%** | `at_most(0.03, 0.08)` |
| **E5** | Occlusion leakage | Stage H synthetic suite **≤ 3% overall and ≤ 5% per type**; human-tagged real occluded items: **0 graded** | point thresholds (suite n ≥ 900) + `zero_required` |
| **E6** | Latency | H3 **p95 ≤ 60 ms** (sandbox CPU); the close-up path p95 is reported against 700 ms | point |
| **E7** | Better than what exists | H3 genuine acceptance higher than both G3 and H2 on the same items, with wrong ID no higher | point, same items |
| **E8** | Nothing else breaks | TS and Python tests pass; the e2e CV flow and Android tests are preserved; A/B/C grades stay blocked; 64 px GrabCut is not adopted until its extra leakage is fixed | tests |

**Uncertain results.** If any of E1-E4 is UNCERTAIN, the result is reported as **uncertain, not a pass**. More J-eval-style items are
collected and labelled under R1-R4 (target ≥ 40 clean supported per class), and the **same frozen model** is re-evaluated once on the
enlarged set. No retraining between the two looks.

**What a pass does not mean.** Passing E1-E8 does not promote H3 to users and does not enable grades. Showing a grade needs its own
frozen criteria and an independent validation (Stage H A8 stays in force).

## 5. Reference: why these numbers

- Stage H **H-A5** required correct-ID verification ≥ 0.60 with clean false reject ≤ 0.20; H-final reached **0.14**: it was safe only
  because it abstained on about 90% of real items. E1 restates that floor per split and per class so it cannot be met by accepting one
  easy class.
- Stage H **H-A2** allowed wrong ID ≤ 3%; the user tightened it to **≤ 2%** for H3 (2026-10-15 instruction).
- H-A3, H-A4 and H-A6 carry over as E3, E5 and E6 unchanged.
- With 100 items, a 95% interval is about ±10 points, which is why the E1 margin is 0.10 and why borderline results are UNCERTAIN
  rather than pass/fail.
