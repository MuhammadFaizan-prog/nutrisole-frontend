# G9 follow-up ablation A3: addendum (written and committed BEFORE any A3 number)

Date: Wed 2026-10-14 (PKT). Parent documents: `G9_fp_prereg.md` (Stage A prereg + Addendum A) and `G9_fp_stageA.md` (Stage A closeout, commit 7c79d09).

## Status of this test (read first)
- **A3 is a post-hoc follow-up ablation.** It was proposed **after** the Stage A holdout results were seen (G9_fp_stageA.md section 6.1: "A0 + minHits 3 without the high thresholds"). It is therefore **NOT a preregistered confirmatory test** on the VB8 holdout. The holdout has been looked at for this exact question; any A3 holdout number is a **re-use of an already-seen holdout** and is labelled as such.
- **Even a pass is only "provisional"**, until it is confirmed on fresh, independent footage (new recordings / uploaders not in VB8-holdout or DEV).
- Nothing is trained or tuned, on DEV or on the holdout. The holdout is never used to pick or change any parameter.

## Fixed configuration (no free parameters)
A3 = G3 exactly as deployed in A0, plus a 3-frame confirmation:
| item | A3 value | same as |
|---|---|---|
| model | G3 (`det_yolo11n_640_raw.onnx`, sha256 c6fcb32a…, raw 480, class-wise NMS 0.7) | A0 |
| detector score floor | **0.35 for all 12 classes** (G3 original; NOT the A1 per-class thresholds) | A0 |
| preprocessing, letterbox, decode, scene guard (minAreaFrac 0.01, maxSameClass 0) | unchanged | A0 |
| tracker | IouTracker defaults except **minHits 3** (a track is displayed only after 3 matched frames), **birth margin 0** | A2's tracker policy |
| target fps (holdout) / stride (DEV) | 10 fps fixed-frame / stride 1 | A0-A2 |
Config literal: `{"model": "G3", "thr": [0.35]*12, "minHits": 3, "delta": 0.0}`. G3, its default app config and the Roboflow results in `ml/runs/G9/existing/` are not changed.

## Evaluation (same as A0-A2)
- DEV: the same cached-detection replay (`ml/runs/G9/fp/scripts/g9fp_replay.py`, DEV synthetic det + neg clips, val stills), same metrics.
- Holdout: replayed **once** on Kaggle free CPU with the same pipeline code as kernel `mfaizannnn/nutrisole-g9-fp-holdout` (A0 re-run in the same kernel as a parity check against G8/Stage A), scored with the same unchanged scorer (`g9fp_holdout_score.py` -> G8 `g8_holdout_score.py` functions) and the same verified-window / TTFC extras.

## Promotion limits (unchanged from Stage A; checked vs A0 = G3)
A3 "passes" only if **all** hold on the holdout:
1. **No lost showcase-class pair** (citrus, apple, banana, tomato, carrot) vs G3.
2. **At most 1 other lost verified clip-class pair** vs G3 (22 verified pairs).
3. FA/min <= 0.5 x A0 (whole clip, provisional; also reported in verified-review-frame windows).
**An FA reduction cannot compensate for a recall loss**: failing 1 or 2 is a fail whatever the FA cut. G8 rule 4 and the other G8 promotion rules still apply for any actual promotion, and a pass here is "provisional" only (see status above).

## No changes after seeing results
The 3-frame rule (minHits 3 with the stock IouTracker semantics above) is fixed now. It will not be altered after seeing A3 results. Variants such as **2-of-3 frames** or a **crop verifier** are later work, explored on **DEV only**, and would need their own prereg and fresh footage.
