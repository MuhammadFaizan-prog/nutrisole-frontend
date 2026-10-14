# G9 Stage E: independent market-pile DEV set + G3 selective score-floor grid (pre-registration)

Written 2026-10-14 (PKT) **before any Stage E result**: no M-DEV image has been collected, no M-DEV label exists, and no ssf 0.525 / 0.55 /
0.575 number has been computed. Authoritative brief: user, 2026-10-14 16:21 PKT (`files/nutrisole-g9-stageE-gpt.md`). Branch `cv-gauntlet`
only; no merge, no PR, no main. **G3 stays champion.** Nothing in Stage E can be promoted: promotion needs a separate untouched evaluation
under its own prereg. **No training in Stage E** (no GPU training, no fine-tune, no new weights).

## 0. Stated up front (Stage D facts, `G9_stageD.md`, commit c281d50)

- **D0/ssf50 failed A5** (val box-free false boxes 48 > 43; probe (SYNTHETIC) mixed-scene false tracks 5.078/min = 2.4x > 1.5x limit
  3.17/min), while passing A1 (+21.5 pp small showcase, +10.1 pp small carrot), A2-A4, A6-A8.
- **D0/ssf60 failed A1 and A5**: +15.9 pp small showcase but only +8.3 pp small carrot (< +10 pp); box-free 43 (= limit, passes that
  part) but probe mixed false 4.02/min > 3.17/min.
- The intermediate values 0.525 / 0.55 / 0.575 are **not expected to pass for sure**. Both A1-carrot (needs >= 26 of 228 small val
  carrots displayed; ssf50 shows exactly 26, ssf60 22) and the probe part of A5 (both ends above 3.17/min) are near or past their limits
  at both ends of the grid. **The likely outcome is that no grid point passes**, in which case Stage E closes (section 6).

## 1. Configurations (the only thing that varies)

Fixed for every config: G3 YOLO11n weights (`best.pt` sha256 29cc5212...; ONNX `g3models/k11_480/det_yolo11n_640_raw.onnx`), 480 letterbox,
raw decode + class-wise NMS 0.7, score floor 0.35, 12 classes in G3 order, IouTracker defaults (iouMatch 0.3, minHits 2, maxMissed 4).
Area = fraction of the **source** frame, guard applied per frame after decode/floor/NMS/dst_to_src and before the tracker.

| Config | Rule |
|---|---|
| **g1** (baseline = deployed G3) | drop boxes < 1% of the frame |
| **ssf50 / ssf525 / ssf55 / ssf575 / ssf60** | boxes >= 1%: normal 0.35 floor; boxes in [0.25%, 1%): kept only if score >= 0.50 / 0.525 / 0.55 / 0.575 / 0.60; boxes < 0.25%: dropped |
| none (diagnostic only, never selectable) | all boxes >= 0.35, no guard |

ssf50 / ssf60 are re-run for continuity (they must reproduce Stage D on DEV exactly).

## 2. Physical-produce definition (annotation rule for M-DEV and M-TEST)

A target is a **physical, whole (or nearly whole, >= ~50% visible through occlusion) fruit or vegetable of one of the 12 classes**, as it
would be sold: a single item, or for banana one **hand/bunch per box** (a separated single finger is its own box). Class rules: capsicum =
whole bell pepper (any colour); chilies / long peppers are **not** capsicum (negatives); lemon_lime = lemons and limes only (small
citrus-shaped, yellow or green); large green produce (green mango, guava, green apple, green tomato, gourds, melons, green bell pepper) is
**never** lemon_lime; citrus = orange / mandarin / kinnow / grapefruit / sweet lime (mosambi is citrus; lemon/lime is lemon_lime).
**Not targets:** slices, halves, cut or peeled pieces, juice, cooked food, printed images (posters, cartons, signs, bags, labels, screens),
plastic/toy/decorative fruit, costumes, and any produce outside the 12 classes. A whole item visible through a clear plastic bag counts.

**Completeness:** every target in an evaluated image is boxed. Where a pile is too dense to box item by item at native resolution, the
pile is covered by a **crowd region** with its class (COCO `iscrowd` semantics): GT inside it is not counted, and a detection whose
centre lies inside a crowd region **of the same class** is ignored (neither TP nor FP); a detection of a different class inside a crowd
region counts as a false box (class error). An image whose targets cannot be boxed or crowd-covered with confidence is rejected and
recorded. Labels are produced by the agent, so they are stated as **agent-verified, not human-verified**.

## 3. Market set M: sources, exclusions, split

- **Sources (licence recorded per file):** Wikimedia Commons per-file CC0 / CC BY / CC BY-SA / PD; Zenodo CC BY; Kaggle / Roboflow datasets
  only with a permissive licence recorded per dataset. **Never:** Pexels / Pixabay / Mixkit; DEV (val stills, DEV det/neg/quality clips,
  M-dev clips, probe sources); the reviewed holdout (34 clips + keyframes) and its uploaders; Stage D set S **and all 586 Stage D Commons
  candidates** (they were viewed with G3 proposals) **and the S uploaders**; G3 training images (det_v3 train).
- **Content target:** market / mandi stalls, carts, greengrocer displays with small and piled produce; all 5 showcase classes (citrus,
  apple, banana, tomato, carrot) plus other supported classes; **real negatives** = box-free market scenes (clothing, shoes, signs, bags,
  printed food images, non-supported produce such as chilies, onions, gourds, melons).
- **Source key** = Commons uploader, except bot uploads (GeographBot, Panoramio upload bot, Flickr upload bot, any uploader ending in
  "bot") where the source key is the credited author; Kaggle/Roboflow/Zenodo: dataset id + original author where given.
- **Split rule (fixed now, applied before any labelling):** `sha1(source_key) mod 3 == 0` -> **M-TEST**, else **M-DEV**. All images of one
  source go to one split. **M-TEST is never scored, tuned on, or label-reviewed in Stage E**: it is only collected, licence-recorded and
  pHash-audited; it is reserved for a later untouched evaluation under its own prereg.
- **Size target:** >= 60 M-DEV images (incl. negatives) and >= 30 M-TEST images if sources allow; any shortfall is reported.
- **Leakage audit:** 64-bit pHash of every M image vs DEV val stills, every 10th frame of DEV det/neg/quality clips, all G7 stage-1 clip
  keyframes (holdout + M-dev + M-train), Stage D S + all 586 Stage D candidates, and det_v3 train. Distance <= 10 -> dropped. Within M,
  M-DEV vs M-TEST near-duplicates (<= 10) -> the M-TEST copy is kept and the M-DEV copy dropped.

## 4. Labelling procedure (M-DEV)

- **No G3 proposal is used for labelling.** Boxes are either drawn from scratch or proposed by a **non-G3 open-vocabulary detector**
  (OWLv2 or Grounding DINO, text queries per class), followed by **full manual box-by-box correction** on gridded review sheets: each
  proposed box is kept, deleted, re-drawn, or relabelled; missed targets are added; crowd regions are drawn; the **class of every box is
  verified** (explicit check: no lemon_lime on large green produce; citrus vs apple vs tomato on red/orange round produce; capsicum vs
  chili).
- **Second independent agent pass** on a random sample (>= 15 M-DEV images, seed 0): labelled again from the raw image without seeing the
  first-pass labels; agreement reported as box-level F1 at IoU 0.5 (class-aware and class-agnostic), class agreement on matched boxes,
  and image-level negative agreement. The first pass is the evaluation GT; disagreements are listed by error type.

## 5. Evaluation and frozen acceptance

Material: (a) existing DEV (val stills 402, DEV det/neg clips, Stage C probe **SYNTHETIC**, always reported separately) for **A-gate
continuity**; (b) M-DEV stills (real, agent-verified). CPU latency: same detector as Stage D D0, so A7 uses the Stage D D0 measurement
plus the measured post-processing time of each config.

**A1-A8 are unchanged from `G9_stageD_prereg.md` section 5** (relative to D0/g1 = deployed G3, on DEV): A1 small showcase displayed recall
>= +10 pp and small carrot >= +10 pp; A2 showcase normal recall no drop > 2 pp (val + DEV det); A3 per-class AP50 no drop > 0.02 (weights
unchanged, so 0 by construction); A4 DEV neg FA episodes/min and tracks/min <= 1.00; A5 false boxes per recovered object <= 1.0 **and**
box-free false boxes <= 43 **and** probe (SYNTHETIC) mixed false tracks/min <= 1.5x g1 (<= 3.17); A6 TTFC p90 <= 807 ms; A7 CPU p95 <=
1.10x D0; A8 IDs/segment <= D0 + 0.10. **None is loosened.**

**Additional market checks (can only reject, never admit):** on M-DEV, vs g1:
- **M1** displayed small (<1%) showcase recall >= g1 + 5 pp;
- **M2** (new false boxes) / (new TP) <= 1.0, new TP > 0;
- **M3** false boxes on M-DEV negative (box-free) images <= g1 + 2.

**Reported (brief item 5), per config:** small-produce recall (showcase and all classes, by size bin), small-carrot recall, AP50 (per class
on M-DEV, computed on the displayed set; raw AP50 at floor 0.01 as a reference), box-free false boxes, false boxes per recovered object,
real-market false tracks/min (only if licensed market video exists; otherwise stated as unavailable), fragmentation (DEV det IDs/segment,
ID switches), CPU latency. Synthetic probe results in their own columns.

**Selection:** admissible = passes A1-A8 and M1-M3. Among admissible, the largest DEV small-showcase displayed recall; ties within 1 pp ->
the higher floor (ssf60 > ssf575 > ssf55 > ssf525 > ssf50). Frozen pick -> `ml/runs/G9/stageE/frozen_pick.json`. Any pick is a **DEV pick
only**.

## 6. Close-out rule

**If no grid point is admissible, the frozen pick is g1 (unchanged G3) and the score-floor line is closed**: no further ssf values are
tried. The next step is then (brief item 7) **annotation repair + a larger, properly labelled market training set**, trained with
multiple seeds and a replay-only control, judged on M-DEV and finally on the untouched M-TEST. M-DEV is never used for training after
being used for tuning (brief item 8).
