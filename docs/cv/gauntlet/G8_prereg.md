# G8 pre-registration (written 2026-10-13 ~19:55 PKT, before any G8 result)

Spec: the user's G8 brief (Hark project file `nutrisole-g8-instructions-gpt.md`, received 2026-10-13 14:48 PKT). Scope: the real-time CV camera subsystem only (detection, tracking, visible quality / ripeness / defects, latency). No nutrition, glucose, pricing or assistant work. Branch `cv-gauntlet` only; main is never touched, merged or PR'd.
Starting state (G7 closeout, local 70f3ff5): champion = **G3 control** (yolo11n trained 640, deployed 480 raw + class-wise NMS 0.7; G3 E224 quality classifier T = 0.25; scene guard rule 2 off; IouTracker; ripeness head wired OFF). Order of work follows the spec: **annotation and hard-example mining of the 69 web recordings first; no new YOLO training before the mined, human-checked data exists.**

## 0. Evidence labels
Every number carries split, n, model, imgsz and device: `CPU` = sandbox Linux CPU (2 cores aarch64, shared), `T4` = Kaggle free-tier GPU. Nothing in G8 is phone, emulator, Lahore or human-grader evidence unless a row says so explicitly and it actually happened. Web footage is Wikimedia Commons from other places and is never called Lahore.

## 1. Frozen splits (fixed now; hashes checked at start and end against `ml/runs/G6/locked_hashes.json`)
- Locked image splits (unchanged since G6): `test` 557, `test_rf` 149, `test_oiv7` 123, `test_oiv7c` 181, `neg_test` 80; pooled view n = 829 (test + test_rf + test_oiv7, 11 shared classes); views `test_rf_nostrips`, `test_small6` (never replace a locked split). Never trained on, never used for tuning.
- Historical fixed-frame TEST gauntlet (G1 det / quality / neg + G2 negtest), as in G7 section 8.
- Web-video splits v7 (`ml/runs/G7/video_v7/splits_v7.csv`, grouped by recording and uploader, fixed before any model was tuned on them):
  - **VB8-holdout** (final, never trained or tuned on): `holdout (LOCKED)` 15 clips + `holdout_v7_pending` 9 clips + `negatives_v7` 10 clips.
  - **VB8-dev** (mining and tuning allowed): `dev` 22 + `dev_v7` 6; **train-only**: `train_v7_weak` 6 + the G5 hard-negative clip 1.
  - `weak_exploratory` 5 and `excluded` 3 are not used for any metric.
- **Ground truth rule:** a frame or clip counts only after a human (the user) checked it through the review queue. Model proposals (G3, G6 rpx, G7 rfs, OWLv2, SAM 2 masks) are never ground truth for training or evaluation. The verified counts are reported as they are, including zero.

## 2. Annotation pipeline (P0-1)
Stage 1 `ml/autolabel/extract.py` (G3 boxes + ByteTrack association + adaptive keyframes, CPU) on all 69 clips, order: holdout_v7_pending, holdout, negatives_v7, dev, dev_v7, train_v7_weak. Stage 2 OWLv2 (Kaggle) on the keyframes; G6 rpx and G7 rfs boxes as second detector opinions. Stage 3 `ml/autolabel/merge.py`: agreement / disputed class / missing box / low confidence / temporal inconsistency / ID change / small box flags -> prioritised review queue. SAM 2 only offline as an annotation aid, never in the camera loop.
Review queue sent to the user as small contact sheets (numbered boxes per keyframe), priority: (a) VB8-holdout clip-level presence (which supported classes appear; negatives: confirm none), (b) VB8-holdout keyframe boxes, (c) VB8-dev disputed frames for mining. A reply is recorded verbatim with date in `ml/runs/G8/review/`.

## 3. Hypotheses and arms (each judged by the rules in section 4)
- **H1 hard-example fine-tune (`hm`)**: G3-init fine-tune, G3 replay (class-balanced, apple/banana/tomato floored at the G3 share) + human-checked VB8-dev / train-only frames (misses, class swaps, false boxes on unsupported objects as background) improves video recall and FA/min without per-class regression. Runs only once >= 150 human-checked mined frames exist. Second seed required (rule 7). Recipe fixed in advance: imgsz 640, 40 epochs, lr0 0.002, close_mosaic 10, G3 augmentation, T4.
- **H2 Albumentations (`hm+alb`)**: same as H1 plus restrained MotionBlur (p 0.1, blur <= 7), ISONoise (p 0.1), RandomGamma (p 0.2, 80-120), PlanckianJitter (p 0.2). One-factor ablation vs H1. Multi-scale and close_mosaic changes are separate one-factor arms only if T4 time remains.
- **H3 adaptive inference (`roi`)**: G3 at 480 full frame; boxes with 0.20 <= score < 0.45, or shorter side < 12 px at 480, get one ROI re-detection at 800 (crop of 2x the box, cap 4 ROIs per frame); tracker carries boxes between detector passes (detector every frame vs every 2nd frame both measured); keep-only-latest-frame simulated at camera 30 fps. No continuous tiling; SAHI only on the same uncertain crops as a sub-arm. Inference-only (no training).
- **H4 tracking**: IouTracker vs ByteTrack b15 vs BoT-SORT (GMC sparseOptFlow) on identical recordings; separate new-track and match thresholds; minHits 1 for score >= 0.6 (provisional box shown immediately, marked not-stable; quality still waits for stable). The G7 DEV tune grid output (`pick.json` empty) is re-derived from its saved per-config results with the G7 addendum-C pick rule before any TEST run.
- **H5 citrus refiner**: coarse-to-fine lemon/orange crop classifier triggered only on citrus/lemon boxes whose top score < tau (tau chosen on OIV7c val only); never on every box.
- **H6 night quality classifier**: G7 Kaggle `nutrisole-g7-night` (N1, N2) judged by the unchanged G7 prereg section-5 gate.
- **H7 ripeness / defects**: de-duplicated per-fruit ripeness by source/session group, and across lighting / variety; visible-defect labels (MangoDHDS) separate from ripeness and freshness, with abstain. No internal-quality or food-safety claim.
- **H8 distillation (P2)**: only if H1 produced a promoted or near-pass model and VB8-holdout has >= 5 verified clips; otherwise deferred.

## 4. Promotion rules (detector / pipeline). G3 stays champion unless ALL pass.
1. Pooled mAP50 (n = 829, CPU, imgsz 480, conf 0.001, iou 0.7) >= G3 0.314, and the source-level bootstrap 95% CI of (candidate - G3) has lower bound >= -0.01.
2. Strict per-class: no supported class with >= 20 instances drops > 0.02 mAP50 vs G3 on test, test_rf, test_oiv7 or test_oiv7c (apple, banana, tomato, citrus, capsicum explicitly checked). Transferring errors between classes fails this rule.
3. Historical TEST gauntlet (CPU, r1 = r2 on non-timing fields): det seg acc >= 0.667, rotten seg recall >= 0.875, FA/min <= 1.25 (G1 neg) and <= 0.25 (G2 negtest), static flicker <= 0.625 /10 s.
4. **VB8-holdout (verified only)**: requires >= 5 verified holdout clips from >= 4 uploaders; object/segment recall >= G3 and FA/min <= G3 on the same verified clips, TTFC median not more than 200 ms above G3, ID switches + fragmentation not higher than G3. **If fewer verified clips exist at closeout, rule 4 cannot pass and no detector is promoted in G8** (results are reported as provisional).
5. neg_test image FA (score 0.35, n = 80) <= G3 + 0.0125.
6. Latency (CPU, onnxruntime, same frames): end-to-end p95 <= 1.25x G3@480 for a new detector; <= 1.6x for the adaptive pipeline (H3) and only if its recall gain on test_small6 or VB8 is >= +0.03; simulated preview stays at camera rate (no queue growth) under keep-only-latest.
7. Two seeds of the same recipe both pass rules 1-2.
8. ONNX parity (raw 480, 40 test images) and repo tests EXIT=0.
Tracker change: separate rule (G7 prereg section 3, now confirmatory only on VB8-holdout verified clips); app default stays IouTracker behind `trackerKind` until it passes. Citrus refiner: test_oiv7c lemon wrong-label rate -30% relative with pooled subtype precision not lower, latency rule 6. Classifier: G7 section-5 gate.

## 5. Metrics reported together for G3 and every candidate (identical frozen splits)
mAP50 and mAP50-95 per locked split and pooled; per-class AP / recall and confusion matrix; video object and segment recall; FA/min; time to first correct (median, p90); ID switches, fragmentation, track births per minute; ripeness and defect agreement (by group); end-to-end p50 / p95 latency; preview responsiveness (dropped/aged frames under keep-only-latest). Source-level (recording / capture-group) bootstrap CIs, 1000 resamples, where n permits. Ablation table: which change helped, failed, interacted.

## 6. Integrity
No tuning on test or VB8-holdout; no silent exclusions (every dropped item is listed with its reason); no post-hoc class or threshold changes after viewing locked results; never Pexels / Pixabay / Mixkit. Jobs are idempotent with markers in `/workspace/work/cv/g8logs/`; restarts are logged, nothing is re-run selectively to change an outcome. Any change to this file after a result exists is an addendum, dated, stating what had been seen.
