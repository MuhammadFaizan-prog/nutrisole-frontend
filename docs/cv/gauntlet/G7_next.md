# G8 plan (proposed at the G7 closeout, 2026-10-13; not run)

**G8 follows the user's G8 spec: `files/nutrisole-g8-instructions-gpt.md` (Hark project "Nutri sole"; received 2026-10-13 14:48 PKT).** This file only maps G7's leftovers onto it. CV camera subsystem only.

State after G7: champion unchanged (G3 control detector yolo11n trained 640, deployed 480 raw + class-wise NMS 0.7; G3 E224 quality classifier T = 0.25; scene guard rule 2 off; IouTracker). Every G7 number is sandbox CPU or Kaggle T4; nothing has been validated on a phone, an emulator, Lahore footage or by human graders.

## P0 - real-video evidence (spec P0 #1; do this before any new YOLO training)
1. **Finish annotation of the 69 independent web recordings** (38 G6 + 31 G7 Wikimedia Commons; 44 uploaders; register `docs/cv/gauntlet/G7_data_register.md`, splits `ml/runs/G7/video_v7/`). G7 stage 1 (G3 detections + ByteTrack + adaptive keyframes, `ml/autolabel/extract.py`) covered only **12 / 69 clips** (2 676 sampled frames, 298 keyframes, 13 362 G3 boxes, all *proposed*) before it was stopped for CPU budget. Resume it (marker `g7logs/STOP_AL` - delete to resume), then stage 2 (OWLv2 on Kaggle, `kaggle/g7/k_al`, launcher `g7_al_kaggle.sh`, marker `STOP_ALK`) and `ml/autolabel/merge.py` (agreement / disagreement flags + prioritised review queue). SAM 2 propagation only offline for annotation.
2. **Human verification queue** for the smallest useful subset (holdout_v7_pending 9 clips first, then negatives_v7 10 clips to verify absence). Verified count in G7 = **0**; nothing unverified is ground truth.
3. **Error-driven mining** on verified frames: misses, class swaps (apple, lemon/citrus, mango/guava, capsicum), false boxes on unsupported objects, lost-during-motion.

## P0 - class errors (spec P0 #2)
4. **Apple / banana / tomato regression of from-scratch rpx training.** G7 sA/sB (two seeds, same recipe) and rfs all lose test_rf banana / apple / tomato vs G3 (see `G7.md` section 6 and `G7_failures.md`). The rpx mix adds OIV7c + guava + whole capsicum; G3-domain (test_rf) classes lose share and the G3 test split (557 images, many tiny boxes) drops 0.015-0.025 mAP50. Next: class-balanced replay with corrected labels, judged on the verified web-video holdout as well as the locked image splits.
5. **Lemon vs citrus:** the anchor-score ambiguity rule failed its gate (-4.7% wrong labels, needed -30%); the hierarchical "citrus unless subtype confident" view raises subtype precision (G3 0.791 -> 0.801 at 78.7% coverage). G8 candidate (pre-register first): coarse-to-fine citrus refiner triggered only on uncertain boxes; the val-only score-tau grid (`ml/runs/G7/citrus/exploratory_score_tau_val.json`) is a starting point, not a result.
6. **Guava:** independent Mendeley guava set (270 images, Larkana PK, studio) shows the domain gap: G6rpx 0.993 hit rate, G7 from-scratch arms much lower: sA 0.337, sB 0.541, rfs 0.615 (`G7.md` section 10). Guava stays unsupported in the app until a promoted model detects it.

## P0 - adaptive inference (spec P0 #3)
7. Tiny objects: 13.6% of locked-test boxes are < 6 px at 480. Recall by size (G3, test n=557, CPU): 480 0.301, 640 0.346, 800 0.401, tile480 0.435 at 5x the latency (357 vs 68 ms p50). Benchmark selective ROI re-detection of uncertain boxes, keep-only-latest-frame, total pipeline latency; no continuous tiling.

## P1
8. **Tracking:** finish the DEV tune grid (G7 ran 3 / 8 configs before CPU priority went to detector evals; `g7_tune.sh` resumes from markers), then IouTracker vs ByteTrack vs BoT-SORT on the same *verified* recordings. ByteTrack b15 is the recommended A/B candidate (post-hoc rule, exploratory); app default stays IouTracker behind the flag.
9. **Night / lighting quality classifier:** `nutrisole-g7-night` (N1 light-aug, N2 reduced-hue) - v2 was still RUNNING on Kaggle at the G7 close (no result claimed); collect it with `g7_night_post.sh` (output -> `ml/runs/G7/night/`) and apply the G7 prereg section-5 gate unchanged.
10. **Ripeness:** per-fruit head wired OFF; de-duplicated test_cc0 top-1 0.968 (n=155). Next: de-duplicate by source/session, independent lighting/variety benchmark, no aggressive hue (hue shift +20 deg drops G3 E224 rotten recall 0.983 -> 0.782).

## Blockers that need the user
- Lahore phone clips and phone / emulator runs (`G6_device_validation_pending.md`): still pending; nothing in G7 is phone-validated.
- Human review of the auto-label queue (small, prioritised).
