# G3 plan: attacks G2's top-3 failure modes (Kaggle T4 available, max 2 concurrent GPU sessions)

Rule: keep the locked test / test_rf / neg_test and the G1 clips unchanged so G3 is comparable. Add new test material as separate, additional splits.

## A. Detector data -> det-v3 (failure mode 1)
1. **OIV7 produce subset.** Kaggle CPU kernel `mfaizannnn/nutrisole-oiv7-produce` is already extracting it. Contents:
   - YOLO format, 12-class v1 index order: banana, apple, mango, citrus, guava, pomegranate, lemon_lime, tomato, potato, cucumber, carrot, capsicum.
   - Up to 1500 images each for mango and pomegranate; 1200 each for lemon, capsicum and cucumber.
   - All other target-class boxes in those images; depictions excluded.
   - Per-image licence CSV and stats.json.
   - Output: oiv7_produce.tgz + labels/ + boxes_index.csv.
2. **Build det-v3 = det-v2 + OIV7.** Keep OIV7's own train/val/test split. Add OIV7 test as a NEW split `test_oiv7` without touching the locked test. Dedupe vs LVIS by pHash; overlap is not expected, since LVIS is COCO-based. This gives **11/12 classes**. Guava is not an OIV7 class; it stays a gap and needs Lahore photos or a licensed guava set.
3. **LVIS label hygiene.** For each LVIS image, drop or ignore target classes listed in `not_exhaustive_category_ids` / not in `neg_category_ids`. This stops penalising correct detections. Re-evaluate whether to train on the crowded-scene subset at all, or to cap instances per image.
4. **Train on Kaggle T4.** Use yolo11n and yolo26n at 640 with the same settings as G2 (now with absolute split paths and try/except eval). Add a second pair at **imgsz 480 with multi_scale**, so the deploy size matches training. Do a val-only LR sweep only if time allows.
5. **Report** per-class test, test_rf and test_oiv7 at 384/480. Deploy rule unchanged (written before results).

## B. False alarms (failure mode 2)
1. **Hard-negative mining.** Run the G2 detectors over COCO train backgrounds and plain/texture images (seats, balls, lights, red fabric, bricks, wood). Add the top false-positive images (no labels) to det-v3 train as background (about 10-15% of train). Keep `neg_test` and the negtest clip locked.
2. **App-side guards in tracker/rules, mirrored in TS + Python with fixture parity:**
   - Max same-class boxes per frame (the app grades one item). If more than 6 same-class boxes appear, treat the frame as a "scene" and show nothing.
   - Minimum box area fraction.
   - Track confirmation by minHits on a stable box.
   Tune on a DEV negative clip built from COCO val (never neg_test).
3. **Fix the FA metric.** Report both FA tracks/min and FA *episodes*/min (merging overlapping tracks), so one stadium frame cannot dominate. Keep the old metric for continuity.

## C. Classifier crop and lighting gap (failure mode 3)
1. **Train on detector-style crops.** Use `item_crop` with box jitter (±15% scale/shift), padding and background bleed, applied to TRAIN only. Also add tube-light/fluorescent WB augmentation, which regressed.
2. **Recipe sweep on Kaggle T4** (val-selected): 192 and 224 px; epochs 15/30; batch 32/64; lr0 0.01/0.002. Reproduce the CPU 192 recipe on GPU as a control.
3. **Headline classifier metric becomes rotten recall on item crops** (grading proxy, TEST), with full-image accuracy and robustness as secondary. Promotion requires crop rotten recall >= G1 (0.983) and low-light rotten recall >= 0.95.
4. **Guava rotten.** Inspect the worst items; consider class-balanced sampling.
5. **3-level stays quarantined.** Mild recall is 0.24. Either collect labelled mild examples (Lahore panel) or drop mild until human labels exist.

## D. Process
- Run gauntlets sequentially on an idle CPU (check load average < 2 before each). Report latency and dropped frames, and rerun the G1 champion in the same session as the control.
- Re-tune tracker scoreAlpha/switchMargin on DEV clips with the G3 detector.
- Re-run grading tune (VAL) only if the classifier changes; the rubric grade thresholds stay untuned until human graders exist.
- Same promotion rule: better on test_rf AND gauntlet, no per-class regression > 1 pt. Add: FA/min on the negtest clip must not get worse than the champion's.
