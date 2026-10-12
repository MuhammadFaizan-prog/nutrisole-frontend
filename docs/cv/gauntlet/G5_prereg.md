# G5 pre-registration (written 2026-10-12 ~15:30 UTC, BEFORE any G5 model result was seen)

All numbers are measured on the sandbox CPU (2-core aarch64, onnxruntime / PyTorch CPU) unless a row says Kaggle T4. Nothing here is a phone, emulator, Lahore or real-device measurement.

## Promotion views (unchanged from G4)
- **Strict:** test_rf (n=149) mAP50 better than the champion; no test_rf per-class drop > 1 pt vs the G1 champion; fixed-frame gauntlet det segments not worse than the champion (0.667); negtest FA not worse (0.00/min).
- **Combined:** pooled (n=829) mAP50 + fixed-frame gauntlet (det segments, frame acc, quality-graded acc, rotten seg recall, flicker) + both negative clips + neg_test image rate, against the G3 control. A candidate that wins still images but loses the gauntlet is not promoted.
- Every gauntlet comparison is fixed-frame stride 1, run twice (r1/r2) for anything that could be promoted.
- det-v4hyg is **test-informed** (added after A1's test results) and may only be promoted if it also wins on the gauntlet and both negative clips.

## G5.1b temporal rescoring (causal Seq-NMS / tubelet smoothing)
- Window chosen on DEV only (G3 DEV det + neg clips and G3 devneg clip; windows 3 and 5; 7 dropped for CPU budget), for the G3 control and A1 separately. DEV pick rule: highest DEV det segment acc, ties -> lower DEV FA, then lower static flicker.
- Adopt in the app (default on) only if, on the TEST fixed-frame gauntlet r1 = r2 with the champion detector: det segment acc not lower AND (FA/min on G1 neg or negtest lower, or det segment acc higher) AND static det flicker not higher AND quality-graded acc / rotten seg recall not lower. Otherwise the code ships off by default.

## G5.1a video hard negatives
- g5hn (A1 + filtered hard-negative crops) is judged like any detector candidate (both views). It is the direct test of "does mining isolated video detections fix A1's video false alarms": success = G1-neg FA <= 1.25/min AND det segments >= 0.625 with pooled mAP50 >= 0.36.

## G5.2 classes
- g5hnc must not lose more than 1 pt pooled mAP50 vs g5hn on the shared 11 classes; guava is reported on the new split test_guava (Kaggle T4) and stays "unsupported" in the app unless test_guava mAP50 >= 0.5 AND the model is promoted.
- Capsicum re-score excluding sliced strips is a separately labelled VIEW (`test_rf_nostrips`), never a replacement for the locked test_rf.

## G5.3 ripeness
- Valid only if every class has >= 50 training images (asserted in the kernel). Report test_cc0 (n=180) accuracy and per-class recall, and the HF banana test separately. Ship as a chip only if test_cc0 overripe recall >= 0.7 and accuracy >= 0.8.

## G5.4 low light (leave-one-lighting-out)
- night_sodium_hard and tube_light_hard are held out of training AND selection. Candidate cls5 replaces the G3 E224 classifier only if: night_sodium_hard rotten recall >= 0.983 AND tube_light_hard rotten recall >= 0.992 (both = champion) AND synthetic low_light rotten recall >= 0.95 AND item-crop rotten recall >= 0.983 AND gauntlet quality-graded acc / rotten seg recall not lower.

## G5.5 gates (new documented view; old gates still reported)
- **Old gates (kept):** detector mAP50 >= 0.85 (pooled), FA <= 1/min, synthetic low-light rotten recall >= 0.95, item-crop rotten recall >= 0.983, ONNX parity.
- **New per-split view (proposal):** test_rf mAP50 >= 0.55; test_oiv7c mAP50 >= 0.70; pooled mAP50 >= 0.45; fixed-frame video det segment acc >= 0.80; FA <= 1.0/min on BOTH negative clips; rotten seg recall (video) >= 0.875; held-out night_sodium_hard rotten recall >= 0.983. Rationale: the pooled 0.85 target was set before we knew test (LVIS crowded piles, partial labels) caps any detector far below 0.85 (zero-shot OWLv2 reaches only 0.685 on test_rf); per-split targets track what the app actually needs (single handheld items, few false alarms).
