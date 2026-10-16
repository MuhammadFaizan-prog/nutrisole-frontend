# G10b: offline scene-guard sweep + G3 / henningheyen YOLOv8m complementarity (REPORT-ONLY)

Written 2026-10-16 (PKT). Brief: `files/g10/g10b/G10b_brief_guard_ensemble.md` (Option A, offline only). Branch `cv-gauntlet` (PR #1) only.

**Evidence level of every number below: EXPLORATORY.** All labels are dataset- or agent-curated (det_v3, Stage H triage).
**Independently (human-)verified results: 0.** Everything ran on the sandbox CPU (2 vCPU aarch64, shared), not a phone.
DEV/VAL data only; M-TEST was not opened; no locked test split was run.

## Answers

| | Question | Answer (exploratory) |
|---|---|---|
| **A** | Would loosening the scene guard help? | **Not for what the app does (tap → identify).** At 0.5 % / 0.25 % the detector finds +149 / +221 more correct boxes on dev val, but it also gets +101 / +154 extra false positives. 231 of the 232 recovered boxes are small, far-away items in LVIS crowd scenes. **None of them is big enough for the 96 px close-up gate** (median about 40 px). Tap identity does not change: G3+H2 (P-a) is the same at every guard (30 correct / 1 wrong / 4 negatives accepted of 191 / 181), and wide-only ID loses 2 correct and gains 1 accepted negative. **Also: the device app does not apply the guard at all** (see A0), so the "28 %" figure describes the Python eval pipeline and the `postprocess.ts` spec, not the APK. |
| **B** | Does a G3 + YOLOv8m ensemble add value? | **Not deployable value. Stop criterion met.** Fusion looks strong on the dev val overall (mAP50 0.401 → 0.555). But that gain sits almost entirely on the LVIS half, which is **v8m's own checkpoint-selection set** and the same annotation source it was trained on. On the only independent detection domain (OIV7, 57 images), fusion is *worse* than G3: mAP50 0.502 → 0.482, correct boxes at the operating point 75 → 61, false positives 25 → 73. On the independent Stage H close-up items, the oracle adds 22/191 correct wide IDs, but v8m makes 50 % more wrong names (36 vs 24). v8m costs 639 ms p50 per frame vs G3's 45 ms (G3+v8m 716 / 1478 ms p50/p95; 391 MB vs 137 MB peak RSS), so it cannot run in real time on a phone. |
| **C** | Is G3 still the best option? | **Yes.** G3@480 + H2 P-a (frozen) stays the best *deployable* pipeline on this evidence. Nothing here justifies a guard change, a second model or a threshold change. |

**Smallest justified next step:** change no code. (1) Ask the J8 owner, as a user decision, whether the live overlay is *meant* to run
without `sceneGuard`. The spec says 1 %, the device path never calls it. Document it either way. (2) Once human-labelled phone
captures exist (C rank 1 in G10), replay them through `g10b_ident.py` at guards 0 and 0.01. The tooling is ready and nothing needs
building. Do not build a G3+v8m ensemble or a v8m teacher on this evidence.

## A0. Audit finding: the device does not apply the scene guard
- `native/src/cv/pipeline/postprocess.ts` defines `sceneGuard` with `DEFAULT_SCENE_GUARD = { maxSameClass: 0, minAreaFrac: 0.01 }`, mirrored by `ml/eval/scene_guard.py`.
- On remote `cv-gauntlet-device` **`fd64b24`** (read via the contents API, read-only), the files `native/src/cv/device/debugPipeline.ts`
  (blob 52414f9b), `native/src/cv/device/live.ts` (e0ecbf59) and `native/responsive/CvDebugScan.tsx` (638a8af7) import only
  `decodeRawWithNms` (decode floor `DET_DECODE_FLOOR = 0.25`). **`sceneGuard` / `minAreaFrac` appear nowhere in them.** The only other
  reference is `tests/cvSceneGuard.test.ts`. The local J8 worktree `/workspace/work/j8/wt` (`6e0d77f`) is the same; it was not modified.
- Result: the phone runs with **effectively guard = 0**. Naming still needs idMinScore 0.5 and 3 hits, plus H2 P-a for the close-up.
  The "guard 0" rows below are therefore the closest thing to device behaviour.
- Nothing was changed: J8, PR #2 and `cv-gauntlet-device` are owned elsewhere. This needs the user's decision.

## Phase 1: scene-guard sweep (G3 frozen, every other parameter frozen)

### 1a. Detection on det_v3 val (402) + negdev (110)
Setup: G3 `best.pt` (29cc5212), imgsz 480, Ultralytics predict with single-label NMS 0.7, rubric score ≥ 0.35, `scene_guard.py` maxSameClass 0.
Matching is class-aware, IoU ≥ 0.5, greedy by score. Unmatched boxes are split four ways:
- **duplicate:** a second box on a GT that is already matched.
- **wrong-class:** IoU ≥ 0.5 with a supported GT of another class.
- **unsupported:** IoU ≥ 0.5 with an *original* LVIS box of one of the 49 dropped produce classes (`g1data/lvis/labels/val`).
- **background:** everything else. LVIS is federated, so some of these are unlabelled real produce, and FP is overstated.

The table reproduces G10 D3 exactly (593/243/1, 742/344/2, 814/397/2, 825/433/3).

| minAreaFrac | TP | recall | FP total | background | wrong-class | duplicate | unsupported | precision | negdev imgs / boxes |
|---|---|---|---|---|---|---|---|---|---|
| **0.01 (spec)** | 593 | 0.293 | 243 | 165 | 31 | 31 | 16 | 0.709 | 1 / 1 |
| 0.005 | 742 (+149) | 0.367 | 344 (+101) | 235 (+70) | 44 (+13) | 39 (+8) | 26 (+10) | 0.683 | 2 / 2 |
| 0.0025 | 814 (+221) | 0.403 | 397 (+154) | 269 (+104) | 54 (+23) | 45 (+14) | 29 (+13) | 0.672 | 2 / 2 |
| 0 (= device) | 825 (+232) | 0.408 | 433 (+190) | 296 (+131) | 56 (+25) | 47 (+16) | 34 (+18) | 0.656 | 3 / 3 |

- **Precision of the marginal band** (the boxes added below 1 %): 149/250 = 0.60 at 0.5 %; 221/375 = 0.59 at 0.25 %. Above 1 % it is 0.71.
- **Domain:** of the 232 recovered TPs, 231 are LVIS and 1 is OIV7. Of the 190 added FPs, 180 are LVIS, 7 OIV7 and 1 negative.
- **Recovered TPs per class** (0.5 % / 0.25 %):
  - banana 68 / 100, tomato 23 / 41, carrot 22 / 34, apple 19 / 23, citrus 15 / 21, lemon_lime 1 / 1, cucumber 1 / 1.
  - mango, pomegranate, capsicum and potato: 0.
- **Added wrong-class pairs at 0.5 %** (predicted <- truth): tomato<-carrot 4, banana<-apple 3, apple<-citrus 2, citrus<-apple 1,
  carrot<-potato 1, carrot<-capsicum 1, apple<-pomegranate 1.
- **Unsupported produce accepted:** at 0.5 % this is mostly apple<-grape (8 of 10). At 0 it is 18 added (apple<-grape 10,
  tomato<-watermelon/strawberry/cherry 5, others).
- **negdev added:** 1 banana box at 0.5 % / 0.25 %; banana + apple at 0.
- **Size distribution of the recovered TPs** (area as a fraction of the frame):

  | guard | 0.1-0.25 % | 0.25-0.5 % | 0.5-1 % |
  |---|---|---|---|
  | 0.5 % | 0 | 0 | 149 |
  | 0.25 % | 0 | 73 | 148 |
  | 0 | 10 | 73 | 148 |

  At 0 there is 1 more below 0.1 %. Shorter side at 480 scale: 12-24 px 25 and 24-48 px 124 (at 0.5 %).
  Full-resolution side √area: median 42.9 px (0.5 %) and 39.3 px (0); **0 of 232 reach the 96 px close-up gate.**
- **Scores:** recovered TPs median 0.64, added FPs median 0.47. At ≥ 0.5 (the naming score), 0.5 % recovers 113 TPs and adds 39 FPs.
- **GT share below 1 % by class:** banana 63 %, tomato 56 %, lemon_lime 58 %, carrot 52 %, potato 45 %, apple 43 %, capsicum 41 %,
  citrus 34 %, cucumber 32 %, mango 9 %, pomegranate 6 %.

### 1b. End-to-end identity (Stage H items; separate from detection and from grading)
Items: the 378 Stage H identity items, all DEV:
- 191 supported items/piles;
- 181 negatives (unsupported, printed, cut);
- 6 greyscale.

Stage H tune and eval subsets are both reported. Nothing was tuned on either.

Setup:
- Models: G3 ONNX (c6fcb32a) at 480, then guard, tapped box (smallest box containing the tap), then DEFAULT_ID (0.5 score, 3 hits).
  Then H2 v2 (20898d7c) on the 8 %-padded crop, then FROZEN_VERIFY P-a (tau 0.4).
- **Parity:** guard 1 %, floor 0.35, 1-frame reproduces Stage H eval exactly (H0 46 correct / 10 wrong / 13 negatives of 77;
  P-a 9 / 0 / 0 of 99 / 77).
- Two frame policies:
  - **1-frame** = the Stage H convention (one still, 3 hits assumed).
  - **3-frame** = `burstWide` over 2 deterministic jitters plus the still. The jitters are shift ±1.5 %, scale 0.98/1.02 and
    brightness 0.92/1.08; this is agent-designed, not a Stage H set.
- Grading is OFF and was not run.

Cells read pooled correct / wrong / negatives accepted (of 191 / 191 / 181).

| decode floor, policy | arm | 1 % | 0.5 % | 0.25 % | 0 |
|---|---|---|---|---|---|
| 0.35, 1-frame | H0 wide-only | 86 / 24 / 34 | 84 / 24 / 34 | 84 / 24 / 35 | 84 / 24 / 35 |
| 0.35, 1-frame | **P-a (G3+H2 agree)** | **30 / 1 / 4** | 30 / 1 / 4 | 30 / 1 / 4 | 30 / 1 / 4 |
| 0.35, 3-frame | H0 | 70 / 20 / 19 | 70 / 20 / 19 | 70 / 20 / 20 | 70 / 20 / 20 |
| 0.35, 3-frame | P-a | 27 / 1 / 1 | 27 / 1 / 1 | 27 / 1 / 1 | 27 / 1 / 1 |
| 0.25 (device floor), 1-frame | H0 | 81 / 23 / 29 | 80 / 23 / 29 | 80 / 23 / 30 | 80 / 23 / 30 |
| 0.25, 1-frame | P-a | 27 / 1 / 2 | 27 / 1 / 2 | 27 / 1 / 2 | 27 / 1 / 2 |
| 0.25, 3-frame | P-a | 24 / 1 / 1 | 24 / 1 / 1 | 24 / 1 / 1 | 24 / 1 / 1 |

Stage H eval subset only, P-a: 9 / 0 / 0 at every guard (8 / 0 / 0 with 3 frames).

- **The guard does not move the verified identity at all.** The tapped close-up items are much larger than 1 % of the frame.
- Wide-only ID gets slightly *worse* below 1 %:
  - 2 supported items go from correct to unable, because the tap now lands in a smaller part-box that fails the 0.5 score.
  - 1 negative becomes named.
- **Side finding (exploratory, not acted on):** the device's lower decode floor of 0.25 costs 3 P-a correct (30 → 27) through the same
  smallest-box-at-the-tap mechanism.

## Phase 2: G3 + henningheyen YOLOv8m complementarity

### 2a. Compatibility checks (done before any fusion)
| check | result |
|---|---|
| Class mapping | v8m ONNX/pt names (63) are **identical** to `g1data/lvis/data.yaml`, the source NutriSole's LVIS labels were built from via `ml/data/class_map.csv`. 13 LVIS names map to 9 NutriSole classes (orange/mandarin/clementine → citrus; lemon/lime → lemon_lime; Tomato/tomato → tomato; banana, apple, potato, cucumber, carrot, bell pepper → capsicum). **No mango, guava or pomegranate.** The 49 other classes are dropped (unsupported produce). |
| Label definitions | Identical on the LVIS half of val by construction (same annotations). They differ on OIV7: v8m names OIV7 bell peppers carrot/tomato (wrong-class carrot<-capsicum 12, tomato<-capsicum 8 after fusion), and "citrus" in NutriSole includes kinnow/malta, which LVIS splits into orange/mandarin. |
| Licence | Ultralytics **AGPL-3.0** is stamped in the checkpoint and ONNX metadata. Repo MIT, dataset card MIT/Apache-2.0, LVIS annotations CC BY 4.0, COCO/Flickr images per-image licences (G10 C1). The same AGPL obligation already applies to G3. |
| Output format | v8m `output0` (1, 67, 8400) = 4 box + 63 class scores, no objectness, 640 input. G3 (1, 16, 4725) = 4 + 12, 480 input. Both are Ultralytics Detect heads, decoded identically. |
| Preprocessing | Both are Ultralytics letterbox (pad 114), RGB, /255, no mean/std. Only the input size differs (640 vs 480); each model ran at its own size. |
| Data leakage | **The LVIS half of det_v3 val is the first half of henningheyen's own HF validation set, which v8m used for checkpoint selection.** v8m numbers on it are optimistic by construction. OIV7 (57 images) and the Stage H Commons items are independent of v8m. |

### 2b. Detection results (det_v3 val 402, negdev 110)
Fusion (the one documented deployable method): **class-wise Weighted Boxes Fusion**.
- Method: Solovyev et al.; ZFTurbo `conf_type='avg'`.
- Inputs: iou_thr 0.55, weights 1:1, model inputs at score ≥ 0.01.
- Scoring: cluster score = mean × min(T, 2)/2, so a box seen by only one model is halved.
- Mango, guava and pomegranate pass through from G3 unchanged; v8m's unsupported classes are dropped.

Union + NMS 0.7 is shown only as a sensitivity row. The operating point stays at the frozen 0.35 (not re-tuned).

| model | mAP50 val (11 cls) | mAP50 LVIS 295 | **mAP50 OIV7 57** | op 0.35 + 1 % guard: TP / FP / wrong-class | OIV7 TP / FP | negdev imgs (1 % / no guard) |
|---|---|---|---|---|---|---|
| **G3 alone** | 0.401 | 0.310 | **0.502** | 593 / 243 / 31 | **75 / 25** | 1 / 3 |
| v8m alone (9 mapped) | 0.433 | 0.593 | 0.150 | 682 / 266 / 48 | 23 / 127 | 3 / 13 (41 boxes) |
| **WBF G3+v8m** | 0.555 | 0.574 | 0.482 | 633 / 167 / 51 | 61 / 73 | 1 / 4 (7 boxes) |
| union + NMS (sensitivity) | 0.549 | 0.574 | 0.382 | 772 / 498 / 72 | 77 / 150 | 4 / 15 |

Per-class AP50:

| class | G3, full val | WBF, full val | G3, OIV7 | WBF, OIV7 |
|---|---|---|---|---|
| banana | 0.51 | 0.75 | n/a | n/a |
| apple | 0.57 | 0.77 | n/a | n/a |
| mango | 0.69 | 0.68 | 0.70 | 0.69 |
| citrus | 0.74 | 0.83 | 0.995 | 0.995 |
| pomegranate | 0.43 | 0.42 | 0.52 | 0.505 |
| lemon_lime | 0.08 | 0.64 | n/a | n/a |
| tomato | 0.44 | 0.56 | n/a | n/a |
| potato | 0.00 | 0.03 | n/a | n/a |
| cucumber | 0.27 | 0.40 | 0.41 | 0.47 |
| carrot | 0.40 | 0.53 | 0.44 | 0.31 |
| capsicum | 0.27 | 0.48 | 0.46 | 0.40 |

At no guard (the device setting): G3 825 TP / 433 FP, WBF 1009 / 293 (wrong-class 56 → 64), v8m 1237 / 633.

**Oracle upper bound (NOT deployable):** a GT counts if either model hits it at 0.35; FPs are ignored.
- **1 % guard:** G3 593, v8m-only +207, G3-only 118, oracle 800 (recall 0.293 → 0.396).
  - v8m-only by domain: **202 LVIS / 5 OIV7**. G3-only: 61 LVIS / 57 OIV7.
  - v8m-only by class: carrot 48, banana 46, lemon_lime 25, tomato 23, apple 21, citrus 18, cucumber 14, capsicum 10, potato 2.
- **No guard:** G3 825, oracle 1327 (v8m-only 502: 488 LVIS / 14 OIV7).

### 2c. Identity-level complementarity (Stage H items, independent of v8m; wide ID only, single still, 1 % guard)
| | correct (of 191 supported) | wrong | negatives named (of 181) |
|---|---|---|---|
| G3 wide | 86 | 24 | 34 |
| v8m wide (mapped classes) | 89 | **36** | 34 |
| oracle (either right; NOT deployable) | 108 (+22) | n/a | n/a |
| both must agree (a deployable vote) | 67 | 2 | 12 |
| reference: G3 + H2 P-a (frozen) | 30 | 1 | 4 |

- Of the 22 v8m-only correct items, only **6** are items where G3 named the wrong class; the other 16 are G3 abstentions.
- v8m's explicit "unsupported produce" classes vetoed **0** of G3's 34 negative namings.

### 2d. Latency and memory (MEASURED here, sandbox CPU, ORT CPU EP, 2 threads, 40 runs, fresh process each)
| config | model ms p50 / p95 | peak RSS | ONNX size |
|---|---|---|---|
| G3 @480 | **45.0 / 54.7** | 137 MB | 10.6 MB |
| v8m @640 | 639 / 1288 | 348 MB | 103.8 MB |
| G3 + v8m (sequential per frame) | 716 / 1478 | 391 MB | 114.4 MB |
| WBF step only (inputs ≥ 0.35 / ≥ 0.01) | 0.08 / 1.0 · 0.7 / 8.0 | n/a | n/a |

J8's live loop targets 3-8 updates/s (125-333 ms per frame). The ensemble alone is about 2-6x over that budget (716 ms p50) on this CPU, before
any phone thermal limits.

### Why Phase 2 stopped here
- The stop criteria in the brief are met: on data independent of v8m, the gain is negligible or negative, and mobile cost is unrealistic.
- No further fusion variants were tried.
- No threshold was re-tuned for the fused scores. Re-tuning would be threshold selection on dev and is not authorised.

## What was frozen / not touched
- No change to the models: G3 (c6fcb32a / best.pt 29cc5212), H2 (20898d7c) and E224 were only read, with hashes checked.
- No change to `FROZEN_VERIFY`, `DEFAULT_ID`, `DEFAULT_SCENE_GUARD` or any threshold.
- No training, distillation, dataset mixing or quantisation.
- No product or app code changed.
- Not opened: M-TEST and the locked test splits.
- Not touched: J8 / `cv-gauntlet-device` (read-only API reads of `fd64b24`), PR #2, `main`, glucose PR #3.
- Nothing looped more than twice. One foreground run hit the 120 s tool limit and was relaunched once in the background; no other retries.

## Files
- Scripts, all new and small, reusing `g10_ext_bench.py` (`match`, `box_iou`, `MAPS`), `size_buckets.gt_of`, `scene_guard.py`,
  `closeup.py`, `verify.py`, Ultralytics `ap_per_class`. They live in `ml/runs/G10b/scripts/`:
  - `g10b_cache.py`: one predict pass per model and image;
  - `g10b_analyze.py`: Phase 1 detection plus Phase 2 mAP, operating point, WBF and oracle;
  - `g10b_ident.py` and `g10b_ident_table.py`: identity, guard × floor × frame policy, and v8m identity complementarity;
  - `g10b_latmem.py`;
  - `g10b_fusion_time.py`;
  - the `run_*.sh` chains.
- Results in `ml/runs/G10b/`: `analysis.json`, `ident_guard.json` (per-item), `ident_table.json`, `latmem_{G3,v8m,G3_v8m}.json`,
  `fusion_time.json`, `g10b_summary.json`.
- Sandbox only, not committed: prediction caches `/workspace/work/cv/g10b/cache/*.pkl` (3 MB) and logs `/workspace/work/cv/g10b/logs/`.
- Commit: see `files/g10/g10b/G10b_commit_sha.txt`.
