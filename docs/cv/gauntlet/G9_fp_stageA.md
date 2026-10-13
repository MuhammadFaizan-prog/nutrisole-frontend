# G9 Stage A: false-positive elimination with post-processing only (no training)

Date: Wed 2026-10-14 (PKT). Briefs: `files/nutrisole-g8-fp-elimination-gpt.md` (Stage A) and `files/nutrisole-g9-existing-models-gpt.md` (Phase 4 arm A), plus the user's additions of 02:20 PKT (verified-negative windows, TTFC audit, raw vs tracked). Pre-registration: `docs/cv/gauntlet/G9_fp_prereg.md` (main part committed a3bbcde before any Stage A number; Addendum A committed 05d7eb9 after the DEV freeze and before any holdout replay). Data and scripts: `ml/runs/G9/fp/`.
Evidence labels: **sandbox CPU** = DEV replays (2-core shared Linux, onnxruntime); **Kaggle CPU** = holdout replay (kernel `mfaizannnn/nutrisole-g9-fp-holdout` v1, 34 clips, 1 thread, ~10 fps fixed-frame, wall 2 188 s). Nothing here was measured on a phone, and nothing was trained.

## Bottom line
- **Promotion: none. G3 stays champion.** No arm meets the holdout confirmation rule or G8 rule 4.
- **Tracker gate + thresholds (A2) cut holdout false alarms by 69% (2.86 to 0.88 per min, whole clip, provisional), and by 78% in the unbiased verified-negative windows (2.86 to 0.64 per min).** The uploader bootstrap CI excludes 0 ([-2.52, -1.12]). But A2 also **loses 2 of 22 verified clip-class pairs (11 to 9: lemon_lime #1 and carrot #16, carrot being a showcase class).** The prereg allowed at most 1 lost pair and no lost showcase pair, so **the goal is not confirmed on the holdout.**
- **DEV goal met but thin.** FA/min on the DEV neg clip fell 0.75 to 0.25 (-67%, which is 3 tracks down to 1 in 4 min) for A1 and A2. Val-still recall stays within 5 pp per class by construction. However, **frame recall on the synthetic DEV det clip drops by more than 5 pp for banana** (0.627 to 0.538 for A1, 0.521 for A2).
- **Which component removes the false alarms (holdout negatives, whole clip):** raw G3 boxes at 0.35 = 45.1/min. The **area guard** (already in G3) leaves 18.5/min (-59%). **A1 per-class thresholds** leave 14.2 raw boxes/min (-24%) and cut tracks 104 to 74 (-29%). **A2 minHits 3** (tracker display gate) leaves raw boxes unchanged but cuts displayed tracks 74 to 32 (-57%). Most holdout false tracks are 1-2-frame flickers, which the display gate removes.

## 1. Arms and frozen choices (DEV only)
| arm | detector floor | tracker | frozen in |
|---|---|---|---|
| A0 | 0.35 all classes (G3 as deployed) | IouTracker default (minHits 2) | - |
| A1 | per-class t_c (below) | minHits 2 | `thresholds_A1.json` |
| A2 | per-class t_c | **minHits 3, birth margin 0** (A2 grid, `policy_A2.json`) | `policy_A2.json` |

**A1 thresholds** (rule: largest t in 0.35..0.90 with val recall drop <= 5 pp, applied to all 12 classes, n < 10 keeps 0.35). Val = G3 val stills (n = 402), raw 480:

| class | t_c | val n | recall 0.35 -> t_c | val FP boxes 0.35 -> t_c | precision 0.35 -> t_c |
|---|---|---|---|---|---|
| banana | 0.40 | 469 | 0.531 -> 0.486 (-4.5 pp) | 132 -> 100 | 0.65 -> 0.70 |
| apple | 0.40 | 199 | 0.583 -> 0.558 (-2.5) | 67 -> 58 | 0.63 -> 0.66 |
| mango | 0.50 | 11 | 0.636 -> 0.636 | 2 -> 1 | 0.78 -> 0.88 |
| citrus | 0.45 | 208 | 0.673 -> 0.639 (-3.4) | 33 -> 21 | 0.81 -> 0.86 |
| guava | 0.35 | 0 | (no val instances) | - | - |
| pomegranate | 0.35 | 16 | 0.563 -> 0.563 | 9 -> 9 | 0.50 |
| lemon_lime | 0.75 | 77 | 0.052 -> 0.013 (-3.9) | 4 -> 0 | 0.50 -> 1.00 |
| tomato | 0.45 | 317 | 0.429 -> 0.382 (-4.7) | 104 -> 65 | 0.57 -> 0.65 |
| potato | 0.90 | 20 | 0.0 -> 0.0 | 3 -> 0 | 0.0 -> n/a |
| cucumber | 0.60 | 154 | 0.169 -> 0.123 (-4.5) | 18 -> 7 | 0.59 -> 0.73 |
| carrot | 0.45 | 435 | 0.301 -> 0.262 (-3.9) | 51 -> 33 | 0.72 -> 0.78 |
| capsicum | 0.80 | 116 | 0.224 -> 0.181 (-4.3) | 10 -> 0 | 0.72 -> 1.00 |

Read-out: for lemon_lime, potato and capsicum the rule allows very high thresholds because G3's val recall for them is already near zero. In those classes the 5 pp budget protects almost nothing, and this is where A1 can lose real detections on new footage (it did for lemon_lime on the holdout). The DEV det clip guard (prereg 3.5) did not trigger. Curves are in `dev_threshold_curves.csv` and `dev_threshold_curves.png`, including FA/min on the DEV neg clip with each class thresholded alone.

**A2 grid** (minHits {2,3,4} x birth margin {0, .05, .10, .15}, `dev_A2_grid.csv`): every config gave the same DEV neg FA/min (0.25), so the prereg tie-break (mean false-track lifetime) picked **minHits 3, delta 0** (0.267 s vs 0.333 s). minHits 4 was inadmissible because it lost a det-clip segment. Birth margins added nothing on DEV.

## 2. DEV results (synthetic g3clips_dev; A0 replay reproduces G8 DEV exactly: seg 0.5417, frame 0.4365, TTFC 533/733 ms, 68 ID switches, 22 fragmentations, FA 0.75)
| metric | A0 | A1 | A2 |
|---|---|---|---|
| **raw detector**, neg clip boxes/min (frames with a box /3600) | 3.75 (15) | 2.00 (8) | 2.00 (8) |
| raw detector, val box-free stills: false boxes / images with a false box (n = 90) | 66 / 16 | 45 / 14 | 45 / 14 |
| **post-tracking**, neg clip FA/min = false track births/min | **0.75** (3 tracks) | **0.25** (1) | **0.25** (1) |
| false-track lifetime mean / max s | 0.20 / 0.33 | 0.33 / 0.33 | 0.27 / 0.27 |
| FA episodes/min | 0.75 | 0.25 | 0.25 |
| det clip segment acc (24) | 0.5417 | 0.5417 | 0.5417 |
| det clip frame acc | 0.4365 | 0.4029 | 0.3925 |
| det clip per-class frame recall banana / apple / citrus / carrot | .627 / .671 / .565 / .150 | .538 / .667 / .565 / .108 | .521 / .658 / .555 / .096 |
| TTFC from segment start p50 / p90 ms | 533 / 733 | 400 / 1013 | 533 / 1053 |
| **TTFC from first GT visibility** p50 / p90 ms | 467 / 707 | 400 / 1013 | 400 / 1053 |
| ID switches / fragmentations | 68 / 22 | 34 / 22 | 27 / 19 |
| static label flicker /10 s | 5.0 | 2.5 | 2.08 |
DEV goal (FA/min <= 0.5 x A0): **met by A1 and A2** (0.25 <= 0.375). Caveat: this is 3 tracks vs 1 on one 4-min synthetic clip. The det clip is built from val images, so it is not independent of the threshold choice.

## 3. FP error register (analysis only; `ml/runs/G9/fp/error_register.csv`)
All 74 reviewed absence-check tiles (VB8-holdout clips) are forbidden for training or tuning and were not used for any choice.
- Categories: **unrelated object 41**, out-of-taxonomy produce 12, uncertain 11, correct 8, real produce wrong class 1 (mango called apple), printed produce 1 (printed tomato on packaging).
- Visual groups of the 66 false tiles: clothing 12, unclear 7, packaging/printed 5, sign 4, meat/fish 4, background/blur 4, equipment 7, oil palm 3, leafy greens 3, pod 3, melon 2, maybe-guava 2, sack 2, person/hand 2, and 1 each of umbrella, bag, chili, grapes, grain/seed, mango-as-apple.
- Basis: 14 tiles carry a human type note. The category and group of the other un-noted false tiles were **assigned by me from the tile images** (column `category_basis`). **Flag:** the three "oil-palm fruit" tiles (009, 011, 012, clip "Fresh onion market video") look to me like red or spring onions. They are out-of-taxonomy either way, but worth one look from the user.
- A1 vs the G3 false tiles: A1's thresholds would remove **14 of the 44 false G3 tiles** (13/35 unrelated objects, 1/7 out-of-taxonomy). The high-score false positives survive: banana 0.91 (pod), 0.87 (fish scene), 0.84 (sacks); tomato 0.83 (clothing); mango 0.83 (grass); apple 0.90 (mango). **Score thresholds cannot fix confident wrong-object detections.** This is the case for Stage B/C (hard negatives, crop verifier).

## 4. Holdout (run once; Kaggle CPU; scorer = unchanged G8 functions; A0 reproduces G8's G3 row exactly)
### 4a. Recall and whole-clip FA (G8 definitions; whole-clip FA is **provisional**, since negatives are verified only at reviewed moments)
| config | pairs detected / 22 | clip presence recall | FA/min whole clip (36.37 min) | FA tracks | neg clips with class FA | births/min (pos) | label changes / track-min |
|---|---|---|---|---|---|---|---|
| A0 (G3) | 11 | 0.500 | 2.859 | 104 | 4/16 | 34.6 | 3.87 |
| A1 | 9 | 0.409 | 2.034 (-29%) | 74 | 4/16 | 28.9 | 0.84 |
| **A2** | 9 | 0.409 | **0.880 (-69%)** | 32 | 4/16 | 25.2 | 0.92 |
Showcase-5 view (14 pairs): A0 7, A1 6, A2 6. Per class: lost carrot (#16 ca1cbf110, a 2.2-s clip: A0 showed carrot exactly 0.50 s, A1 0.40 s, A2 0.30 s, just under the 0.5-s rule) and lemon_lime (#1 c6e08132a: shown 7.9 s by A0, removed by t = 0.75). Everything else is unchanged.
Bootstrap (uploaders, 1000), candidate - A0: A1 recall [-0.22, 0.0], FA/min [-1.46, -0.62]; **A2 recall [-0.22, 0.0], FA/min [-2.52, -1.12]**.
Per negative clip FA tracks A0/A1/A2: #7 c0a13587f (Tehran night walk, 22.3 of the 36.4 negative minutes) 71/54/20; #15 10/8/4; #20 9/4/3; #33 5/4/4; #29 3/1/0; #27 2/1/0; #30 2/1/1; #10 1/1/0; #26 1/0/0; others 0.

### 4b. FA inside verified-negative windows (user addition 1; ±1 s windows, `holdout_neg_windows*.csv`)
| window set | evaluated min | A0 FA/min (tracks) | A1 | A2 | clips with window FA A0/A1/A2 |
|---|---|---|---|---|---|
| **presence-review frames only (6 evenly spaced per clip, unbiased)** | 3.15 | 2.86 (9) | 1.27 (4) | **0.64 (2)** | 7 / 4 / 2 |
| absence-check tile moments only (chosen *because* a detector fired: biased toward FA) | 1.34 | 14.87 (20) | 9.67 (13) | 6.69 (9) | 7 / 6 / 4 |
| union (prereg definition) | 4.10 | 5.61 (23) | 3.41 (14) | 2.19 (9) | 9 / 7 / 4 |
The tile windows over-sample false alarms by construction, which is why the union rate is above the whole-clip rate. The unbiased presence-frame windows agree with the whole-clip result (A0 2.86 in both), and the A2 cut there is -78%. Raw boxes/min inside the presence windows: A0 7.9, A1/A2 4.4.
Note: the four tiles in #6 (onion clip) came from the auto-label pass. In the 10-fps app replay, all raw G3 boxes there fall below the 1% area guard, so A0 shows 0 tracks in #6.

### 4c. Candidates for a full-video human check (user addition 1; `full_video_check_candidates.csv`)
Rule: an A0 track on a negative clip, displayed >= 0.5 s outside the verified windows, with max score >= 0.70. **3 tracks, all banana, in #20 cfe0b39f1 (Funchal market), 112.9-125.3 s, max scores 0.73-0.75, displayed 2.6 / 5.5 / 2.8 s; A1 and A2 still show them.** The reviewed tile 044 at 118.6 s (banana 0.87, fish-cutting scene) was judged false, so these are probably the same object. A check of 112-126 s of that video would settle it.

### 4d. TTFC audit (user addition 2; `holdout_ttfc_pairs.csv`)
The G8 holdout TTFC proxy runs from **clip start** to the first display of the class. Per detected pair (A0): c6e08132a lemon_lime 0.08 s, banana 1.04, citrus 1.60, apple 2.24; cd4211720 mango 0.16; ca1cbf110 carrot 0.80; c4880a292 cucumber 12.5; c9030be18 banana 21.9, citrus 24.4, capsicum **28.1**; cd1a3f857 banana **72.8**. The **p90 of 28.1 s is c9030be18's capsicum**, whose first raw G3 box of that class comes at 28.03 s in a 152-s clip. In 10 of 11 detected pairs, display follows the first raw box of the class within 0.1-0.6 s. **The proxy measures when the produce first appears or is first detected in a long web recording, not pipeline latency.** The exception is cd1a3f857 banana (412-s clip): the first raw box is at 41.2 s but display only at 72.8 s, because earlier boxes were too brief to become a displayed track. A1/A2 p50 rises to ~22 s mostly because two early pairs were lost. For pairs detected by both, A1/A2 add 0-0.3 s, except cd1a3f857 banana (72.8 to 120.7 s) and c4880a292 cucumber (12.5 to 23.0 s). On DEV, where object-appearance truth exists, TTFC from first visibility is 467/707 ms for A0 vs 400/1013 ms for A1 and 400/1053 ms for A2 (table in 2).

## 5. Goal and promotion
| test | A1 | A2 |
|---|---|---|
| DEV FA/min <= 0.5 x A0 | yes (0.25 vs 0.75) | yes (0.25) |
| DEV recall <= 5 pp per class (val stills) | yes (by rule) | yes |
| DEV det-clip per-class frame recall <= 5 pp (reported) | **no** (banana -8.9 pp) | **no** (banana -10.6, carrot -5.4) |
| Holdout FA/min <= 0.5 x A0 (whole clip, provisional) | no (-29%) | **yes (-69%)** |
| Holdout FA/min <= 0.5 x A0 (verified presence windows) | yes (-56%, 4 vs 9 tracks) | yes (-78%) |
| Holdout recall: <= 1 pair lost and no showcase pair lost | **no** (2 lost, carrot) | **no** (2 lost, carrot) |
| G8 rule 4 (recall >= A0 and FA <= A0) | no | no |
| G8 rules 1, 2, 7, 8 (weights) | unchanged weights | unchanged |
| G8 rule 3 (TEST gauntlet), rule 5 (neg_test FA) | **not run**: the shared CPU lock was held by the parallel G9-existing jobs the whole time | not run |
| Rule 6 latency | post-processing only; Kaggle CPU detector p50/p95 152/184 ms (1 thread, shared kernel) | same |
**Did FA/min halve within the recall limit? On DEV yes. On the holdout, A2 halves it (by 69-78%) but not within the recall limit (2 of 22 pairs lost, one of them a showcase class). Result: goal not confirmed, no promotion.**

## 6. What this means for Stage B/C
1. **The display gate (minHits 3) is the cheapest large win.** On real footage it removes ~57% of false tracks on top of the thresholds, and on its own it costs no holdout pair (both lost pairs come from thresholds: lemon_lime t = 0.75, and carrot falling under the 0.5-s display rule on a 2.2-s clip). The obvious next DEV-only test is **A0 + minHits 3 without the high thresholds**. It was not preregistered here, so it was not run on the holdout. It should go into the next prereg with a **fresh** holdout or with this holdout's re-use declared.
2. The rule "R drop <= 5 pp" is too permissive for classes G3 barely detects (lemon_lime, potato, capsicum). Next time, cap t_c (for example at <= 0.6) or require a minimum recall.
3. Confident wrong-object detections (clothing, sacks, pods, meat, signs at 0.75-0.91) survive any threshold that keeps recall. That points to Stage B hard negatives from non-holdout footage and the Stage C crop verifier.
4. One recording (#7 Tehran night walk) contributes 68% of holdout false tracks and 61% of negative minutes, so pooled FA/min is dominated by it. Report per-clip numbers alongside.

## 7. Integrity and deviations
- Nothing trained. Thresholds and policy were chosen on DEV only (val stills + synthetic DEV clips) and frozen before the holdout replay. The holdout ran once per arm. The 74 holdout tiles were used only for the error register, after the freeze.
- **Deviation 1:** the per-class threshold option was not added to the shared `ml/eval/video_gauntlet.py`. That file had uncommitted edits by the parallel G9-existing agent (roboflow adapter), so a separate replay (`scripts/g9fp_replay.py`) reuses its `metrics()` unchanged. The replay reproduces the G8 DEV G3 row exactly, and default scorer behaviour is untouched.
- **Deviation 2:** a Kaggle dataset upload failed (blob "Upload unsuccessful", twice). The kernel therefore used the existing G8 `nutrisole-cv-g8-holdrun` dataset (same G3 ONNX, sha256 c6fcb32a…) with the frozen config embedded in `run.py` (identical to `g9fp_config.json`).
- A planned local smoke test of the kernel on a DEV clip was cancelled (CPU lock busy). The Kaggle run is the only execution, and A0 there reproduces G8's G3 holdout row exactly.
- Detector caches for DEV live outside git: `/workspace/work/cv/g9fp/`. Holdout replay JSONs: `/workspace/work/cv/g9fp/hold_out/hold/`.
