# G9 Stage H: close-up identity verification and occlusion safety (FINAL)

**Decision: NOT ACCEPTED.** 4 of 8 frozen criteria pass (H-A2, H-A3, H-A7, H-A8). H-A1, H-A4, H-A5 and H-A6 fail.

- The H2 close-up classifier was trained twice on free Kaggle, the maximum the prereg allows. **No third attempt will be made.**
- G3 stays the unchanged champion. Stage G stays rejected for user-facing grading.
- **No A/B/C grade and no grade-specific price is shown in the app.**

**Exploratory only.** Every Stage H label (class, whole/cut, supported/unsupported, fresh/rotten) was checked by the agent from Commons
metadata and contact sheets. No human annotator was available, so **no claim of independently verified accuracy is made**. The
human-labelling protocol (`G9_stageH_human_labeling_protocol.md` + `ml/runs/G9/stageH/human_label_template.csv`) defines the independent
set that has to come first.

**Ground rules followed:**
- Prereg `G9_stageH_prereg.md` (b9415a1) was synced before any Stage H result. Its criteria were not changed.
- Branch `cv-gauntlet` only; draft PR #1 is the review path. No main, no merge.
- No YOLO training. M-TEST was not opened. M-DEV was not used for tuning.

## 1. H2 classifier (the only training allowed)

**Model:** MobileNetV3-Small (timm `mobilenetv3_small_100`, ImageNet init), 13 outputs (12 classes + `unknown`), 224 px, ONNX FP32.

### Attempt 1 (`mfaizannnn/nutrisole-g9h-h2` v1): failed, no weights
- ~85 min was spent in recursive `glob` over `/kaggle/input` before training started.
- The ONNX export crashed (`onnxscript` missing in the Kaggle image), so the weights were lost.
- It used untriaged Commons labels. On H-val: balanced accuracy 0.37, unknown recall 0.03.

### Attempt 2 (`mfaizannnn/nutrisole-g9h-h2v2` v1): trained and exported
- Free T4, 26.7 min in total. Report: `ml/runs/G9/stageH/out/h2_report.json`.
- **Changes from attempt 1:**
  - **Triaged Commons labels.** H-train was triaged again by the agent (`htrain_triage.json`): 224 of 417 kept (38 single items, 97
    piles/bunches, 89 negatives: 65 cut, 14 printed, 10 unsupported). H-val is the existing triage (114 items).
  - **Commons oversampled** to 40% of draws (class-balanced). The other 60% came from Fruits-360, Fruit Recognition and the Vegetable Image
    Dataset (Kaggle, class-balanced; 160 dropped as near evaluation hashes).
  - **Bounded directory search** instead of recursive globs (dataset listing took 9 min).
  - **`.pt` saved before export**, then the legacy exporter (`dynamo=False`), with `onnxscript` installed as a fallback.
- **Result:** best epoch 7, H-val (triaged, full image) balanced accuracy **0.68** (supported accuracy 0.65, unknown recall 0.59).
- **Commons training data was thin:** potato 1 image, lemon_lime 3, cucumber 4, carrot / citrus 5 each.
- Artefacts: `/workspace/work/g9h/h2/h2_mnv3s.onnx`, `/workspace/work/g9h/h2v2/h2_mnv3s.{pt,onnx}`.

## 2. Identity (P1): H0 / H1 / H2 on EVAL

Eval set: CU-check, CU-neg check and H-eval. It has 99 supported items (64 single whole items) and 77 negatives (24 unsupported, 16 printed,
37 cut). Single still, tap at the centre. Settings were frozen on TUNE before eval.

| Arm | Correct ID | Wrong ID | Abstain | Unsupported/printed/cut accepted | Wide-correct legit rejected |
|---|---|---|---|---|---|
| H0 Stage G wide ID | 46/99 (0.46) | 10/99 (0.10) | 0.43 | 13/77 (0.17) | n/a |
| H1 = P-c (G3 re-run on the crop must agree) | 29/99 (0.29) | 7/99 (0.07) | 0.64 | 10/77 (0.13) | 17/46 (0.37) |
| H2-only (classifier alone with reject) | 12/99 (0.12) | 25/99 (0.25) | 0.63 | 21/77 (0.27) | 28/46 (0.61) |
| P-a (wide + H2 agree) = **H-final** | 9/99 (0.09) | **0/99** | 0.91 | **0/77** | 37/46 (0.80) |
| P-b (P-a + H1 veto) | 9/99 (0.09) | 0/99 | 0.91 | 0/77 | 37/46 (0.80) |

- **Frozen pick (`FROZEN_VERIFY`, TUNE only):** P-a, tau 0.4, margin 0, maxUnknown 0.5.
  - The prereg selection rule was **infeasible**: none of the 240 grid settings reached correct-item acceptance ≥ 0.60 on tune. The best
    was 0.23 (H-final tune: correct 0.23, wrong 0.011, 4/104 negatives accepted).
  - So the pre-coded fallback was applied: maximum correct at tune error ≤ 3%.
- **H1 does not fix wide errors.** On the 10 eval items with a wrong wide ID, G3 on the crop repeated the error 7 times and corrected it 0
  times.
- **H2 is a good veto but a weak identifier on real close-up crops.** Alone, it is wrong more often than right (12 correct, 25 wrong). It
  removes every wrong ID and every unsupported acceptance only because it agrees with the wide class so rarely.
- **Stage G approach simulation on CU-check (29 items):**
  - Stage G identified 19, 6 correctly, and graded 11, **8 of them on a wrong ID**.
  - With H-final, 3 are verified. **7 of the 8 wrong-ID grades are blocked.**
  - The one left: **cu0100, a guava** that the wide scan called lemon_lime. H2 also said lemon_lime, so it was verified, it passes the
    occlusion cues (solidity 0.97, ellipse IoU 0.94), and Stage G had graded it.
- **Latency (sandbox CPU):** H2 p50 6.5 / p95 14.4 ms; H1 p50 78 / p95 149 ms.

### User-assisted fallback (separate UX arm; not counted as accuracy)
"Is this a <A> / <B> / something else?" A confirmation unlocks the **category reference price only, never a grade**. On EVAL:

- **Supported items:** 90 came out "Unable to identify". The true class was among the suggestions for 31 (34%).
  - A careful (oracle) user confirms those 31 correctly.
  - A careless user who always taps the first suggestion confirms a **wrong** category on 47.
- **Negatives:** a careless user confirms a supported category for **48 of 77** unsupported, printed or cut items.

**Conclusion:** the fallback is usable as a UX aid with neutral wording and a visible "something else" option. It is not a safety layer, it
must never unlock a grade, and its category price needs a "you selected this" label.

## 3. Occlusion (P2)

### Why the 35 Stage G degraded crops were graded (unchanged from the interim, `out/leak35.json`)
- The 35 = 24 occlusion, 7 blur, 4 low light.
- Every occluded leak had condition-model confidence ≥ 0.989 and a GrabCut visible fraction of 0.25-0.70, all above the 0.25 check.
- 16 of the 24 were rotten items whose visible half still showed rot.
- 23 of the 24 had no correct wide ID; the feasibility suite graded regardless of identity.

### Extended suite on CU-check
990 occluded or truncated crops (18 occluder types × 55) plus 165 blur / low-light / JPEG crops, at 96 and 192 px.

| Layer | Occluder leakage | Max per type | Clean crops graded |
|---|---|---|---|
| Stage G checks (baseline, unchanged) | 597/990 (60.3%) | grey block 78%, hand_1 80% | 43/55 |
| + occlusion rule (`FROZEN_OCC`) | 273/990 (27.6%) | bag_full 56% | 28/55 (15/43 = 0.35 clean false reject) |
| **Full H-final pipeline** (identity re-verified on the occluded crop → occlusion → Stage G) | **23/990 (2.3%)** | **trunc25_inner 6/55 (10.9%)**; block_blue, hand_2 5.5% | **7/55 (0.13)** |
| Identity verification only (no occlusion rule) | 52/990 (5.3%) | 14.5% | 8/55 |

- **Frozen occlusion rule (`FROZEN_OCC`, CU-tune only):** solidity ≥ 0.8, ellipse IoU ≥ 0.7, straight-edge fraction ≤ 0.4, border fraction ≤
  0.7. That is 4 geometric cues, not area, confidence or colour alone.
- **The H2 half-crop agreement cue was available but not picked.** It did not lower tune leakage within the ≤ 0.20 clean-false-reject limit.
- **Each cue alone on check:** occluder leakage 45-56%, so no single cue does the job.
- The pick rejected 18% of clean crops on tune but **35% on check**, so the clean-rejection limit does not hold out of sample.
- **Most of the full-pipeline drop comes from identity abstention, not from detecting occlusion.** Only 9/55 clean crops are even verified.
  This is close to the "safe by rejecting everything" pattern H-A5 exists to catch.
- Blur, low light and JPEG: 0 leaks in the full pipeline.

## 4. End-to-end DEV metrics (frozen configs, `out/e2e_h.json`; identity, grading and safety reported separately)

| | H0 (Stage G path) | H-final |
|---|---|---|
| Grades issued (single still, eval) | 57 | 8 |
| Grades on a wrong or unsupported identity | **21 (36.8%)**, 12 of them negatives | **0** |
| Supported items reaching a grade with the correct ID | 35/99 (0.35) | **8/99 (0.08)** |
| CU items reaching a grade | 0.21 | 0.03 |
| Fresh/rotten agreement with agent labels (not a criterion) | 4/6 | 1/1 |
| Outcomes | n/a | 171 unable to identify, 2 not graded, 8 internally graded (not shown) |

**Latency (sandbox CPU, load average ~2.5 from other jobs; not a phone):**
- Close-up path p50 341 / **p95 1136 ms**.
- The time goes to GrabCut occlusion cues (p95 556 ms) and the Stage G assess step (p95 557 ms). H2 itself is p95 14 ms.

## 5. Acceptance against the frozen criteria (DEV eval)

| ID | Criterion (frozen) | Result | Pass |
|---|---|---|---|
| H-A1 | Wrong-identity grading: 0 on CU-check and ≤ 1% pooled | Single-still eval 0/8. **CU-check approach: 1 of 2 grades on a wrong ID** (cu0100 guava → lemon_lime). Pooled 1/10 | **FAIL** |
| H-A2 | Wrong-identity acceptance ≤ 3% of supported items | Eval 0/99. CU-check approach 1/29. Pooled 1/128 (0.8%) | PASS |
| H-A3 | Unsupported/printed/cut accepted ≤ 2% and 0 graded | 0/77 accepted, 0 graded (greyscale 0/5) | PASS |
| H-A4 | Occlusion leakage ≤ 3% overall and ≤ 5% per type | Full pipeline 23/990 = 2.3% overall, but **trunc25_inner 10.9%** (block_blue, hand_2 5.5%). Rule alone 27.6% | **FAIL** |
| H-A5 | Correct-ID verification ≥ 0.60; clean false reject ≤ 0.20; clean supported crops graded ≥ 0.40 | **9/64 = 0.14**; **0.35**; **0.13** (suite) / 0.08 (e2e) | **FAIL** |
| H-A6 | H2 p95 ≤ 60 ms; close-up path p95 ≤ 700 ms | H2 14.4 ms; **close-up 1136 ms** | **FAIL** |
| H-A7 | TS + Python tests pass; parity on the new policy + occlusion rule | TS 114/114 (`cvVerify` 10/10); Python 9/9; parity fixture regenerated with the frozen values | PASS |
| H-A8 | No A/B/C, no grade-specific price; category price only when identity and source verified | `stageh_decision` / `closeupDisplay`: grades disabled, category reference price only when verified or user-confirmed | PASS |

### Why it is not accepted
- The wrong-ID grades drop from 21 to 0 on single stills, and 7 of the 8 Stage G approach errors are blocked.
- But that safety comes from abstaining on about 90% of legitimate items. Correct-item acceptance is 0.14 against the 0.60 floor.
- One wrong-ID grade still gets through when the wide detector and H2 make the same mistake (guava vs lime). Two models agreeing is not
  proof, as the brief warned.
- Occlusion is solved overall only through that abstention. Inner truncation still leaks at 11%, and the geometric rule rejects 35% of clean
  crops.

## 6. What remains in place (unchanged contract)

**Mobile (P5): RN CV interfaces are kept.**
- `verify.ts` and `display.ts` mirror the Python exactly (parity-tested).
- Dependency review and Android device plan: `G9_stageH_device_test.md`, plus `native/scripts/g9h-device-check.ps1`.
- No phone FPS is claimed (no device).

**Safety and pricing (P6):**
- No A/B/C in the app.
- No grade-specific price.
- A category reference price only when identity and source are verified.
- Nutrition, glucose, diet, footwear and assistant are untouched.

## 7. What would have to change (not done in Stage H)

1. **Human-labelled independent close-up set first.** Run the protocol pilot (≥ 100 items, balanced). Without it, no accuracy claim is
   possible.
2. **Real close-up training data for H2.** It needs phone-style crops at 96-400 px, with tens of licensed Commons images per class
   rather than 1-6, plus the human set's train split. The H-val score (0.68 on full images) did not carry over to tap crops (H2-only
   correct 0.12).
3. **Independent evidence for look-alike pairs** (guava vs lime, citrus vs lemon_lime) beyond two models agreeing; or route those pairs
   to the user-confirm UX by default.
4. **Faster occlusion cues on device** (a smaller GrabCut input or a learned visibility head) and a truncation-specific check.

## Files
- **Prereg:** `docs/cv/gauntlet/G9_stageH_prereg.md`
- **This report:** `docs/cv/gauntlet/G9_stageH.md`
- **Human-labelling protocol:** `G9_stageH_human_labeling_protocol.md`, template `ml/runs/G9/stageH/human_label_template.csv`
- **Device plan:** `G9_stageH_device_test.md`
- **Results** (in `ml/runs/G9/stageH/out/`):
  - `identity.json`
  - `occlusion.json` (and the pre-H2 `occlusion_noh2.json`)
  - `occ_h2.json`
  - `e2e_h.json`
  - `stageH_acceptance.json`
  - `h2_report.json`
  - `leak35.json`
  - `h_leak_split.json`
  - `demo_cases.json`
- **Triage:** `htrain_triage.json`, `hval_triage.json`, `heval_triage.json`
- **Kernels:** `kaggle/k_h2` (attempt 1), `kaggle/k_h2v2` (attempt 2)
- **Demo video:** `out/video/g9h_demo_H0_vs_H.mp4` (33 s, H0 vs H-final on four cases, plus a credits frame); stills
  `out/video/g9h_demo_frames.png`. Not committed (binary); copied to the project files.
  1. Occluded apple (cu0130, 192 px, synthetic hand): H0 grade shown → H "Not graded" (outline_incomplete), category price only.
  2. Wrong ID (cu0130, true apple, Stage G said citrus and graded it) → H "Unable to identify", no grade, no price.
  3. Unsupported item (h01683, chilli peppers; H0 said banana and graded it) → H "Unable to identify" (close_up_unknown).
  4. User-confirm fallback (cu0127, apple) → "Is this: Apple / Carrot / something else?" → category reference price only.
