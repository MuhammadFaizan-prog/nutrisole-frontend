# G9 Stage F: market-domain dataset repair + controlled training (pre-registration)

Written 2026-10-14 17:40 PKT **before any Stage F result**: no M-DEV v2 label exists, no market-train (MT) image has been labelled, no
F1/F2 weights exist and no Stage F number has been computed. Authoritative brief: user, 2026-10-14 17:25 PKT
(`files/nutrisole-g9-stageF-gpt.md`), plus the user's scope guardrails (17:27 PKT). Branch `cv-gauntlet` only; no merge, no PR, no main.
**G3 stays champion.** Free Kaggle T4 only.

## 0. Scope guardrails and closed lines

- **The Stage E score-floor grid stays closed.** No ssf value (or any other guard/score-floor value) is evaluated as a candidate in
  Stage F, and no Stage E file or number is edited. The deployed post-processing (1% source-frame guard, floor 0.35, class-wise NMS 0.7,
  IouTracker iouMatch 0.3 / minHits 2 / maxMissed 4) is **fixed for every arm**.
- **12 classes stay exactly as in G3** (banana, apple, mango, citrus, guava, pomegranate, lemon_lime, tomato, potato, cucumber, carrot,
  capsicum). The 5-class showcase (citrus, apple, banana, tomato, carrot) is a reporting milestone, not a class cut. Persimmon, plum,
  peach, papaya, other unsupported produce and printed fruit are **negative / reject examples only, never new classes**. Capsicum = whole
  bell pepper; chilies are negatives.
- No crop counting, yield estimation or farm monitoring. The ripeness / defect / quality-grading pipeline is kept intact; P6 only
  measures whether detections carry enough pixels to feed it (identify -> condition -> grade -> reference price).
- No architecture change (YOLO11n, 12-class head), no score-floor change, no tracker change in F0/F1/F2.

## 1. Data and splits (fixed now)

| Set | Role in Stage F | Rule |
|---|---|---|
| det_v3 train (G3 training set) | replay data for F1/F2 | unchanged |
| det_v3 val (DEV val stills, 402) + DEV det/neg clips + Stage C probe (**SYNTHETIC**, separate columns) | A-gate continuity (DEV) | never trained on |
| **M-DEV** (Stage E, 67 evaluated + 17 pool images, 52+ Commons sources) | market evaluation only | **never trained on**; labels repaired in P2 (v2) |
| **M-TEST** (Stage E, 94 images, 65 sources) | reserved | **untouched**: only the pHash check is run against new data. It is scored only if a config passes every gate below **and the user approves**; default = untouched |
| old holdout (34 clips + keyframes) + its uploaders | excluded | never used |
| Stage D set S (24 images, G3-seeded labels) + S uploaders | excluded from training | G3-seeded labels are not allowed (brief P3) |
| **MT** (new market-train set, P3) | F2 training | see below |

**MT rules.** Sources: Wikimedia Commons per-file CC0 / CC BY / CC BY-SA / PD images and videos; Zenodo CC BY; Kaggle / Roboflow only
with a permissive licence recorded. **Never** Pexels / Pixabay / Mixkit. Candidate pool: the 586 Stage D Commons candidates (downloaded,
licence recorded, never labelled except S) plus any new Commons search. Source key = uploader (credited author for bot uploads).
Excluded source keys: all M-DEV and M-TEST source keys, all Stage E candidate source keys, S uploaders, holdout uploaders, M-dev/M-train
clip uploaders, DEV material. **Cap: <= 4 images per source key.** Leakage: 64-bit pHash vs G3 train (det_v3 train), DEV val stills, DEV
clip frames, G7 stage-1 keyframes (holdout + M-dev + M-train), Stage D S + 586 candidates already used as S, M-DEV and M-TEST; distance
<= 10 -> dropped. Recording-level: frames from one video are one source. MT is split by source key into MT-train (~85%) and MT-val
(~15%, in-domain sanity only, never used for selection).

**MT content target:** market / mandi / greengrocer / cart scenes with small, overlapping and occluded **citrus, apple, banana, tomato,
carrot**, coverage of all 12 classes, and negatives / mixed scenes: persimmon, plum, peach, papaya, other unsupported produce (onion,
chili, gourd, melon, eggplant ...), printed fruit, clothing, bags, market equipment. Size target >= 60 MT images incl. >= 15 negatives;
shortfalls reported.

**MT labelling:** **no G3 proposal is used.** OWLv2 (`google/owlv2-base-patch16-ensemble`, Apache-2.0) proposals on whole image + tiles,
then full manual agent correction (keep / delete / relabel / add boxes) on zoomed review sheets. Piles that cannot be boxed item by item
are **greyed out** (pixels set to 114) in the training image, so unlabelled real produce never becomes background. Labels are
**agent-verified, not human-verified**.

## 2. Label version policy (M-DEV)

- `ml/runs/G9/stageE/m_labels.json` = **v1**, kept byte-identical (sha256 recorded in the report).
- P2 writes `ml/runs/G9/stageF/m_labels_v2.json` + an edit log. v2 edits are made **without viewing any model prediction** (no G3, F1 or
  F2 output is shown on review sheets; only raw images and OWLv2 proposals).
- Repair scope: overlaps, missing boxes, duplicate boxes, mislabels, excessive crowd/ignore regions. Inside crowd regions individual
  boxes are drawn wherever instances are genuinely separable at native resolution; otherwise a documented crowd/ignore region stays.
  Real produce is never turned into background. The 17 unlabelled M-DEV pool images are labelled.
- Matching rules unchanged from Stage E: a same-class detection whose centre lies in a crowd region is ignored (never a TP); any
  detection in an ignore region is ignored (never a TP); a different-class detection in a crowd region is a class-error false box.
- Independent second pass in a fresh context using a **different-crop protocol** (fixed random 2x2 / quadrant crops drawn from scratch,
  no v2 overlay) on >= 15 images (seed 1); agreement as box F1 @IoU 0.5 (class-aware / agnostic), class agreement, image-level
  negative agreement. Disagreements are preserved in a file and ambiguous objects flagged; pass 1 (v2) stays the GT.
- **v2 is frozen (sha256 recorded) before any F1/F2 output is evaluated on M-DEV.** G3 (F0) is re-run on v2 before comparing.
- Per-class v2 instance counts are reported; any class with **< 30 individually boxed M-DEV instances is "thin"**: reported, never used
  to rank arms or make claims.

## 3. Arms (all YOLO11n from G3 `best.pt`, deployed at 480, fixed post-processing)

| Arm | Definition |
|---|---|
| **F0** | G3 unchanged (`best.pt` sha256 29cc5212...). Champion, no training. |
| **F1** (replay-only control) | Fine-tune from G3 on det_v3 train only. To match F2's iterations, the train list is det_v3 train + a seeded random duplicate sample of det_v3 train images of the same count as F2's MT entries. |
| **F2** (market) | Fine-tune from G3 on det_v3 train + MT-train, MT entries oversampled to **<= 15% of the train list** (balanced against the original positives and non-target negatives; MT negatives kept >= 25% of MT entries where available). |

**Matched schedule** (both arms, both seeds): imgsz 640, 20 epochs, batch 32, SGD lr0 0.002 lrf 0.1 cosine, momentum 0.937, warmup 1,
mosaic 1.0, close_mosaic 5, scale 0.5, fliplr 0.5, degrees 10, translate 0.1, hsv_s 0.6, hsv_v 0.5, mixup 0, deterministic=True (Stage D
D1 recipe). Identical train-list length for F1 and F2 at a given seed. **Seeds: 0 and 1** for F1 and for F2 (4 runs). The only
F1-vs-F2 difference is MT replacing duplicated det_v3 images.

**Feasibility arm R (separate measurement, never selectable):** for F0 and F2-seed0: (a) 640 full-frame inference, (b) 480 full frame +
2x2 tiled 480 crops (5 passes, merged NMS). Reported: raw small recall on M-DEV v2 / DEV val, CPU p50 / p95 per frame (sandbox ONNX
Runtime, 2 threads, same session) and peak RSS.

## 4. Compute budget

Free Kaggle T4 only, **<= 6 GPU-hours total** for Stage F (OWLv2 proposals ~0.5 h; 4 training runs ~0.25-0.35 h each from Stage D wall
times; exports). Kaggle dataset upload has failed before: inputs are pulled by URL (Commons) or through other kernels' outputs / existing
datasets, as in the Stage D template. No paid compute.

## 5. Metrics (P5), on revised M-DEV v2 and existing DEV

Raw (all boxes >= 0.35, before the guard) and postprocessed (1% guard; displayed) **reported separately** for every arm/seed:
per-class AP50, precision, recall (12 classes + showcase); recall by size bucket (<0.25%, 0.25-0.5%, 0.5-1%, >=1% of the frame);
wrong-class predictions; false boxes on unsupported fruit / box-free images; false tracks/min on independently verified market video
intervals (stated unavailable if no licensed independent market video exists); false boxes per recovered object; fragmentation (DEV det
IDs/segment, ID switches); CPU p50/p95 and ONNX export; results per source/market; seed variance (|seed0 - seed1|). No strong claims for
thin classes.

## 6. Gates (frozen; relative to F0 = deployed G3)

**A1-A8 unchanged from `G9_stageD_prereg.md` section 5** (incl. A1's raw small-showcase +5 pp clause for trained arms; A3 per-class AP50
no drop > 0.02 on det_v3 val at 480). **Market checks M1-M3 exactly as pre-registered in `G9_stageE_prereg.md` section 5** (reject-only),
recomputed on v2 labels. **No new market gate is added.**

**Stated up front:** with the 1% guard fixed, displayed recall of GT < 1% needs predicted boxes >= 1% of the frame, so **A1 (displayed)
and M1 are not expected to pass for any arm**; Stage F is primarily a training-evidence stage (raw recall, false-positive behaviour,
seed stability). A guard or resolution change would need its own prereg.

**Admissible** = passes A1-A8 and M1-M3 **for both seeds**. Among admissible: largest mean DEV val small-showcase displayed recall; ties
within 1 pp -> F1 over F2 (simpler). If none: **frozen pick = F0 (unchanged G3)** -> `ml/runs/G9/stageF/frozen_pick.json`. Any pick is a
DEV pick only.

## 7. P6 quality-grading feasibility

On the smallest correctly detected market produce (raw, <0.25% and 0.25-1% buckets): pixel size of the item at 480 and at native
resolution vs what ripeness (colour distribution over the surface) and defect cues (spots, bruises, cracks: ~2-5% of item diameter)
need, using example crops. No grade is issued from insufficient evidence. If infeasible, a move-closer / ROI scanning workflow is
proposed within the existing proposal (identify -> condition -> grade -> reference price).

## 8. Loop rule

Any step that loops more than twice is recorded and skipped. The report is written and synced even if partial.
