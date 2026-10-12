# CV dashboard: NutriSole produce detection + visual grading

Last update: G2 (2026-10-12). Reports: [G1](gauntlet/G1.md), [G2](gauntlet/G2.md), [G2 failures](gauntlet/G2_failures.md), [G3 plan](gauntlet/G2_next.md).
Device for every number: sandbox CPU (2 cores aarch64, onnxruntime). This is not a phone. Training: CPU (G1), Kaggle T4 (G2).

## Current champions
| component | champion | since | notes |
|---|---|---|---|
| Detector | G1 yolo26n 320 (8 ep CPU), e2e ONNX | G1 | G2 yolo11n@480 / yolo26n@384 not promoted: worse gauntlet + false alarms |
| Quality classifier | G1 yolo26n-cls 192 (T=0.889) | G1 | G2 q2aug 192 is a candidate: better low light, worse crop rotten recall |
| Measurements / rubric | measure-v0.3-g2 / rubric-v0.2-g2 (agreement gate 0.05) | G2 | tuned on VAL; rubric grade thresholds still untuned (no human graders) |
| Tracker | scoreAlpha 0.2 (was 0.35) | G2 | tuned on DEV clips; TS + Python + parity fixture in sync |

## Headline numbers by iteration
| metric | G1 | G2 best candidate | gate |
|---|---|---|---|
| Det test mAP50 / 50-95 | 0.125 / 0.065 | 0.315 / 0.188 (yolo11n@480) | mAP50 >= 0.85 (FAIL) |
| Det test_rf mAP50 / 50-95 | 0.323 / 0.177 | 0.375 / 0.256 (yolo11n@480) | |
| Neg images with any box | 2.5% | 2.5% | |
| Gauntlet det segment acc | 62.5% | 58.3% | |
| Gauntlet FA/min (G1 neg clip / new negtest) | 3.75 / n/a | 42.5 / 5.25 | <= 1 (FAIL) |
| Gauntlet quality static flicker /10s | 4.06 | 5.0 (11n) / 0.0 (26n) | |
| Cls rotten recall test / low light | 0.992 / 0.857 | 0.992 / 0.966 | low light >= 0.95 (candidate only) |
| Cls rotten recall on item crops | 0.983 | 0.941 | |
| Grading proxy TEST (cls+rules) | 0.669 | 0.978 (G1 cls + G2 rules) | weak proxy, no kappa |
| Export parity (ONNX) | PASS | PASS | |
| Repo checks | all EXIT 0 | all EXIT 0 | |

## Open gates
No Lahore data, no phone/emulator, no human grading panel; detector far below target; false alarms > 1/min; guava/mango/pomegranate not detectable (G3 adds mango/pomegranate via OIV7).
