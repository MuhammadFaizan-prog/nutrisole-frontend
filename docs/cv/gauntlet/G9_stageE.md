# G9 Stage E: independent market-pile DEV set (M-DEV) + G3 selective score-floor grid

2026-10-14 PKT, branch `cv-gauntlet`. The pre-registration `docs/cv/gauntlet/G9_stageE_prereg.md` was committed and synced **before any
Stage E result** (commit bfa75b7). No training was run. M-TEST was not scored (pHash leakage check only). Nothing is promoted.
**G3 stays champion.**

## Verdict

- **No grid point is admissible. Frozen pick = g1 (unchanged G3)**, in `ml/runs/G9/stageE/frozen_pick.json`. Under the prereg close-out
  rule (section 6), **the score-floor line is closed**.
- As stated up front in the prereg, Stage D's results reproduce exactly: **ssf50 fails A5** (box-free 48 > 43; probe SYNTHETIC 5.08/min
  = 2.4x > 1.5x), and **ssf60 fails A1 + A5** (small carrot +8.3 pp; probe 4.02/min = 1.9x).
- **The intermediate values also fail.**
  - ssf525, ssf55 and ssf575 all fail **A1**: small carrots 25 / 23 / 23 of 228, but 26 are needed for +10 pp.
  - All three fail the **A5 probe limit**: 4.65 / 4.23 / 4.23 per min, against a limit of 3.17.
  - ssf525 and ssf55 also fail the A5 **box-free** limit (46 / 44 > 43).
  - So there is no window between 0.50 and 0.60 where A1-carrot and A5 both hold.
- **On the new independent market set M-DEV (67 real Commons images, agent-verified), G3 is close to blind on small market produce at
  480.**
  - At g1 it finds **0 of 780 individually boxed targets**, with 56 false boxes.
  - Every ssf point adds the same **4 true boxes** (3 apples, 1 tomato) for **+15 to +35 false boxes**. So all five fail M1 (+0.65 pp),
    M2 (3.75-8.75 false per recovered) and M3 (box-free +6 to +17).
  - **90% of the boxed M-DEV targets are smaller than 0.25% of the frame.** Both g1 and every ssf point drop those boxes by construction,
    so no point on this grid can reach them.
- **Next step** (prereg section 6 / brief item 7): annotation repair plus a larger, properly labelled market training set, trained with
  several seeds and a replay-only control. It is judged on M-DEV and then once on the untouched M-TEST under its own prereg.

## 1. Dataset manifest (market set M)

Full manifest: `ml/runs/G9/stageE/m_manifest.csv`, one row per image (178 rows). Each row has the Commons page, licence, uploader,
author, source key, split, label status, box/crowd counts, review note and pHash distance.

| Part | Images | Content | Label status |
|---|---|---|---|
| **M-DEV evaluated** | **67** (52 sources) | 43 selected as positive: market/mandi stalls, carts, greengrocers, piles. 24 selected as negative: clothing, bags, shoes, fabric with printed fruit, printed posters/shop fronts/vending machines, chilies, tomato **slices**, persimmons, plums, peaches, dragon fruit, flowers. After review, **23 are box-free**, 17 have individual boxes and 27 are crowd/ignore-only | **agent-verified, not human-verified**: OWLv2 proposals + agent box/region edits |
| M-DEV pool (unscored) | 17 | selected positives that were not labelled (budget) | OWLv2 proposals only, not evaluated |
| **M-TEST (reserved)** | **94** (65 sources; 67 positive, 27 negative by thumbnail triage) | same content mix | **unlabelled, never scored or label-reviewed**; only licence-recorded and pHash-audited |

- **Size:** M-DEV meets the >= 60 target (67) and M-TEST meets >= 30 (94).
- **Showcase coverage in M-DEV:**
  - citrus: 3 images with boxes (387 boxes) + crowd regions in 5 more
  - apple: 1 boxed (12) + 4 crowd
  - banana: 2 boxed (1 each) + 8 crowd
  - tomato: 3 boxed (204) + 9 crowd
  - carrot: 2 boxed (28) + 8 crowd
  - other classes: pomegranate 67, lemon_lime 70, cucumber 16, mango 5 boxes, plus crowd regions for potato, capsicum, lemon_lime and
    cucumber
  - Apple, banana and carrot have few individual boxes, so their M-DEV recall numbers are thin.
- **Sources and licences:** Wikimedia Commons only, per-file licence. Counts over the 161 M-DEV evaluated + M-TEST rows: CC BY-SA 4.0
  83, CC BY-SA 3.0 22, CC0 17, CC BY 2.0 14, CC BY-SA 2.0 10, CC BY 4.0 9, PD 6. Zenodo, Kaggle and Roboflow were not needed.
- **Split rule (prereg section 3):** source key = uploader, or the credited author for bot uploads. `sha1(key) % 3 == 0` -> M-TEST.
  M-DEV and M-TEST share **0 sources**.
- **Exclusions applied at search time:**
  - holdout uploaders, overlap-excluded uploaders and M-dev uploaders
  - Stage D S uploaders and **all 586 Stage D candidate titles**
  - Pexels / Pixabay / Mixkit (never queried)
- **Leakage audit** (`out/leakage_audit_all.json`): 64-bit pHash of all 746 downloaded M candidates against 6729 reference hashes:
  - 1528 G7 stage-1 clip keyframes (holdout + M-dev + M-train)
  - 402 DEV val stills
  - 651 DEV det/neg/quality clip frames
  - 3562 det_v3 train images (G3 training)
  - 586 Stage D candidates / S

  Result: **0 within distance 10. The minimum distance among the 178 used images is 12.** There are no M-DEV vs M-TEST near-duplicates
  among used images. The 2 cross-split and 17 same-split near-duplicates found were all in unused candidates.
- **Labels:** `ml/runs/G9/stageE/m_labels.json`; agent edit log with a per-image note: `m_edits.json`. OWLv2 proposals (3.7 MB) stay in
  the sandbox (`/workspace/work/cv/g9e/owl_props.json`) and are not committed. Proposer kernel: `mfaizannnn/nutrisole-g9e-owl` v1
  (free T4, `google/owlv2-base-patch16-ensemble`, Apache-2.0, whole image + 3x3 tiles).
- **Video:** no independent licensed market video. The two suitable Commons market videos found are already project material:
  - "Vegetable Market (Amman)" is a **holdout** clip.
  - "Fruit Stand - Kitasenju" is an **M-train** clip.

  Both were deleted unused, as soon as the `mining_split.csv` check flagged them. **Real-market false tracks/min therefore cannot be
  reported in Stage E.**

## 2. Annotation review

**Definition** (prereg section 2): whole physical produce of the 12 classes; one box per item, one per banana hand/bunch. Slices, cut
pieces, printed images, props and non-class produce are not targets. lemon_lime is lemons and limes only and is never put on large green
produce. Capsicum is a bell pepper; chilies and pointed peppers are negatives. Piles that cannot be boxed item by item are **crowd
regions** of their class: a same-class detection inside is ignored, and another class inside counts as a false box. Regions whose class
cannot be verified are **ignore** regions (any detection ignored, no GT).

**Procedure:**
- **No G3 proposal was used.** OWLv2 proposals at score >= 0.25 went through a mechanical cleanup (drop pile "container" boxes, NMS 0.4,
  drop fragments that sit inside a larger same-class box).
- Every image then got a 1400-px gridded review: keep, delete or relabel by region; add boxes; crowd and ignore regions. Ambiguous scenes
  were zoom-checked. Label renders were re-checked on 5 images.
- In total: **780 boxes, 72 crowd regions and 41 ignore regions**. Box-level checking inside dense piles was done at review resolution,
  not box by box, and 27 of the 44 non-negative images are crowd/ignore-only.

**Second agent pass** (prereg section 4). Sample: 15 of 67 images, `random.seed(0)` (`out/pass2_sample.json`). The second pass worked
from raw images with no overlays and did not look up the pass-1 labels. It is the **same model in the same session**, so it is not a
truly independent annotator, and these agreements are an upper bound.

| Agreement | Result |
|---|---|
| Image-level negative / non-negative | 14/15 (m0596 orange-juice vending machine: pass 2 says box-free; pass 1 has an ignore region over oranges seen in the hopper window) |
| Target class set per image | 13/15 exact. m0374: pass 2 calls the front fruit pomegranates; pass 1 ignored them as mango/pomegranate unclear. m0684: pass 2 adds citrus at the left edge **and finds a pass-1 error**, see below |
| Box-level, boxes drawn from scratch on zoomed crops (m0446 tomatoes, m0492 cucumbers; 53 pass-1 vs 46 pass-2 boxes; `out/pass2_boxes.json`) | **F1 0.79 at IoU 0.5** (0.78 / 0.80); **0.83 at IoU 0.3** |
| Class agreement on matched boxes | 100% (39/39) |

**Error types found:**
- **lemon_lime on large green produce (pass-1 error, fixed after adjudication).** m0684 had a lemon_lime crowd region over **avocados**.
  It was removed and the left edge became an ignore region. This is the same failure the brief flagged for D2.
- **Proposer class errors caught in pass 1:**
  - persimmons called citrus/apple (m0002 and m0148 turned into negatives)
  - oranges called lemon (m0650; the title confirms oranges)
  - limes called apple (m0140)
  - green or unripe tomatoes called apple (m0484)
  - ripe yellow cucumbers called banana/mango (m0492)
  - papayas called mango (m0492)
  - pomegranates called apple (m0184)
  - printed apples on cartons boxed as apples (m0653)
  - printed citrus on a banner (m0605)
- **Box errors (pass 2 vs pass 1):** 2 overlapping cucumbers merged into one box; 1 cucumber missed; about 9 extra tomato boxes in a
  dense heap (duplicates or heavily occluded items).
- **lemon_lime vs large green produce check:**
  - G3 emits lemon_lime only twice on M-DEV, both on the large green citrus-like fruit in m0492. Labels leave that fruit unlabelled
    (ignore region, since green orange vs lime is not verifiable), so those two do not count as errors.
  - On real limes (m0140, 62 boxes) G3 outputs 2 "apple" and no lemon_lime.

## 3. Full comparison table

DEV val stills (402) and DEV clips are **real**. The probe is **SYNTHETIC** and is kept in its own columns. M-DEV is **real**,
agent-verified. "Small" = GT < 1% of the source frame. A5 false/recovered and A7 are in the A-gate table below.

| Config | DEV val small showcase R | DEV val small carrot R | DEV val TP / FP | DEV box-free FP | DEV neg tracks/min / episodes/min | TTFC p90 ms | IDs/seg / ID sw | probe small show R (SYNTH) | probe mixed false/min (SYNTH) | M-DEV TP / FP | M-DEV small showcase | M-DEV small carrot | M-DEV box-free FP | M-DEV class-error FP | M-DEV dets in crowd/ignore | M-DEV mAP50 (displayed) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **g1 (G3)** | 2.6% (22/857) | 1.3% (3/228) | 558 / 232 | 39 | 0.75 / 0.75 | 707 | 1.208 / 68 | 0.3% | 2.116 | 0 / 56 | 0/620 | 0/28 | 47 | 4 | 132 | 0.000 |
| ssf50 | 24.0% (206/857) | 11.4% (26/228) | 752 / 303 | 48 | 0.75 / 0.75 | 707 | 1.208 / 68 | 3.0% | 5.078 | 4 / 91 | 4/620 | 0/28 | 64 | 19 | 386 | 0.003 |
| ssf525 | 23.2% (199/857) | 11.0% (25/228) | 745 / 288 | 46 | 0.75 / 0.75 | 707 | 1.208 / 68 | 2.8% | 4.654 | 4 / 86 | 4/620 | 0/28 | 62 | 17 | 364 | 0.003 |
| ssf55 | 21.2% (182/857) | 10.1% (23/228) | 728 / 279 | 44 | 0.75 / 0.75 | 707 | 1.208 / 68 | 2.7% | 4.231 | 4 / 81 | 4/620 | 0/28 | 59 | 15 | 341 | 0.003 |
| ssf575 | 19.6% (168/857) | 10.1% (23/228) | 713 / 270 | 43 | 0.75 / 0.75 | 707 | 1.208 / 68 | 2.4% | 4.231 | 4 / 75 | 4/620 | 0/28 | 56 | 13 | 322 | 0.003 |
| ssf60 | 18.4% (158/857) | 9.7% (22/228) | 703 / 265 | 43 | 0.75 / 0.75 | 707 | 1.208 / 68 | 2.4% | 4.020 | 4 / 71 | 4/620 | 0/28 | 53 | 13 | 298 | 0.003 |
| none (diagnostic) | 34.5% (296/857) | 17.5% (40/228) | 844 / 433 | 66 | 1.25 / 1.0 | 707 | 1.208 / 68 | 5.0% | 8.674 | 57 / 191 | 57/620 | 2/28 | 78 | 78 | 738 | 0.030 |

- **M-DEV raw reference** (floor 0.01, no guard; diagnostic, not displayable): small showcase recall 24.4% (151/620), small carrot
  46.4% (13/28), mAP50 0.077. Best classes: tomato 0.23, cucumber 0.23, carrot 0.18.
- **M-DEV boxed GT by size:** <0.25%: 702; 0.25-0.5%: 62; 0.5-1%: 14; >=1%: 2. In the 0.25-1% band, the only band the grid changes,
  every ssf point finds 4 of 76 (g1 0, raw 15).
- **CPU latency:** same detector as Stage D D0 (p50 57.9 / p95 78.4 ms, sandbox ONNX Runtime 2 threads). Guard + tracker
  post-processing p95 is 0.185 ms (g1) and 0.194-0.199 ms (ssf), so every config is about 78.4 ms against the A7 limit of 86.2.
- **Fragmentation:** DEV det IDs/segment and ID switches are identical for all configs. The guard does not touch boxes >= 1%, and the
  DEV det clip's displayed tracks come from those. There is no video fragmentation number for M (no independent video).

**A-gates (limits unchanged from Stage D) and market checks:**

| Config | A1 small show / carrot gain (pp), limit +10 / +10 | A2 | A3 | A4 | A5 false/recovered (<= 1.0) / box-free (<= 43) / probe x (<= 1.5) | A6 | A7 p95 ms | A8 | M1 gain pp (>= +5) | M2 false/recovered (<= 1.0) | M3 box-free (<= 49) | Failed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ssf50 | 21.5 / **10.1** | pass (0) | pass (weights unchanged) | 0.75/0.75 | 0.37 / **48** / **2.40** | 707 | 78.4 | 1.208 | **0.65** | **8.75** | **64** | A5, M1, M2, M3 |
| ssf525 | 20.6 / **9.6** | pass | pass | pass | 0.30 / **46** / **2.20** | pass | 78.4 | pass | **0.65** | **7.50** | **62** | A1, A5, M1-M3 |
| ssf55 | 18.7 / **8.8** | pass | pass | pass | 0.28 / **44** / **2.00** | pass | 78.4 | pass | **0.65** | **6.25** | **59** | A1, A5, M1-M3 |
| ssf575 | 17.0 / **8.8** | pass | pass | pass | 0.25 / 43 / **2.00** | pass | 78.4 | pass | **0.65** | **4.75** | **56** | A1, A5, M1-M3 |
| ssf60 | 15.9 / **8.3** | pass | pass | pass | 0.23 / 43 / **1.90** | pass | 78.4 | pass | **0.65** | **3.75** | **53** | A1, A5, M1-M3 |

Per-config JSON: `ml/runs/G9/stageE/dev/G3_{g1,ssf50,ssf525,ssf55,ssf575,ssf60,none}.json`; M-DEV: `out/mdev_eval.json`; criteria:
`out/summary.json`.

## 4. Failure analysis

1. **The two binding DEV gates pull in opposite directions across the whole grid.**
   - A1 needs >= 26 small val carrots displayed. Only ssf50 gets there (26), and ssf525 already loses one (25). Small carrots score low,
     so any floor above 0.50 removes them first.
   - A5's probe (SYNTHETIC) mixed-scene false tracks never drop below 4.02/min, against a limit of 3.17.
   - The score floor trims val false boxes efficiently (false per recovered 0.23-0.37), but the synthetic mixed scenes produce
     confident small false tracks that survive even 0.60.
2. **On real market scenes the issue is recall, not the floor.**
   - G3 at 480 detects almost none of the individually boxed market produce. Even the raw diagnostic (floor 0.01, no guard) reaches only
     24% small showcase recall, and displayed configs reach <= 0.7%.
   - Most market targets are below 0.25% of the frame (median side ~14 px at 480), the region that g1 and every ssf point drop.
   - Where G3 does fire on piles, it mostly lands inside crowd regions: 132 (g1) to 386 (ssf50) ignored detections. That is consistent
     with pile-level detections, but crowd regions cannot credit them.
3. **False boxes on real negatives are specific, not general.**
   - All box-free false boxes on M-DEV come from the three **persimmon** images: m0326 34-40, m0002 7-18, m0331 6 (G3 calls them tomato,
     citrus or apple).
   - Printed fruit (posters, shop fronts, vending machines, fabric), clothing, bags, shoes, tomato slices, chilies, plums, peaches and
     flowers gave **0** displayed false boxes at g1.
   - The ssf points add class errors inside labelled scenes (tomato<-citrus 6-8, apple<-citrus 4, apple<-pomegranate 2,
     banana<-cucumber 1-3). These are wrong labels on real produce, which a floor does not fix.
4. **Annotation is the limiting factor on the market side.**
   - 27 of 44 non-negative M-DEV images are crowd/ignore-only, and pass-2 box F1 is 0.79.
   - M-DEV small-recall numbers are therefore dominated by a few boxed images: citrus in m0605 and m0709, tomato in m0446 and m0484,
     limes in m0140, pomegranates in m0184.
   - For apple, banana and carrot (12 / 2 / 28 boxes), M-DEV recall is too thin to rank configs. It is reported, not over-read.
5. **Single-image noise.** The 4 extra true boxes every ssf point adds on M-DEV are the same 3 apples (m0561) and 1 tomato. M1-M3 would
   fail even if label noise doubled them.

## 5. Recommendation

- **Keep G3 (g1) unchanged and close the score-floor line.** No value between 0.50 and 0.60 passes DEV. On real market scenes every value
  adds 4-9 false boxes per recovered object.
- **Next (brief item 7):**
  - (a) **Annotation repair:** turn M-DEV crowd regions into item-level boxes where items are separable, and get an independent (human
    or second-annotator) verification of M-DEV.
  - (b) **A larger, properly labelled market training set,** source-separated from M-DEV/M-TEST, with item-level boxes, including
    persimmon/plum/peach hard negatives and printed-fruit negatives.
  - (c) **Training arms with >= 2 seeds plus a replay-only control,** at a resolution that keeps 0.1-0.25% items above about 14 px
    (480 cannot). The CPU budget (A7) has to be revisited for that.
  - Judge on M-DEV, then once on the untouched M-TEST under its own prereg. **M-DEV is never used for training after being used for
    tuning.**
- **No licensed independent market video exists in the project yet.** Real-market false tracks/min needs new, independently sourced and
  licensed footage.

## 6. Files

- **Prereg:** `docs/cv/gauntlet/G9_stageE_prereg.md`. **Report:** this file. **Frozen pick:** `ml/runs/G9/stageE/frozen_pick.json`.
- **Market set:** `ml/runs/G9/stageE/m_manifest.csv`, `m_labels.json`, `m_edits.json`; `out/leakage_audit_all.json`,
  `out/pass2_sample.json`, `out/pass2_boxes.json`.
- **Eval:** `dev/G3_*.json` (DEV continuity), `out/mdev_eval.json`, `out/summary.json`.
- **Scripts** (`ml/runs/G9/stageE/scripts/`): `commons_market.py` (search/download/split), `triage_sheets.py`,
  `owl_kernel_template.py` (Kaggle OWLv2 proposer), `review_sheet.py`, `build_labels.py` (cleanup + edit ops), `leakage_e.py`,
  `cache_m.py`, `eval_m.py`, `stageE_eval.py` + `run_dev.sh` (DEV grid, a copy of stageD_eval with ssf525/55/575),
  `video_m.py` (prepared, not run: no independent video), `summarize_e.py`.
- `ml/runs/G7/night/night_gate.json` was left untouched; it belongs to another project.
