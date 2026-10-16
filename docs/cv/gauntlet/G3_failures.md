# G3 failure analysis

Sources: `ml/runs/G3/eval_det_{k11_480,k26_640,k11ms_384}/eval_det.json`, `ml/runs/G3/kaggle_tables.md`, `ml/runs/G3/guard_tune_*/guard_tune.json`, `ml/runs/G3/gauntlet_*/gauntlet.json`, `ml/runs/G3/eval_cls_*/eval_cls.json`, `ml/runs/G3/grading_proxy_*/grading_proxy.json`, `ml/data/builds/v3/det_manifest.json`. All eval on the sandbox CPU (2 cores aarch64), not a phone.

## 1. Detector: the per-class rule still fails (citrus, capsicum, lemon_lime), and the locked test fell vs G2
- **test_rf per class (G1 champion -> G3 yolo11n@480 / yolo26n@640):** citrus 0.82 -> **0.67 / 0.56**, capsicum 0.09 -> **0.02 / 0.01**, lemon_lime 0.02 -> 0.02 / 0.00, apple 0.28 -> 0.27 / **0.21**. Gains: tomato 0.33 -> 0.68 / 0.65, banana 0.74 -> 0.84 / 0.76, carrot 0.25 -> 0.30 / 0.43. test_rf is 149 images (instance counts: citrus 34, lemon_lime 4, capsicum 110), so single classes are noisy, but citrus and capsicum regress on every G3 model.
- **capsicum domain split (inferred):** capsicum is 0.76 mAP50 on test_oiv7 (n=120 instances, OIV7 "Bell pepper") but recall 0.00 on test_rf (n=110). The test_rf capsicum instances look unlike OIV7 bell peppers (inferred from the gap, not yet inspected image by image). G4 must look at those 110 boxes before adding more capsicum data.
- **lemon_lime:** 452 train instances vs 1 543 citrus; test mAP50 0.03 (G2 0.22). The detector folds limes into citrus or misses them. The G4 two-stage plan (crop classifier for type) is the direct attack.
- **Locked test (crowded LVIS) fell from 0.315 (G2 yolo11n@480) to 0.224 (G3 yolo11n@480).** Two det-v3 changes explain this (inferred, not ablated): (a) LVIS hygiene dropped 834 train/val images whose labelled classes are not exhaustively annotated, which are mostly the crowded piles that dominate the locked test; (b) 1 005 of 3 562 train images (28%) are now backgrounds (COCO negatives + 475 hard negatives). Both trade crowded-pile recall for fewer false alarms and better photo-like detection. The locked test is still kept byte-identical for comparability, but it is no longer the split that matches the app.
- **New classes work on OIV7:** mango 0.00 -> 0.41, pomegranate 0.00 -> 0.76 (test_oiv7, yolo11n@480). Guava is still absent (no OIV7 class).

## 2. CPU real-time budget and replay noise
- The G3 candidates at 480/640 do not fit real time on the 2-core sandbox CPU while another workspace job (a Chromium test run) shares it: det p50/p95 84/184 ms (yolo11n@480) and 180/365 ms (yolo26n@640) in the gauntlet; 62-68% of det-clip frames dropped. The G1 champion at 320 drops 10-28%.
- The realtime replay is therefore **non-deterministic under load**: the same G1 detector gives quality static flicker 1.56-4.06 /10s and G1-neg-clip FA 2.5-3.75 /min across four runs that differ only in the guard, the classifier and CPU contention, and negtest FA 0.75 vs 1.88 /min for two runs with the identical detector and guard. Differences below about 1 FA/min or 2.5 flicker /10s between runs are noise.
- yolo26n@640 lost det segment accuracy (54.2% vs 62.5%), which is plausibly frame dropping as much as the model (inferred). It was picked by the deploy-size rule on Kaggle numbers (0.3567 vs 0.3556 test_rf, a 0.001 margin); on the CPU eval yolo11n@480 is higher (0.355 vs 0.341).
- The repeatable fix is a fixed-frame (non-realtime) gauntlet mode for model comparison plus a separate latency-only run (G4).

## 3. Classifier selection is degenerate on a saturated VAL, and calibration got worse
- All five Kaggle sweep runs scored val full-image acc 0.993-1.000 and val crop rotten recall 0.994-1.000. The pre-stated selection rule picked E_224_e15_b64_sgd01 (1.000 / 1.000), but the rule cannot separate the runs.
- Temperature fitted on that VAL is **T = 0.25** (sharpening); test ECE goes 0.009 -> 0.011 (worse), NLL 0.028 -> 0.064. The app will show over-confident probabilities. Refit T on a harder held-out crop set (G4).
- TEST rotten recall 0.983 (117/119) vs G1 0.992 (118/119): one image, inside the CI. Item-crop (grading proxy) rotten recall improved 0.983 -> 0.992.
- The G1 leakage caveat still holds (135/270 Sultana test images have a near-duplicate in train).

## Also seen
- **Scene guard rule 2 (maxSameClass) on DEV:** the DEV tune (rule: minimise DEV FA episodes subject to segment accuracy within 0.02) picks rule 2 **off** for every detector because 3-8 same-class boxes are normal in the DEV det clip (LVIS piles). On the locked negtest clip the G1 detector gave 0.75 FA/min with the default guard in one run and 1.88 in a second run with the identical detector and guard (G1det_G3cls; the neg clip does not use the classifier), the same as no guard and as rule 2 off. So the guard's effect on the negtest clip is **within replay noise**, not shown. The shipped default keeps 6 (the G2 plan rule) because it cost nothing on the G1 clips; the DEV/test disagreement is noted, not resolved.
- **G3 hard negatives worked on DEV:** with the same yolo11n recipe, DEV negative-clip FA went 114.5 /min (G2 weights) -> 1.25 /min (G3 weights) before any guard.
