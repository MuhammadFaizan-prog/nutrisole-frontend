# G4 failure analysis

Sources: `ml/runs/G4/det_table.md`, `ml/runs/G4/det_deltas.json`, `ml/runs/G4/eval_det_*`, `ml/runs/G4/eval_pooled_*`, `ml/runs/G4/neg_fa_*`, `ml/runs/G4/gauntlet_ff_*/gauntlet.json`, `ml/runs/G4/gauntlet_ff_table.json`, `ml/runs/G4/eval_cls_{cls4,G3E224_vh}/eval_cls.json`, `ml/runs/G4/capsicum_testrf_inspect.json`, `ml/runs/G4/teacher_owlv2/teacher_eval.json`. All eval on the sandbox CPU (2 cores aarch64), not a phone or emulator; gauntlet clips are synthetic clips built from locked TEST images, not Lahore video.

## 1. The image metrics and the video gauntlet disagree for the detector
- **A1 hygiene off** (yolo11n 640, eval 480) is the best detector on every still-image split that matters: pooled n=829 mAP50 0.385 vs 0.314 (G3 control), test_rf n=149 0.406 vs 0.355, test n=557 0.323 vs 0.224, test_oiv7c n=181 0.665 vs 0.634, and 0/80 neg_test images with a box (control 2/80). It is the first model with **no test_rf per-class regression > 1 pt vs G1**.
- On the fixed-frame gauntlet (deterministic, r1 = r2) the same model is clearly worse: det segment acc 0.458 vs 0.667, det frame acc 0.398 vs 0.496, static det flicker 4.79 vs 0.00 /10s, TTFC p90 2000 vs 760 ms, G1-neg-clip FA 6.25 vs 1.25 /min, negtest 1.50 vs 0.00 /min, rotten segment recall 0.750 vs 0.875.
- **Why (inferred, not ablated):** without the hygiene step the train set keeps LVIS crowded piles whose other produce is unlabelled, so the model learns to fire more boxes on cluttered scenes (good for pooled mAP on crowded LVIS test images) but also on textured backgrounds and with less stable class scores on single handheld items, which is what the gauntlet clips show. The gauntlet clips are synthetic and small (24 det segments, 2 negative clips), so a 4-segment gap is meaningful but not decisive.
- **A2 bg15** recovers frame accuracy (0.545) and TTFC but adds false alarms (3.75 / 0.38 FA/min) and lowers pooled mAP50 (0.297); it fails both views.
- det-v4 / det-v4hyg (the OIV7 citrus/lemon attack, with and without hygiene) did not finish before the cutoff, so whether extra photo-domain citrus data changes this picture is open (G5).

## 2. Detector classes still broken: lemon_lime, capsicum on test_rf, guava
- **capsicum on test_rf:** all 110 test_rf capsicum boxes are sliced red-pepper strips (`capsicum_testrf_inspect.json`), not whole peppers. Every model scores ~0-0.12 there; this split measures a non-target and should not drive capsicum decisions (it stays locked for comparability). On pooled data capsicum is 0.22 (control) / 0.32 (A1).
- **lemon_lime:** test_rf 0.01-0.02 for every detector (only 4 GT instances, so noisy), pooled 0.02 (control) vs 0.23 (A1). The control folds limes into citrus. The OIV7 citrus/lemon data (det-v4) and the type classifier of the two-stage plan were the two attacks; neither produced a promotable result inside G4 (see Deferred in G4.md).
- **guava:** still no detector training data and no GT in any test split.
- **Zero-shot OWLv2 beats every trained detector on test_rf** (0.685 vs best 0.406; test_oiv7 0.542), which says the bottleneck is labels, not model capacity. Its 1 172 proposals are all pending human review.

## 3. Classifier: gates passed but robustness moved, not improved
- cls4 passes both formal gates on the grouped Sultana test (n=270, imgsz 224, CPU): synthetic low_light rotten recall 0.975 (gate >= 0.95; G3 E224 0.941) and item-crop rotten recall 0.992 (gate >= 0.983).
- But on the **held-out night_sodium_hard** condition (not in any training augmentation) rotten recall falls 0.983 -> **0.941** (2 -> 7 of 119 rotten missed; inferred count from recall x 119), and tube_light_hard rotten recall falls 0.992 -> 0.966. Accuracy on those conditions rises because fresh recall improved, but a missed rotten item is the costlier error for a buyer. Training on one low-light family moved the error to a neighbouring held-out family (inferred).
- On the gauntlet, cls4 is identical to the G3 E224 classifier on every metric (quality-graded acc 0.929, rotten seg recall 0.875, grade flicker 0.00), so it brings no measured video benefit.
- The test set is near saturation (0.989 -> 0.996 is 2 images), and the G1 leakage caveat holds (135/270 test images have a near-duplicate in train). Classifier decisions now rest on the synthetic held-out conditions more than on test accuracy.

## Also seen
- **Kaggle GPU slots were the critical path:** only 2 T4 sessions at once; det-v4 and det-v4hyg held both slots from 10:15 / 11:30 UTC, so the GPU ripeness and type kernels never started (queue log `/workspace/work/cv/g4logs/gpuq.log`: "Maximum batch GPU session count of 2 reached" every ~95 s from 12:13 UTC). CPU fallback kernels were pushed at ~12:30 UTC; GPU pushes for ripe/type were disabled at 12:40 UTC because they could not land before the cutoff.
- **Ripeness label bug:** the CC0 ripeness dataset spells its train folder `Overipe`; the parser matched only `/overripe`, so the CPU run trained on 2 classes and scored overripe recall 0.000 on test_cc0 (n=180, acc 0.661). Caught at eval, nothing shipped. Every class count must be asserted before training.
- Workers died on sandbox session resets several times; `g4_up.sh` restarts them idempotently.
- Fixed-frame mode removed the G3 replay noise: every accuracy/FA/flicker number was identical across r1/r2 for G1 control, G3 control, guard-off control, A1 and cls4.
