# G6 pre-registration (written 2026-10-13 ~03:20 PKT, before any G6 training result)

Champion at start of G6: **G3 control** = `det_yolo11n_640_raw.onnx` (G3 best.pt sha256 29cc5212..., trained 640, deployed 480, raw + class-wise NMS 0.7) + G3 E224 quality classifier (`E_224_e15_b64_sgd01.onnx`, T = 0.25, cls imgsz 224), scene-guard rule 2 off (`--max-same-class 0`).
Historical reference numbers (G3/G4/G5 reports, sandbox CPU, not re-measured here unless a row says so): pooled mAP50 0.314 (n=829, imgsz 480); fixed-frame gauntlet det segment acc 0.667 (24 segments), FA 1.25/min (G1 neg clip) and 0.00/min (G2 negtest clip); held-out night_sodium_hard rotten recall 0.983 (G3 E224; G4 cls4 was 0.941).

## Detector candidates (G6.3), both fine-tuned from the G3 checkpoint (not A1)
Fixed for both: imgsz 640 train / 480 eval, SGD lr0 0.002, lrf 0.1, warmup 1, 40 epochs, cos LR, close_mosaic 10, batch 32, seed 0, G3 default augmentation. Kernel `ml/runs/G6/kernels/det_ft_g6.py`.
- **rp** (replay control): full G3 det-v3 train/val mix minus the G6.1 audit TRAIN removals (exact/near duplicates of locked eval images).
- **rpx**: rp + OIV7c train/val (G4) + guava 300 (CC BY 4.0) + deepNIR whole capsicum (CC0).
Only one seed each is affordable (2 free GPU sessions); a single-seed result can be at most *provisional*, never promoted alone.

## Evaluation (unchanged definitions)
Locked splits test (557), test_rf (149), test_oiv7 (123), test_oiv7c (181), pooled (829), neg_test (80) at imgsz 480, conf 0.001, iou 0.7 (PyTorch CPU); test_rf_nostrips stays a VIEW. Fixed-frame gauntlet `g6_gaunt.sh TAG DET raw 480 CLS 0.25 224 --max-same-class 0` (G1 clips + G2 negtest clip). ONNX parity as G5.

## Promotion rule (strict AND combined must both pass)
1. pooled mAP50 > 0.314 on the unchanged historical benchmark;
2. strict per-class: no supported class (banana, apple, citrus, lemon_lime, tomato, potato, cucumber, carrot, capsicum) drops > 0.02 mAP50 on test_rf, test_oiv7 or test_oiv7c vs G3;
3. gauntlet det segment acc >= 0.667, rotten segment recall >= 0.875, FA/min <= 1.25 (G1 neg) and <= 0.25 (negtest), r1 = r2 replay;
4. ONNX parity pass; repo tests pass;
5. a second seed (or second replay) confirms 1-3. Without it the best outcome is "provisional / inconclusive", G3 stays deployed.

## Tracking (G6.4)
"Without tracking" here means the app's current IouTracker (hysteresis tracker, already in the G3 control pipeline); there is no tracker-free mode in the app. G3 + IouTracker vs G3 + ByteTrack (`ml/eval/bytetrack_adapter.py`: Ultralytics BYTETracker association, high/new-track thresh 0.35 = rubric detectorMinScore, low thresh 0.1, match 0.8, fuse_score; same label hysteresis/stability rules as IouTracker; reset per clip). ByteTrack `track_buffer` chosen on DEV (g3clips_dev + g3clips_devneg) from {8, 15, 30}: highest DEV det segment acc, ties -> lower DEV FA/min, lower static flicker, smaller buffer. Then TEST r1 + r2 once. Tracking is adopted only if det segment acc does not drop, FA/min does not rise, and grade flicker falls; metrics also include ID switches and processing time. Stays behind a flag regardless.

## Data rules
Locked split files are byte-identical (hash check before and after). Audit corrections are written as new TRAIN manifests and VIEWs; locked test membership is never edited. External video: Wikimedia Commons only with per-file CC0 / CC BY / CC BY-SA / PD; Pexels, Pixabay, Mixkit rejected; YouTube listed only. Splits by uploader; no uploader > 25% of the held-out set. External footage is never called Lahore footage.

## Deviation (2026-10-13 03:35 PKT, before any ByteTrack or fine-tune result was seen)
The sandbox CPU is shared with other jobs (load ~10 on 2 cores; G3 det latency p50 177 ms vs 34 ms in G4), so a full DEV run takes ~40 min. To fit the 09:00 PKT cutoff:
- the ByteTrack DEV grid uses the DEV **det clip only** (no DEV neg/quality); tie-break -> lower static label flicker, then smaller buffer; DEV IouTracker reference = G6 dev_iou det metrics (seg 0.5417, identical to G5 DEV);
- TEST r1 for the control (IouTracker, re-run for the new id-switch metric) and for the ByteTrack pick; r2 only if ByteTrack passes the adoption rule on r1;
- fine-tune candidates: locked image evals first; the gauntlet r1 only for a candidate that passes the strict image rule (same convention as G5).
