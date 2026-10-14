# G9 Stage B: hard-negative fine-tune, crop verifier, carrot #16 (report)

Wed 2026-10-14 PKT. Pre-registration: `docs/cv/gauntlet/G9_stageB_prereg.md` (commit 273d151, written before any Stage B result).
Brief: `files/nutrisole-g9-stageB-gpt.md` (user, 07:40 PKT). Artefacts: `ml/runs/G9/stageB/`.

## Decision

**No promotion. G3 stays champion.** Both arms failed pre-registered DEV gates before the holdout was touched, so neither could be
promoted whatever the holdout said (prereg section 5: "an arm failing a DEV gate is still replayed once on the holdout for the record
but cannot be promoted").

- **B1 (G3 + hard-negative fine-tune)** fails gate 3 (DEV recall): apple val recall -9.5 pp (limit 5), carrot AP50 0.441 -> 0.394
  (-0.047, limit 0.02), apple AP50 -0.021, and banana DEV-clip frame recall -7.7 pp.
- **B2 (G3 + MobileNetV3-Small crop verifier)** fails gate 5 (no tau meets false rejection <= 2% overall and <= 5% per showcase class;
  the least-rejecting value, tau 0.05, gives 4.0% overall and carrot 6.2%, apple 5.0%) and gate 3 (apple DEV-clip frame recall -16.7 pp).
- **B3 (B1 + verifier)** was not run: prereg requires both arms to pass their DEV gates first. Not justified.
- The holdout replay (section 8) was run once for the record. B1: 12/22 pairs (+#11 carrot), FA/min 2.859 -> 4.069 (+42%). B2: 11/22 pairs, FA/min 2.859 -> 1.540 (-46%), verified windows 2.855 -> 2.221. This does not change the decision.

What we learned: about 160 agent-verified hard negatives cut false boxes on hard-negative images and box-free stills, but even at 4%
of the training mix they cost real apple and carrot recall. The verifier rejects about 40% of hard-negative crops, but it also rejects
4-6% of real fruit, and carrot is the worst. Neither trade is acceptable under the rule "never promote by suppressing real fruit".

## 1. Hard-negative dataset (manifest `ml/runs/G9/stageB/hn_manifest.csv`)

| item | value |
|---|---|
| Mining sources | G3 (raw 480, floor 0.35, area guard) on 22 mining-pool video clips at 2 fps (M-train 16, M-dev 6, split by uploader in `mining_split.csv`) + 1,999 Wikimedia Commons stills (per-file CC0 / CC BY / CC BY-SA / PD; 191 fired) |
| Reviewed | 86 video context tiles (26 rejected) + 191 Commons stills (48 rejected) |
| Near-duplicates dropped | 15 (pHash Hamming <= 6) |
| **Kept** | **192**: train 161 (115 Commons whole images + 46 video crops), dev 31 (21 Commons + 10 video crops). 1 train crop (vc_vt084) failed to read on Kaggle, so 160 trained |
| Review status | **all 192 `agent_verified_negative`** (Hark visual review on contact sheets). **0 human-verified.** Nothing here is called human-verified |
| Labels | background-only: empty label files (whole images with no supported produce, or crops >= 2.5x the false box with no produce). No partially labelled mixed scenes |
| Mistake types (kept) | fruit-coloured objects 46, leafy/other veg 24, printed fruit 20, fish 14, clothing / fabric / umbrella 24, market misc / crowd 14, out-of-taxonomy produce (tapereba, papaya, cupuacu, onion, cabbage) 17, utensil / fish / fabric 12, sacks / seed sacks 9, spices 5, equipment 3, bags 2, packaging 1, crate 1 |
| G3 score on kept HNs | min 0.352, median 0.555, max 0.945; 31 at >= 0.75 |
| Neighbour frames | +-0.5 s around each video candidate kept as metadata (not trained) |

## 2. Leakage audit (`ml/runs/G9/stageB/leakage_audit.json`)

Clean.
- No holdout clip, holdout tile, Muktee1494 clip or M-dev clip in training (counts 0 / 0 / 0 / 0). The 34 holdout clips are `holdout_never_used`.
- pHash of every kept HN against 864 holdout keyframes: minimum Hamming distance 16; none within 10.
- Commons uploaders vs holdout uploaders: 6 Commons images by holdout uploaders were excluded (cw_0057, cw_0579-0582, cw_1020); no overlap after exclusion.
- Video HN sources: 9 clips, roles M-train (training) and M-dev (dev only).

## 3. B1: G3 + HN fine-tune (Kaggle T4, `mfaizannnn/nutrisole-g9b-train` v2)

Initialised from G3 best.pt, 20 epochs, 3,562 G3 train images + 160 HN (4.3%, cap 20%), seed 0, 672 s train. val480 mAP50 **0.4163 vs G3 0.4282**
(mAP50-95 0.3042 vs 0.3090).

Per-class on G3 val stills (n = 402 images; P/R at 0.35 from the DEV replay; AP50 from the Kaggle val480 run):

| class | n | G3 P / R | B1 P / R | B2 P / R (after verifier, tau 0.05) | G3 AP50 | B1 AP50 | dR B1 pp | dR B2 pp |
|---|---|---|---|---|---|---|---|---|
| banana | 469 | 0.654 / 0.531 | 0.601 / 0.559 | 0.659 / 0.516 | 0.563 | 0.559 | +2.8 | -1.5 |
| apple | 199 | 0.634 / 0.583 | 0.795 / 0.487 | 0.634 / 0.548 | 0.626 | 0.605 | **-9.5** | -3.5 |
| mango | 11 | 0.778 / 0.636 | 0.700 / 0.636 | 0.778 / 0.636 | 0.646 | 0.581 | 0.0 | 0.0 |
| citrus | 208 | 0.809 / 0.673 | 0.797 / 0.716 | 0.815 / 0.635 | 0.745 | 0.773 | +4.3 | -3.8 |
| pomegranate | 16 | 0.500 / 0.563 | 0.588 / 0.625 | 0.529 / 0.563 | 0.549 | 0.474 | +6.2 | 0.0 |
| lemon_lime | 77 | 0.500 / 0.052 | 0.118 / 0.026 | 0.500 / 0.052 | 0.101 | 0.090 | -2.6 | 0.0 |
| tomato | 317 | 0.567 / 0.429 | 0.545 / 0.461 | 0.572 / 0.413 | 0.458 | 0.459 | +3.2 | -1.6 |
| potato | 20 | 0.000 / 0.000 | 0.333 / 0.050 | 0.000 / 0.000 | 0.009 | 0.020 | +5.0 | 0.0 |
| cucumber | 154 | 0.591 / 0.169 | 0.634 / 0.169 | 0.619 / 0.169 | 0.295 | 0.285 | 0.0 | 0.0 |
| carrot | 435 | 0.720 / 0.301 | 0.679 / 0.287 | 0.719 / 0.276 | **0.441** | **0.394** | -1.4 | -2.5 |
| capsicum | 116 | 0.722 / 0.224 | 0.619 / 0.224 | 0.722 / 0.224 | 0.278 | 0.338 | 0.0 | 0.0 |

(guava has no val boxes.)

Other DEV measures:

| measure | G3 (B0) | B1 | B2 (tau 0.05) |
|---|---|---|---|
| val box-free images (90): false boxes | 66 | 50 | 61 |
| HN-dev (31): images with a false box / false boxes / boxes >= 0.75 | 29 / 88 / 19 | 15 / 70 / 20 | 20 / 45 / 11 |
| DEV det clip frame accuracy / segment accuracy | 0.437 / 0.542 | 0.430 / 0.625 | 0.405 / 0.542 |
| DEV det clip frame recall: banana / apple / citrus / carrot | 0.627 / 0.671 / 0.565 / 0.150 | 0.550 / 0.654 / 0.522 / 0.171 | 0.615 / **0.504** / 0.565 / 0.150 |
| DEV neg clips FA/min (4.0 min) | 0.75 | 0.75 | 0.25 |
| TTFC from visibility p50 / p90 ms | 467 / 707 | 333 / 920 | 533 / 773 |
| fragmentations / ID switches (24 segments) | 22 / 68 | 26 / 31 | 22 / 68 |
| label flicker per 10 s (all) | 4.19 | 1.89 | 4.09 |
| M-dev video (6 clips, 4.38 min, unverified): displayed tracks, births/min | 206, 47.0 | 243, 55.4 | 197, 44.9 |
| M-dev agent-checked real produce retained | 41/41 | 36/41 (carrot 0/2) | 39/41 (carrot 0/2) |

B1 removes false boxes on still images and stabilises labels, but in video it shows **more** tracks on M-dev (55 vs 47 births/min) and loses
real apple, carrot and banana recall. **Gate 3 fails** (apple val R -9.5 pp; carrot AP50 -0.047; apple AP50 -0.021; banana DEV-clip frame recall -7.7 pp).

## 4. B2: crop verifier (Kaggle T4, `mfaizannnn/nutrisole-g9b-verifier` v1)

MobileNetV3-Small (ImageNet init), 128 x 128 crop of the box x1.2, 12 epochs, 1.52 M params, 161 s train. Positives 6,856 GT crops (G3 train,
12 classes); negatives 2,476 (952 G3 false boxes on train images + 508 HN-train crops with their augmentations; the HN images are the same 160).
Selective inference: verify a track at its display birth, then at most every 10 processed frames (~1 s), and use the mean of the cached p(produce).

**False rejection of real fruit** (val GT crops, n = 2,020) vs true rejection (`verifier_tau.json`):

| tau | FRR overall | citrus | apple | banana | tomato | carrot | rejects val false boxes | rejects HN-dev crops | admissible |
|---|---|---|---|---|---|---|---|---|---|
| **0.05** | **4.0%** | 2.9% | 5.0% | 3.2% | 2.5% | **6.2%** | 11.5% | 39.8% | no |
| 0.10 | 5.2% | 3.9% | 5.5% | 4.7% | 4.4% | 7.6% | 13.0% | 44.7% | no |
| 0.25 | 7.7% | 5.3% | 8.5% | 5.6% | 7.6% | 11.7% | 18.2% | 49.6% | no |
| 0.50 | 11.3% | 7.7% | 15.1% | 7.1% | 12.7% | 16.1% | 24.5% | 52.0% | no |

No tau in {0.05 ... 0.50} meets the rule (<= 2% overall, <= 5% per showcase class with n >= 20). **Gate 5 fails.** Carrot is always the
worst class: it is the class with the most small, thin, partly hidden boxes, where a 128-px crop has the least context. B2 was frozen at
tau 0.05 (least-rejecting value) only so that it could be replayed for the record (deviation 1). On DEV video, the verifier
drops apple frame recall from 0.671 to 0.504 (-16.7 pp, **gate 3 fails**) and removes both M-dev carrots. It cuts DEV negative FA/min from 0.75 to 0.25.

## 5. Latency and mobile feasibility

Sandbox CPU, 2 threads, interleaved per frame on the same 300 DEV frames, full app step (detector + guard + tracker [+ verifier]) (`latency_sandbox.json`):

| arm | p50 ms | p95 ms | p95 vs G3 | gate 4 (<= 1.10x) |
|---|---|---|---|---|
| B0 (G3) | 55.9 | 95.5 | 1.00 | - |
| B1 | 62.1 | 97.6 | 1.02 | pass |
| B2 | 56.8 | 98.1 | 1.03 | pass (41 verifier calls in 300 frames) |

Holdout Kaggle CPU (1 thread per clip, 40,548 frames per arm): p95 G3 191.6, B1 186.5 (0.97x), B2 192.2 ms (1.003x); verifier 0.031 calls per frame.

Verifier batch call: p50 3.6 ms, p95 18.2 ms (sandbox, 663 batches). Calls per processed frame: 0.39 on the DEV det clip (busy produce
scenes), 0.0008 on DEV negative clips. Mobile: verifier ONNX 6.1 MB fp32 (int8 would be roughly a quarter of that; not measured), 1.52 M params, 128 px input. That would
add one small model to the app bundle next to the 10.6 MB detector. It is feasible on-device because it runs on about 0.2-0.4 crops per
frame. B1 has the same size and cost as G3. Latency was never the blocker; recall was.

## 6. Carrot #16 (ca1cbf110, 2.2-s clip): why the track fragments in ~0.6 s

Source: `carrot16_trace.json` (G3 replay, 10 fps, existing pipeline, no tuning).
- Carrot is visible as a **pile of several small carrots at the bottom edge of the frame**, not one object. From t = 0.6 to 1.2 s G3 fires 1-4
  carrot boxes per frame at scores 0.36-0.67. Each box covers only **1.0-2.6% of the frame**, and most raw boxes (e.g. 14 of 15 at
  t = 0.7 s, 17 of 21 at 1.1 s) are removed by the 1% area guard.
- The surviving boxes jump between different carrots in the pile from frame to frame. IoU with the previous track is 0.0-0.69 (often < 0.3).
  So the IoU matcher starts a new track instead of extending one: **7 track IDs are born in 0.6 s** (t 0.6-1.2), each displayed for only
  0.1-0.3 s once it reaches 2 hits.
- At t = 1.3 s all detections stop (camera pans away). The tracks coast and die by 1.6 s. Four new low-score boxes at 2.2 s come too late to be displayed.
- Net: the carrot class is displayed for about 0.5 s in total, made of several short IDs. That is why it sits exactly on the scorer's 0.5-s rule
  and why any confirmation rule loses it.

DEV short-lived-object study (`dev_shortlived.json`): truncating DEV det segments to 0.2 / 0.4 / 0.6 / 1.0 / 4.0 s, segments displayed >= 0.5 s
= 0 / 0 / 3 / 13 / 17 of 24; mean IDs per displayed segment rises 2.0 -> 9.2 with duration. Consecutive-frame IoU is high for large
objects (median 0.95, 1% below 0.3, n = 630) but low for small ones (< 3% of frame: median 0.18, half below 0.3, n = 2). So the failure is
**small, multi-instance objects plus IoU-only association**, not the confirmation gate. Ways to study this later, none tested here (prereg forbids a new gate variant):
class-aware merging of same-class tracks for display (count presence per class, not per ID), centre-distance or appearance association for small
boxes, and a carrot-specific small-object recall fix in data.

## 7. Comparison video

`files/g9/stageB/G9B_side_G3_vs_B2.mp4` (39.2 s, 1280 x 360): G3 (left) vs B2 G3 + verifier tau 0.05 (right). Both run the app pipeline at
10 fps on M-dev clips c237ace91 (fruit stall: papaya, pineapple, banana) and cec084f0c (vegetable market). These are independent clips: never
trained on, not holdout. Rendered with `ml/runs/G9/stageB/scripts/render_side.py`. Known cosmetic issue: cec084f0c is a portrait clip, so its
panel is stretched to 640 x 360 and the overlay text looks enlarged. The detections are unaffected. The video is gitignored (*.mp4), so the copy lives in files/.

## 8. Holdout record (34 clips, once, Kaggle CPU, `mfaizannnn/nutrisole-g9b-holdout` v1)

Run once after the DEV freeze, for the record (34 clips; 4 CPUs, 4,070 s wall; 40,548 processed frames per arm). Scored once with the unchanged G8
scorer functions plus the unchanged G9 extra script (deviation 4). Full tables: `ml/runs/G9/stageB/holdout/holdout_scores.md` / `.json`,
per-arm window files in `holdout/extra_B*/`. **Parity check:** B0 reproduces G9 A0 exactly (11/22, 2.859 and 2.855 FA/min).

| arm | verified pairs detected /22 | recovered vs G3 | lost vs G3 | showcase pairs /14 | FA/min whole clip (provisional, 36.37 min) | FA/min verified review-frame windows (3.15 min, unbiased) | FA/min union windows (4.10 min, tile part biased) | TTFC proxy p50 / p90 s | births/min (pos) | label changes / track-min | Kaggle CPU p50 / p95 ms per frame (1 thread) | verifier calls / frame |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 (G3) | 11 | - | - | 7 | 2.859 (104 tracks) | 2.855 (9) | 5.607 (23) | 2.24 / 28.11 | 34.63 | 3.873 | 162.3 / 191.6 | 0 |
| B1 (HN fine-tune) | 12 | #11 carrot | none | 8 | **4.069 (148), +42%** | 3.490 (11) | 4.876 (20) | 14.02 / 30.97 | 33.82 | 3.485 | 161.4 / 186.5 | 0 |
| B2 (verifier, tau 0.05) | 11 | none | none | 7 | **1.540 (56), -46%** | 2.221 (7) | 3.901 (16) | 2.24 / 28.11 | 32.48 | 4.154 | 162.4 / 192.2 | 0.031 |

Uploader-level bootstrap (1000 resamples, 25 uploaders), arm minus G3: B1 recall [0.0, +0.18], FA/min [-0.28, +1.74]; B2 recall [0.0, 0.0], FA/min [-1.48, -0.35].

Per-pair notes:
- B1 recovers #11 carrot (shown 0.8 s) but shows real fruit for less time elsewhere. #1 apple drops from 10.0 s to 2.9 s shown, and its first display slips from 2.2 s to 16.9 s (this drives the TTFC p50 jump). #3 banana drops from 3.75 s to 1.58 s. B1 adds false tracks on the busiest negative clip (#7 c0a13587f: 71 -> 100) and on #33 (5 -> 14), #13 (0 -> 5) and #34 (0 -> 2).
- B2 loses no pair, but shows real fruit for less time: #18 banana drops from 4.0 s to 1.2 s and #22 cucumber from 5.25 s to 4.67 s. Carrot #16 stays exactly on the 0.5-s rule (6 -> 4 track IDs). It halves whole-clip false tracks, mostly on #7 (71 -> 33).
- Mixed-scene false alarms (a class shown >= 0.5 s on a verified-positive clip but not in that clip's truth): 9 clips for G3, 8 for B1, 9 for B2. The verifier does not remove wrong-class boxes on real produce, as expected, since it only judges produce vs non-produce.

On this holdout B2 at tau 0.05 would meet holdout gates 1 and 2. This does not change the decision. B2 failed DEV gates 3 and 5 before the holdout was run. tau 0.05 is not a valid operating point under the prereg (it rejects 4% of real fruit and 6.2% of real carrots). And this is the 4th use of these 34 clips. The direction (FA roughly halved with no clip-level pair lost) is worth confirming on fresh footage with a verifier that meets the false-rejection rule. B1 fails holdout gate 2 outright (+42% FA).

## 9. Gates (prereg section 5)

| gate | B1 | B2 (tau 0.05) |
|---|---|---|
| 1. holdout recall (no showcase pair lost, <= 1 other) | pass (12/22, none lost, #11 carrot recovered) | pass (11/22, none lost) |
| 2. holdout FA (whole clip <= 0.75 x G3 and verified windows <= G3) | **fail** (4.069 vs limit 2.144; windows 3.49 > 2.855) | pass on paper (1.540 <= 2.144; windows 2.221 <= 2.855), record only |
| 3. DEV recall | **fail** (apple val R -9.5 pp; carrot AP50 -0.047; apple AP50 -0.021; banana frame R -7.7 pp) | **fail** (apple DEV-clip frame R -16.7 pp) |
| 4. DEV latency p95 <= 1.10x | pass (1.02x) | pass (1.03x) |
| 5. verifier FRR | n/a | **fail** (no admissible tau; 4.0% overall, carrot 6.2%, apple 5.0% at 0.05) |
| **promoted** | **no** | **no** |

## 10. Deviations and workarounds

1. **tau 0.05 run.** The prereg freezes tau as the largest admissible grid value. None was admissible, so B2 has no valid operating point.
   It was replayed at 0.05, the least-rejecting value, for the record only. It is marked failing gate 5 throughout.
2. **Verifier retrained in a second kernel.** In the train kernel (`nutrisole-g9b-train` v2), the verifier trained but ONNX export failed (torch 2.11
   default dynamo exporter). A verifier-only kernel (`nutrisole-g9b-verifier` v1) retrained it on the same data with `dynamo=False` legacy export and also
   saved the state_dict. The evaluated verifier is that retrain, not the weights from v2. The G3 val pass in the verifier kernel errored and was skipped;
   G3 val numbers come from the train kernel.
3. **HN count 160, not 161.** One video crop (vc_vt084) failed to read on Kaggle.
4. **Holdout scoring adaptation.** The Stage B kernel stores raw boxes per detector model rather than one list per clip. Scoring runs the unchanged G8
   `clip_stats / score / boot` (exec of `g8_holdout_score.py` up to its result section, as in `g9fp_holdout_score.py`) and the unchanged
   `g9a3_holdout_extra.py`, once per arm on a per-arm view of the replay (raw = that arm's detector, floor 0.35). Script:
   `ml/runs/G9/stageB/scripts/g9b_holdout_score.py`. It was checked on the A3 replay (A0 as all three arms), where it reproduces A0 exactly (2.859 FA/min whole, 2.855 in verified windows).
5. **Holdout re-use.** This is the 4th replay of the same 34 clips (G8, G9 A, A3, Stage B), so any holdout number here is descriptive only.
6. **Agent review, not human.** All HN labels and the M-dev "real produce retained" counts come from the agent's visual review. No human verified them.
7. B3 not run (not justified, prereg section 3).

## 11. Next

G3 remains the shipped detector. Ideas, not tested here: (a) a stronger verifier needs more context than a 128-px crop, or produce-specific
negatives, before it can reach 2% FRR. Carrot is the class to beat. (b) The HN effect on apple/carrot suggests trying a smaller HN share or
adding matched positives (apple/carrot in market scenes) rather than more negatives. (c) Carrot #16 points at association of small, multi-instance
objects. All of these need fresh independent footage for confirmation, because the current holdout is used up.
