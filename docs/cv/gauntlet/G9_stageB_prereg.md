# G9 Stage B pre-registration: hard-negative fine-tune, crop verifier, carrot #16 analysis

Written Wed 2026-10-14 ~08:00 PKT, **before any Stage B result exists**: no hard-negative mining pass, no fine-tune, no verifier
training and no Stage B replay (DEV or holdout) had been run when this file was committed. Brief (authoritative):
`files/nutrisole-g9-stageB-gpt.md` (user, 2026-10-14 07:40 PKT). Champion and reference: **G3** (yolo11n trained 640, deployed raw 480 +
class-wise NMS 0.7, `det_yolo11n_640_raw.onnx` sha256 c6fcb32a…40c1, scene guard minAreaFrac 0.01 / maxSameClass 0, detector floor 0.35,
IouTracker app defaults incl. minHits 2, E224 quality classifier). **G3 and the Roboflow results are not changed.** No threshold or
gate is tuned on the reviewed holdout. No architecture change, no new confirmation-gate variant.

## 1. Data roles
- **Holdout (never trained on, never mined, never used for a choice)**: G6 locked 15 + `holdout_v7_pending` 9 + `negatives_v7` 10 = 34 clips
  (`ml/runs/G7/video_v7/splits_v7.csv`), truth `ml/runs/G8/review/holdout/clip_level_truth.csv`. The 74 reviewed absence-check tiles
  (66 false) only define the **mistake types** to look for elsewhere; they are never training data.
- **Holdout re-use is declared**: this is the 4th replay of the same holdout (G8, G9 Stage A, G9 A3, Stage B). No fresh independent
  final footage exists at the time of writing. Any Stage B "pass" is therefore **provisional until replayed once on fresh, independent
  footage** with DEV decisions frozen as recorded here.
- **Mining pool M** (independent of the holdout): VB8 / G7 recordings whose split is `dev`, `dev_v7`, `train_v7_weak`, `weak_exploratory`
  or `train_only`, **minus** (a) every clip by uploader **Muktee1494** (this uploader also has holdout clips: source leakage risk) and
  (b) the 3 `excluded` clips. M is split **by uploader** into **M-train** (mined for training) and **M-dev** (never trained on; DEV
  video and DEV hard-negative evaluation). The split is written to `ml/runs/G9/stageB/mining_split.csv` before mining.
- **New still images**: Wikimedia Commons files with a per-file CC0 / CC BY / CC BY-SA / public-domain licence (licence and author
  recorded per file), searched for the target types (clothing / fabric, sacks, fish, spices, signs, packaging, printed fruit pictures,
  fruit-coloured objects). Never Pexels, Pixabay or Mixkit. Split by Commons uploader into train / dev (about 80 / 20).
- **Genuine produce**: the unchanged G3 training data (`det_v3` det / neg / oiv7 / hardneg train; val untouched).
- **DEV (selection allowed)**: G3 val stills (n = 402), synthetic DEV det / neg clips (`g3clips_dev`), the M-dev video clips and the
  HN-dev images (agent-verified produce-free, section 2).

## 2. Hard-negative (HN) mining and verification
- G3 (as deployed: raw 480, floor 0.35, area guard) runs on M-train / M-dev frames sampled at 2 fps and on the Commons stills. A
  **candidate** is a G3 box >= 0.35 on an object that is not one of the 12 supported classes. High-confidence boxes (0.75-0.91) and the
  target types are prioritised. For video candidates the neighbouring frames (+-0.5 s) and the detection metadata (clip, t, class, score,
  box) are kept. Near-duplicates are removed (perceptual hash, Hamming <= 6, within and across clips).
- **Training samples are background-only**: (a) whole frames / images that contain no supported produce get an empty label file;
  (b) in mixed scenes a crop around the false box (box expanded to >= 2.5x, square, min 160 px) that contains no supported produce
  gets an empty label. **No mixed-scene frame with partial labels is used**: a full frame with produce is used only if ALL supported produce in
  it is annotated and verified; if that cannot be done the frame is not used.
- **Verification**: there is no human reviewer in this run. Every HN sample used for training or evaluation is checked **by the agent
  (Hark) visually on contact sheets**, and must also not overlap an OWLv2/G3 auto-label "agree" proposal where those exist. Status values in
  the manifest: `agent_verified_negative`, `agent_rejected` (contains or may contain supported produce, or unclear), `not_reviewed`.
  Only `agent_verified_negative` is used. **Nothing is called human-verified.** Auto-labels are never treated as ground truth.
- Leakage audit (reported): no sample from a holdout clip, no Muktee1494 clip, no M-dev clip in training; perceptual-hash comparison of
  every HN training sample against holdout keyframes (G7 stage-1 keyframes of the 34 holdout clips) and against the 74 reviewed tiles;
  Commons uploaders vs holdout uploaders.

## 3. Arms
- **B0 = G3** as deployed (reference; replayed in the same kernels).
- **B1 = G3 + HN fine-tune**: initialised from G3 `best.pt`, imgsz 640, same 12 classes, data = all G3 train images + HN-train
  (agent-verified, empty labels) with HN images capped at 20% of the training images; SGD lr0 0.002, lrf 0.1, warmup 1, 20 epochs,
  hsv_h 0 (no hue), otherwise G3-style augmentation; free Kaggle T4. Checkpoint = ultralytics best (val fitness). Deployed exactly as G3
  (raw 480 ONNX, floor 0.35, guard, IouTracker defaults). One seed (0); a second seed only if compute allows (reported, not selected on).
- **B2 = G3 + crop verifier**: MobileNetV3-Small (ImageNet init), binary produce vs non-produce, input 128 x 128 crop of the box expanded
  1.2x. Positives: GT boxes of the G3 train split (all 12 classes). Negatives: G3 false boxes (>= 0.35, IoU < 0.1 with every GT) on G3 train
  images + HN-train crops. **Selective inference with cached track results**: the verifier runs on a track's box when the track is born and then
  at most once per second of video (every 10th processed frame) while it lives; the track's verdict is the mean of its cached
  p(produce); a track is displayed only if (IouTracker would display it) AND verdict >= tau. **tau is frozen on DEV**: the largest tau in
  {0.05, 0.10, ..., 0.50} with **false rejection of real produce <= 2% on val GT crops (n = all val boxes)** and <= 5% for each showcase class
  with n >= 20.
- **B3 = B1 + verifier**: run only if B1 and B2 each pass their DEV gates (section 5) and each lower a DEV FA metric; otherwise not run
  and reported as "not justified".

## 4. Metrics (all arms)
DEV: val per-class AP50 / P / R (P/R at 0.35; for B2/B3 P/R after verifier at tau, AP50 for detector arms only), val false boxes on
box-free images, DEV det clip segment / frame accuracy and per-class frame recall, DEV neg clip FA/min, HN-dev false-box rate (images or crops
with >= 1 displayed-class box >= 0.35 / n), M-dev video displayed track births/min (unverified, report only), TTFC (DEV from first
visibility), ID switches / fragmentations, verifier false-rejection on real produce (val GT crops, per class) and true-rejection on HN-dev /
val false boxes. Holdout (once per arm, Kaggle CPU, scorer unchanged from G8/G9-A): verified positive pairs detected / recovered / lost vs G3
(22 pairs; showcase 14), FA/min whole clip (provisional) and in the verified presence-review windows, false alarms in mixed market scenes
(false tracks on verified-positive clips of a class not in that clip's truth), TTFC proxy, tracking stability (births/min, label changes per
track-min), CPU p50 / p95 per frame (detector + verifier), verifier calls per frame. Mobile feasibility: params, ONNX size, measured CPU ms.

## 5. Promotion limits (frozen now)
An arm is promoted over G3 only if **all** hold:
1. **Holdout recall**: no verified **showcase-class pair** (citrus, apple, banana, tomato, carrot) lost vs G3, and **at most 1 other verified
   pair** lost vs G3.
2. **Holdout false alarms**: whole-clip FA/min <= 0.75 x G3 (same kernel) AND FA/min in the verified presence windows <= G3.
3. **DEV recall**: on val stills, recall at 0.35 (after verifier for B2/B3) drops <= 5 pp vs G3 for every class with n >= 10, and showcase
   AP50 drops <= 0.02 per class (detector arms); DEV det clip per-class frame recall of the showcase classes drops <= 5 pp.
4. **DEV latency**: CPU p95 per frame (detector + verifier as run, same machine, interleaved) <= 1.10 x G3.
5. B2/B3 only: verifier false rejection on real produce (val GT crops) <= 2% overall and <= 5% per showcase class (n >= 20).
Gate 3-5 are checked on DEV **before** the holdout replay; an arm failing a DEV gate is still replayed once on the holdout for the record
but cannot be promoted. Promotion is never decided by suppressing real fruit or because boxes look cleaner. Even a pass is provisional
(section 1, holdout re-use).

## 6. Carrot #16 (analysis only)
Document from the existing holdout replays (no new tuning) why the carrot track in #16 (ca1cbf110, 2.2-s clip) fragments within ~0.6 s:
per-frame raw boxes, scores, IoU between consecutive boxes, matcher decisions. Study association of short-lived objects on DEV only (DEV det clip:
track lifetimes, fragmentations vs object duration, IoU drop between consecutive frames). No confirmation-gate variant is proposed or tested.

## 7. Loop limit
Any step that needs more than two attempts stops; the reason is recorded in `G9_stageB.md` and the next step proceeds.
