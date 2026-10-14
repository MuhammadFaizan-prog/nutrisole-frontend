# G9 Stage F: market-domain dataset repair + controlled training

2026-10-14 PKT, branch `cv-gauntlet`. The pre-registration `docs/cv/gauntlet/G9_stageF_prereg.md` was committed and synced **before any
Stage F result** (commit 9c46e09). Order followed: P1 prereg -> P2 M-DEV label repair (v2 frozen) + P3 market-train set -> P4 GPU
training -> P5 evaluation -> P6 quality-grading feasibility. **G3 stays champion.** M-TEST was not touched (pHash check only).
The Stage E score-floor grid stayed closed: every arm uses the deployed post-processing (1% source-frame guard, floor 0.35, class-wise
NMS 0.7, IouTracker defaults). All 12 classes kept; persimmon / plum / peach / papaya / feijoa / pitaya / printed fruit appear only as
negatives. No crop counting, yield or farm monitoring.

## Verdict

**No arm passes the frozen gates for both seeds. Frozen pick: F0, unchanged G3, which stays champion.** M-TEST was not touched, the Stage E grid stayed closed, and no new market gate was added.

- **F2 (market data plus negatives)** cuts guarded M-DEV false boxes from 63 to 25/28. Box-free false positives drop from 47 to 13/15, nearly all of them persimmons. In-domain val mAP50 rises from 0.058 to 0.123/0.088. But DEV val mAP50 falls from 0.428 to 0.406/0.409, and A1, A2, A3 and A5 fail. Seed 1's DEV-neg false tracks reach 2.75 per minute.
- **F1 (replay-only control)** is worse than G3 on false positives for both seeds. Part of every fine-tune's damage is drift from the fine-tune itself.
- **Seed variance:** pomegranate AP50 swings by up to 0.22, and DEV-neg tracks run from 0.25 to 2.75 per minute. That noise is larger than the 0.02 A3 limit, so single-seed claims are unreliable.


## 1. Data audit and licensed source manifest (P3)

**Market-train set MT** (`ml/runs/G9/stageF/mt_manifest.csv`, one row per image with Commons page, licence, uploader, author, source
key, split, label method, review note, pHash distance; labels `mt_labels.json`, decisions `scripts/mt_ops.py`, edits `mt_edits.json`):

| Item | Value |
|---|---|
| Candidate pool | 401 Wikimedia Commons images: 257 eligible Stage D candidates (never labelled; S and every source key that also appears in Stage E dropped: 305 excluded) + 144 from 25 new searches (of 42 planned; negatives + showcase piles) |
| Selected after thumbnail triage | 88 (66 intended positive, 22 intended negative), cap **<= 4 images per source key** (3 dropped by the cap, 1 pHash duplicate) |
| Rejected in review | 8 (mixed stalls whose classes cannot be separated by region; banana images whose proposals are finger-level while the class rule is one box per hand) |
| **Used** | **80 images, 70 sources** (Commons uploader / credited author): **MT-train 70** (60 sources), **MT-val 10** (10 sources, in-domain sanity only, never used for selection) |
| Boxes (MT-train) | 3536: tomato 903, citrus 809, carrot 458, mango 306, apple 251, capsicum 208, banana 146, potato 129, lemon_lime 119, cucumber 102, pomegranate 65, guava 40 |
| Box-free / negative images | 23 (20 train): persimmons x4, feijoa, pitaya x2, ARTIFICIAL plastic produce, PRINTED fruit (bags, Millot plate, slot-machine cherries), clothing street, fabric stalls, woven bags, crates, scale, juice bottles, candies x2, cooked food, chili heap (+1 cucumber boxed) |
| Licences (used) | CC BY-SA 4.0 45, CC BY-SA 3.0 13, CC0 8, CC BY-SA 2.0 4, CC BY 4.0 4, CC BY 2.0 3, PD 2, CC BY 2.5 1. Never Pexels / Pixabay / Mixkit. Zenodo / Kaggle / Roboflow not used |
| Markets | 70 distinct photographers; Nigeria (Kaduna, Onitsha, Badagry), Philippines (Iloilo), Hong Kong, India (Bangalore, Pune, Goa, Jaipur, Kolkata, Alagar Koil), Pakistan (kinnow), Bhutan, Rwanda, Ethiopia, Madagascar, Peru (Puno), Côte d'Ivoire, Indonesia, Israel, Serbia, Latvia, Germany, UK, USA, Australia, Japan, Taiwan |
| Source separation | source keys of every Stage E candidate (M-DEV, M-TEST and unused), Stage D S uploaders, holdout / overlap / M-dev / M-train clip uploaders excluded at pool level |
| pHash leakage (`out/leakage_mt.json`) | 64-bit pHash of all 401 pool images vs 6913 references (det_v3 train = G3 train 3562, DEV val 402, DEV det/neg/quality clip frames 651, G7 stage-1 keyframes = holdout + M-dev + M-train 1528, Stage D S 24, **all 746 Stage E market candidates incl. M-DEV and M-TEST**): **0 within distance 10**; 4 within-pool near-duplicates dropped |

**Label method (stated honestly).** No G3 output was used. OWLv2 (`google/owlv2-base-patch16-ensemble`, Apache-2.0, whole image +
3x3 tiles, Kaggle kernel `mfaizannnn/nutrisole-g9f-owl` v1) proposed boxes; the agent then corrected **at region level** on gridded review
sheets: class of every region verified (e.g. mosambi -> citrus, calamansi-like green citrus greyed, oca tubers deleted, courgettes are not
cucumbers, red pointed peppers and scotch bonnets are chilies, printed carrots / apples on cartons deleted), non-target regions deleted,
unverifiable piles greyed (pixels -> 114 in the training image so unboxed produce never becomes background). 7 images were boxed by hand
(mandarins, banana hands, Carrara bunches). **Item-level box tightness inside dense piles was not verified** for the other images: MT
boxes are a noisy, region-verified training signal, not evaluation-grade labels. Labels are **agent-verified, not human-verified**.

**Video.** A fresh Commons video search (4 queries, `video_search_f.json` in the sandbox) found no new licensed market footage: the
suitable hits are the two clips already used as holdout / M-train in earlier stages; the rest are cheese markets, 360-degree VR, archival
films and interviews. **No independent licensed market video exists, so real-market false tracks/min cannot be reported.**

## 2. Annotation review: M-DEV labels v2 (P2)

- **v1 kept byte-identical**: `ml/runs/G9/stageE/m_labels.json` sha256 `f2fc15df...`. **v2**: `ml/runs/G9/stageF/m_labels_v2.json`
  sha256 **`8063dbcc...`** (`out/m_labels_v2.sha256`), edit log `m_edits_v2.json`, decisions with reasons `scripts/v2_ops.py`, builder
  `scripts/build_labels_v2.py`. v2 was **frozen before any F1/F2 output was evaluated on M-DEV**; no model prediction was shown on any
  review sheet (raw images + OWLv2 proposals only).
- **Scope:** 84 images = 67 v1 images + **the 17 previously unlabelled M-DEV pool images**. 23 box-free images unchanged.

| | v1 | v2 |
|---|---|---|
| Boxes | 780 | **1493** (+151 hand-drawn inside former crowd regions, +536 accepted proposal conversions, +26 in new images) |
| Crowd + ignore regions | 113 (72 crowd, 41 ignore) | 158 (89 crowd, 69 ignore) |
| Images with individual boxes | 17 | 27 |
| Boxes per class | citrus 376, tomato 204, lemon_lime 70, pomegranate 67, carrot 28, cucumber 16, apple 12, mango 5, banana 2 | tomato 569, citrus 402, lemon_lime 267, pomegranate 85, apple 46, carrot 45, banana 43, cucumber 31, mango 5, guava 0, potato 0, capsicum 0 |

**What was repaired.**
- **Crowd regions audited one by one (72):** native-pixel crops with OWLv2 region proposals. 15 regions with median item side < 20 px
  were kept as crowd (not separable at the 1280-px rendition). Of the rest, **15 regions were converted to hand-drawn individual boxes**
  where instances are genuinely separable (cucumbers m0024, banana hands m0059 / m0197 / m0428, tomatoes m0140, pomegranates m0184,
  lemons m0350, carrots m0577, netted apples m0649, oranges / banana hand m0653), with residual crowd only where a part stays inseparable.
- **Proposal-based conversions were tested and mostly rejected.** A zoom QA of OWLv2 boxes inside piles (m0684, m0592, m0649,
  m0576, m0653, m0449) showed misaligned, fragmented or merged boxes, so **17 proposal-based conversions were reverted to crowd**; only
  m0262 limes, m0687 and m0707 tomatoes passed and keep the v1 region as a residual crowd behind the boxes (unboxed members stay ignored).
- **Mislabels found:** two v1 "potato" crowds are **kiwifruit** (m0684: shop sign reads "Kiwi"; m0220 same fruit), now ignore regions;
  a carrot bunch inside a cucumber crowd (v1 would have counted a correct carrot detection as a class error) -> ignore region; the
  tomato crowd in m0140 is tomatoes in cups next to limes and chilies -> hand boxes + ignore for pale cups.
- **Duplicates / overlaps:** same-class IoU > 0.7 check on all v2 boxes: 0 left; cross-class IoU > 0.5 conflicts: 0 left (5 apple/citrus
  conflicts created by a proposal conversion in m0592 disappeared when that conversion was reverted).
- **Matching rules unchanged** (Stage E): same-class detection inside a crowd region or any detection inside an ignore region is
  ignored, never a TP; different class inside a crowd region = class-error false box. **No unboxed real produce was turned into
  background**: every reverted or unverifiable area is a crowd or ignore region.
- **Ambiguous objects flagged** (`m_edits_v2.json` "flags"): kiwi vs potato (m0220, m0684), banana hand extents (m0428), oranges seen
  through basket slats (m0650), hand-drawn boxes at review resolution (m0350 lemons, m0577 carrots, m0649 apples).

**Independent second pass** (`out/pass2_sample.json`, `out/pass2_result.json`): different-crop protocol (random quadrant of each image,
raw crop, no v2 overlay, seed 1, 15 of 61 non-negative images). It is the same model, and some images had been seen whole in pass 1, so
these agreements are an **upper bound**, not an independent-annotator figure.

| Agreement | Result |
|---|---|
| Quadrant target presence | 13/15 (disagree: m0163 ambiguous small items in a crate; m0184 small citrus/lemon heap that pass 1 ignores) |
| Target class set, exact | 10/15 (11/15 counting pass-2 classes that fall in a pass-1 ignore region) |
| Granularity | 3/15 quadrants where pass 2 would box items pass 1 left as crowd (m0549 carrots, m0582 oranges, m0629 tomatoes) |
| Box level | m0531: 3/3 pass-2 boxes matched at IoU >= 0.5 (IoU 0.95 / 0.75 / 0.95); m0555 carrots 15 boxed vs 12-15 counted. n is too small for an F1 claim |
| Pass-1 omissions found | 2, **adjudicated before the v2 freeze**: cucumbers in m0629 and small apples in m0582 (crowd regions added) |

**Thin classes on M-DEV v2** (prereg: < 30 individually boxed instances): **mango (5), guava (0), potato (0), capsicum (0)**. They are
reported but never used to rank arms. Apple (46 boxes in 3 images), banana (43 in 5), carrot (45 in 3) and cucumber (31 in 2) clear the
count but are concentrated in very few images, so their recall numbers are image-dominated.

**G3 re-run on v2** (F0): displayed (g1) 14 TP / 63 FP (v1: 0 / 56), box-free FP 47; raw (>= 0.35, no guard) small showcase recall
11.7% (126/1074), raw AP50 (floor 0.01) 0.102.


## Results (P5)

### DEV (val stills 402 + DEV clips; probe SYNTHETIC)

| Arm | val small show displayed (g1) | val small carrot (g1) | val small show RAW (>=0.35) | val TP / FP (g1) | box-free FP | DEV neg tracks/min / episodes/min | TTFC p90 | IDs/seg / ID sw | probe mixed false/min (SYNTH) | val mAP50 (480) |
|---|---|---|---|---|---|---|---|---|---|---|
| F0 | 2.6% (22/857) | 1.3% (3/228) | 34.5% (296/857) | 558 / 232 | 39 | 0.75 / 0.75 | 707 | 1.208 / 68 | 2.116 | 0.4282 |
| F1s0 | 3.1% (27/857) | 2.2% (5/228) | 33.6% (288/857) | 571 / 222 | 25 | 1.75 / 1.25 | 1233 | 1.375 / 45 | 3.808 | 0.4337 |
| F1s1 | 1.5% (13/857) | 0.9% (2/228) | 31.3% (268/857) | 544 / 222 | 31 | 1.25 / 0.75 | 620 | 1.625 / 44 | 5.078 | 0.4386 |
| F2s0 | 3.0% (26/857) | 1.3% (3/228) | 28.0% (240/857) | 540 / 188 | 14 | 0.25 / 0.25 | 667 | 1.208 / 41 | 2.75 | 0.4063 |
| F2s1 | 2.7% (23/857) | 2.6% (6/228) | 30.8% (264/857) | 536 / 199 | 14 | 2.75 / 2.25 | 727 | 1.167 / 66 | 3.597 | 0.4091 |

### Per-class AP50 on det_v3 val at 480 (Ultralytics val; P / R in brackets)

| Class | F0 | F1s0 | F1s1 | F2s0 | F2s1 | max |seed diff| |
|---|---|---|---|---|---|---|
| banana | 0.563 (0.68/0.55) | 0.570 (0.75/0.50) | 0.578 (0.69/0.53) | 0.502 (0.59/0.50) | 0.531 (0.64/0.52) | 0.029 |
| apple | 0.626 (0.68/0.58) | 0.659 (0.82/0.62) | 0.625 (0.74/0.59) | 0.620 (0.73/0.57) | 0.651 (0.78/0.57) | 0.034 |
| mango | 0.646 (0.64/0.64) | 0.711 (0.64/0.55) | 0.693 (0.84/0.64) | 0.618 (0.64/0.64) | 0.607 (0.62/0.55) | 0.018 |
| citrus | 0.745 (0.80/0.69) | 0.743 (0.83/0.66) | 0.744 (0.79/0.68) | 0.701 (0.74/0.64) | 0.714 (0.75/0.67) | 0.013 |
| guava | - | - | - | - | - | - |
| pomegranate | 0.548 (0.56/0.56) | 0.456 (0.54/0.62) | 0.676 (0.60/0.66) | 0.514 (0.50/0.44) | 0.462 (0.45/0.44) | 0.220 |
| lemon_lime | 0.101 (0.49/0.04) | 0.049 (0.07/0.01) | 0.031 (0.08/0.01) | 0.050 (0.12/0.03) | 0.053 (0.15/0.04) | 0.018 |
| tomato | 0.458 (0.57/0.45) | 0.473 (0.59/0.46) | 0.435 (0.44/0.45) | 0.442 (0.59/0.42) | 0.459 (0.53/0.45) | 0.039 |
| potato | 0.009 (0.00/0.00) | 0.052 (0.00/0.00) | 0.021 (1.00/0.00) | 0.045 (1.00/0.00) | 0.079 (1.00/0.00) | 0.034 |
| cucumber | 0.295 (0.66/0.19) | 0.300 (0.62/0.21) | 0.254 (0.55/0.18) | 0.256 (0.51/0.19) | 0.248 (0.53/0.20) | 0.046 |
| carrot | 0.441 (0.75/0.32) | 0.444 (0.68/0.37) | 0.462 (0.62/0.40) | 0.415 (0.63/0.38) | 0.398 (0.60/0.37) | 0.018 |
| capsicum | 0.278 (0.71/0.22) | 0.315 (0.74/0.24) | 0.306 (0.58/0.26) | 0.307 (0.53/0.29) | 0.299 (0.45/0.27) | 0.009 |

### M-DEV v2 (84 real Commons market images, agent-verified)

| Arm | g1 TP / FP | g1 box-free FP | g1 class errors | raw035 small show | raw035 small all | raw035 small carrot | raw035 TP / FP | raw035 box-free FP | raw035 wrong-class | raw001 mAP50 | ignored in crowd (raw035) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F0 | 14 / 63 | 47 | 4 | 11.7% (126/1074) | 8.6% (126/1461) | 4.4% (2/45) | 141 / 309 | 78 | 82 | 0.1024 | 885 |
| F1s0 | 15 / 103 | 85 | 6 | 10.6% (114/1074) | 7.9% (116/1461) | 0.0% (0/45) | 131 / 303 | 139 | 77 | 0.0715 | 628 |
| F1s1 | 15 / 79 | 66 | 4 | 16.2% (174/1074) | 12.3% (180/1461) | 6.7% (3/45) | 196 / 264 | 121 | 45 | 0.1128 | 737 |
| F2s0 | 16 / 25 | 13 | 4 | 12.8% (137/1074) | 10.0% (146/1461) | 0.0% (0/45) | 161 / 165 | 44 | 50 | 0.1273 | 696 |
| F2s1 | 14 / 28 | 15 | 6 | 13.2% (142/1074) | 10.0% (146/1461) | 0.0% (0/45) | 159 / 189 | 55 | 44 | 0.1007 | 874 |

### M-DEV v2 raw AP50 per class (floor 0.01, no guard; thin classes marked *)

| Class | F0 | F1s0 | F1s1 | F2s0 | F2s1 |
|---|---|---|---|---|---|
| banana | 0.0144 | 0.0183 | 0.0147 | 0.0733 | 0.0497 |
| apple | 0.3125 | 0.2359 | 0.3069 | 0.4026 | 0.3092 |
| mango* | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| citrus | 0.0292 | 0.0518 | 0.1746 | 0.222 | 0.232 |
| guava* | None | None | None | None | None |
| pomegranate | 0.0 | 0.0 | 0.0 | 0.0029 | 0.0 |
| lemon_lime | 0.0078 | 0.0054 | 0.0449 | 0.047 | 0.0304 |
| tomato | 0.2215 | 0.1737 | 0.2205 | 0.2263 | 0.2052 |
| potato* | None | None | None | None | None |
| cucumber | 0.2312 | 0.1249 | 0.2242 | 0.1298 | 0.0726 |
| carrot | 0.1048 | 0.0338 | 0.0293 | 0.042 | 0.0069 |
| capsicum* | None | None | None | None | None |

### Gates (fixed g1 post-processing)

| Arm | A1 | A2 | A3 | A4 | A5 | A6 | A7 | A8 | M1 | M2 | M3 | failed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F1s0 | **fail** (0.6/0.9/raw -0.9 pp) | **fail** (min val -2.2, min DEVdet -10.4 pp) | **fail** (worst -0.093) | **fail** (1.75/1.25) | **fail** (f/r -0.769, bf 25, probe x1.8) | **fail** (1233) | pass (80.7 vs 77.4) | **fail** (1.375) | **fail** (0.19 pp) | **fail** (1/40) | **fail** (85 vs 49) | A1, A2, A3, A4, A5, A6, A8, M1, M2, M3 |
| F1s1 | **fail** (-1.1/-0.4/raw -3.3 pp) | **fail** (min val -4.0, min DEVdet -16.3 pp) | **fail** (worst -0.070) | **fail** (1.25/0.75) | **fail** (f/r None, bf 31, probe x2.4) | pass (620) | pass (68.1 vs 77.4) | **fail** (1.625) | **fail** (0.19 pp) | **fail** (1/16) | **fail** (66 vs 49) | A1, A2, A3, A4, A5, A8, M1, M2, M3 |
| F2s0 | **fail** (0.5/0.0/raw -6.5 pp) | **fail** (min val -5.7, min DEVdet -11.9 pp) | **fail** (worst -0.061) | pass (0.25/0.25) | **fail** (f/r None, bf 14, probe x1.3) | pass (667) | pass (81.6 vs 77.4) | pass (1.208) | **fail** (0.1 pp) | pass (2/-38) | pass (13 vs 49) | A1, A2, A3, A5, M1 |
| F2s1 | **fail** (0.1/1.3/raw -3.7 pp) | **fail** (min val -6.3, min DEVdet -16.3 pp) | **fail** (worst -0.087) | **fail** (2.75/2.25) | **fail** (f/r None, bf 14, probe x1.7) | pass (727) | pass (81.3 vs 77.4) | pass (1.167) | **fail** (0.1 pp) | **fail** (0/-35) | pass (15 vs 49) | A1, A2, A3, A4, A5, M1, M2 |

### Feasibility arm R (M-DEV v2, raw, never selectable)

| Model / mode | raw035 small show | raw035 small carrot | raw035 TP / FP | raw035 box-free FP | raw001 mAP50 | p50 / p95 ms (isolated run) | peak RSS MB |
|---|---|---|---|---|---|---|---|
| G3 base480 | 11.7% (126/1074) | 4.4% (2/45) | 141 / 309 | 78 | 0.1024 | 112.7 / 221.1 | 164.3 |
| G3 full640 | 20.8% (223/1074) | 17.8% (8/45) | 238 / 454 | 112 | 0.1565 | 103.5 / 196.2 | 188.8 |
| G3 tile480 | 36.2% (389/1074) | 22.2% (10/45) | 404 / 1050 | 311 | 0.1608 | 347.2 / 1044.4 | 169.8 |
| F2s0 base480 | 12.8% (137/1074) | 0.0% (0/45) | 161 / 165 | 44 | 0.1273 | 67.2 / 159.1 | 163.0 |
| F2s0 full640 | 19.2% (206/1074) | 2.2% (1/45) | 237 / 213 | 60 | 0.1664 | 90.7 / 180.4 | 188.6 |
| F2s0 tile480 | 39.1% (420/1074) | 20.0% (9/45) | 453 / 700 | 218 | 0.1935 | 308.5 / 903.4 | 169.8 |


## 6. P6: quality-grading feasibility on the smallest detections

**Question:** do market-scale detections carry enough pixels for the existing condition (fresh/rotten) and ripeness models, both of which
classify a **224-px crop** of the detected item (`docs/cv/ripeness.md`; condition model `E_224_e15_b64_sgd01`)? Script
`scripts/p6_quality.py`, output `out/p6_quality.json`, examples `out/p6_examples.jpg`.

**(1) Pixel budget.** Side length (sqrt of box area) of the 1493 boxed M-DEV v2 items:

| Where the crop comes from | p10 | p25 | median | p75 | p90 | share < 24 px | share < 64 px |
|---|---|---|---|---|---|---|---|
| detector input, 480 letterbox | 6.1 | 8.1 | **11.7** | 17.1 | 24.7 | 88.9% | 99.3% |
| 1280-px Commons rendition | 20.6 | 26.3 | 35.7 | 50.7 | 81.2 | 19.7% | 83.8% |
| same framing on a 1080p camera frame (1920 px) | 24.2 | 32.5 | 47.0 | 68.3 | 98.9 | 9.6% | 71.6% |
| same framing on a 4K frame (3840 px) | 48.4 | 65.0 | 93.9 | 136.7 | 197.8 | 0% | 24.2% |

Working assumptions (engineering rules of thumb, not measured thresholds): colour-based ripeness needs the item surface at roughly
>= 32 px side to give a stable colour distribution once upsampled to 224; a defect cue (spot, bruise, crack ~2-5% of the item diameter)
needs >= 2-3 px on the defect, i.e. an item side of roughly 64-100+ px. At market framing even a 4K crop meets the defect budget for
fewer than half of the items, and the 480 detector input never does.

**(2) Measured sensitivity of the deployed condition model** on 150 M-DEV items whose native side is >= 64 px, degraded to the size a
small detection would give and resized back:

| Crop side | 12 px | 16 px | 24 px | 32 px | 48 px |
|---|---|---|---|---|---|
| fresh/rotten label flips vs the native crop | 44% | 38% | 35% | 31% | 26% |
| mean max-probability | 0.80 | 0.81 | 0.81 | 0.80 | 0.81 |

The model stays confident (max-prob ~0.8) while its label flips for a quarter to almost half of the items: **confidence does not warn
that the crop is too small.** Even at native size it calls 62 of 150 market items "rotten" (produce on sale, not verified), which points
to a domain gap for market crops, in addition to the resolution problem. `out/p6_examples.jpg` shows the loss: tomato surface blemishes
and banana tips visible natively are gone at 12-16 px and only hinted at 32-48 px.

**Verdict: grading is not feasible on market-scale detections.** Identification can run at market scale; condition, ripeness and
defect grading cannot, and no grade should be issued from such crops.

**Proposed workflow inside the existing proposal (identify -> condition -> grade -> reference price):**
1. **Scan (wide):** the 480 detector identifies produce types in the stall view and shows the reference price per type. No grade is
   shown at this distance; the UI says "move closer to check quality".
2. **Move-closer gate:** a grade is attempted only when the tracked item's crop is >= 96 px side on the **full-resolution camera frame**
   (not the 480 letterbox) and stable for >= 3 frames. Until then the item shows "type + price, quality: get closer".
3. **ROI capture:** the user taps an item or pile (or the tracker picks the largest stable box); the app takes the crop from the
   full-resolution frame (or a high-resolution still), not from the detector input, and runs condition -> ripeness -> grade on it.
4. **Grade + price:** grade bands map to the reference price adjustment already in the proposal; low-confidence or small-crop cases
   return "not graded" rather than a guess.
5. This needs no new detector class and no change to the 12-class detector; it is a UI gate plus a crop-source change.


## Recommendation

Keep G3 and stop detector-training cycles here. Carry F2-style market negatives forward only under a new prereg with at least 3 seeds and a replay control.

**Scope guardrails (user, 14 Oct):**
- Persimmon, plum, peach, papaya and printed fruit are reject or negative examples only, never new classes.
- All 12 supported classes are kept. The 5-class showcase is a milestone.
- No counting, yield or farm monitoring.

### Next: end-to-end mobile CV workflow test
The workflow under test: identify, then condition, then grade, then reference price.

1. The wide view identifies the produce type with G3 (480, 1% guard) and shows the official Lahore or AMIS reference price for that type.
2. Move-closer gate: an item crop of at least 96 px on the full-resolution camera frame, stable for 3 frames, before any grade is shown. Below that, the result is "not graded", never a guessed grade.
3. Run the ripeness, defect and grade model on the ROI taken from the full-resolution frame, not the 480 detector input.
4. Measure:
   - Gate pass rate and time to grade.
   - Grade stability across frames.
   - "Not graded" rate.
   - End-to-end p95 latency on device, or in the emulator with a video camera.
   - Behaviour on unsupported produce: it should be rejected, not graded.
5. Do not let detection optimisation delay the nutrition, glucose, guidance, footwear and assistant scope.

## Frozen pick

```json
{
 "name": "G9 Stage F frozen DEV pick",
 "frozen": "2026-10-14 PKT",
 "prereg": "docs/cv/gauntlet/G9_stageF_prereg.md (commit 9c46e09, written and synced before any Stage F result)",
 "status": "DEV pick only. Nothing promoted. G3 remains champion. M-TEST untouched (pHash audit only). Stage E score-floor grid closed.",
 "pick": "F0 = unchanged G3 (no arm passes A1-A8 + M1-M3 for both seeds)",
 "detector": {
  "weights": "G3 YOLO11n det_yolo11n_640_raw.onnx (best.pt sha256 29cc52123247f62ca93ba41952fa4b221e88fa208f3adf566214870435be1cf4; onnx sha256 c6fcb32a5fb2f51ba34e88ce9106a52d6bbd12ae385ca8361b292d54e3d340c1)",
  "deploy_imgsz": 480,
  "decode": "raw + class-wise NMS 0.7",
  "score_floor": 0.35
 },
 "scene_guard": {
  "minAreaFrac": 0.01,
  "area_reference": "source frame",
  "maxSameClass": 0,
  "small_score_floor": null
 },
 "tracker": {
  "type": "IouTracker",
  "iouMatch": 0.3,
  "minHits": 2,
  "maxMissed": 4
 },
 "labels": {
  "mdev_v1_sha256": "f2fc15dfce355a5dcfc1b23d5fb6140b953f4b90c0589106b0c40a21b2f94cb0",
  "mdev_v2_sha256": "8063dbccf0d45015e6f0a088c2586314e5fd212dd65dd20d1b02e0af980c4077"
 },
 "arms_failed": {
  "F1s0": [
   "A1",
   "A2",
   "A3",
   "A4",
   "A5",
   "A6",
   "A8",
   "M1",
   "M2",
   "M3"
  ],
  "F1s1": [
   "A1",
   "A2",
   "A3",
   "A4",
   "A5",
   "A8",
   "M1",
   "M2",
   "M3"
  ],
  "F2s0": [
   "A1",
   "A2",
   "A3",
   "A5",
   "M1"
  ],
  "F2s1": [
   "A1",
   "A2",
   "A3",
   "A4",
   "A5",
   "M1",
   "M2"
  ]
 },
 "F1_admissible": false,
 "F2_admissible": false,
 "kaggle": {
  "F1": "mfaizannnn/nutrisole-g9f-f1 v1",
  "F2": "mfaizannnn/nutrisole-g9f-f2 v1",
  "OWLv2": "mfaizannnn/nutrisole-g9f-owl v1"
 },
 "next": "Not a further detector stage by default: an end-to-end mobile workflow test (see G9_stageF.md section 8). F2-style market negatives are the one training signal worth carrying forward, only under a new prereg with more seeds."
}
```
