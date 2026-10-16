# CV dashboard: NutriSole produce detection + visual grading

Last update: G7 (2026-10-13, early closeout). Reports: [G1](gauntlet/G1.md), [G2](gauntlet/G2.md), [G2 failures](gauntlet/G2_failures.md), [G3](gauntlet/G3.md), [G3 failures](gauntlet/G3_failures.md), [G4](gauntlet/G4.md), [G4 failures](gauntlet/G4_failures.md), [G5](gauntlet/G5.md), [G5 failures](gauntlet/G5_failures.md), [G6](gauntlet/G6.md), [G6 failures](gauntlet/G6_failures.md), [G6 dataset audit](gauntlet/G6_dataset_audit.md), [G6 web-mandi video benchmark](gauntlet/G6_video_benchmark.md), [G6 phone validation pending](gauntlet/G6_device_validation_pending.md), [G7 plan](gauntlet/G6_next.md), [G7](gauntlet/G7.md), [G7 prereg](gauntlet/G7_prereg.md), [G7 failures](gauntlet/G7_failures.md), [G7 data register](gauntlet/G7_data_register.md), [G7 numeric appendix](gauntlet/G7_results_autogen.md), [G8 plan](gauntlet/G7_next.md).
Device for every number: sandbox CPU (2 cores aarch64, onnxruntime / PyTorch CPU). This is not a phone or an emulator. Training: CPU (G1), Kaggle free T4 (G2-G4, G6, G7), Kaggle CPU (G5). Gauntlet clips are synthetic clips from locked TEST images; from G4 the gauntlet is fixed-frame (deterministic).

## Current champions
| component | champion | since | notes |
|---|---|---|---|
| Detector | **G3 yolo11n 640 -> 480 raw+NMS** (G3 control) | G3 | Kept in G4-G7 under both views. G7 from-scratch rpx arms (Kaggle T4): sA s0 pooled 0.282, sB s1 0.286, rfs (repeat-factor + apple/tomato floor) 0.311 - all fail rule 1 (> 0.314) and strict (test_rf banana -0.10 to -0.13, tomato -0.09 to -0.10); lemon->citrus wrong rate 0.658 -> 0.13-0.21; independent guava present-rate rfs 0.615 / sB 0.541 vs G6rpx 0.993; descriptive gauntlet worse than G3 (det seg 0.54-0.58 vs 0.667, FA 2.5-5.0/min). G6 fine-tunes from the G3 checkpoint (Kaggle T4, 1 seed): rp replay pooled 0.299, rpx (+OIV7c, guava, whole capsicum) pooled 0.310 (test_oiv7c 0.784) - both fail strict (rpx: test_rf apple -0.070, tomato -0.023). G5 fine-tunes ft0/fthn/fthnc reach pooled 0.348/0.331/0.360 but fail strict (tomato, banana) and the gauntlet (best fthnc 0.583 segments, 6.25 FA/min). Pooled n=829 mAP50 0.314; fixed-frame gauntlet det segments 0.667, FA 1.25 / 0.00 per min (G1 neg / negtest). A1 hygiene-off has higher pooled mAP50 (0.385) but fails the gauntlet (0.458 segments, 6.25 FA/min). Strict per-class rule vs G1 still fails (test_rf citrus -15.5, capsicum -7.6; all test_rf capsicum boxes are sliced strips) |
| Quality classifier | **G3 yolo26n-cls 224 E (quality2-g3crop, Kaggle), T=0.25 in the app** | G3 | G5 cls5 fails held-out lighting (night_sodium_hard 0.975, tube_light_hard 0.941). G4 cls4 passes both gates (low light rotten recall 0.975, crop 0.992) but is not promoted: held-out night_sodium_hard rotten recall 0.983 -> 0.941 and no gauntlet change |
| Scene guard | **maxSameClass off (0), minAreaFrac 0.01** (TS + Python) | G4 | rule 2 off gains one det segment on the fixed-frame gauntlet with identical FA |
| Measurements / rubric | measure-v0.3-g2 / rubric-v0.2-g2 (agreement gate 0.05) | G2 | rubric grade thresholds still untuned (no human graders) |
| Temporal rescoring | off by default (code + parity test shipped) | G5 | TEST w3: det segments 0.667 -> 0.625, static flicker 0 -> 0.417 |
| Tracker | IouTracker scoreAlpha 0.2 (G2 default) | G2 | G7: ByteTrack ported to TS behind `createTracker(kind)` (default `'iou'`, parity fixture); passes a post-hoc movable rule (exploratory) -> recommended phone A/B candidate; BoT-SORT (no ReID/GMC) passed DEV gate, TEST ID sw 27 vs ByteTrack 30 vs IoU 43, not adopted. DEV tune rejected in G4. G6 ByteTrack b15 (eval-only, `--tracker-kind bytetrack`): TEST r1 = r2 non-inferior (det seg 0.667, FA 1.25/0.00, q acc 0.929, rotten 0.875), fewer ID switches 30 vs 43, but not adopted: pre-registered rule needs grade flicker to fall (0 for both) and TTFC p90 933 vs 760 ms |
| Ripeness | **G7 per-fruit head (yolo11n-cls 224, 15 classes), wired OFF by default** | G7 | Kaggle T4; test_cc0 n=180 stage acc among assessed 0.989, overripe recall 0.967, top-1 0.972 (de-duplicated n=155: 0.968); hfbanana n=562 0.993. Single-fruit web photos, not market/Lahore/human-graded. Assessments schema (`ripeness/visibleDefects/freshness` with unable_to_assess) |
| Two-stage (det + type crop cls) | not adopted | G4 | test_rf 0.337 -> 0.353, test_oiv7c 0.549 -> 0.542, CPU p50 49 -> 122 ms |
| Prices | official Lahore retail rate-list OCR | G4 | kept cells 254/254 correct, priced-row recall 0.886 (2026-10-12 in-sample for the lexicon) |

## Headline numbers by iteration
| metric | G1 | G2 best candidate | G3 champion (yolo11n@480) | G4 best candidate | G5 best candidate | G6 best candidate | G7 best candidate | gate |
|---|---|---|---|---|---|---|---|---|
| Det test mAP50 / 50-95 (n=557) | 0.125 / 0.065 | 0.315 / 0.188 (yolo11n@480) | 0.224 / 0.139 | 0.323 / 0.200 (A1 hyg-off@480) | 0.288 / 0.177 (ft0) | 0.218 / 0.139 (rpx) | 0.224 / 0.141 (rfs) | mAP50 >= 0.85 (FAIL) |
| Det test_rf mAP50 / 50-95 (n=149) | 0.323 / 0.177 | 0.375 / 0.256 | 0.355 / 0.231 | 0.406 / 0.266 (A1) | 0.393 / 0.258 (fthnc) | 0.359 / 0.239 (rpx) | 0.385 / 0.262 (sB) | |
| Det test_oiv7 mAP50 (n=123) | 0.112 | 0.144 | 0.381 | 0.454 (A2 bg15) | 0.522 (fthnc) | 0.483 (rp) | 0.523 (sB) | |
| Det test_oiv7c mAP50 (n=181, new in G4) | - | - | 0.634 | 0.665 (A1) | 0.629 (ft0) | 0.784 (rpx) | 0.773 (rfs) | |
| Det pooled mAP50 (n=829) | 0.095 | 0.253 | 0.314 | 0.385 (A1) | 0.360 (fthnc) | 0.310 (rpx) | 0.311 (rfs) | |
| Neg images with any box (n=80) | 2.5% | 2.5% | 2.5% | 0.0% (A1) | 0.0% (fthnc) | 1.25% (rp, rpx) | 1.25% (sA, sB) | |
| Fixed-frame gauntlet det segment acc (24 seg) | 62.5% | - | 66.7% (guard rule 2 off) | 66.7% (A2; A1 45.8%) | 58.3% (fthnc) | 66.7% (control + ByteTrack; candidates not run) | 58.3% (rfs; descriptive, non-gating) | |
| Fixed-frame FA/min G1 neg / negtest | 3.75 / 1.88 | - | 1.25 / 0.00 | best still the control | 6.25 / 1.50 (fthnc) | 1.25 / 0.00 (control + ByteTrack) | 2.5 / 1.88 (rfs; descriptive) | <= 1 (FAIL, close) |
| Cls rotten recall test (n=270) / synthetic low light | 0.992 / 0.857 | 0.992 / 0.966 | 0.983 / 0.941 | 0.992 / 0.975 (cls4, not promoted) | 0.992 / 0.975 (cls5, not promoted) | no G6 classifier | no G7 classifier (night kernel pending) | low light >= 0.95 (champion FAIL, cls4 pass) |
| Cls rotten recall on item crops | 0.983 | 0.941 | 0.992 | 0.992 (cls4) | 0.992 (cls5) | - | - | >= 0.983 |
| Grading proxy TEST (cls+rules, n=270) | 0.669 | 0.978 | 0.981 | 0.985 (cls4) | 0.996 (cls5) | - | - | weak proxy, no kappa |
| OWLv2 zero-shot mAP50 test_rf / test_oiv7 | - | - | - | 0.685 / 0.542 (teacher only) | - | - | - | |
| Export parity (ONNX) | PASS | PASS | PASS | PASS | PASS (fthn, fthnc, cls5); ft0 1 box/681 beyond tol | PASS (rp, rpx) | PASS (sA, sB, rfs, ripeness) | |
| Repo checks | all EXIT 0 | all EXIT 0 | all EXIT 0 | all EXIT 0 | all EXIT 0 | all EXIT 0 | all EXIT 0 (9/9) | |

## Open gates
G7: 69 independent Commons recordings (44 uploaders) registered, 0 human-verified, auto-label proposals for 12 / 69 clips only - still no real-video accuracy. G7 night/lighting classifier (Kaggle) pending at close.
G6 web-mandi benchmark (15 Commons holdout clips) is unlabelled, so no real-footage accuracy exists. No Lahore data, no phone/emulator, no human grading panel, real-world latency unmeasured (all **unverified**); detector far below target; champion FA 1.25/min on the G1 neg clip (> 1); guava not detectable. CAPA data is research-only pending ULG consent. OWLv2 review queue (1 172 items) all pending human review.
