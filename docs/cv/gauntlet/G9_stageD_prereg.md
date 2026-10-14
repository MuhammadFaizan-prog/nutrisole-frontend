# G9 Stage D: small-object training + false-positive control (DEV ONLY), pre-registration

Written 2026-10-14 (PKT) **before any Stage D result** (no D1/D2 weights exist, no Stage D number has been computed). Authoritative
brief: user, 2026-10-14 14:07 PKT (`files/nutrisole-g9-stageD-gpt.md`). Branch `cv-gauntlet` only; no merge, no PR, no main.
**G3 stays champion.** Nothing in Stage D can be promoted without fresh, independently labelled footage; the existing holdout
(G6 locked 15 + holdout_v7_pending 9 + negatives_v7 10, incl. carrot #16) is **not used at all**, neither for tuning nor as validation.

Inputs carried over from Stage C (already published, commit b4e047e): the 1% guard is 1% of the **source** frame and runs before the
IouTracker; G3 detects 17.5% of small (<1%) val carrots raw and the guard removes all of them; lower guards alone fail on false
positives; the 640 diagnostic only lifts probe carrots 8 -> 17 of 132. Hypothesis for Stage D: **training coverage of small, distant,
overlapping and piled produce is the main limiter**, so a fine-tune with verified small/pile examples (D1) and small-object
augmentation (D2) should raise *raw* small-object recall at 480, and a size-aware filter should keep the extra false positives down.

## 1. Arms (detector)

All arms: YOLO11n, 12 classes in the G3 order (banana, apple, mango, citrus, guava, pomegranate, lemon_lime, tomato, potato, cucumber,
carrot, capsicum), deployed at 480 letterbox, raw decode + class-wise NMS 0.7, score floor 0.35, IouTracker defaults (iouMatch 0.3,
minHits 2, maxMissed 4). Only the weights and the post-detector filter (section 2) vary.

| Arm | Definition |
|---|---|
| **D0** | G3 unchanged (`best.pt` sha256 29cc5212...; ONNX `det_yolo11n_640_raw.onnx`). Baseline and champion. |
| **D1** | Fine-tune from G3 `best.pt` on the full original G3 training set (det/neg/oiv7/hardneg train, replay, all 12 classes) **plus** the new agent-verified small/overlapping/piled set S (section 3). S images are oversampled so S is at most 15% of training images per epoch. Same recipe as Stage B B1 (imgsz 640, SGD lr0 0.002 cosine, 20 epochs, mosaic 1.0, scale 0.5, close_mosaic 5, seed 0). |
| **D2** | D1 data and recipe **plus** small-object augmentation: (a) offline zoom-out collages (2x2 and 3x3 grids of training images, every box carried, objects shrink to 1/2-1/3) making up ~20% of training images, drawn from base train and S; (b) online `scale` 0.5 -> 0.9 (wider random scale range). No copy-paste of unlabelled crops (YOLO copy-paste needs masks; collages paste whole fully labelled images, so no produce is left unlabelled). |
| D-ctl (analysis only, never selectable) | Replay-only fine-tune: identical recipe to D1 but without S. Separates fine-tune drift from the effect of S (Stage B saw drift: B1 apple val R -9.5 pp). |
| **D3** | 640 / tiled inference. **Not run in Stage D** unless the evidence justifies it: it costs ~1.8x detector FLOPs (Stage C estimate), so it cannot meet the CPU p95 limit (A7) by construction. It would only be reconsidered, under a new prereg, if D1/D2 fail A1 *and* a hardware budget change is agreed. |

## 2. Guard variants (Exp3), evaluated for every arm, raw (pre-guard) and displayed (post-guard)

| Guard | Rule (applied per frame after decode/floor/NMS/dst_to_src, before the tracker; area = fraction of the source frame) |
|---|---|
| **g1** | minAreaFrac 1% (current G3) |
| **g05** | minAreaFrac 0.5% |
| **g025** | minAreaFrac 0.25% |
| **ssf50 / ssf60** (alternative filter: size-dependent score floor) | boxes >= 1% use the normal 0.35 floor; boxes in [0.25%, 1%) are kept only if score >= 0.50 (ssf50) or >= 0.60 (ssf60); boxes < 0.25% are dropped. Justification: Stage C false boxes concentrate in the small bins at low score; a small box must be more confident to be shown. |

The "reduced guard chosen on DEV" is, per arm, whichever of g05 / g025 passes all criteria with the larger small-object gain (ties
within 1 pp -> the higher guard). Raw = all boxes >= 0.35 before any guard (diagnostic, never displayed).

## 3. Data rules (Exp1)

- Sources allowed: Wikimedia Commons per-file CC0 / CC BY / CC BY-SA / PD (licence, author, uploader, page recorded per file); Zenodo CC BY;
  Kaggle/Roboflow datasets only with a permissive licence recorded. **Never**: DEV (val stills, DEV det/neg clips, M-dev clips, probe
  sources), the reviewed holdout (34 clips and their keyframes), Commons uploaders who appear in the holdout, Muktee1494 clips,
  Pexels / Pixabay / Mixkit.
- Labelling: boxes are proposed by G3 on high-resolution tiles (objects are large in a tile, so the teacher sees them at its trained
  scale), then **agent-verified** on contact sheets: wrong boxes removed/relabelled, missed produce added. **All produce of the 12
  classes in a mixed scene is annotated**; an image whose produce cannot be fully annotated is rejected (or the unlabelled region is
  greyed out, recorded per image). Labels are stated as agent-verified, not human-verified.
- Small objects are created by downscaling the verified full-resolution image (2-4 scales), so the same labels are exact at small size.
- Leakage: pHash (64-bit) of every kept image vs DEV val stills, DEV clip frames, M-dev clips and all holdout keyframes; any distance
  <= 10 is dropped. Uploader overlap with the holdout -> dropped.
- Split: S is split by uploader into S-train (~80%) and S-dev (~20%, analysis only, never used for selection).

## 4. Evaluation material (DEV only)

DEV val stills (n=402, det_v3 val), DEV det clip and DEV neg clip (`g3clips_dev`), and the Stage C **SYNTHETIC** probe (always labelled
synthetic). Per-class AP50 / precision from Ultralytics val at 480 on det_v3 val (12 classes). CPU latency: sandbox, ONNX Runtime
2 threads, same session for all arms.

## 5. Frozen acceptance criteria (all relative to **D0 + g1 = deployed G3**; a config = arm x guard)

| # | Criterion | Limit |
|---|---|---|
| A1 | **Required small-object gain.** Val small (<1% source area) showcase recall, displayed: **>= D0/g1 + 10 pp** (2.6% -> >= 12.6%) **and** small-carrot displayed recall **>= +10 pp** (1.3% -> >= 11.3%). For D1/D2 additionally: **raw** small showcase recall >= D0 raw + 5 pp (training effect, not just a guard change). |
| A2 | Showcase normal-size recall (citrus, apple, banana, tomato, carrot; GT >= 1%): per class on val stills (raw >= 0.35, IoU 0.5) and per-class frame recall on the DEV det clip: **no drop over 2 pp**. |
| A3 | Per-class AP50 (Ultralytics val 480, all 12 classes): **no class drops over 0.02**. |
| A4 | DEV neg: FA episodes/min **<= 1.00** and displayed tracks/min **<= 1.00** (G3 0.75 + 0.25). |
| A5 | False boxes per recovered object (val stills, displayed vs D0/g1): (new false boxes) / (new true positives) **<= 1.0** (Stage C lower guards were ~4.5 on the probe and ~1.2-2.8 on val); new TP must be > 0. Plus box-free image false boxes **<= D0/g1 + 4** (39 -> <= 43) and probe (SYNTHETIC) mixed-scene false tracks/min **<= 1.5x D0/g1**. |
| A6 | TTFC from visibility p90 on the DEV det clip **<= D0/g1 + 100 ms** (707 -> <= 807 ms). |
| A7 | CPU p95 (detector + post, sandbox, same session) **<= 1.10x D0** p95. |
| A8 | Fragmentation (DEV det IDs/segment): reported; **<= D0 + 0.10** required. |

**Selection rule.** A config is admissible if it passes A1-A8. Among admissible configs pick the largest val small-showcase displayed
recall; ties within 1 pp -> prefer (i) D1 over D2 (simpler), (ii) the higher guard / g1 > g05 > ssf60 > ssf50 > g025. If none is
admissible, the frozen DEV pick is **D0 + g1 (unchanged G3)**. The pick is written to `ml/runs/G9/stageD/frozen_dev_pick.json`.
Whatever is picked is a **DEV pick only**: promotion requires fresh, independent footage under a separate prereg.

## 6. What will be reported (Exp4)

Small-carrot recall; small-object recall for the 5 showcase classes (raw and displayed, by size bin); per-class mAP50 / P / R; false
boxes per recovered object; false tracks/min on verified DEV negatives; missed produce; fragmentation (IDs/segment, ID switches, IDs per
GT object); TTFC; CPU p95; dataset audit; failure analysis; side-by-side DEV video (G3 vs the best D arm). If a step loops more than
twice it is recorded and skipped.
