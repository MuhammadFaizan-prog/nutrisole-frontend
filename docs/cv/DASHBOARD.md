# CV dashboard: NutriSole produce detection + visual grading

Last update: G3 (2026-10-12). Reports: [G1](gauntlet/G1.md), [G2](gauntlet/G2.md), [G2 failures](gauntlet/G2_failures.md), [G3](gauntlet/G3.md), [G3 failures](gauntlet/G3_failures.md), [G4 plan](gauntlet/G3_next.md).
Device for every number: sandbox CPU (2 cores aarch64, onnxruntime). This is not a phone. Training: CPU (G1), Kaggle T4 (G2, G3).

## Current champions
| component | champion | since | notes |
|---|---|---|---|
| Detector | **G3 yolo11n 640 -> 480 raw+NMS (combined view)**; G1 yolo26n 320 e2e under the strict rule | G3 | Combined view (pooled 829-img mAP50 + gauntlet + negatives, user-requested): pooled 0.314 vs G1 0.095, FA 1.25 / 0.00 per min, det segments tie 62.5%. Strict G2 rule fails (test_rf citrus -15, capsicum -7). More flicker (2.29/10s) and 84 ms p50 on the shared CPU; phone unverified |
| Quality classifier | **G3 yolo26n-cls 224 E (quality2-g3crop, Kaggle), T=0.25** | G3 | crop rotten recall 0.983 -> 0.992; calibration needs a refit on a harder VAL (G4) |
| Scene guard | **maxSameClass 6, minAreaFrac 0.01** (TS + Python + parity fixture) | G3 | minAreaFrac tuned on DEV; rule 2 kept from the G2 plan, DEV prefers it off |
| Measurements / rubric | measure-v0.3-g2 / rubric-v0.2-g2 (agreement gate 0.05) | G2 | rubric grade thresholds still untuned (no human graders) |
| Tracker | scoreAlpha 0.2 | G2 | DEV re-tune for G3 yolo11n@480 suggests scoreAlpha 0.5 / switchMargin 0.1 / minHits 3 (flicker 4.13 -> 3.13); not adopted until a TEST gauntlet check (G4) |

## Headline numbers by iteration
| metric | G1 | G2 best candidate | G3 best candidate | gate |
|---|---|---|---|---|
| Det test mAP50 / 50-95 (n=557) | 0.125 / 0.065 | 0.315 / 0.188 (yolo11n@480) | 0.234 / 0.153 (yolo26n@640) | mAP50 >= 0.85 (FAIL) |
| Det test_rf mAP50 / 50-95 (n=149) | 0.323 / 0.177 | 0.375 / 0.256 (yolo11n@480) | 0.365 / 0.236 (yolo11n-480ms@384) | |
| Det test_oiv7 mAP50 (n=123, new in G3) | 0.112 | 0.144 | 0.543 (yolo26n@640) | |
| Det pooled mAP50 test+test_rf+test_oiv7 (n=829, 11 classes) | 0.095 | 0.253 | **0.314** (yolo11n@480) | |
| Neg images with any box | 2.5% | 2.5% | 2.5% | |
| Gauntlet det segment acc | 62.5% | 58.3% | 62.5% (yolo11n@480) | |
| Gauntlet FA/min, G1 neg clip / negtest | 3.75 / n/a (G3 rerun: 2.5-3.75 / 0.75-1.88) | 42.5 / 5.25 | 1.25 / 0.00 (yolo11n@480) | <= 1 (FAIL) |
| Cls rotten recall test / low light | 0.992 / 0.857 | 0.992 / 0.966 | 0.983 / 0.941 (champion) | low light >= 0.95 (FAIL, close) |
| Cls rotten recall on item crops | 0.983 | 0.941 | 0.992 (champion) | >= 0.983 to promote |
| Grading proxy TEST (cls+rules) | 0.669 | 0.978 (G1 cls + G2 rules) | 0.981 (G3 cls) | weak proxy, no kappa |
| Export parity (ONNX) | PASS | PASS | PASS | |
| Repo checks | all EXIT 0 | all EXIT 0 | all EXIT 0 | |

## Open gates
No Lahore data, no phone/emulator, no human grading panel, real-world latency unmeasured; detector far below target; false alarms > 1/min for the champion detector; guava not detectable (mango/pomegranate now detectable on OIV7 by the non-promoted G3 detectors). The video gauntlet is a realtime replay on a shared CPU and shows ~1 FA/min run-to-run noise (G3_failures.md).
