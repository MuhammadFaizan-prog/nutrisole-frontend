# CV dashboard: NutriSole produce detection + visual grading

Last update: G5 (2026-10-13). Reports: [G1](gauntlet/G1.md), [G2](gauntlet/G2.md), [G2 failures](gauntlet/G2_failures.md), [G3](gauntlet/G3.md), [G3 failures](gauntlet/G3_failures.md), [G4](gauntlet/G4.md), [G4 failures](gauntlet/G4_failures.md), [G5](gauntlet/G5.md), [G5 failures](gauntlet/G5_failures.md), [G6 plan](gauntlet/G5_next.md).
Device for every number: sandbox CPU (2 cores aarch64, onnxruntime / PyTorch CPU). This is not a phone or an emulator. Training: CPU (G1), Kaggle free T4 (G2-G4). Gauntlet clips are synthetic clips from locked TEST images; from G4 the gauntlet is fixed-frame (deterministic).

## Current champions
| component | champion | since | notes |
|---|---|---|---|
| Detector | **G3 yolo11n 640 -> 480 raw+NMS** (G3 control) | G3 | Kept in G4 and G5 under both views. G5 fine-tunes ft0/fthn/fthnc reach pooled 0.348/0.331/0.360 but fail strict (tomato, banana) and the gauntlet (best fthnc 0.583 segments, 6.25 FA/min). Pooled n=829 mAP50 0.314; fixed-frame gauntlet det segments 0.667, FA 1.25 / 0.00 per min (G1 neg / negtest). A1 hygiene-off has higher pooled mAP50 (0.385) but fails the gauntlet (0.458 segments, 6.25 FA/min). Strict per-class rule vs G1 still fails (test_rf citrus -15.5, capsicum -7.6; all test_rf capsicum boxes are sliced strips) |
| Quality classifier | **G3 yolo26n-cls 224 E (quality2-g3crop, Kaggle), T=0.25 in the app** | G3 | G5 cls5 fails held-out lighting (night_sodium_hard 0.975, tube_light_hard 0.941). G4 cls4 passes both gates (low light rotten recall 0.975, crop 0.992) but is not promoted: held-out night_sodium_hard rotten recall 0.983 -> 0.941 and no gauntlet change |
| Scene guard | **maxSameClass off (0), minAreaFrac 0.01** (TS + Python) | G4 | rule 2 off gains one det segment on the fixed-frame gauntlet with identical FA |
| Measurements / rubric | measure-v0.3-g2 / rubric-v0.2-g2 (agreement gate 0.05) | G2 | rubric grade thresholds still untuned (no human graders) |
| Temporal rescoring | off by default (code + parity test shipped) | G5 | TEST w3: det segments 0.667 -> 0.625, static flicker 0 -> 0.417 |
| Tracker | scoreAlpha 0.2 (G2 default) | G2 | DEV tune rejected on the G4 TEST gauntlet (grade flicker 0 -> 0.62, frame acc down) |
| Ripeness | interface only (separate chip; Py + TS) | G4 | first CPU run (yolo11n-cls 224, test_cc0 n=180 acc 0.661) invalid: 0 overripe train images (folder typo); rerun in G5 |
| Two-stage (det + type crop cls) | not adopted | G4 | test_rf 0.337 -> 0.353, test_oiv7c 0.549 -> 0.542, CPU p50 49 -> 122 ms |
| Prices | official Lahore retail rate-list OCR | G4 | kept cells 254/254 correct, priced-row recall 0.886 (2026-10-12 in-sample for the lexicon) |

## Headline numbers by iteration
| metric | G1 | G2 best candidate | G3 champion (yolo11n@480) | G4 best candidate | G5 best candidate | gate |
|---|---|---|---|---|---|---|
| Det test mAP50 / 50-95 (n=557) | 0.125 / 0.065 | 0.315 / 0.188 (yolo11n@480) | 0.224 / 0.139 | 0.323 / 0.200 (A1 hyg-off@480) | 0.288 / 0.177 (ft0) | mAP50 >= 0.85 (FAIL) |
| Det test_rf mAP50 / 50-95 (n=149) | 0.323 / 0.177 | 0.375 / 0.256 | 0.355 / 0.231 | 0.406 / 0.266 (A1) | 0.393 / 0.258 (fthnc) | |
| Det test_oiv7 mAP50 (n=123) | 0.112 | 0.144 | 0.381 | 0.454 (A2 bg15) | 0.522 (fthnc) | |
| Det test_oiv7c mAP50 (n=181, new in G4) | - | - | 0.634 | 0.665 (A1) | 0.629 (ft0) | |
| Det pooled mAP50 (n=829) | 0.095 | 0.253 | 0.314 | 0.385 (A1) | 0.360 (fthnc) | |
| Neg images with any box (n=80) | 2.5% | 2.5% | 2.5% | 0.0% (A1) | 0.0% (fthnc) | |
| Fixed-frame gauntlet det segment acc (24 seg) | 62.5% | - | 66.7% (guard rule 2 off) | 66.7% (A2; A1 45.8%) | 58.3% (fthnc) | |
| Fixed-frame FA/min G1 neg / negtest | 3.75 / 1.88 | - | 1.25 / 0.00 | best still the control | 6.25 / 1.50 (fthnc) | <= 1 (FAIL, close) |
| Cls rotten recall test (n=270) / synthetic low light | 0.992 / 0.857 | 0.992 / 0.966 | 0.983 / 0.941 | 0.992 / 0.975 (cls4, not promoted) | 0.992 / 0.975 (cls5, not promoted) | low light >= 0.95 (champion FAIL, cls4 pass) |
| Cls rotten recall on item crops | 0.983 | 0.941 | 0.992 | 0.992 (cls4) | 0.992 (cls5) | >= 0.983 |
| Grading proxy TEST (cls+rules, n=270) | 0.669 | 0.978 | 0.981 | 0.985 (cls4) | 0.996 (cls5) | weak proxy, no kappa |
| OWLv2 zero-shot mAP50 test_rf / test_oiv7 | - | - | - | 0.685 / 0.542 (teacher only) | - | |
| Export parity (ONNX) | PASS | PASS | PASS | PASS | PASS (fthn, fthnc, cls5); ft0 1 box/681 beyond tol | |
| Repo checks | all EXIT 0 | all EXIT 0 | all EXIT 0 | all EXIT 0 | all EXIT 0 | |

## Open gates
No Lahore data, no phone/emulator, no human grading panel, real-world latency unmeasured (all **unverified**); detector far below target; champion FA 1.25/min on the G1 neg clip (> 1); guava not detectable. CAPA data is research-only pending ULG consent. OWLv2 review queue (1 172 items) all pending human review.
