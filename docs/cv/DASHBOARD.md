# G1 — Gauntlet iteration 1 (2026-10-12, CPU sandbox)

Device for all numbers: sandbox CPU, 2 cores aarch64, no GPU. Not a phone, not an emulator. Proof level reached: 4 (model validated on public locked test) for the classifier only; detector below usable.

## What changed vs G0
- Dataset v1: det-v1 from LVIS F&V (Apache-2.0), 9/12 v1 classes (no mango, guava, pomegranate). Splits train 2639 / val 439 / locked test 557 / locked test_rf 149 (Roboflow-photo subset). CPU training used a 1378-image subset.
- Quality v1: Sultana originals (apple, banana, guava, orange, pomegranate) fresh/rotten, MD5+pHash dedupe, pHash-cluster grouped splits. Residual leakage: 135/270 test images have a train neighbour with cosine >= 0.90 (no physical-fruit IDs exist).
- Per-object tracker with hysteresis and reset on new objects; quality throttled to stable boxes (500 ms).
- Measurements + rubric v0.1; TS pipeline (contracts, preprocess, postprocess, tracker, rules) in native/src/cv with tests.
- Docs: datasets.md, licences.md, labelling-handbook.md, android-spike.md; PRD/Techspec/Structure/Tracker/ImplementationPlan/README updated (CV in scope, Expo wording removed).

## Detector (yolo26n, 320 px, 8 epochs, CPU) — UNDERTRAINED
| split | head | mAP50 | mAP50-95 | P | R |
|---|---|---|---|---|---|
| test (n=557 imgs) | one2many+NMS | 0.125 | 0.065 | 0.255 | 0.152 |
| test_rf (n=149) | one2many+NMS | 0.323 | 0.177 | 0.553 | 0.324 |
| test | one2one (NMS-free) | 0.107 | 0.056 | 0.382 | 0.127 |
| test_rf | one2one (NMS-free) | 0.308 | 0.185 | 0.631 | 0.323 |
test_rf best classes: citrus mAP50 0.823, banana 0.744; worst: lemon_lime, capsicum, cucumber near 0.
YOLO11n baseline: training killed after 2 epochs for time budget; NO comparison possible. Promotion decision deferred.

## Quality classifier (yolo26n-cls, 192 px, 15 epochs), grouped Sultana test n=270
top-1 98.1%, macro-F1 0.981, fresh recall 0.974, rotten recall 0.992 (118/119); T=0.889, ECE 0.0161 -> 0.0134.
Robustness (acc / rotten recall): tube-light WB 0.981/0.966; sodium WB 0.974/0.958; low light 0.900/0.857 (FAIL); motion blur 0.926/1.0; JPEG40 0.963/1.0. Likely optimistic (leakage above).

## Grading proxy (fresh->A/B, rotten->C/Reject; not human grades, no kappa)
classifier only 0.978; measurements only 0.654; classifier+rules 0.669 (fresh->A/B only 0.411). Dark-defect measurement over-fires on fresh produce (median 12% "defect").

## Export parity (40 imgs, same letterbox)
Classifier ONNX: max dprob 1.7e-6, 0 disagreements. Classifier .pte (Python ExecuTorch, desktop): max diff 4.8e-7. Detector ONNX e2e and raw: 0 class disagreements, min IoU 0.999997, max dconf 6.4e-6 — PASS (G0 mismatch fixed). LiteRT export blocked on aarch64.

## Video gauntlet (synthetic handheld clips from locked TEST images — regression test only)
| clip set | metric | e2e (NMS-free) | raw+NMS |
|---|---|---|---|
| det (24 segs, 1424 GT frames) | frame acc | 47.5% | 52.0% |
| | segment acc | 62.5% (8 never correct) | 62.5% |
| | time-to-first-correct p50/p90 | 500/733 ms | 467/667 ms |
| | label flicker static /10s | 0.0 | 0.63 |
| | no-box fraction while static | 44% | 34% |
| quality (16 segs) | graded-segment quality acc | 84.6% (11/13) | — |
| | rotten segment recall | 0.75 (6/8) | — |
| | label flicker static /10s | 4.06 (FAIL) | — |
| negatives (0.8 min) | false alarms/min | 3.75 (FAIL, gate <=1) | — |
| all | det latency p50/p90/p95 | 21.9/30.8/38.7 ms | 18.5/22.5/27.6 ms |
| all | full pipeline p95 | 49 ms; ~43 det FPS (CPU, ONNX) | 61 ms |

## Repo checks after changes
Root build, check:runtime, domain, expansion, native tests, CV tsc, pytest 27/27: all EXIT 0. Native lint/typecheck not runnable (no native/node_modules).

## Gates
None pass. No Lahore data, no phone/emulator, no human panel; detector far below mAP50 0.85; false alarms 3.75/min; quality-clip flicker 4.06/10s; low-light rotten recall 0.857.

## Top 3 failure modes -> G2
1. Detector undertrained (CPU, 8 epochs, half the data) and missing 3 classes -> freeze backbone + longer training, Open Images V7 for mango/guava/pomegranate, Kaggle GPU when credentials exist.
2. Dark-defect measurement fires on fresh produce -> shadow/specular-aware mask, require classifier agreement before defect-only C/Reject, tune on val.
3. Robustness: low-light rotten recall, negative false alarms, label flicker on close-ups -> low-light/noise augmentation, negative images in detector training, tracker hysteresis tuned on dev clips.

Raw outputs: ml/runs/G1/ ; logs /workspace/work/cv/g1logs/ ; models /workspace/work/cv/g1models/.
