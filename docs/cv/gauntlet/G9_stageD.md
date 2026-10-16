# G9 Stage D: small-object training + false-positive control (DEV ONLY)

2026-10-14 PKT, branch `cv-gauntlet`. The pre-registration was committed and synced **before any Stage D result**:
`docs/cv/gauntlet/G9_stageD_prereg.md` (commit ec66796). The old holdout (G6 locked 15 + holdout_v7_pending 9 + negatives_v7 10, incl.
carrot #16) was **not used at all**. Nothing is promoted. **G3 stays champion.**

## Verdict

- **No arm x guard config passed the frozen criteria A1-A8. Frozen DEV pick = D0/g1 (unchanged G3)**:
  `ml/runs/G9/stageD/frozen_dev_pick.json`.
- **Training did not raise raw small-object recall at 480 on DEV val stills.** Raw small showcase recall went 34.5% (D0) -> 31.3% (D1)
  and 30.6% (D2). Small carrots went 17.5% -> 18.4% / 18.9% (+1 to +3 boxes of 228). A1 also requires a raw gain of at least +5 pp, so
  both fine-tunes fail it. Both also fail A3 on class AP50: D1 pomegranate -0.152 and citrus -0.064; D2 citrus -0.048, pomegranate
  -0.037 and tomato -0.032.
- **In-domain signal (analysis only, not a gate):** on the 4-image agent-labelled S-dev market set, mAP50 went 0.106 (G3) -> 0.206 (D1)
  and 0.230 (D2). Citrus recall went 0.02 -> 0.39 / 0.71. On the DEV det clip, tomato frame recall went 0.000 -> 0.517 and carrot went
  0.150 -> 0.217 (D2). So the market-pile data helps where it matches, but not on the kitchen-domain val stills, and it brings drift
  elsewhere.
- **The closest miss is a post-processing change, not training: D0/ssf50.** This is G3 weights with a size-dependent score floor:
  boxes between 0.25% and 1% of the frame must score at least 0.50.
  - It passes A1 (+21.5 pp small showcase, +10.1 pp small carrot), A2, A3, A4 (DEV neg 0.75/0.75 = G3), A6, A7 and A8.
  - It fails A5: box-free false boxes 48 vs the 43 limit, and probe (SYNTHETIC) mixed-scene false tracks 2.4x vs the 1.5x limit.
  - It is the best candidate to carry into a fresh-footage prereg. It is **not** picked.
- **Final validation of anything here awaits fresh, independently labelled footage.**

## 1. Exp1: dataset / annotation audit of the G3 training data (det_v3 train, 3562 images, 2557 labelled)

Sizes are measured against the **source frame**, as the guard measures them. "Side at 480" is the equal-area square side inside the 480
letterbox. Full output: `ml/runs/G9/stageD/out/train_audit.json`. Showcase classes:

| Class (train) | boxes / images | share < 1% of frame | share < 0.25% | side at 480 < 32 px | side at 480 p10 / p50 / p90 | overlapping same-class (IoU > 0.1) |
|---|---|---|---|---|---|---|
| citrus | 1543 / 246 | 45.6% | 15.4% | 31.8% | 16.9 / 44.9 / 106.2 | 46.3% |
| apple | 2849 / 430 | 65.9% | 38.1% | 55.5% | 8.2 / 27.7 / 88.3 | 44.7% |
| banana | 3825 / 487 | 54.9% | 23.7% | 43.7% | 12.4 / 36.1 / 123.6 | 78.1% |
| tomato | 3192 / 447 | 70.0% | 32.5% | 57.8% | 12.1 / 27.6 / 69.4 | 29.3% |
| carrot | 3290 / 340 | 62.6% | 26.3% | 47.9% | 12.6 / 33.2 / 76.8 | 56.2% |

- **Small boxes are not scarce.** Most showcase training boxes are already below 1% of the frame. Carrot images split by carrot count
  as 1: 49, 2-4: 87, 5-9: 104, >=10: 100, so piles are present too.
- Other classes: guava has **0** training boxes in det_v3 train, so its head is kept but untrained here. Mango has 276 boxes,
  lemon_lime 452 and potato 696; these are thin classes.
- DEV val is similar (carrot 52% < 1%, 435 boxes / 50 images).
- **Missing boxes / label quality.** I reviewed 36 random train images with showcase boxes (agent review, not human), with G3 640-tiled
  proposals that matched no GT drawn in red (`out/missing_sample.json`, `out/missing_review.json`):
  - 5/36 (~14%) miss at least one real produce box (LVIS federated labels, e.g. half a banana bunch unlabelled).
  - 10/36 (~28%) carry their small boxes on **slices or pieces** (tomato on pizza or salad, carrot sticks) or props (a banana costume
    with 34 boxes), not whole produce.
  - Only **1/36 is a market or vendor scene.**
- **Domain gap (headline):** the small objects G3 learned from are mostly kitchen and table food items photographed close (COCO / LVIS /
  OIV7, median long side 640). Distant, piled market produce is nearly absent. The deploy-time gap is resolution (trained 640,
  deployed 480: objects are 0.75x) plus domain, not a lack of small boxes.

## 2. Collected independent small / overlapping / piled set S

- **Source.** Wikimedia Commons, searched with 32 produce-market queries. Only files with a per-file CC0 / CC BY / CC BY-SA / PD
  licence, JPEG, long side >= 1200. Uploaders of holdout clips (and those excluded for holdout overlap) were skipped at search time.
  - 586 candidates were downloaded at 1600 px.
  - Box proposals came from G3 at its trained 640 on overlapping 640-px tiles plus a whole-image pass (`scripts/teacher_tiles.py`).
- **Agent verification** (stated as agent-verified, **not** human):
  - A shortlist of 196 (single-class-dominated, many small proposals) was triaged on overview sheets. 44 were reviewed on gridded
    detail sheets.
  - Per image (`review_edits.json`): wrong boxes dropped by grid cell; whole images or cells relabelled to the true class (e.g. teacher
    "apple" on oranges -> citrus, "citrus" on yellow tomatoes -> tomato); unboxed or ambiguous produce greyed out (ignore regions, grey
    114). The aim is that every remaining produce item of the 12 classes is boxed.
  - A second visual pass on the final labels fixed 5 images and rejected 1 more.
  - Box-level completeness inside dense piles was judged at review resolution, not counted box by box.
  - 26 were accepted and 11 rejected (marigold-like or ambiguous fruit, printed fruit on cartons, coconuts/limes boxed as apple,
    bagged mixed fruit). Banana piles were not used: the teacher mixes finger and hand boxes inconsistently.
- **Leakage audit** (`out/leakage_audit.json`): 64-bit pHash vs all keyframes of the 69 G7 stage-1 clips (34 holdout + M-dev + M-train),
  402 DEV val stills, every 10th frame of the DEV det/neg/quality clips, and det_v3 train.
  - 6143 reference hashes; **minimum distance 14, 0 within 10, 0 near-duplicates within S.**
  - 1 image dropped because its uploader also uploaded an M-dev clip.
- **Final S = 24 images, 3701 boxes** (`s_manifest.csv` with page, licence, uploader and author per file; labels in `s_labels.json`).
  Licences: CC BY-SA 4.0/3.0/2.0, CC BY 2.0, CC0. Split by uploader (~20%):
  - **S-train 20 images:** tomato 1319, carrot 992, apple 561, citrus 276 boxes. 90-97% of boxes are < 1% of the frame; median side
    at 480 is 13-21 px.
  - **S-dev 4 images** (546 boxes, analysis only).
  - Stats: `out/s_stats.json`.
- **Not used:** DEV, the reviewed holdout, Muktee1494, Pexels/Pixabay/Mixkit, Zenodo/Kaggle/Roboflow (not needed; no licence-verified
  produce-pile set was found within budget).
- Caveat: labels started from G3 proposals, so S inherits G3's notion of what a box is, and G3's S-dev carrot recall (0.73) is inflated
  by that.

## 3. Exp2: training (free Kaggle T4; kernels `mfaizannnn/nutrisole-g9d-ctl` v1 and `mfaizannnn/nutrisole-g9d-train` v1)

- **Recipe.** All arms start from G3 `best.pt`, with 12 classes in G3 order and the recipe of Stage B B1: imgsz 640, SGD lr0 0.002 cosine,
  20 epochs, mosaic 1.0, close_mosaic 5, seed 0. Inputs came from the existing Kaggle datasets `nutrisole-cv-g3` (det_v3.tar) and
  `nutrisole-cv-g6-w` (G3_best.pt). S images were fetched by URL inside the kernel.
- **D-ctl:** replay only (3562 base images). 628 s.
- **D1:** base + S-train repeated 31x = 620 rows (14.8% of the list). 841 s.
- **D2:** D1 + 1045 offline zoom-out collages (2x2 / 3x3 of fully labelled base+S images, 20.0%) + scale 0.9. 991 s.
- **D3 not run:** ~1.8x detector FLOPs cannot meet A7 by construction.
- **ONNX:** raw 480 exports (Ultralytics export, same as B1).
- **Weights:** sandbox and Kaggle output only. sha256 is in the pick JSON.
- **Kernel metrics:** `kaggle_out/*.json`.

**Per-class AP50 (Ultralytics val 480, det_v3 val; guava has no val boxes):**

| AP50 (val 480) | banana | apple | mango | citrus | pomegranate | lemon_lime | tomato | potato | cucumber | carrot | capsicum | mAP50 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D0 | 0.5627 | 0.6261 | 0.6462 | 0.7446 | 0.5485 | 0.1007 | 0.4581 | 0.0092 | 0.2952 | 0.4409 | 0.2779 | 0.4282 |
| D1 | 0.5292 | 0.6626 | 0.7533 | 0.6806 | 0.3961 | 0.0703 | 0.4375 | 0.0607 | 0.2641 | 0.4025 | 0.2688 | 0.4114 |
| D2 | 0.5372 | 0.6078 | 0.6615 | 0.6964 | 0.5119 | 0.0955 | 0.4266 | 0.0143 | 0.3164 | 0.4379 | 0.3451 | 0.4228 |
| Dctl | 0.5716 | 0.6679 | 0.6038 | 0.7606 | 0.5488 | 0.0743 | 0.4817 | 0.0323 | 0.2873 | 0.4613 | 0.3093 | 0.4363 |

**S-dev (4 agent-labelled market images, analysis only), P / R / AP50:**
- citrus: G3 .11/.02/.003; D1 .72/.39/.43; D2 .54/.71/.65
- tomato: G3 .35/.24/.17; D1 .25/.28/.19; D2 .49/.20/.11
- carrot: G3 .29/.73/.47; D1 .37/.74/.62; D2 .31/.77/.62

## 4. Exp3/Exp4: DEV evaluation, raw (pre-guard) and displayed (post-guard)

- **Material:** DEV val stills (402); DEV det clip (24 segments) and DEV neg clip (4.0 min, verified negatives); Stage C **SYNTHETIC**
  probe (4254 frames).
- **Guards:**
  - g1 = 1% (G3).
  - g05 / g025 = reduced guards.
  - ssf60 / ssf50 = size-dependent score floor: 0.25-1% boxes need score >= 0.60 / 0.50; boxes < 0.25% are dropped.
  - none = raw diagnostic.
- **Small** = GT < 1% of the source frame. **Normal** = GT >= 1%.
- **Files:** per-config JSON `ml/runs/G9/stageD/dev/{ARM}_{GUARD}.json`; summary and criteria `out/summary.json`.
- D-ctl is analysis only and never selectable.

| Config | val small showcase R | val small carrot R | val TP / FP | box-free FP | DEV neg tracks/min / episodes/min | probe small showcase R (SYNTH) | probe mixed false/min (SYNTH) | TTFC p90 ms | IDs/seg | Failed |
|---|---|---|---|---|---|---|---|---|---|---|
| D0/none | 34.5% (296/857) | 17.5% (40/228) | 844 / 433 | 66 | 1.25 / 1.0 | 5.0% | 8.674 | 707 | 1.208 | raw (diagnostic) |
| D0/g1 | 2.6% (22/857) | 1.3% (3/228) | 558 / 232 | 39 | 0.75 / 0.75 | 0.3% | 2.116 | 707 | 1.208 | A1, A5 |
| D0/g05 | 20.6% (177/857) | 11.4% (26/228) | 725 / 335 | 51 | 1.25 / 1.0 | 2.3% | 5.501 | 707 | 1.208 | A4, A5 |
| D0/g025 | 31.6% (271/857) | 17.1% (39/228) | 819 / 399 | 59 | 1.25 / 1.0 | 4.0% | 8.039 | 707 | 1.208 | A4, A5 |
| D0/ssf60 | 18.4% (158/857) | 9.7% (22/228) | 703 / 265 | 43 | 0.75 / 0.75 | 2.4% | 4.02 | 707 | 1.208 | A1, A5 |
| D0/ssf50 | 24.0% (206/857) | 11.4% (26/228) | 752 / 303 | 48 | 0.75 / 0.75 | 3.0% | 5.078 | 707 | 1.208 | A5 |
| D1/none | 31.3% (268/857) | 18.4% (42/228) | 808 / 427 | 46 | 1.75 / 0.75 | 4.1% | 12.694 | 847 | 1.5 | raw (diagnostic) |
| D1/g1 | 2.3% (20/857) | 0.9% (2/228) | 549 / 210 | 24 | 1.5 / 0.75 | 0.2% | 2.962 | 847 | 1.5 | A1, A3, A4, A5, A6, A8 |
| D1/g05 | 18.3% (157/857) | 10.5% (24/228) | 697 / 314 | 36 | 1.75 / 0.75 | 1.6% | 4.866 | 847 | 1.5 | A1, A3, A4, A5, A6, A8 |
| D1/g025 | 29.0% (249/857) | 18.0% (41/228) | 789 / 379 | 42 | 1.75 / 0.75 | 3.1% | 9.52 | 847 | 1.5 | A1, A3, A4, A5, A6, A8 |
| D1/ssf60 | 16.3% (140/857) | 9.2% (21/228) | 676 / 237 | 27 | 2.0 / 0.75 | 1.4% | 3.597 | 847 | 1.5 | A1, A3, A4, A5, A6, A8 |
| D1/ssf50 | 22.3% (191/857) | 13.2% (30/228) | 730 / 278 | 35 | 1.75 / 0.75 | 2.1% | 5.501 | 847 | 1.5 | A1, A3, A4, A5, A6, A8 |
| D2/none | 30.6% (262/857) | 18.9% (43/228) | 815 / 389 | 49 | 1.25 / 1.0 | 5.5% | 13.752 | 747 | 1.708 | raw (diagnostic) |
| D2/g1 | 3.0% (26/857) | 1.8% (4/228) | 567 / 211 | 30 | 1.0 / 1.0 | 0.2% | 2.116 | 747 | 1.708 | A1, A2, A3, A8 |
| D2/g05 | 19.4% (166/857) | 13.2% (30/228) | 719 / 289 | 39 | 1.25 / 1.0 | 1.6% | 5.712 | 747 | 1.708 | A1, A2, A3, A4, A5, A8 |
| D2/g025 | 28.7% (246/857) | 18.4% (42/228) | 799 / 341 | 46 | 1.25 / 1.0 | 3.8% | 8.251 | 747 | 1.708 | A1, A2, A3, A4, A5, A8 |
| D2/ssf60 | 14.7% (126/857) | 11.4% (26/228) | 672 / 234 | 33 | 1.25 / 1.0 | 2.2% | 2.962 | 747 | 1.708 | A1, A2, A3, A4, A8 |
| D2/ssf50 | 21.3% (183/857) | 14.5% (33/228) | 733 / 275 | 38 | 1.25 / 1.0 | 2.8% | 4.866 | 747 | 1.708 | A1, A2, A3, A4, A5, A8 |
| Dctl/none | 33.5% (287/857) | 16.7% (38/228) | 828 / 336 | 32 | 1.5 / 1.25 | 3.7% | 7.193 | 627 | 1.292 | raw (diagnostic) |
| Dctl/g1 | 2.5% (21/857) | 1.8% (4/228) | 549 / 172 | 11 | 1.25 / 1.25 | 0.5% | 3.173 | 627 | 1.292 | A1, A2, A3, A4, A5 |
| Dctl/g05 | 19.4% (166/857) | 11.0% (25/228) | 705 / 262 | 23 | 1.5 / 1.25 | 2.2% | 4.443 | 627 | 1.292 | A1, A2, A3, A4, A5 |
| Dctl/g025 | 31.5% (270/857) | 16.7% (38/228) | 811 / 315 | 29 | 1.5 / 1.25 | 3.1% | 6.135 | 627 | 1.292 | A1, A2, A3, A4, A5 |
| Dctl/ssf60 | 19.8% (170/857) | 11.8% (27/228) | 706 / 200 | 13 | 1.5 / 1.25 | 1.7% | 4.02 | 627 | 1.292 | A1, A2, A3, A4, A5 |
| Dctl/ssf50 | 25.7% (220/857) | 15.3% (35/228) | 757 / 230 | 15 | 1.5 / 1.25 | 2.2% | 5.078 | 627 | 1.292 | A1, A2, A3, A4, A5 |

**Acceptance details** (A4 = the DEV neg columns above; A6 = TTFC; A8 = IDs/seg). Limits: A1 >= +10 / +10 / +5 pp; A2 >= -2 pp;
A3 >= -0.02; A5 <= 1.0 plus box-free <= 43 plus probe mixed false <= 1.5x (2.116 -> <= 3.17/min); A6 <= 807 ms; A7 <= 86.2 ms;
A8 <= 1.308.

| Config | A1 gain show / carrot / raw (pp) | A2 worst normal val / DEV det (pp) | A3 worst dAP50 | A5 false per recovered | A7 p95 ms |
|---|---|---|---|---|---|
| D0/g1 | 0.0 / 0.0 / 0.0 | 0.0 / 0.0 | banana 0.0 | None | 78.4 |
| D0/g05 | 18.1 / 10.1 / 0.0 | 0.0 / 0.0 | banana 0.0 | 0.617 | 78.4 |
| D0/g025 | 29.0 / 15.8 / 0.0 | 0.0 / 0.0 | banana 0.0 | 0.64 | 78.4 |
| D0/ssf60 | 15.9 / 8.3 / 0.0 | 0.0 / 0.0 | banana 0.0 | 0.228 | 78.4 |
| D0/ssf50 | 21.5 / 10.1 / 0.0 | 0.0 / 0.0 | banana 0.0 | 0.366 | 78.4 |
| D1/g1 | -0.2 / -0.4 / -3.3 | -1.9 / -0.5 | pomegranate -0.1524 | None | 82.8 |
| D1/g05 | 15.8 / 9.2 / -3.3 | -1.8 / -0.5 | pomegranate -0.1524 | 0.59 | 82.8 |
| D1/g025 | 26.5 / 16.7 / -3.3 | -1.8 / -0.5 | pomegranate -0.1524 | 0.636 | 82.8 |
| D1/ssf60 | 13.8 / 7.9 / -3.3 | -1.8 / -0.5 | pomegranate -0.1524 | 0.042 | 82.8 |
| D1/ssf50 | 19.7 / 11.8 / -3.3 | -1.8 / -0.5 | pomegranate -0.1524 | 0.267 | 82.8 |
| D2/g1 | 0.5 / 0.4 / -4.0 | -7.9 / -4.3 | citrus -0.0482 | -2.333 | 79.7 |
| D2/g05 | 16.8 / 11.8 / -4.0 | -6.4 / -4.3 | citrus -0.0482 | 0.354 | 79.7 |
| D2/g025 | 26.1 / 17.1 / -4.0 | -6.4 / -4.3 | citrus -0.0482 | 0.452 | 79.7 |
| D2/ssf60 | 12.1 / 10.1 / -4.0 | -7.9 / -4.3 | citrus -0.0482 | 0.018 | 79.7 |
| D2/ssf50 | 18.8 / 13.2 / -4.0 | -7.9 / -4.3 | citrus -0.0482 | 0.246 | 79.7 |
| Dctl/g1 | -0.1 / 0.4 / -1.1 | -3.5 / -17.5 | mango -0.0424 | None | None |
| Dctl/g05 | 16.8 / 9.6 / -1.1 | -2.7 / -17.5 | mango -0.0424 | 0.204 | None |
| Dctl/g025 | 28.9 / 15.3 / -1.1 | -2.7 / -17.5 | mango -0.0424 | 0.328 | None |
| Dctl/ssf60 | 17.3 / 10.5 / -1.1 | -2.7 / -17.5 | mango -0.0424 | -0.216 | None |
| Dctl/ssf50 | 23.1 / 14.0 / -1.1 | -2.7 / -17.5 | mango -0.0424 | -0.01 | None |

**Small / normal recall by showcase class, raw (no guard), val stills:**

| Arm (raw, no guard) | citrus small R | apple small R | banana small R | tomato small R | carrot small R | citrus normal R | apple normal R | banana normal R | tomato normal R | carrot normal R |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 | 36.6% | 33.7% | 49.8% | 30.5% | 17.5% | 83.2% | 77.0% | 58.6% | 58.6% | 44.0% |
| D1 | 32.4% | 33.7% | 44.4% | 24.3% | 18.4% | 82.5% | 75.2% | 58.1% | 59.3% | 43.0% |
| D2 | 42.2% | 36.0% | 40.7% | 21.5% | 18.9% | 83.2% | 77.0% | 60.9% | 50.0% | 46.9% |
| Dctl | 35.2% | 29.1% | 49.1% | 30.5% | 16.7% | 83.9% | 74.3% | 57.5% | 56.4% | 44.4% |

**DEV det clip (displayed at g1):**

| Arm | DEV det frame recall: citrus / apple / banana / tomato / carrot | frame acc | seg acc | ID switches | missed frac |
|---|---|---|---|---|---|
| D0 (g1) | 0.565 / 0.671 / 0.627 / 0.000 / 0.150 | 0.4365 | 0.5417 | 68 | 0.4644 |
| D1 (g1) | 0.645 / 0.800 / 0.622 / 0.517 / 0.154 | 0.4958 | 0.625 | 45 | 0.4323 |
| D2 (g1) | 0.612 / 0.700 / 0.584 / 0.517 / 0.217 | 0.4714 | 0.625 | 79 | 0.4455 |
| Dctl (g1) | 0.676 / 0.496 / 0.605 / 0.400 / 0.163 | 0.4427 | 0.5833 | 27 | 0.4784 |

- **False boxes per recovered object:** every lower-guard config stays under the 1.0 ceiling on val (0.02-0.64, against Stage C's ~4.5 on
  the probe). A5 fails instead on box-free images and on probe mixed-scene false tracks. Small boxes still create new false tracks in
  scenes without labels.
- **False tracks/min on verified negatives (DEV neg):**
  - G3 0.75.
  - D0/ssf50 and D0/ssf60 0.75. The score floor removes every extra negative track the plain lower guards add (1.25).
  - D1 1.5-2.0 and D2 1.0-1.25. The fine-tunes themselves add negative tracks.
- **CPU (sandbox, same session, 2 threads, detector + guard + tracker, 150 frames):** D0 p50 57.9 / p95 78.4 ms; D1/ssf50 58.0 / 82.8;
  D2/ssf50 57.7 / 79.7 (`out/latency_d.json`). Same architecture, so all are within the 1.10x limit.
- **TTFC p90 (DEV det):** D0 707, D1 847 (fails), D2 747, D-ctl 627 ms.

## 5. Failure analysis

1. **The fine-tunes did not raise small recall where the gate measures it.** DEV val small objects come from the same kitchen-domain
   sources as the training data (slices, table scenes). S-train teaches distant market piles. The fine-tunes moved recall toward S-like
   content (S-dev citrus, DEV det tomato and carrot) and away from val-like content (D2 raw small tomato on val 30.5% -> 21.5%, banana
   49.8% -> 40.7%; normal tomato 58.6% -> 50.0%).
2. **Drift is not only from S.** D-ctl (replay only) already moves AP50 by -0.042 (mango) / -0.026 (lemon_lime) and DEV det apple by
   -17.5 pp, with DEV neg 1.25-1.5 tracks/min. A 20-epoch fine-tune of YOLO11n on this data is noisy at the 0.02 AP / 2 pp resolution
   of the gates. Stage B saw the same thing (B1 apple -9.5 pp). Any future training arm needs multi-seed runs to separate effect from
   noise.
3. **D1 class collapse on pomegranate (-0.152) and citrus (-0.064).** These are inferred from S content (dense red tomatoes and apples,
   and oranges relabelled from teacher "apple"): S-train repeats 20 images 31x, so a few photos dominate colour cues for red/orange round
   produce. D2's collages dilute this (pomegranate -0.037) but do not remove it.
4. **Fragmentation got worse with the fine-tunes:** DEV det IDs/segment 1.21 -> 1.50 (D1) and 1.71 (D2); ID switches 68 -> 45 (D1) and
   79 (D2). More small and pile boxes make association harder, which is Stage C's "boxes jumping between items in a pile" again.
5. **Missed produce stays high everywhere.** About 66% of small showcase GT is missed even raw (D0 34.5% recall), and DEV det missed
   fraction is 0.43-0.48. The side-by-side video shows typical cases: piles of tomatoes, peppers and limes at 360p with no or sparse
   boxes; D2 adds a few boxes in piles, including at least one wrong class (a red pepper/tomato shown as "apple").
6. **The guard is the cheaper lever.** D0/ssf50 recovers +194 val TP for +71 FP (0.37 per recovered object) with no change on DEV neg.
   Its remaining problem is box-free stills (+9) and the synthetic probe (2.4x mixed false tracks). An ssf between 0.50 and 0.60 was not
   in the prereg grid, so it was not tried.

## 6. Recommendation

- **Do not promote anything.** G3 (D0/g1) stays champion and is the frozen DEV pick.
- **Do not continue this training line as is.**
  - 24 verified market images cannot shift a 3.5k-image kitchen-domain model without drift, and the val stills do not measure the
    target domain.
  - The next useful data step is a **DEV set in the target domain**: market piles, labelled independently, from fresh footage. Then
    gates measure what the app sees.
  - Training data should then be scaled to hundreds of market-pile images with independent labels, not teacher-seeded ones.
  - Training arms should run with >= 2 seeds and a replay-only control.
- **Carry D0/ssf50 (and a finer ssf grid, e.g. 0.50-0.60) into a new prereg** to be judged on fresh independent footage with real
  negatives. It is the only change that adds small-object recall (+21.5 pp val) without adding DEV-neg false tracks.
- Pile-level display (one label per same-class cluster) remains the fix for fragmentation, as in Stage C.

## 7. Files

- **Prereg:** `docs/cv/gauntlet/G9_stageD_prereg.md`. **Report:** this file.
  **Frozen pick:** `ml/runs/G9/stageD/frozen_dev_pick.json`.
- **Audit:** `out/train_audit.json`, `out/missing_sample.json`, `out/missing_review.json`.
- **S set:** `s_manifest.csv`, `s_labels.json`, `review_edits.json`, `out/s_stats.json`, `out/leakage_audit.json`.
- **Training:** `kaggle_train/run_template.py`, `kaggle_out/` (metrics, kernel metadata).
- **Eval:** `dev/*.json` (24 configs), `out/summary.json`, `out/latency_d.json`.
- **Scripts:** `scripts/` (audit_train, audit_missing, commons_small, teacher_tiles, review_sheets, build_s, leakage, make_payload,
  cache_probe_any, pipeline.sh, run_evals.sh, stageD_eval, summarize_d, tables_d, latency_d).
  `ml/runs/G9/stageB/scripts/render_side.py` gained optional `LGUARD` / `RGUARD` env vars (default g1, so existing behaviour is
  unchanged).
- **Video (not committed; in `files/g9/stageD/`):** `G9_stageD_side_G3_vs_D2ssf50_DEV.mp4`, 24 s, 1280x360, 10 fps. Left is G3 at 1%;
  right is D2 + ssf50 (rejected). It runs on M-dev clips c237ace91 and c3d1561b2 (independent DEV real footage, not trained on).
