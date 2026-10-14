# G9 Stage I: targeted recognition recovery and mobile readiness (report)

**Plan:** `G9_stageI_plan.md` (commit 4ed9e36). It was synced before any Stage I result.

**Ground rules followed:**
- No retraining, so no GPU was used.
- Stage H results and frozen configs (`FROZEN_VERIFY`, `FROZEN_OCC`) are unchanged.
- M-TEST is sealed. Nothing was promoted.
- No A/B/C grade and no grade-specific price is shown in the app.
- Branch `cv-gauntlet` only.

Every number re-computed on Stage H items is a **post-hoc diagnostic** stored under `ml/runs/G9/stageI/out/`. Nothing in
`ml/runs/G9/stageH/` was rewritten. All labels are agent or source labels, so **they are exploratory**.

## 1. Diagnosis (I1): no implementation bug; H2 fails from train/deploy domain mismatch

### Checks on the existing weights (`out/h2_audit.json`, `out/geom_scores.json`)
| Check | Result |
|---|---|
| Reproduce the Stage H H2 probabilities from the saved crops | 378/378 top-1 identical, max abs diff 5e-6 |
| ONNX vs PyTorch (`h2_mnv3s.pt`, timm mobilenetv3_small_100) | max abs prob diff **2e-6**, top-1 agrees on 378/378 |
| Output semantics | The ONNX graph ends in `Softmax`. `verify.py`/`.ts` read index 12 as a probability. No double softmax, no sigmoid |
| Class index map | Kernel `C` = `verify.py H2_CLASSES` = `verify.ts` = G3 `N` + unknown (regression test `test_class_maps_agree_everywhere`) |
| RGB vs BGR | Correct (cv2 BGR → RGB). Feeding BGR on purpose drops eval top-1 from 28 to 17/99 |
| Mean/std, range | ImageNet mean/std on /255 in both train and inference |
| Train-eval transform (PIL `Resize(256)+CenterCrop(224)`) vs the cv2 inference path | Same: top-1 28 vs 28, H2-only 13/26 vs 12/25 |
| Letterbox instead of centre crop | Eval top-1 36 vs 28, but tune H2-only correct 31 vs 38: not consistently better |
| **Crop context** (post-hoc) | See the crop-geometry table below |
| **Folder → class map in the kernel** | **Label defects:** the prefix rule mapped Fruits-360 `Mangostan` → mango and `Potato Sweet` → potato, and sent `Kumsquats` (a citrus) to unknown. None of the 5 priority classes is mislabelled. Fixed for future kernels in `ml/eval/h2_labels.py` (+ test). The Stage H kernels are left as they are |

**Crop geometry (post-hoc):**

| Variant | Tune H2-only correct / wrong | Eval H2-only correct / wrong | Eval P-a correct / wrong | Eval negatives accepted |
|---|---|---|---|---|
| Stage H crop (pad 0.08 → short 256 → centre 224) | 38 / 10 | 12 / 25 | 9 / 0 | 0/77 |
| Square context crop (sq15) | 37 / 10 | 17 / 14 | 11 / 0 | 0/77 |
| tap_roi grown to 0.6 + sq15 | 35 / 8 | 19 / 11 | 11 / 0 | 0/77 |
| Whole image (upper bound, not a crop) | 34 / 10 | 29 / 12 | 20 / 0 | 0/77 |

- On eval, crops that fell back to tap_roi (a 0.35-of-frame patch on close-ups where G3 found nothing) score top-1 7/36, rising to
  16/36 with the grown ROI.
- **The selection on tune keeps the Stage H crop**, so no geometry change is adopted. The eval gain is not confirmed out of sample.

### Why H2 rejects 90 supported items and is wrong on 25 (eval)
- **It collapses to "unknown":** the top class is unknown for 42/99 supported eval items. Only 28/99 are top-1 correct.
- **"potato" acts as an attractor:** it is predicted for 17 supported items and 20 negatives.
- **Its confidence is low even when it is right:** mean top probability 0.45 when correct, 0.33 when wrong.
- **The same failure appears on new sources.** The Stage I candidates are new, independent, licensed sources, including real phone captures
  (`out/i_explore.json`, source labels, exploratory). H2 top-1 on the Stage H crop:

  | Source | H2 top-1 |
  |---|---|
  | Commons | 50/229 |
  | FruitNet phone photos | 28/141 |
  | Mendeley carrot phone photos | **0/30** (19/30 on the whole image) |
  | Mendeley tomato phone photos | 31/62 |
  | **Citrus, all sources** | **5/80** |

  So the problem is not specific to the Stage H eval set.
- **Mechanism (inferred from the training report):**
  - 60% of draws were Kaggle studio/lab images: Fruits-360 at 100 px on white with background swap, Fruit Recognition trays, and the
    Vegetable Image Dataset.
  - Real photos were thin: Commons has 1-46 per class (citrus 5, carrot 5, potato 1).
  - The only class with many diverse real photos was `unknown` (89 Commons negatives). The model learnt "real-photo look → unknown"
    rather than the produce.
  - H-val (0.68 balanced accuracy) was measured on whole images and doubled as the epoch-selection set, so it overstated close-up
    performance.

**Conclusion:**
- **Not a bug:** index map, colour order, normalisation, resize, export and softmax all check out.
- **The errors are domain mismatch**, made somewhat worse by tap_roi patch crops.
- **Loosening H2's reject threshold would not help:** the true class is in H2's top 2 for only 45/99 eval items.

## 2. Code changes (minimal; no Stage H behaviour changed)
- `ml/eval/occlusion.py`:
  - Added `targeted_cues` (sideTouch, skinFrac, specFrac, hullGap) and `targeted_reasons`. These are additive and can only add rejections.
  - `FROZEN_OCC` and `occlusion_reasons` are unchanged.
- `native/src/cv/pipeline/verify.ts`: added the `targetedReasons` / `DEFAULT_TARGETED` mirror. No threshold is frozen.
- `ml/eval/camera_io.py` + `native/src/cv/pipeline/camera.ts` (new, pure arithmetic, no dependencies):
  - preview tap → analysis frame (rotation, mirroring, cover/letterbox) → full-resolution still;
  - `identityCrop` (`stageH` default; `square` is a candidate only);
  - `h2Input` (with integer box pre-reduction for downscales);
  - `checkModelIO`;
  - `stillCropPlan`.
- `ml/eval/h2_labels.py`: corrected Fruits-360 folder map, for future kernels only.
- `ml/eval/fixtures/camera_parity.json` and the device parity bundle `ml/runs/G9/stageI/device_parity/` (12 crops + expected
  probabilities).
- Scripts: `ml/runs/G9/stageI/scripts/` (audit, geometry, collection, leak audit, exploratory run, review sheets, occlusion benchmark,
  fixtures). Device scripts: `native/scripts/g9i-device-check.{ps1,sh}`.
- No dependency was added to `native/package.json`.

## 3. Tests
- **TS: 122/122** (`npm test`). Stage H had 114; Stage I adds `cvCamera.test.ts` (8 tests: mapping, still plan, crops, H2 tensor
  parity, model I/O, targeted reasons). `tsc --noEmit -p src/cv/tsconfig.json` is clean.
- **Python: 58/58** across `ml/eval/test_verify.py`, `test_closeup.py`, `test_camera_io.py` (new, 13 tests), `ml/prices/tests` and
  `ml/grading/tests`. The new tests include the audit regression locks: class maps, the ONNX Softmax / I/O contract, and the
  look-alike folder mapping.

## 4. Metrics

| Metric | Value | Source |
|---|---|---|
| Genuine-item acceptance (H-final, Stage H frozen eval) | 9/99 (0.09), item-level 9/64 (0.14). Unchanged; Stage I does not alter the policy | `stageH/out/identity.json` |
| Class accuracy (H2 top-1, eval supported) | 28/99. Priority classes 18/60. Confusion in `h2_audit.json` | post-hoc |
| Post-hoc, crop geometry (not adopted) | P-a 11/99, H2-only 19 correct / 11 wrong | `geom_scores.json` |
| Wrong-ID acceptance | H-final 0/99 (Stage H). On the Stage I candidates, exploratory: 6/462 supported verified wrong (35/462 verified correct) | `i_explore.json` |
| Unsupported / printed / cut acceptance | 0/77 (Stage H). Stage I Commons negatives, exploratory: 3/194 accepted (unsupported produce) | |
| Abstention | 0.91 (Stage H eval) | |
| Occlusion leakage, full pipeline (CU-check) | 24/990 = 2.4%. **trunc25_inner 10.9% unchanged.** Stage H reported 23/990: GrabCut is not run-order deterministic, and only 1318/2332 crops reproduced the stored cues exactly | `occ_stageI.json` |
| Occlusion leakage, rule only (no identity) | 278/990 = 28.1%, clean false reject 0.30 | |
| Latency, mask step only (192 px, sandbox CPU) | GrabCut p50 134 / p95 340 ms; 64 px GrabCut p50 7 / p95 14 ms; saturation 0.5 ms; Lab 1.5 ms | |
| Latency, close-up path | Stage H measured p95 1136 ms (GrabCut p95 556 ms). Swapping in 64 px GrabCut is **estimated** at about 600 ms p95. Not measured end to end, not a phone figure | |

**Occlusion benchmark** (I3; selection on CU-tune, CU-check reported once):

| Mask | Tune leak, rule only | Check leak, rule only | Check full-pipeline leak | Clean false reject (tune / check) | trunc25_inner (full) | Verdict |
|---|---|---|---|---|---|---|
| GrabCut (Stage H) | 301/918 | 278/990 | 24/990 | 0.18 / 0.30 | 10.9% | baseline |
| GrabCut at 64 px | 286/918 | 276/990 | 31/990 | 0.16 / 0.33 | 10.9% | passes the tune rule (no worse) and is ~20× faster; **check full-pipeline +7 leaks, so not adopted yet** |
| Saturation Otsu | 159/918 | 194/990 | 21/990 | **0.63** / 0.63 | 5.5% | rejected (clean false reject) |
| Lab border distance | 130/918 | 153/990 | 13/990 | **0.63** / 0.74 | 0% | rejected (rejects almost everything clean) |

- **Targeted cues:** no threshold reduced tune leakage while keeping clean false reject ≤ 0.20, so nothing was frozen. On their own
  they separate weakly (AUC, clean vs targeted occluder):
  - sideTouch vs trunc25_inner: 0.59 / 0.59;
  - skinFrac vs hands: 0.66-0.73;
  - specFrac vs bags: 0.61-0.68;
  - hullGap vs overlap: 0.60-0.72.
- **Why inner truncation is not detectable from geometry:** at pad 0.08 a clean tight crop touches the crop border just as much as a
  truncated one.
- **Rejection policy unchanged.**

## 5. Data plan (I2): `G9_stageI_data_plan.md`, `G9_stageI_human_labeling_protocol.md`
- **Collected:** 742 licensed candidates from Commons per-file CC/PD, FruitNet CC BY 4.0 (phone), Mendeley carrot CC BY 4.0 (Realme
  phone) and Mendeley tomato CC BY 4.0 (Redmi phone).
- **Leak audit:** 42 pHash leaks dropped against every earlier pool (including M-DEV/M-TEST hashes). 656 near-duplicate groups.
- **Split:** I-dev / I-eval-A by Commons uploader (177 uploaders). External phone datasets go whole to I-eval-B.
- **Review material:** 33 shuffled contact sheets, a blind annotator CSV and a separate adjudicator key.
- **Protocol:** 2 annotators + adjudicator. Gate before any accuracy claim: ≥ 100 adjudicated supported close-ups (≥ 20 per priority
  class) + ≥ 60 negatives, and κ(class) ≥ 0.85.
- **Gap:** the Commons negative queries are noisy (maps, illustrations), so the final yield depends on the human review.

## 6. Android readiness (I4): `G9_stageI_android_test.md`
- The integration layer and parity tests pass in the sandbox.
- Device steps A1-A9, with scripts that run them and summarise the logs. The dependency set is the one reviewed in Stage H.
- **Not run on a device. No FPS or phone-latency claim.**
- **Measured caveat:** the device resize path matches the Stage H cv2 path's H2 decision on 370/378 crops, so on-device parity (A3,
  ≤ 0.02) must pass before any phone identity number counts.
- The H2 `.pte` (ExecuTorch) export has not been done. The ONNX fallback runtime runs the same file.

## 7. Fine-tuning (I5)
None run. The audit justifies one (domain mismatch, not a bug), so a separate prereg is written, **not run**:
`G9_stageI_finetune_prereg.md` ("H3").
- Same 13-way head (no relabelling).
- 5-class weighting.
- Training only from sources disjoint from I-eval-A/B.
- Crops made the way the pipeline crops.
- Real-photo negatives balanced against supported classes.
- Blocked until the human set exists.

## 8. Recommended next experiment
1. **Run the human labelling first** (no GPU): the two annotators on I-dev + I-eval-A/B, then adjudication and the agreement report.
2. Then **H3 per its prereg**: one free-Kaggle attempt, evaluated once on human-labelled I-eval-A and I-eval-B.
3. In the same evaluation, test the two candidates found here without freezing them now:
   - the `square` identity crop with the tap_roi grown to 0.6;
   - GrabCut at 64 px (latency).
4. **On a phone, run A2-A6** (model load, parity, coordinate mapping) before trusting any device number.

## Files
- **Docs:** `G9_stageI_plan.md`, this report, `G9_stageI_data_plan.md`, `G9_stageI_human_labeling_protocol.md`,
  `G9_stageI_android_test.md`, `G9_stageI_finetune_prereg.md`.
- **Results** (`ml/runs/G9/stageI/out/`):
  - `h2_audit.json` (+ `h2_audit_raw.jsonl`, `h2_audit_ctx.jsonl`)
  - `geom.jsonl`, `geom_scores.json`
  - `i_leak_split.json`, `i_explore.json(l)`
  - `occ_bench.jsonl`, `occ_stageI.json`, `occ_cue_auc.json`
  - `camera_h2_agreement.json`, `review_ids.json`
- **Review:** `ml/runs/G9/stageI/review_annotator_blind.csv`, `review_adjudicator_key.csv`. Sheets are not committed (binary) and are
  copied to the project files.
