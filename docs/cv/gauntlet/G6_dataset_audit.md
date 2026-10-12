# G6.1 dataset audit (2026-10-13, sandbox CPU; agent-run, no human review)

Scope: every detector split the G3 control and later candidates touch: det-v3 `train` (3 562), `val` (402), locked `test` (557), `test_rf` (149), `test_oiv7` (123), `neg_test` (80), G4 `test_oiv7c` (181), OIV7c `train`/`val` (967 / 71, used by det-v4 and G6 rpx), G5 video hard negatives `g5hn_train` (212 = 53 crops x 4). 6 304 images hashed, 0 unreadable.
Scripts: `g6_audit_hash.py` (md5 + 64-bit pHash + dHash + label stats), `g6_audit_report.py`, `g6_owl_queue.py`, `g6_lemon_cm.py` (copies under `ml/runs/G6/scripts/`). Outputs: `ml/runs/G6/audit/`.
**Locked split files were not modified** (byte-identical; hashes re-checked at G6 close, see G6.md). Every correction below is a new TRAIN manifest or a labelled VIEW.

## 1. Duplicates and leakage (`dup_pairs.csv`, `phash_sensitivity.json`)
| check | rule | result |
|---|---|---|
| exact duplicates (md5) | identical bytes | only inside `g5hn_train` (53 groups = the intended x4 oversampling); **none across splits** |
| near duplicates eval vs train/val | pHash Hamming <= 6 AND dHash <= 8 | **1 pair: test `000000069340.jpg` ~ val `000000369594.jpg`** (val only; no train leak) |
| sensitivity | pHash <= 4 / 8 / 10 / 12 alone | test 1 / 1 / 2 / 13 images; test_oiv7 0/0/0/1; test_rf 0/0/0/1 (Hamming 12 on 64 bits is mostly unrelated images) |
| OIV7c train vs every locked split | same rule | none |
| Roboflow source groups | `test_rf` file names `<date>_<uuid>_<n>_png.rf.*` | **149 test_rf images come from only 22 capture UUIDs (70 date+uuid groups)**; train/val contain no Roboflow images, so no cross-split leak, but test_rf's effective sample size is ~22 recordings, not 149 |

Corrected TRAIN manifest: `g6data/det_g6/train_corrected.txt` = G3 train unchanged (3 562), removal list `g6_removed_basenames.txt` is empty. The G6 fine-tunes therefore replay exactly G3's train mix.

## 2. Class distribution (instances; `class_dist.csv`)
| class | train | val | test | test_rf | test_oiv7 | test_oiv7c | OIV7c train |
|---|---|---|---|---|---|---|---|
| banana | 3825 | 469 | 5048 | 75 | 0 | 0 | 21 |
| apple | 2849 | 199 | 2122 | 25 | 1 | 6 | 86 |
| mango | 276 | 11 | 0 | 0 | 22 | 0 | 0 |
| citrus | 1543 | 208 | 1833 | 34 | 1 | 609 | 3918 |
| **guava** | **0** | **0** | **0** | **0** | **0** | **0** | 0 |
| pomegranate | 540 | 16 | 0 | 0 | 48 | 0 | 0 |
| lemon_lime | 452 | 77 | 290 | 4 | 0 | 299 | 1514 |
| tomato | 3192 | 317 | 659 | 122 | 41 | **4** | 39 |
| potato | 696 | 20 | 366 | 0 | 0 | 0 | 2 |
| cucumber | 1074 | 154 | 111 | 73 | 173 | 0 | 0 |
| carrot | 3290 | 435 | 1558 | 84 | 3 | 4 | 3 |
| capsicum | 1177 | 116 | 280 | **110 (all sliced strips)** | 120 | 0 | 0 |
Background-only images: train 1 005, val 90, test 50, **test_rf 60 of 149**, neg_test 80.

Consequences:
- **test_oiv7c has 4 tomato, 4 carrot and 6 apple instances.** The G5 report's "fthnc tomato collapses 0.74 -> 0.17 on test_oiv7c" rests on **4 boxes**; it is not evidence of a tomato regression by itself (test_rf tomato, n=122, is). G6 reports per-class AP with n and does not use oiv7c tomato/carrot/apple in the strict rule (correction to G5 interpretation; G5 decision unchanged because test_rf tomato/banana also failed).
- **Guava has zero boxes anywhere in det-v3**, so no G3/G6 locked number can say anything about guava detection. Only the external `test_guava` (n=121, Roboflow guava v5 test, CC BY 4.0) exists.
- Mango has no locked test boxes except 22 in test_oiv7; pomegranate only 48 in test_oiv7.

## 3. Tiny and degenerate boxes (`tiny_boxes.csv`)
0 degenerate boxes (zero/negative size or out of range). Boxes with min side < 6 px after letterboxing to 480: **test 1 666 of 12 267 (13.6%; banana 1 017, apple 210, citrus 189, carrot 151)**, train 576 of 18 914 (3.0%), val 32, OIV7c train 107, test_rf 1, test_oiv7c 2. LVIS-derived `test` is dominated by tiny piled produce, which explains much of its low mAP (G3 0.224) and makes it a poor proxy for a phone held near produce. Proposed VIEW for G7 (not used for any decision here): `test` with < 6 px boxes as ignore regions.
Duplicate label rows: 8 rows in 8 files (train 1, test_oiv7c 3, OIV7c train 3, val 1); Ultralytics drops them at load, so no metric changes.

## 4. test_rf missing-annotation check (`test_rf_missing_label_suspects.json`, `test_rf_empty_suspects.jpg`)
60 test_rf images have no boxes. OWLv2 (G4 teacher) proposes a box >= 0.3 on 18 of them; agent visual check of 8: the proposals are mostly *wrong* (avocado, pineapple, red chilli, salad, spinach), with one plausible miss (a peeled banana; peeled/cut produce is outside the whole-produce rubric). On labelled test_rf images, 95 OWLv2 boxes >= 0.4 overlap no GT (37 images) - candidates for missing labels, not confirmed. Conclusion: test_rf is a food-photo set (plates, cut produce) whose empties are mostly genuine hard negatives; no correction is applied without human review.

## 5. Capsicum strips
All 110 test_rf capsicum boxes are sliced red-pepper strips (G4 inspection). Kept unchanged in the locked test_rf; `test_rf_nostrips` remains a separate VIEW (G5). Whole-capsicum grading is a documented task boundary in `teacher_review.md` / the labelling handbook; the detector benchmark is not silently changed.

## 6. Lemon/lime vs citrus (`g3_confusion_lemon_citrus.json`)
G3 control ONNX @480, conf 0.25, class-wise NMS 0.7, sandbox CPU; each GT box is assigned the class of its best-IoU prediction (IoU >= 0.5) or "missed" (`g6_lemon_cm2.py`):

| split | GT class (n) | -> lemon_lime | -> citrus | -> other class | missed |
|---|---|---|---|---|---|
| test_oiv7c (181 imgs) | lemon_lime (299) | **60 (20%)** | **114 (38%)** | 37 | 88 (29%) |
| test_oiv7c | citrus (609) | 3 | 380 (62%) | 43 | 183 (30%) |
| test (557 imgs) | lemon_lime (290) | 8 | 19 | 6 | **257 (89%)** |
| test | citrus (1 833) | 5 | 715 (39%) | 43 | 1 070 (58%) |

Interpretation: on close-up Open Images photos the lemon/lime failure is mainly **confusion with citrus** (38% of lemons called citrus), not misses; on LVIS `test` it is mainly **misses of tiny lemons** (89%). Train has 452 lemon_lime vs 1 543 citrus boxes (3.4:1); OIV7c train would add 1 514 / 3 918.
Decision (G6): keep `lemon_lime` and `citrus` as separate detector classes (taxonomy and locked benchmark unchanged; the app's Urdu labels leemu vs kinnow/malta differ in price and use). For grading, a citrus-family fallback (show "citrus (lemon/orange?)" when the two scores are within a margin) is proposed for G7 and needs a UX decision; not implemented.

## 7. OWLv2 review queue (`owl_review_queue_prioritised.csv`, `owl_review_queue_summary.json`)
1 172 proposals on 122 LVIS images dropped by G3 hygiene, **all still `pending_review`; nothing enters training** (no human reviewer in the sandbox). Ordered by priority = uncertainty (teacher score near 0.5) + 0.6 x G3-conflict + 0.3 x group box + 0.2 x tiny box + 0.5 x class rarity in G3 train + 0.15 x citrus/lemon. G3 control (480, conf 0.25) agrees (same class, IoU >= 0.5) with 149 proposals, conflicts (other class) on 60, misses 964. Flags: tiny box 251, citrus/lemon 238, group box 10. Top of the queue: lemon_lime/pomegranate/capsicum/potato proposals where G3 says apple.

## 8. Ripeness "Overripe" folder
The CC0 ripeness set spells the folder `Overipe`; G4's run therefore trained with 0 overripe images (invalid). The G5 kernel aliases `/overipe` -> overripe and asserts >= 50 train images per class before training. Verification is the kernel's own count in its output JSON (see G6.md, ripeness section).

## 9. Missing real-world examples (what no current split covers)
1. Any Lahore / Pakistani mandi or cart footage (none exists in any split).
2. Guava detection boxes in the locked splits (0); mango/pomegranate test boxes outside OIV7.
3. Whole capsicum in test_rf (only strips); lemon/lime close-ups at phone distance (OIV7 lemons are mostly small).
4. Low light: share of images with mean luma < 60 is 2-4% in every split, 0% in test_rf; sodium/tube-light market scenes are absent from detector data (only the classifier has synthetic/held-out lighting families).
5. Hands holding produce, partial occlusion in piles, motion blur from a handheld phone.
6. Rotten/damaged produce in situ (quality data are single-fruit crops).
