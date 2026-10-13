# G9 Stage A pre-registration addendum: false-positive elimination, low-cost steps (no training)

Written Wed 2026-10-14 ~02:15 PKT, **before any G9 Stage A number was computed** (no threshold sweep, no DEV replay and no
holdout replay of any G9 arm had been run when this file was committed). Briefs: `files/nutrisole-g8-fp-elimination-gpt.md`
(Stage A) and `files/nutrisole-g9-existing-models-gpt.md` (Phase 4 arm A). Champion and reference: **G3** (yolo11n trained 640,
deployed raw 480 + class-wise NMS 0.7, `det_yolo11n_640_raw.onnx` sha256 c6fcb32a…40c1, scene guard rule 2 off / minAreaFrac 0.01,
IouTracker app defaults, detectorMinScore 0.35). Promotion rules of G8 (`G8_prereg.md` section 4 + Addendum 2026-10-14) are kept.
Another G9 track (existing public detectors, `ml/runs/G9/existing/`) runs in parallel and is not part of this addendum.

## 1. Arms (same weights for all three; only post-processing changes)
- **A0** = G3 as deployed (global detector score >= 0.35, IouTracker DEFAULT incl. minHits 2).
- **A1** = A0 + per-class detector score thresholds t_c (applied to decoded boxes before the scene guard and tracker, replacing
  the single 0.35 floor; t_c >= 0.35 always), chosen on DEV by the rule in section 3.
- **A2** = A1 + provisional-display / new-track evidence policy, tuned on DEV (section 4). Two knobs only:
  `minHits` in {2, 3, 4} (a track is displayed only after that many matched detections) and a **birth margin** delta in
  {0, 0.05, 0.10, 0.15}: a detection that does not overlap an existing track (IoU < iouMatch 0.3 with every live track box)
  may start a new track only if score >= t_c + delta; detections continuing a track need only t_c. (minHits 2, delta 0) == A1.

## 2. Data roles
- **DEV (selection allowed)**: G3 `val` stills (n = 402, 90 without boxes; `g3data/det_v3/val.txt`) and the synthetic G3 DEV
  clips `/workspace/work/cv/g3clips_dev` (det clip: 24 segments built from val images, so not independent of val; neg clip:
  240 s from 60 `devneg` stills; `g3clips_devneg/neg_clip` is byte-identical and is not counted twice).
- **DEV negatives** for the FA goal: the DEV neg clip (4.0 min) = primary; the 90 box-free val stills (image-level false-box rate)
  = secondary. Caveat stated now: the primary pool is tiny (G3 had 3 false tracks there in G8), so a halving is 3 -> <= 1 track.
- **Holdout (confirmation only, run ONCE per arm after freezing)**: VB8-holdout clip-level truth
  (`ml/runs/G8/review/holdout/clip_level_truth.csv`: 22 verified positive clip-class pairs on 13 clips / 11 uploaders, 16 reviewed
  negative clips, 36.37 min), replayed exactly as the G8 closeout (`g8_holdout_kernel.py` pipeline on Kaggle free CPU, 480,
  ~10 fps fixed-frame, 1 thread) and scored with the unchanged `ml/runs/G8/scripts/g8_holdout_score.py` (pair detected = class
  displayed >= 0.5 s; FA/min = distinct displayed track ids per negative minute).
- **Analysis only**: the 74 reviewed absence-check tiles / 66 human-false tiles (G8 hard-negative list) - error register only;
  never used to pick a threshold or a policy. Locked image/test splits: not used for any choice.

## 3. Per-class threshold rule (A1), frozen now
1. Run G3 (raw 480, class-wise NMS 0.7, decode floor 0.35) on the 402 val stills. Match boxes to ground truth greedily by score,
   same class, IoU >= 0.5. For each class c and each t in {0.35, 0.40, ..., 0.90}: P_c(t), R_c(t), F1_c(t), FP_c(t), and the
   FA/min of G3 + IouTracker on the DEV neg clip with only class c thresholded at t (others at 0.35).
2. **Recall constraint: R_c(t) >= R_c(0.35) - 0.05** (at most 5 percentage points of recall lost per class). The brief requires
   this for the 5 showcase classes (citrus, apple, banana, tomato, carrot); it is applied to **all 12 classes** here (more
   conservative; no supported class is silently sacrificed).
3. **t_c = the largest grid t meeting the constraint** (the most false positives removed within the recall budget).
4. A class with fewer than 10 val instances keeps t_c = 0.35 (too little evidence).
5. One-time guard on the DEV det clip: if A1 loses more than 1 of 24 segments (segment_acc drop > 0.042) vs A0, the classes of the
   lost segments revert to 0.35 once; no further iteration. Thresholds are then frozen in `ml/runs/G9/fp/thresholds_A1.json`.

## 4. A2 policy rule, frozen now
Grid = 3 x 4 = 12 configs on top of frozen A1, replayed on the DEV det + neg clips (fixed-frame, stride 1, quality classifier
E224 T 0.25 as in G8 DEV runs). Admissible: segment_acc >= A0 - 0.042 (<= 1 segment), frame_acc >= A0 - 0.05,
TTFC p90 <= A0 p90 + 500 ms. Pick: min DEV neg FA/min, then min mean false-track lifetime, then max frame_acc, then smallest
(minHits, delta). If none is admissible, A2 = A1. Frozen in `ml/runs/G9/fp/policy_A2.json`.

## 5. Goal and confirmation
- **DEV goal**: FA/min on the DEV neg clip <= 0.5 x A0 (and secondary val false boxes / box-free image reported) while every class
  keeps R_c within 5 pp (by construction for A1; reported for A2 via the det clip).
- **Holdout confirmation (once)**: FA/min <= 0.5 x A0's holdout FA/min (A0 replayed in the same kernel; expected ~2.86) AND clip
  presence recall drop <= 5 pp, i.e. **at most 1 of 22 pairs lost**, and **no showcase-class pair lost** (n per class <= 4, so
  any lost pair exceeds 5 pp for that class). Reported with the uploader-level bootstrap (1000) as in G8.
- **Promotion = G8 rules unchanged.** Rules 1, 2, 7, 8 concern weights (identical here, so they are reported as unchanged).
  Rule 3 (historical TEST gauntlet) and rule 5 (neg_test image FA at the arm's thresholds) are run once on the frozen arms if CPU
  allows, else reported as not run. Rule 4 (clip level, provisional): recall >= A0 AND FA/min <= A0. Rule 6 latency: post-processing
  only, reported. An arm that meets the G9 goal but fails a G8 rule is reported as "goal met, not promoted".

## 6. Metrics reported for A0 / A1 / A2
DEV: per-class P/R/F1 vs threshold, val false boxes on box-free images, det clip segment / frame accuracy, TTFC p50/p90,
ID switches, fragmentations; neg clip FA/min, false track births/min (= distinct displayed ids per minute), mean / max false-track
displayed lifetime (s), FA episodes/min. Holdout: everything in `holdout_scores.md` (recall, per class, FA/min, neg clips with a
class FA, TTFC proxy, births/min, tracks per pair, label changes).

## 7. Loop limit
If any step needs more than two attempts, it stops, the reason is recorded in `G9_fp_stageA.md`, and the next step proceeds.

## Addendum A (Wed 2026-10-14 ~02:25 PKT): user additions, written after the DEV freeze and BEFORE any holdout replay of A0/A1/A2
Frozen DEV choices at this point (unchanged by this addendum): A1 thresholds `ml/runs/G9/fp/thresholds_A1.json`, A2 policy
`ml/runs/G9/fp/policy_A2.json` (minHits 3, delta 0). These additions change only what is reported, not any arm.
1. **Holdout negatives are verified only at reviewed moments.** Holdout false alarms are reported two ways, each with its evaluated
   negative minutes: (a) **whole clip** (G8 definition, labelled *provisional*); (b) **verified-negative windows only**: the union per
   negative clip of [t - 1 s, t + 1 s] around every reviewed absence-check tile moment (`absence_check.csv` t_s) and around each of the
   6 clean presence-review frames (t = D (k + 0.5) / 6, k = 0..5, D = clip duration, as in `g8_holdout_presence_sheets.py`; the
   +-1 s around these instants is our assumption, stated). A displayed track counts as a window false alarm if it is displayed at any
   processed frame inside a window; window FA/min = such tracks / window minutes; displayed track-seconds inside windows also reported.
   The goal test (section 5) is reported on both; (b) is the verified one, (a) stays provisional.
2. **Candidates for a full-video human check**: every whole-clip negative track (any arm) displayed >= 0.5 s with max displayed
   score >= 0.70 outside the verified windows is listed (clip, time span, class, max score) - these may be real produce in
   un-reviewed parts of the recording.
3. **TTFC audit**: holdout TTFC proxy is time from clip start to first display of the class (G8 definition); per-pair values are
   listed and the high p90 is explained per clip. On the DEV det clip (box-level object truth) TTFC is also measured from the
   first frame the GT object is visible (first frame of the segment with a GT box of the segment class), next to the scorer's
   segment-start TTFC.
4. **Raw detector vs post-tracking** metrics are reported separately: raw = boxes after the per-class threshold and area guard,
   before the tracker (boxes/min, frames with >= 1 box, per class); post-tracking = displayed tracks (FA/min, births, lifetime).
   The holdout kernel additionally records per processed frame the raw G3 boxes (class, score) at the 0.35 floor after the area guard
   so raw metrics for every arm's thresholds are computed from the same replay.
