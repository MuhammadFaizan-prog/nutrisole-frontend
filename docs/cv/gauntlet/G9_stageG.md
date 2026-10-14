# G9 Stage G: end-to-end mobile CV and quality-grading validation

Brief: user, 2026-10-14 20:35 PKT (14 items + demo story). Prereg `G9_stageG_prereg.md` (commit 5ef183c, synced before any Stage G
code ran). Branch `cv-gauntlet` only. **G3 unchanged** (480, conf 0.35, NMS 0.7, 1% guard, IouTracker), 12 classes, no detector
training. DEV only; **M-TEST not opened**. Nutrition, glucose, diet/exercise, footwear and assistant code untouched (git diff empty on
`native/App.tsx`, `src/`, `worker/`). No Supabase, no production.

## Verdict

**Not accepted.** The gated workflow is not ready to show a quality grade to users. Three acceptance criteria fail and three pass only in
the sandbox. The building blocks are solid and tested: the move-closer gate, quality checks, ROI fallback, coordinate mapping and price
contract. Two problems block it:

1. **Close-range identification is wrong too often.** In the simulated approach on independent close-ups (CU-check), G3 named 19 of 29
   items, but only **6 of the 19 correctly**. **8 of the 11 grades were issued on a wrong identity** (for example apple read as citrus or
   pomegranate, mango read as pomegranate).
2. **The 96 px gate did not generalise from tune to check.** At 96 px, gated grades disagree with the native-crop reference on **18.2%**
   of clean CU-check crops (5.9% on CU-tune). Gated fresh/rotten correctness is 0.727, against 0.759 for naive grading.

| Criterion | Result | Status |
|---|---|---|
| G-A1 no grade on sub-threshold / degraded crops (DEV suite) | CU-check: **35 / 878** emitted. Sub-threshold 0; blur 7, low light 4, occlusion 24; JPEG 0, truncation 0. Default checks: 208 / 878 | **FAIL** |
| G-A2 abstention >= 95% on unsupported / printed / partial / poor light; no grade on any unsupported item | 69 / 72 abstained = **95.8%** (grades: 1 of 32 unsupported, 2 of 22 cut/processed); partial (truncation) 0 graded; poor light 4 graded | **FAIL** (1 unsupported item graded) |
| G-A3 ID FPs not worse than G3 | false-ID tracks: DEV det clip 98 -> 42, DEV quality clip 56 -> 34, DEV neg clips 3 -> 1; M-DEV false boxes 63 -> 52 | PASS |
| G-A4 consecutive grade flips <= 5% | CU-check jittered frames 13 / 288 = **4.5%**; DEV quality clip 0 / 52 | PASS (narrow) |
| G-A5 gate acceptance >= 70% on good close-ups >= chosen size | single frame 0.83; **3-frame gate 0.679**; approach 11 / 19 identified items graded (0.58) | **FAIL** (narrow) |
| G-A6 sandbox p95: close-up <= 600 ms, detector <= 250 ms | close-up path **494.8 ms**; detector 76-102 ms | PASS (sandbox CPU only) |
| G-A7 tests and Python/TS parity | TS **104 / 104** (13 new in `cvCloseup.test.ts`), Python **11 / 11**, `tsc` clean | PASS |
| G-A8 price display contract | verified category + current row only; source, date, location and unit always present; never a seller price | PASS |

**What can ship behind a flag:** the wide-scan identification policy plus the official category price (with source, date, location and
unit), and "Move closer to check quality". **What must not be shown as a claim:** any A/B/C or fresh/rotten grade. That needs a close-range
identity re-check on the high-resolution crop and a human-labelled close-up set first (see Next).

## 1. Grading feasibility (brief items 5, 8, 9)

**Data (CU, new, independent).** 191 Wikimedia Commons candidates from 42 searches (`ml/runs/G9/stageG/cu_manifest.json`: title, page,
licence, uploader, author). Never Pexels, Pixabay or Mixkit. Agent triage on contact sheets (`cu_triage.json`) kept:

- **55 graded items:** apple 13, mango 8, banana 8, tomato 9, citrus 7, guava 6, carrot 2, lemon_lime 1, potato 1. Labels: 35 rotten, 20 fresh.
- **19 crowded scenes.**
- **33 unsupported:** persimmon-like osage orange, rose hips, insects, plants, pool and train scenes, and more.
- **12 printed or art, 6 greyscale photos, 24 cut or processed.**

**Leakage check (`out/cu_leak_split.json`):** Commons title overlap and 64-bit pHash against 1607 earlier Commons images (Stage D/E/F
pools, M-DEV and M-TEST titles and hashes only, never scored). 7 candidates were dropped, none of them graded items. The tune/check
split is by uploader: **CU-tune 26 items, CU-check 29**.

**Label provenance:** fresh/rotten comes from the Commons category or title (for example *Monilinia fructigena*, blossom-end rot,
*Penicillium*) and was checked visually by the agent. Labels are **agent-verified, not human-verified**. There are **no independent A/B/C
labels**, so no A/B/C correctness is claimed. FruQ-DB was not used (224 px only, third-party video frames, part of the condition
model's history).

**Suite (`scripts/feas_g.py`, `out/feas_items.jsonl`):**

- **Item crop:** a tap ROI selects a G3 box when one contains the tap. Otherwise a square user ROI is segmented with GrabCut (the ROI
  fallback). The native item side is 96-1251 px, median 448.
- **Crop sizes:** 32 / 64 / 96 / 128 / 192 / 256 px side, area-downsampled from the native crop. These are the pixels a camera frame
  carries at that size.
- **Conditions:**
  - clean
  - blur (Gaussian sigma 2 px)
  - low light (gamma 1.8, x0.35, noise sigma 5)
  - JPEG q15
  - occlusion (half the item covered)
  - truncation (40% cut at the frame border)
- **Stability frames:** 5 jittered consecutive frames per size (box shift ±4%, scale ±5%, sensor noise) for clean and JPEG.
- **Pipeline:** the existing one. E224 condition, `measure.py`, rules `rubric-v0.2-g2`, and the g7 per-fruit ripeness chip, recorded
  only (never merged into A/B/C).

**Gate selection on CU-tune (`scripts/feas_table.py`, `out/feasibility.json`), following the prereg rule:**
1. **Size:** the default checks failed every size because low light and JPEG crops passed them. A disclosed DEV step was added: a grid over
   `minMeanV` {40, 60, 80} x `minVisibleFrac` {0.25, 0.35, 0.45} x a new 8x8 JPEG `maxBlockiness` {1.4, 1.5, 1.6}. It minimises
   degraded emissions while keeping clean acceptance >= 0.70. Pick: **minMeanV 80, minVisibleFrac 0.25, maxBlockiness 1.4** (tune
   emissions 25 / 812, clean acceptance 0.81).
   Then the frozen size rule:

   | Size | Clean grade flip | Degraded max flip | Gated correctness | Naive correctness | Passes |
   |---|---|---|---|---|---|
   | 32 | 0.167 | 0.50 | | | no |
   | 64 | 0.125 | 0.667 | | | no |
   | **96** | **0.059** | **0.0** | 0.895 | 0.885 | **yes** |

2. **Frames.** Consecutive flip is 1.7% for every candidate, so all candidates tie. The tie-break takes the strictest candidate that still
   meets G-A5:

   | Frames | Mode | Graded rate | Agreement with native ref | Pick |
   |---|---|---|---|---|
   | 1 | count | 0.86 | 0.849 | |
   | **3** | **count** | **0.75** | **0.893** | **pick** |
   | 3 | score | 0.74 | 0.892 | |
   | 5 | count | 0.65 | 0.908 | |
   | 5 | score | 0.62 | 0.903 | |

   Score mode (quality-score stability) gave no gain over a fixed count.
3. **Frozen gate (`FROZEN_GATE` in `ml/eval/closeup.py` and `native/src/cv/pipeline/closeup.ts`):**
   - 96 px side on **full-resolution frame pixels**
   - 3 consecutive agreeing assessments
   - Laplacian variance >= 15
   - mean V between 80 and 245
   - not touching the frame edge (1%)
   - mask fraction >= 0.25
   - E224 max-prob >= 0.7 and margin >= 0.3
   - blockiness <= 1.4
   - rubric not "ungradable"

**Feasibility table, CU-check (29 items, frozen gate, single frame).**
- *Naive* means the fresh/rotten label from confidence alone, always shown.
- *Flip* is consistency against the item's own native-resolution crop.
- *Correct* means fresh/rotten agrees with the agent-verified source label. For reference, E224 on the native crops gets 0.745 right.

| Crop | Naive flip | Naive correct | Gated accept | Gated grade flip | Gated correct |
|---|---|---|---|---|---|
| 32 clean | 0.241 | 0.690 | 0.0 | n/a | n/a |
| 64 clean | 0.207 | 0.724 | 0.0 | n/a | n/a |
| 96 clean | 0.103 | 0.759 | 0.759 | 0.182 | 0.727 |
| 128 clean | 0.143 | 0.714 | 0.821 | 0.174 | 0.739 |
| 192 clean | 0.115 | 0.731 | 0.885 | 0.174 | 0.739 |
| 256 clean | 0.087 | 0.696 | 0.870 | 0.150 | 0.700 |
| 96 blur / low light / JPEG / occlusion / truncation | 0.31 / 0.28 / 0.45 / 0.24 / 0.21 | 0.62 / 0.59 / 0.76 / 0.62 / 0.72 | 0.069 / 0.034 / 0 / 0.207 / 0 | | |
| 192 blur / low light / JPEG / occlusion / truncation | 0.27 / 0.12 / 0.50 / 0.23 / 0.19 | | 0.115 / 0.038 / 0 / 0.269 / 0 | | |

**Reading:**
- Below 96 px nothing is graded. Naive grading at 32-64 px flips 21-24% of fresh/rotten calls while staying confident, which confirms
  Stage F P6.
- At 96 px and above the gate removes all JPEG and truncated crops and most blurred and dark crops.
- **Occlusion is the main leak:** 21-27% of half-covered crops still pass. The mask-fraction check does not see a flat skin-coloured block.
- On CU-check, about 15-18% of the A/B/C grades that pass the gate still differ from the native reference. The condition model itself is
  only about 0.75 right on these independent close-ups (a domain gap, as Stage F saw).
- **96 px is the smallest size that passed on tune, but grades above it are not reliable on check.** The bottleneck is model quality and
  identity, not pixels alone.

## 2. End-to-end harness (brief items 2, 3, 6, 7, 10, 11) — `scripts/e2e_g.py`, `out/e2e*.json`

**Model versions and processing (recorded in `out/e2e.json`):**
- Detector: G3 `det_yolo11n_640_raw` at imgsz 480 (sha256 c6fcb32a).
- Condition: E224 `E_224_e15_b64_sgd01`.
- Ripeness chip: g7 per-fruit 15-class.
- Rules: `rubric-v0.2-g2`; measurements `measure.py` (GrabCut).
- The close-up crop is taken from the full-resolution frame. Its analysis copy is capped at **256 px** (`ANALYSIS_MAX_SIDE`): without
  the cap, GrabCut p95 was 6.5 s.

**Wide scan, DEV clips** (tracker + identification policy: tracked score >= 0.5, >= 3 hits, not citrus-ambiguous, else "Unable to
identify"):

| Clip | Frame precision G3 -> policy | Frame recall G3 -> policy | Items identified | Time to ID p50 / p95 | False-ID tracks / min |
|---|---|---|---|---|---|
| det_clip (24 items) | 0.793 -> 0.840 | 0.410 -> 0.353 | 0.79 -> 0.67 | 400/1007 -> 500/750 ms | 50.8 -> 21.8 |
| quality_clip (16 items) | 0.374 -> 0.426 | 0.506 -> 0.459 | 0.69 -> 0.63 | 333/3133 -> 433/2200 ms | 43.4 -> 26.4 |
| neg_clip / devneg_clip | | | | | 1.49 -> 0.50 / 0.75 -> 0.25 |

Matching uses IoU >= 0.3 against per-frame clip boxes on tracker-smoothed boxes. These are synthetic slide-in clips from DEV val images.

**M-DEV v2 stills (market scale):** of 1493 labelled boxes, G3 finds **14 true positives**, with 63 false boxes (47 on box-free images).
With the policy: 13 true positives, 52 false boxes (37 box-free). This matches Stage F: identification at market scale is weak, and the
policy only trims false positives.

**Close-up path on the DEV quality clip.** The user taps once the item is identified; assessments run at 5 Hz.
- 15 of 16 items identified, 14 graded.
- **Grade band matches the dataset fresh/rotten label 14 / 14** (fresh -> B/A, rotten -> Reject). This is in-distribution: the same
  dataset family as E224's training.
- 0 / 52 consecutive grade flips.
- Time to ID p50 533 / p95 1520 ms; time to grade p50 1467 / p95 3556 ms.
- 81 of 222 assessments were "Not graded".

**Demo story: simulated move-closer on CU-check stills (29 items).** Each still is scaled 0.2 -> 1.0 over 20 frames at 15 fps, so it
never exceeds its native pixels. The tap is on the item.
- Identified 19, "Unable to identify" 10. **ID correct 6 / 19 (0.32).**
- Graded 11 (A 3, B 5, Reject 3). **Only 3 on a correct ID.** 8 / 11 grade bands match the fresh/rotten label.
- Time to ID p50 400 / p95 947 ms; time to grade p50 533 / p95 933 ms; ID to grade p50 133 ms.
- Prices: 8 grade-specific official lines, 8 category lines, 3 withheld below list grade, 10 not identified (no price).

**Unsupported and adversarial stills (single-frame gate):**

| Group | n | Identified | Graded | Abstention |
|---|---|---|---|---|
| unsupported | 32 | 1 | 1 | 0.969 |
| printed / art | 12 | 2 | 0 | 1.0 |
| greyscale photo | 6 | 1 | 0 | 1.0 |
| cut / processed | 22 | 6 | 2 | 0.909 |
| crowded (supported produce) | 17 | 8 | 7 | 0.588 |

Crowded scenes are graded when a single item is tapped, which is the intended behaviour.

**ROI and still fallback (item 6).**
- When no identified track contains the tap, `roiFromTap` returns a square user ROI. In the feasibility suite, GrabCut inside that ROI
  recovered the item for 23 of 55 stills where G3 had no box at the tap.
- In the app flow, a fallback ROI with no identification gives "Unable to identify": no name, no grade and no price. A wrong forced label
  is never produced.
- The high-resolution still path is in the device plan (D6). There is no camera stack to test it with here.

**Price contract (item 3; `native/src/cv/prices/display.ts`, mirror `ml/prices/display.py`).** It sits on top of the G4.6 module and
never computes a price.
- **Wide scan:** the official list range across list grades for a **verified** category, for example: "Rs 195-405 per kg (official list
  range; Market Committee Lahore / PAMRA retail rate list, Lahore, 2026-10-12)". It carries the label "Official reference price, not
  this seller's price".
- **After a gated A/B:** the official **list-grade** row ("official list price, grade 1"), never "this item is worth".
- **No price shown for:**
  - C or Reject
  - a list more than 2 days old
  - an unknown location
  - an item that is not identified
- **"Not graded":** keeps only the category line.

**API / DB (item 12).** The repo has no CV endpoint and no Supabase table. The only interface is the `CvAssessment` contract
(`native/src/cv/contracts.ts`). `toCvAssessment` maps every close-up outcome onto it, and the tests check that each validates. No
price ever enters the assessment, and its banned-claims rule already rejects "price".

## 3. Latency (sandbox CPU: 2 vCPU, ONNX Runtime FP32, Python — not phone)

| Stage | p50 ms | p95 ms |
|---|---|---|
| G3 detect (approach frames) | 46.7 | 89.3 |
| crop + 256 cap | 1.1 | 3.4 |
| E224 condition | 10.6 | 20.4 |
| measurements (GrabCut) | 129.8 | 770.1 |
| ripeness chip | 6.2 | 12.7 |
| rules + quality checks | <0.5 | <0.5 |
| **close-up path (crop -> checks), all runs** | **110.5** | **494.8** |
| per approach frame (detect + close-up when gated) | 56.1 | 444.8 |

**Not measured here:** phone FPS, camera latency, VisionCamera frame-processor overhead, NNAPI/XNNPACK, thermals, battery.

## 4. What runs where

| Piece | Status |
|---|---|
| `native/src/cv/pipeline/closeup.ts` | **Tested in the sandbox (node --test)**: coordinate mapping, crop, ROI, ID policy, checks, gate, blockiness, CvAssessment mapping, all at Python parity |
| `native/src/cv/prices/display.ts` | Tested at Python parity |
| Python reference harness (`ml/eval/closeup.py`, `ml/runs/G9/stageG/scripts`) | Run on DEV, CU and M-DEV material |
| VisionCamera frame processor, resizer, executorch / onnxruntime-react-native model loading, `takePhoto` still fallback | **Not present in the repo** (Techspec lists them as planned, not installed). Not run. Plan: `G9_stageG_device_test.md`; PC script `native/scripts/g9g-device-check.ps1` |
| Emulator | Not available (no KVM / SDK). Function only when the user runs it. Never an FPS source |

## 5. Recordings (`ml/runs/G9/stageG/out/video/`, ffmpeg, licensed Commons stills, credits frame in each)

- `g9g_demo_walkthrough.mp4` (29.3 s), with credits:
  1. Wide scan of M-DEV `m0531` (Ballarat apples, Commons). Apples are identified with the official Lahore apple range, plus one
     "Unable to identify".
  2. "Move closer" on CU `0014` (apple). The item is identified, then **graded A** after 3 agreeing assessments, with the official
     grade-1 list line.
  3. CU `0068` (orange). Identified, but every close-up assessment fails a check, so the result is **"could not be graded reliably"**.
- `g9g_naive_vs_gated.mp4` (65.6 s): 4 CU-check items at 32-256 px under clean, low-light and occlusion conditions. Naive grading shows a
  confident fresh/rotten call on every crop, including 32 px. Gated grading shows "Not graded" with its reasons. It also shows the
  occlusion leak honestly: some half-covered crops still get a grade.

## 6. Limitations

- **Labels:** CU fresh/rotten labels are source-derived and agent-verified, not human-verified. The quality-clip labels come from the
  dataset, in-distribution for E224. There are no A/B/C ground-truth labels. **A human review is needed before any grading-accuracy
  claim.**
- **Sample size:** CU is small (55 items; tune 26 / check 29). Single-item results swing 3-4 points.
- **Simulation:**
  - The approach sequences scale a still image; they are not real camera motion.
  - The degradations are synthetic.
  - No independent licensed market video exists (Stage F).
- **Measurement method:** blur and blockiness are measured on the crop as analysed. On a phone, frames are uncompressed YUV, so the JPEG
  check matters mainly for the still and upload path.
- **Disclosed post-hoc step:** the quality-check grid (minMeanV, minVisibleFrac, maxBlockiness) was added after the first table, on DEV
  only.
- **Phone:** no device run, no FPS, no thermal data.

## 7. Next (proposal, not started)

1. **Close-range identity re-check:** before any grade, check identity on the high-resolution crop. For example, require the detector
   class to be confirmed on the full-res crop (G3 re-run on the crop, or a crop classifier); otherwise "Unable to identify". This targets
   the 13 / 19 wrong close-range IDs.
2. **Occlusion check:** compare mask fraction against box area, or test colour uniformity inside the mask. Target: occlusion leak below 5%.
3. **Human-labelled close-up set:** 100+ items, the 5 showcase classes, fresh / defect / rotten. A person labels them. Use it before any
   grade is shown.
4. **Phone run:** D1-D10 from the device plan, after the Techspec camera spike is installed.

## Files

- **Docs:** `docs/cv/gauntlet/G9_stageG_prereg.md`, `G9_stageG.md`, `G9_stageG_device_test.md`.
- **Code:** `ml/eval/closeup.py`, `ml/eval/test_closeup.py`, `ml/eval/make_closeup_fixture.py`, `ml/eval/fixtures/closeup_parity.json`,
  `ml/prices/display.py`, `native/src/cv/pipeline/closeup.ts`, `native/src/cv/prices/display.ts`, `native/tests/cvCloseup.test.ts`,
  `native/scripts/g9g-device-check.ps1`.
- **Data and runs:** `ml/runs/G9/stageG/` (`cu_manifest.json`, `cu_triage.json`, `scripts/`, `out/feasibility.json`, `out/e2e*.json`,
  `out/feas_items.jsonl`, `out/feas_block.jsonl`, `out/cu_leak_split.json`, `out/video/`).
