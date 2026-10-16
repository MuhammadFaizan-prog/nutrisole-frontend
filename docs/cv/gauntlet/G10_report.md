# G10: CV improvement audit, free external model research and fair benchmark

Written 2026-10-16 (PKT), branch `cv-gauntlet` (PR #1) only. Brief: `files/g10/G10_master_prompt_cv_improvement.md` plus the user's
02:59 PKT additions (screen on dev/validation splits only, M-TEST sealed, per-model availability / licence / classes / per-class
benchmark vs G3 / sandbox latency / size / ONNX / verdict, ranked recommendation, no automatic integration).

**Bottom line.** No external checkpoint is a genuine improvement over G3 that NutriSole can ship. G3 (`c6fcb32a`), E224 (`c51d21994`)
and H2 (`20898d7c`) stay unchanged; no threshold, policy or user-facing code was changed; nothing was trained; M-TEST was not opened;
`main`, PR #2 / `cv-gauntlet-device` and PR #3 were not touched. One candidate (henningheyen YOLOv8m) beats G3 on the LVIS part of
the dev split but loses badly off its training domain, has 4x the negative false alarms, is 10x larger and ~15x slower on CPU, and is
AGPL-3.0, so it is at most a research reference. G3 inference at 640 instead of 480 gains +0.02 mAP50 on dev, but the gain is on
small objects that the shipped 1 % scene guard drops anyway, so with the guard it buys nothing and costs +73 % CPU latency.

**Evidence levels used below.** MEASURED = run here, sandbox CPU (2 vCPU aarch64, shared, not a phone). PRE-EXISTING = earlier
measurement quoted from the repo. PUBLISHED = the author's claim, not reproduced. UNVERIFIED = not checked. Every label set used is
dataset- or agent-curated: **0 human-verified labels exist**, so every accuracy number here is exploratory.

## A. Audit (Phase 1, read-only)

### A1. Repo state
- Local clone `/workspace/work/nutrisole`, branch `master` = remote `cv-gauntlet` (local `25cf932` == remote `0116206`, synced in J6).
  Untracked G7/G8 artefacts in the working tree were left alone (not added).
- `cv-gauntlet-device` (PR #2): latest remote commit `0b4cb2a` (J7 build fix 2, 2026-10-16 01:48 PKT); local worktree
  `/workspace/work/j8/wt` at `4bc71cf` (tree-identical). **No J8 commit exists on the remote yet.** Inspected read-only with `git show`.
- `main` = `0bac361` (untouched).

### A2. Models (sha256 re-verified before any test)
| model | file | sha256 | bytes | where |
|---|---|---|---|---|
| G3 detector, YOLO11n trained 640, exported 480 raw (1,16,4725) | `det_yolo11n_640_raw.onnx` | c6fcb32a5fb2f51b… | 10,600,677 | `/workspace/work/cv/g3models/k11_480/`; source `best.pt` 29cc5212… |
| E224 freshness classifier | `E_224_e15_b64_sgd01.onnx` | c51d21994444d2a5… | 6,161,022 | `/workspace/work/cv/g3models/cls/` |
| H2 MobileNetV3-S verifier, 13 out | `h2_mnv3s.onnx` | 20898d7cdfc1f058… | 6,133,032 | `/workspace/work/g9h/h2v2/`, `files/g9/stageH/` |
All three match `native/src/cv/device/models.ts` (`DEVICE_MODELS`) and `NutriSole_G9J5_device_models.zip`.

### A3. Inference flow and files (device branch `4bc71cf`)
- `native/responsive/CvDebugScan.tsx`: VisionCamera photo output; **tap -> `BURST` (= `DEFAULT_ID.idMinHits` = 3) sequential
  `capturePhoto()` stills** -> `runDebugPipeline`. Runtime `onnxruntime-react-native` (`InferenceSession`), CPU EP defaults.
- `native/src/cv/device/debugPipeline.ts`: per still G3 at 480 letterbox -> `decodeRawWithNms` (floor 0.25, N_ANCHORS 4725 hard-coded)
  -> tapped detection -> `burstWide` (modal class over the 3 stills, `idPolicy` idMinScore 0.5, idMinHits 3) -> tap crop on the last
  still -> H2 -> `verifyIdentity(FROZEN_VERIFY P-a tau 0.4 margin 0 maxUnknown 0.5)` -> `stageHDecision` (grades disabled) -> `fromStageH`
  -> `DisplayResult` (title only; reason `quality_gate_not_run_in_debug`).
- `native/src/cv/device/modelSource.ts` + `models.ts`: bundled QA-APK asset first, adb push second; size + sha256 must match or
  "Models not loaded"; no mock fallback. `ModelKey` is only `h2 | g3_det`.
- `native/src/cv/pipeline/`: `postprocess.ts` (`sceneGuard`, `DEFAULT_SCENE_GUARD = { maxSameClass: 0, minAreaFrac: 0.01 }`),
  `closeup.ts` (96 px gate, 3 frames, blur/brightness/blockiness), `verify.ts` (`FROZEN_VERIFY`), `tracker.ts`/`temporal.ts`/`bytetrack.ts`,
  `camera.ts` (`MODEL_IO`, rotation/mirror/letterbox), `cropmap.ts`, `result.ts` (Not graded / Unable to identify / Poor capture).
- `native/src/cv/domainMap.ts` (90 lines): citrus -> `citrus_orange`; `lemon_lime` maps to no domain id (never orange); H2 unknown -> null.
- Python mirrors: `ml/eval/scene_guard.py`, `verify.py`, `camera_io.py`, `closeup.py`, `tracker.py` with parity fixtures.

### A4. J8 status (read-only)
At remote `0b4cb2a` the debug screen does **not** process live frames: it takes 3 still photos per tap (`capturePhoto`), and the
"3 consistent sightings" are those 3 stills. There is no frame processor / `useFrameProcessor`. J8 (live-frame inference) is
in progress in another agent's worktree and has not been pushed; it was not inspected beyond the branch ref.

### A5. Tests run before any G10 change (sandbox)
| suite | command | result |
|---|---|---|
| native | `cd native && node --experimental-strip-types --test tests/*.test.ts` | 161/161 pass |
| ML eval/grading/prices | `python -m pytest -q ml/eval ml/grading ml/prices` | 66 passed |
| ML stage J + autolabel | `python -m pytest -q ml/runs/G9/stageJ/scripts ml/autolabel` | 86 passed |
| web domain | `node --experimental-strip-types --test tests/domain.test.ts` | 5/5 |
| expansion | `node --test tests/expansion.test.mjs` | 8/8 |
| runtime lock | `node scripts/check-mobile-runtime.mjs` | passed (28 protected files) |
(J6 reported "ML 161/161"; the two pytest invocations above collect 152; the other 9 live outside these paths. 0 failures.)

### A6. Inconsistencies between the brief and the repo
1. **Class suppression (>6 instances) is OFF.** The brief says "class suppression when more than six instances appear"; the code
   default since G4 is `maxSameClass: 0` (rule 2 disabled). Only the 1 % area rule is active.
2. **E224 is not loaded on the phone.** It is in the device ZIP and in `DEVICE_MODELS.condition`, but `ModelKey` / the QA APK only
   load `h2` and `g3_det`; grading is blocked by design, so E224 never runs on device today.
3. **"Three consistent sightings" = 3 stills per tap**, not live frames (until J8 lands).
4. **Inference resolution 480 is baked in**: ONNX input 480, `N_ANCHORS = 4725` and `MODEL_IO` in TS. A 640 switch is a new model
   file (8400 anchors) + code change + new hash, not a setting.
5. The brief's H2 "supported-item accuracy 0.65" is the 13-way full-image H-val number; the 12-way top-1 on the same items is 0.745 (D4).

### A7. Missing training artefacts
- G3 `best.pt` present (`ml/runs/G3/kaggle/.../best.pt`, 29cc5212; copy `kaggle/g6/up_w/G3_best.pt`). H2 `.pt` present. E224 `best.pt` 320b84b0 referenced.
- Not present in the sandbox: G3's full Kaggle training run directory beyond weights/logs, and any human-verified label set (none exists).
- `ml/runs/G3/kaggle_tables.md` holds the PRE-EXISTING T4 eval of every imgsz (used in D2).

### A8. Integration risks
- Ultralytics AGPL-3.0 covers G3 itself and every YOLO candidate below (see B). Fine for an open-source FYP; a closed-source /
  commercial release needs AGPL compliance (publish the full app source) or an Ultralytics Enterprise licence (https://www.ultralytics.com/license).
- LVIS/COCO image terms already make G1-G3 weights research/FYP-only (`docs/cv/licences.md`).
- Any detector swap changes `N_ANCHORS`, `NC`, class order, `MODEL_IO`, `models.ts` hashes, parity fixtures and the QA-APK model fetch.

## B. Candidate matrix (Phase 2)
CSV: `ml/runs/G10/g10_candidates.csv` (also `files/g10/G10_candidates.csv`).

| # | candidate | task / arch | classes (NutriSole overlap) | weights | licence | input | size | ONNX | benchmark |
|---|---|---|---|---|---|---|---|---|---|
| A1 | mark-360/Fruit-Detection `Models/Yolo11.pt` | det, YOLO11n | apple, mango, banana, orange (4: apple, mango, banana, citrus) | **yes**, in repo (sha256 4f663749…) | **none** (GitHub API `license: null`; README: third-party images keep their licences) + Ultralytics AGPL-3.0 | 640 | 5.48 MB pt / 10.6 MB onnx | export OK (1,8,8400) | MEASURED |
| A2 | mark-360 `Models/Yolo26.pt` | det, YOLO26n | same 4 | **yes** (1b225d69…) | same | 640 | 5.39 MB / 9.8 MB | export OK | MEASURED |
| B | jembilog/Fruit-Detection-YOLO | det, YOLOv8s (stated) | apple, banana, grape, orange, pineapple, watermelon | **no** (README: "best.pt not included") | code MIT; dataset `lakshaytyagi01/fruit-detection` tagged CC0 on Kaggle, Roboflow-style export (640 stretch, x3 aug), image provenance undocumented | 640 | n/a | n/a | not possible |
| C1 | henningheyen LVIS F&V `yolo_fruits_and_vegetables_v1.pt` | det, YOLOv8m | 63 LVIS classes (10 overlap: banana, apple, citrus via orange/mandarin/clementine, lemon_lime via lemon/lime, tomato, potato, cucumber, carrot, capsicum; **no mango, guava, pomegranate**) | **yes**, public gDrive (sha256 a18624d4…) | repo MIT, Kaggle dataset MIT, HF card Apache-2.0; LVIS annotations CC BY 4.0, COCO/Flickr images per-image licences; weights embed Ultralytics AGPL-3.0 | 640 | 52.1 MB / 103.8 MB | export OK (1,67,8400) | MEASURED |
| C2/C3 | same, v2 (YOLOv8l) / v3 (YOLOv8x) | det | same | yes (87.7 MB / 136.8 MB pt) | same | 640 | 88 / 137 MB | not tried | not run: 2-5x heavier than v1, not phone-viable |
| D | Roboflow cse299/fruit-and-vegetable v1 | dataset only (Models: 0) | 20 classes **named only "0".."19"** | n/a | Public Domain (CC0) per page | 416 stretch | 1,037 imgs (2,489 after x3 aug) | n/a | not possible: classes unnamed, provenance undocumented |
| E | HF sharktide/fruitbot-expanded | classifier, ResNet-50 (Keras 2 h5) | config lists 36 (overlap 11: no guava; capsicum = capsicum/bell pepper/paprika) | **yes** (`tf_model.h5`, 107.7 MB, sha256 7c6323ea…) | **none on the model card** | 240 | 107.7 MB, 24.7 M params | tf2onnx conversion **OOM-killed in sandbox (unverified)** | MEASURED vs H2 |

Extra findings: the fruitbot h5 has **60 outputs but its config/README list 36 labels** (indices 36-59 unnamed); on H-val the argmax
indices matched the published order for the first 36 (apple->apple, tomato->tomato, ...), so the mapping was usable but not
verified by the author. The HF `other=fruits` search returned no other fruit-specific detector (the tag listing is dominated by
unrelated models); no further candidate was added. mark-360's README says the public data is a "privacy-safe subset" and the
reported metrics (YOLO11n mAP50 0.947 on its own 4-class test) are PUBLISHED, not reproduced and not comparable.

**Important provenance note:** NutriSole's `test_rf` split is henningheyen's 180-image Roboflow-labelled test set (149 kept), and
G3's `test`/`val` splits are halves of henningheyen's HF validation set (`ml/data/build_det_v1.py`). henningheyen's models used that
validation set for checkpoint selection, so C1 has a mild selection advantage on our val, and full domain match on its LVIS part.

## C. Ranked plan (Phase 3-8)
Ranked by expected useful impact per cost/risk. "Now" = doable without annotators or approval.

| rank | action | impact | difficulty | cost | risk | status |
|---|---|---|---|---|---|---|
| 1 | **Human-verified eval sets** (J pilot+pilot2 with 2 blind annotators + adjudicator; whole-item E224 crop set; phone captures incl. small/occluded/printed/cut) | unlocks every acceptance criterion | low tech, needs people | $0 | none | **BLOCKED on user (annotators)** |
| 2 | **Phone run of the QA APK** (p50/p95, memory, thermal) for G3@480 and H2; J8 live frames once merged | first real latency numbers | low | $0 | none | **BLOCKED on user (phone)**; J8 owned by another agent |
| 3 | Scene-guard re-tune on human-verified phone captures: test minAreaFrac 0.0025-0.005 vs 0.01 with correct-ID and false-acceptance (D3 shows 0.0025 keeps 98.7 % of no-guard TPs with 1-2 neg images) | recovers small/far items | low | $0 | more false names if done blind | after rank 1; needs user approval to change |
| 4 | Only if rank 3 lowers the guard: re-test G3 at 640 (D2 shows the 640 gain appears only below the guard) | +0.02 mAP50 dev | medium (new ONNX + TS anchors) | $0 | +73 % CPU latency | after 2+3, approval |
| 5 | H3 fine-tune of H2 with balanced phone-style data (frozen plan v3 draft) | H2 is the identity bottleneck | medium | $0 Kaggle | label leakage | **BLOCKED: 0 verified labels, `USER_TRAINING_GO.json` absent** |
| 6 | Teacher/distillation research with henningheyen v8m (pseudo-labels for apple/banana/citrus/lemon_lime in LVIS-like scenes) | maybe +recall on 4 classes | medium | $0 | AI labels are never ground truth; AGPL; domain-specific | proposal only; needs approval for any training |
| 7 | ORT mobile tuning: XNNPACK EP, `intraOpNumThreads`, frame skipping; NNAPI/CoreML only after a phone baseline | latency | low | $0 | NNAPI op coverage | after rank 2 |
| — | Replace G3 or H2 with any candidate in B | none (D1, D4) | — | — | regression | **rejected** |

## D. Experiments run (all inference-only, dev splits only)
Splits: **det_v3 `val`** (402 images = 295 LVIS/HF-val + 57 OIV7 + 50 neg; 2,022 GT boxes; it was used for G3's epoch selection,
so G3 also has a selection advantage) and **`negdev`** (110 no-produce images = 50 det_v3 neg val + 60 G3 DEV negatives
`g3data/devneg`). Close-up: **Stage H `H-val`** (114 items: 19 single, 32 piles/bunches, 63 negatives; H2's selection split).
Locked test / test_rf / test_oiv7 / neg_test and M-TEST were **not** run (dev-only instruction). Raw JSON: `ml/runs/G10/`.

Scripts (new, small, reuse Ultralytics + existing helpers): `ml/eval/g10_ext_bench.py` (class-remapped detector bench: Ultralytics
`predict` conf 0.001 / NMS 0.7 / max_det 300, `BaseValidator.match_predictions`, `utils.metrics.ap_per_class`, `size_buckets.gt_of`),
`ml/eval/g10_guard_whatif.py` (uses `scene_guard.py`), `ml/eval/g10_cls_bench.py` (H2 via `camera_io.h2_input` + `verify.h2_decision`).
Existing tools reused: `ml/eval/eval_det.py`, `/workspace/work/cv/g2_bench.py`, Ultralytics export as in `ml/export/export_models.py`.
Chain: `/workspace/work/cv/g10/run_g10*.sh` (copied to `ml/runs/G10/scripts/`).

### D1. Detector candidates vs G3 on dev val (MEASURED, g10_ext_bench)
Parity: the same script on G3@480 gives mAP50 0.401 vs `eval_det.py` (model.val) 0.432. The gap is Ultralytics val using
multi-label NMS (`multi_label=True`) while predict (and the app) use single-label; all rows below use the same single-label path.

| model @ imgsz | mAP50 (11 GT cls) | mAP50-95 | negdev imgs with box >=0.35 | boxes on negdev | predict ms p50 (PyTorch, shared CPU) | ONNX p50/p95 ms (2 thr, CPU) |
|---|---|---|---|---|---|---|
| **G3 @480 (shipped)** | **0.401** | 0.279 | **3/110 (2.7 %)** | 3 | 135 | **43.8 / 44.3** |
| G3 @640 | 0.420 | 0.279 | 5/110 (4.5 %) | 6 | 114 | 75.5 / 78.7 |
| mark-360 YOLO11n @640 | 0.061 | 0.049 | 19/110 (17.3 %) | 409 | 109 | 74.4 / 75.6 |
| mark-360 YOLO11n @480 | 0.070 | 0.056 | 13/110 | 178 | 71 | — |
| mark-360 YOLO26n @640 | 0.056 | 0.045 | 24/110 (21.8 %) | 512 | 104 | 63.9 / 67.1 |
| mark-360 YOLO26n @480 | 0.068 | 0.053 | 22/110 | 225 | 68 | — |
| henningheyen YOLOv8m @640 | 0.433 | 0.349 | 13/110 (11.8 %) | 41 | 778 | 634 / 1421 |

Per-class AP50 on the same val (classes the candidate can predict; others score 0):

| class (GT boxes) | G3@480 | G3@640 | mark-360 Y11@640 | mark-360 Y26@640 | henning v8m@640 |
|---|---|---|---|---|---|
| banana (469) | 0.51 | 0.60 | 0.10 | 0.12 | **0.82** |
| apple (199) | 0.57 | 0.56 | 0.21 | 0.17 | **0.76** |
| mango (11) | **0.69** | 0.72 | 0.08 | 0.06 | — (no class) |
| citrus (208) | 0.74 | 0.72 | 0.29 | 0.26 | **0.83** |
| pomegranate (16) | **0.43** | 0.44 | — | — | — |
| lemon_lime (77) | 0.08 | 0.14 | — | — | **0.63** |
| tomato (317) | 0.44 | 0.44 | — | — | **0.54** |
| potato (20) | 0.00 | 0.03 | — | — | 0.03 |
| cucumber (154) | 0.27 | 0.31 | — | — | 0.30 |
| carrot (435) | 0.40 | 0.42 | — | — | **0.53** |
| capsicum (116) | 0.27 | 0.25 | — | — | 0.31 |

**Domain split (OIV7 part of val only, 57 images, MEASURED):** G3@480 mAP50 0.502, G3@640 0.499, henning v8m **0.150**
(cucumber 0.41/0.43 vs 0.30; capsicum 0.46/0.43 vs 0.11; carrot 0.44/0.37 vs 0.14; mango and pomegranate 0.70/0.52 vs none).
So henning's lead on val comes from the LVIS images it was built on (same source as its training set and checkpoint-selection
set); off that domain it is far worse than G3. Small-object recall at 0.35 (GT shorter side at 480 scale): 6-12 px G3@480 4.3 %,
G3@640 11.0 %, henning 31.3 %; 12-24 px 27.4 / 32.4 / 58.5 %; >=48 px 64.0 / 62.8 / 70.6 %.

Verdicts: mark-360 = **reject** (6-9x lower mAP50 on its own 4 classes, 6-8x more false alarms, no licence). henning v8m =
**not an improvement for NutriSole** (domain-specific gain, 4x negative false-alarm rate, 104 MB ONNX, ~15x CPU latency, no mango /
pomegranate, AGPL); keep only as a possible research teacher (C rank 6).

### D2. G3 resolution 480 vs 640 (MEASURED dev + PRE-EXISTING locked)
| metric | 480 (shipped) | 640 | diff |
|---|---|---|---|
| dev val mAP50 / 50-95, `eval_det.py` (model.val, multi-label) | 0.432 / 0.311 | 0.452 / 0.337 | +0.020 / +0.026 |
| dev val mAP50, single-label bench | 0.401 | 0.420 | +0.019 |
| lemon_lime / banana / potato AP50 (bench) | 0.08 / 0.51 / 0.00 | 0.14 / 0.60 / 0.03 | gains |
| apple / citrus / capsicum AP50 (bench) | 0.57 / 0.74 / 0.27 | 0.56 / 0.72 / 0.25 | small losses |
| negdev images with a box | 3/110 | 5/110 | worse |
| **recall at 0.35 after the shipped 1 % guard** (D3) | **0.293** | **0.287** | **-0.006** |
| FPs on val after the 1 % guard / neg images | 243 / 1 | 277 / 4 | worse |
| ONNX CPU p50 / p95 | 43.8 / 44.3 ms | 75.5 / 78.7 ms | +73 % |
| ONNX size | 10.6 MB | 10.7 MB | same weights |
| PRE-EXISTING Kaggle T4 (`ml/runs/G3/kaggle_tables.md`) test / test_rf / test_oiv7 mAP50 | 0.224 / 0.356 / 0.380 | 0.238 / 0.374 / 0.381 | quoted, not re-run (locked) |
Decision: **reject for now.** The 640 gain sits in boxes below 1 % of the frame; with the shipped guard it disappears and FPs rise.
Re-test only together with a guard change on human-verified phone data (C ranks 3-4).

### D3. Scene-guard what-if (MEASURED, G3@480, score >= 0.35, maxSameClass 0, analysis only; default NOT changed)
| minAreaFrac | GT share below | TP kept | recall | FP on val | negdev imgs |
|---|---|---|---|---|---|
| 0 (off) | 0 % | 825 | 0.408 | 433 | 3 |
| 0.001 | 5.6 % | 824 | 0.408 | 429 | 3 |
| 0.0025 | 15.8 % | 814 | 0.403 | 397 | 2 |
| 0.005 | 31.4 % | 742 | 0.367 | 344 | 2 |
| **0.01 (shipped)** | 49.9 % | 593 | 0.293 | 243 | 1 |
| 0.02 | 67.4 % | 420 | 0.208 | 151 | 1 |
Half of the dev GT boxes are under 1 % of the frame; the shipped guard removes 28 % of G3's correct detections at 0.35 and 44 % of
its FPs. "FP" on LVIS images includes unlabelled real produce (LVIS is federated), so the FP side is overstated. The app shows one
tapped item at close range, so this static-image view is not the deciding test: decide on human-verified phone captures (C rank 3).

### D4. Close-up classifier: fruitbot-expanded vs H2 on H-val (MEASURED, 12-way supported top-1; labels agent-triaged)
| metric (51 supported, 63 negatives) | H2 (frozen) | fruitbot raw 0-255 | fruitbot ResNet50 preprocess | fruitbot /255 |
|---|---|---|---|---|
| top-1 accuracy | **0.745** (38/51) | 0.549 | 0.549 | 0.255 |
| mean per-class top-1 | **0.773** | 0.665 | 0.485 | 0.100 |
| H2 frozen accept (tau 0.4, maxUnknown 0.5): correct / wrong / negatives accepted | 22 / 2 / 16 of 63 | — | — | — |
| fruitbot at p >= 0.5 (no unknown class): correct / wrong / negatives named | — | 26 / 5 / 27 | 26 / 4 / 18 | — |
| latency | ONNX 9.7 / 36.9 ms p50/p95 | Keras predict 131 ms p50 | | |
| size | 6.1 MB | 107.7 MB | | |
Three preprocessings were tried because the card does not state one (choice on dev = optimistic for fruitbot). H2 used its
production preprocessing. Verdict: **reject** (worse top-1, more wrong names and negatives named, no unknown output, 17x larger,
no licence, label/config mismatch). H2 alone still names 16/63 negatives; only the P-a agreement with G3 removed them in Stage H.

### D5. Not run (proposed only)
E224 leakage / whole-item crop re-evaluation, H2 fine-tuning, quantisation (INT8/FP16), NNAPI/CoreML/XNNPACK, tiling, any phone
metric. Reasons: no human-verified crop set, training not authorised, phone required.

## E. Integration changes
**None to the product.** Added only: the three G10 scripts under `ml/eval/`, results under `ml/runs/G10/`, this report and the
candidate CSV. No model file, threshold, policy, TS/app code or user-facing text changed. External checkpoints and exported ONNX
files stay in the sandbox (`/workspace/work/cv/g10/`), not committed.

## F. Validation (original vs proposed)
There is no proposed pipeline: every candidate failed. Original pipeline status unchanged: G3@480 + 1 % guard + H2 P-a; dev numbers
in D1-D4; locked-set and Stage H numbers as in G3.md / G9_stageH.md. Mobile: **pending the user's phone run** (QA APK, J7 guide);
no phone latency, memory or thermal number is claimed. Acceptance criteria 2 (human-verified labels) and 6 (measured mobile
latency) cannot be met by anything today.

## G. Rollback
Nothing product-facing changed, so there is nothing to roll back in the app. To remove G10 entirely: revert the G10 commit on
`cv-gauntlet` (`git revert <G10 sha>`, or delete `ml/eval/g10_*.py`, `ml/runs/G10/`, `docs/cv/gauntlet/G10_*`). Production weights
remain at their recorded hashes (A2) in `g3models/`, `g9h/h2v2/`, the device ZIP and the orphan `qa-models-j7` branch
(`3121970`); restore any of them from those copies and verify with `sha256sum` against `native/src/cv/device/models.ts`.

## What is blocked on the user
1. Two independent annotators + an adjudicator for pilot/pilot2 and the team photo quotas (frozen gates R1-R4).
2. A phone run of the QA APK (latency p50/p95, memory, thermal) and, after J8 merges, live-frame behaviour.
3. Explicit approval before any guard/threshold change, any model swap, and any training (H3 or distillation).
