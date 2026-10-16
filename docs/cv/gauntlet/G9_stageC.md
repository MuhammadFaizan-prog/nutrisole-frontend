# G9 Stage C: small-object detection and tracking (DEV ONLY)

2026-10-14 PKT, branch `cv-gauntlet`. Pre-registration and guard audit committed and synced **before** any result:
`docs/cv/gauntlet/G9_stageC_prereg.md` (commit afc82c7). No training, no holdout re-run, nothing promoted. **G3 stays champion.**

## Verdict

- **Finding label: (3) G3 does not detect small carrots reliably**, with a real but minority **(1)** component: the 1% guard removes
  every small detection G3 does make (on DEV val stills 39 of 228 small carrots, about 17%, are detected raw and all 39 are removed), but
  even with no guard, small-carrot recall is only 17.5% (val) and 0.7% (synthetic probe). Tracking fragmentation **(2)** is a secondary
  effect on piles. It does not explain the missing recall.
- **No lower guard is admissible.** Every lower guard recovers produce but adds false tracks on DEV negatives (0.75 -> 1.25/min, limit
  +0.25) and adds false boxes on box-free stills (+12 to +27, limit +2). They fail prereg rules 3 and 4.
  **Frozen DEV pick = C0 (unchanged G3: guard 1%, IouTracker defaults)**: `ml/runs/G9/stageC/frozen_dev_config.json`.
- **Fragmentation:** association IoU 0.2 or a centre-distance fallback changes almost nothing on DEV. The guard does interrupt some
  tracks (9 of 120 DEV objects straddle 1%), but fragmentation is mostly detection drop-outs and boxes jumping between items in a pile.
- **Where the gain is:** the detector itself, through input resolution and training coverage (see section 6). A 640-px diagnostic of the
  same weights roughly doubles small-carrot hits, but they stay low (6% -> 13% of objects).
- Final evaluation of anything here awaits **fresh, independently labelled footage**. The existing holdout (incl. carrot #16) was not touched.

## 1. Guard audit (full detail in the prereg)

- **What and where:** `scene_guard()` rule 1 (`ml/eval/scene_guard.py`). Its exact mirror is `sceneGuard()` in
  `native/src/cv/pipeline/postprocess.ts` (parity test `native/tests/cvSceneGuard.test.ts`). It runs per frame after decode, the 0.35
  floor, class-wise NMS 0.7 and `dst_to_src`, and **before the IouTracker**. A removed box can neither start nor extend a track.
- **Native runtime:** the native app has **no runtime caller** of `sceneGuard`. Only the library and its tests reference it.
- **What 1% is measured against:** **the source frame**, not the 480 letterbox (padding excluded). In pixels:

  | Source frame | 1% guard, source px | 1% guard, at the 480 input |
  |---|---|---|
  | 480x640 DEV | ~55x55 | ~41.6x41.6 |
  | 480x736 (#16) | ~59x59 | ~38.8x38.8 |
  | 1080p | ~144x144 | ~36x36 |

  So the guard is **not** 48x48 at the input. At 0.5% it is ~25-29 px, and at 0.25% ~18-21 px.
- **How 1% was chosen:** the G3 guard tune (`ml/runs/G3/guard_tune_k11_480/guard_tune.json`) minimised DEV false alarms only. Its
  objective had no small-object recall term.

## 2. Raw vs discarded (G3 boxes >= 0.35 before and after the 1% guard)

`ml/runs/G9/stageC/out/raw_vs_guard_dev.json`; matched = same class, IoU >= 0.5 to a GT box. Showcase classes:

| DEV source | Class | Matched raw / kept@1% | Unmatched raw / kept@1% |
|---|---|---|---|
| val stills (n=402) | carrot | 137 / 98 (**39 removed, all <1%**) | 45 / 21 |
|  | banana | 285 / 120 (165 removed) | 96 / 39 |
|  | tomato | 143 / 88 (55 removed) | 97 / 36 |
|  | apple | 119 / 92 (27 removed) | 64 / 41 |
|  | citrus | 141 / 119 (22 removed) | 32 / 25 |
|  | all classes | 899 / 589 | 378 / 201 |
| DEV det clip | all classes | 3805 / 3724 (carrot 1 removed) | 1897 / 1687 |
| DEV neg clip | all classes | 0 / 0 | 23 / 15 |
| SYNTHETIC probe | carrot | 36 / 15 | 44 / 14 |
|  | all classes | 1280 / 736 | 579 / 280 |

**Every** removed box is < 1% by construction. On val stills, **small (<1%) carrot GT = 228**, of which **39 (17%) are detected raw**,
and the guard drops all 39. The DEV det clip has almost no small objects (as Stage B found), so the guard barely touches it.

## 3. Ablation (weights, 0.35 floor and IouTracker fixed; only `minAreaFrac` varies)

Per-arm JSON: `ml/runs/G9/stageC/dev/arm_{maf}_iou0.3.json`; summary: `ml/runs/G9/stageC/out/summary.json`.

| Metric | C0 1% (G3) | C1 0.5% | C2 0.25% | C3 none |
|---|---|---|---|---|
| DEV det frame recall: citrus / apple / banana / tomato / carrot | .565/.671/.627/.000/.150 | same | same | same |
| DEV det frame acc / segment acc | .4365 / .5417 | same | same | same |
| val R: citrus / apple / banana / tomato / carrot | .567/.452/.224/.259/.214 | .635/.538/.405/.338/.269 | .664/.563/.512/.401/.299 | .673/.583/.531/.429/.301 |
| val small (<1%) showcase recall | 2.6% (22/857) | 20.7% | 31.6% | 34.5% |
| val small carrot recall | 1.3% (3/228) | 11.4% | 17.1% | 17.5% |
| val recall by bin <0.25 / 0.25-0.5 / 0.5-1 / 1-2.5 / >=2.5% (showcase) | 0/0/6.8/45.7/73.3 | 0/12.8/43.8/48.5/73.3 | 2.7/41.6/46.3/48.5/73.3 | 10.4/43.4/46.3/48.5/73.3 |
| probe small (<1%) showcase object-frame recall (SYNTHETIC) | 0.3% (21/6408) | 2.3% | 4.0% | 5.0% |
| probe small carrot (SYNTHETIC) | 0/2178 | 16/2178 | 16/2178 | 16/2178 |
| probe frame acc / segment acc (SYNTHETIC) | .133 / .181 | .156 / .209 | .169 / .232 | .175 / .243 |
| **FA/min** (episodes, DEV neg, 4.0 min) | 0.75 | 1.00 | 1.00 | 1.00 |
| **displayed tracks/min, DEV neg** | 0.75 (3) | **1.25 (5)** | **1.25 (5)** | **1.25 (5)** |
| val false boxes total / on box-free images | 232 / 39 | 335 / **51** | 399 / **59** | 433 / **66** |
| DEV det mixed-scene false tracks | 45 | 53 | 55 | 55 |
| probe mixed-scene false tracks (SYNTHETIC, /min) | 10 (2.12) | 26 (5.50) | 38 (8.04) | 41 (8.67) |
| fragmented tracks, DEV det: IDs/segment, fragmentations, ID switches | 1.208, 22, 68 | same | same | same |
| distinct IDs per GT object (DEV det; probe) | 2.71; 1.42 | 2.73; 1.44 | 2.74; 1.38 | 2.74; 1.39 |
| ID switches (probe) | 32 | 36 | 38 | 40 |
| TTFC from visibility p50/p90 ms (DEV det; probe) | 467/707; 67/413 | 467/707; 67/327 | 467/707; 67/427 | 467/707; 67/467 |
| CPU guard + tracker per frame p50/p95 ms (DEV det) | 0.008/0.190 | 0.008/0.206 | 0.008/0.221 | 0.008/0.218 |

The detector is identical in all arms (sandbox G3 p50 55.9 / p95 95.5 ms, `ml/runs/G9/stageB/latency_sandbox.json`), so the
post-processing difference (<0.04 ms) is negligible.

**Produce recovered vs new false positives, compared with the 1% guard:**

| Arm | Produce recovered | New false positives |
|---|---|---|
| C1 0.5% | **+167** val boxes (incl. **+23 small carrots**, +24 carrot TP); **+124** probe small showcase object-frames (**+16 carrot**); +0 DEV det recall | **+103** val false boxes (+16 carrot), **+12** on box-free images; **+2** false tracks / +1 episode on DEV neg; **+8** mixed false tracks on the DEV det clip; **+16** on the probe |
| C2 0.25% | **+261** val (+36 small carrots, +37 carrot TP); **+236** probe (+16 carrot) | **+167** val false (+24 carrot), **+20** box-free; **+2** tracks / +1 episode on DEV neg; **+10** DEV det mixed; **+28** probe |
| C3 none | **+286** val (+37 small carrots, +38 carrot TP); **+301** probe (+16 carrot) | **+201** val false (+25 carrot), **+27** box-free; **+2** tracks / +1 episode on DEV neg; **+10** DEV det mixed; **+31** probe |

Unmatched val boxes include some unlabelled real produce in piles. The box-free and DEV neg counts are the clean false-positive measures.

**Selection rule (prereg section 5):** rule 1 (showcase recall) passes for all arms, since DEV det is unchanged and val rises. Rule 2
(FA episodes +0.25) passes, at the limit. **Rule 3 (displayed tracks/min, +0.5 > +0.25) fails for C1, C2 and C3. Rule 4 (box-free
+12/+20/+27 > +2; probe false x2.6/x3.8/x4.1 > x1.10) fails for C1, C2 and C3.** Rule 5 (TTFC) passes. No arm is admissible, so
**C0 stays**. For the record only: had the false-positive rules allowed it, the largest small-recall gain would have been C2/C3.
It would have met the 3 pp gain requirement on the probe (C2 +3.7 pp, C3 +4.7 pp); they tie within 1 pp, and ties go to C2, so C2 would have been picked.

## 4. Fragmentation (analysis only; no gate; nothing promoted)

Replays with IouTracker iouMatch 0.3 (stock), 0.2, and 0.3 plus a centre-distance fallback for boxes < 2% of the frame (distance <= 1.0x
mean side). Files: `ml/runs/G9/stageC/dev/arm_*_{iou0.2,ctr}.json`.

| Guard / tracker | DEV det ID switches | IDs/seg | frag | TTFC p90 | probe IDs/object | objects with >1 ID | probe mixed false | fallback matches |
|---|---|---|---|---|---|---|---|---|
| 1% / iou 0.3 | 68 | 1.208 | 22 | 707 | 1.415 | 19/53 | 10 | n/a |
| 1% / iou 0.2 | 67 | 1.167 | 21 | **773** | 1.415 | 19/53 | 10 | n/a |
| 1% / centre | 68 | 1.208 | 22 | 707 | 1.415 | 19/53 | 10 | 1 |
| none / iou 0.3 | 68 | 1.208 | 22 | 707 | 1.394 | 29/94 | 41 | n/a |
| none / iou 0.2 | 67 | 1.167 | 21 | 773 | 1.372 | 27/94 | 41 | n/a |
| none / centre | 68 | 1.208 | 22 | 707 | 1.351 | 26/94 | 39 | 24 |

**Does the guard interrupt association?** (`out/guard_gaps.json`) On the DEV det clip, 9 of 120 detected objects have raw hits on both
sides of 1%, and 70 of 3743 hit-frames are removed. At 0.5% this falls to 3 objects / 31 frames, and at 0.25% to 0. On the probe, 6 of
103 objects straddle 1%, and 46 lose every hit.

**Carrot #16** (existing Stage B trace, read only): surviving boxes sit at area 1.0-2.6%, many just above the line (1.01-1.4%). 6-17 raw boxes per frame are
removed, and the surviving boxes jump between different carrots of one pile. So the 0.277 IoU "miss" at 0.7 s is partly a different
carrot, not one object losing its track.

**Recommendation (not promoted):**
- Do not lower association IoU: there is no DEV benefit, and TTFC p90 rises by 66 ms.
- A centre fallback is harmless but only matters once small boxes are allowed through. Keep it as a candidate to pair with any future
  guard change.
- The real fix for the "7 IDs in 0.6 s" pattern is pile-level display: one label for a same-class cluster instead of one track per
  item. Evaluate that on fresh footage.

## 5. Synthetic probe definition (DEV-only, SYNTHETIC)

The probe is built by `ml/runs/G9/stageC/scripts/build_probe.py`:
- Single-class DEV val stills are scaled by 1/2, 1/3 and 1/4 and pasted onto DEV negatives (480x640), with a 3 px/frame drift.
- Each segment is 18 frames at 15 fps, with 6 gap frames between segments.
- There are 177 segments (4254 frames), up to 6 images per class (seed 0). There are no guava single-class stills.

Detections are cached in `/workspace/work/cv/g9c/probe/` (sandbox, not committed). The probe is a proxy: it ranks arms but cannot confirm
real-world gain.

## 6. Resolution vs training coverage (diagnostic only, not an arm)

The same G3 `best.pt` was exported raw at 640 (its training size). The export lives in the sandbox only, at
`/workspace/work/cv/g9c/det_yolo11n_g3_at640_raw.onnx`. It was run on the probe's showcase segments
(`out/probe_640_diagnostic.json`). Raw hit counts, before any guard:

| Class | Objects with ≥1 hit, 480 -> 640 | Object-frames hit, 480 -> 640 |
|---|---|---|
| carrot | 8 -> 17 of 132 | 39 -> 95 of 2376 |
| apple | 15 -> 21 of 75 | 219 -> 270 |
| banana | 15 -> 23 of 42 | 233 -> 264 |
| citrus | 10 -> 13 of 57 | 101 -> 135 |
| tomato | 8 -> 9 of 81 | 67 -> 99 |

Running at the training resolution helps, roughly doubling carrot hits, at about 1.8x the detector FLOPs (estimate, not measured). But
small carrots stay mostly undetected even at 640, so **training coverage of small, far-away and piled carrots is the main limiter**.
Next steps, all needing fresh footage and a new prereg:
- small-object training data (carrot piles at distance), or tiled / 640 inference;
- then revisit the guard together with a false-positive control, because a lower guard alone floods false tracks.

## 7. Files

- Committed:
  - `docs/cv/gauntlet/G9_stageC_prereg.md` and `docs/cv/gauntlet/G9_stageC.md`
  - `ml/runs/G9/stageC/frozen_dev_config.json`
  - `ml/runs/G9/stageC/scripts/*`: raw_vs_guard, build_probe, cache_probe, stagec_eval, summarize, guard_gaps, probe_objects,
    probe640, render_guard
  - `ml/runs/G9/stageC/dev/arm_*.json` (12 runs)
  - `ml/runs/G9/stageC/out/*.json`
- Video: `files/g9/stageC/G9_stageC_side_G3_vs_guard025_DEV.mp4` (14.8 s), a side-by-side of G3 vs the rejected 0.25% guard:
  - probe segments where the arms differ most;
  - DEV-neg frames where the lower guard shows an extra false track.
