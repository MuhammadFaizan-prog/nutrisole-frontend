# G9 H3 plan, version 3: DRAFT (Stage J5, 2026-10-15 PKT; updated J6, 2026-10-16 PKT). PREPARED, NOT FROZEN, NOT LAUNCHED

> J6 update (in place): added §5 balanced sampling + phone-camera augmentations, §6 the Stage H baseline numbers, §7 the full comparison
> table (per-class accuracy, abstention, grading eligibility, end-to-end latency) and §8 preregistered acceptance criteria. Nothing was
> launched; no Kaggle, no training. Guard unchanged (REFUSED).

**Binding plan stays `G9_stageJ3_H3_frozen_plan_v2.md`** (sha256 `5445793b…`, named by the launch guard and by any user go file).
This draft only proposes how the controlled comparison is laid out once humans have delivered; it changes no gate, threshold or rule
and becomes binding only if the user freezes it as v3 before any J-eval image is seen. `h3_guard.py` today: **REFUSED** (no verified
human manifests, no user go). No GPU, no training.

## 1. What stays exactly as v2
Architecture timm `mobilenetv3_small_100`, 13 outputs; initial weights = H2 v2 `/workspace/work/g9h/h2v2/h2_mnv3s.pt`
(sha256 `02b402a1…`; the kernel refuses any other file); G3 E224 detector frozen as the front end; recipe (AdamW, lr 3e-4 / 1e-4, wd 0.05,
batch 64, ≤ 12 epochs, patience 3 on J-dev, seed 0); data rules (human-verified J-train only + Kaggle ≤ 30 %; J-eval / M-TEST / FruitNet /
carrot_m / tomato_m never in training; in-kernel pHash ≤ 10 drop); one attempt + at most one infrastructure retry per arm; `.pt` before ONNX.

## 2. Controlled candidates (one factor changes per arm)
| Arm | Differs from H2 v2 by | Why |
|---|---|---|
| B1 = G3 (E224 + its head) | baseline, unchanged | current wide pipeline |
| B2 = H2 v2 | baseline, unchanged | current close-up verifier |
| C1 = H3 (v2 recipe) | fine-tuned on human-verified J-train crops made the pipeline way | Stage I found the errors are **domain mismatch** (studio-trained H2 on real phone crops) |
| C2 (optional, only if the user approves before the run) | C1 + verified J5 candidate pool / team-phone training photos | tests whether added phone-style sources help; same everything else |
Selection between C1 and C2 uses **J-dev only**; J-eval is opened once, after selection, for all arms.

## 3. Comparison (same human-verified J-eval items for every arm; `h3_compare.py`)
| Asked for | Measured as (frozen definitions) |
|---|---|
| Recall | top-1 on clean supported items, per priority class and pooled |
| Genuine acceptance | E1 (accepted with the correct class): pooled ≥ 0.60, I-eval-A ≥ 0.60, I-eval-B ≥ 0.50, each class ≥ 0.40 |
| Wrong IDs | E2 ≤ 2 %, 0 graded, 0 priority wrong-ID on I-eval-A |
| Unsupported rejection | 1 − E3 (unsupported / printed / packaging / cut accepted ≤ 2 %) and E4 (other produce as a priority class ≤ 3 %) |
| Occlusion safety | E5 synthetic suite (n ≥ 900) ≤ 3 % overall, ≤ 5 % per type; human-tagged real occluded: 0 graded |
| Latency | E6 full pipeline p50 / p95 on the sandbox CPU (p95 ≤ 60 ms); phone timing only from P1 logs, reported as "first phone timing" |
E7: a candidate must beat **both** baselines (genuine acceptance higher, wrong ID not higher). UNCERTAIN (Wilson) is reported as uncertain,
never as a pass. Grades stay blocked whatever the result.

## 4. Inputs still missing before this can even be assessed
Independent annotators A and B on pilot 265 + pilot2 335 + train 461 + train2 646, a third-human adjudicator, the R2 packaging and occluded
sub-quotas (team eval photos), T1 volume for apple (≈ 65 short) and the user's go file. The J5 single-reviewer record of AI-assisted
labels does not satisfy any of these (see `G9_stageJ5.md` §1).

## 5. Data sampling and augmentation (J6 addition; applies to C1 and C2 identically)
- **Start:** H2 v2 weights (`h2_mnv3s.pt` `02b402a1…`), same `mobilenetv3_small_100`, same 13 outputs, same class order (asserted against
  `native/src/cv/pipeline/verify.ts H2_CLASSES` and `native/src/cv/domainMap.ts`). No new architecture.
- **Balanced sampling:** class-balanced sampler over human-verified J-train crops (inverse class frequency, capped at 3× oversampling of
  any single image); `unknown` drawn from verified negatives (hard negatives incl. persimmon, printed/painted produce, plastic fruit and
  round objects from the J6 candidate pool once labelled) at a fixed 25 % of each batch; Kaggle replay ≤ 30 % as in v2.
- **Crops exactly as the app makes them:** detector-box crop (pad 0.08) or tap ROI 0.35 on the full-resolution still, then `h2_input`
  (short side 256, centre 224, box-reduce + bilinear) — the TS/Python parity verified in J6 (H2 tensor max abs diff 0).
- **Realistic phone-camera augmentations (train only, seeded):** JPEG quality 40–95; downscale-upscale 0.35–1.0 (small/far items);
  Gaussian + Poisson sensor noise; motion blur (kernel 3–9 px) and defocus blur; exposure ±0.7 EV, white balance 3000–7500 K shift, gamma
  0.7–1.4 (indoor tube light, market shade, sun); random rotation ±25° and 90° steps (portrait/landscape), horizontal flip (front camera
  mirroring); crop-box jitter ±15 % (tap error); synthetic partial occlusion (hand/leaf/edge cut-outs 10–45 % area) and transparent-film
  overlay (glare + low contrast) **labelled per the annotation rules** (occluded/packaged items must not be graded); no colour jitter
  strong enough to change ripeness cues (hue ±0.03).
- **Never:** J-eval, M-TEST, FruitNet/carrot_m/tomato_m, `HUMAN_REVIEWED_AI_ASSISTED` or `AI_ASSISTED_NOT_HUMAN` labels as training labels.

## 6. Baselines to beat (frozen numbers, Stage H eval, n = 99 supported + 77 negatives; `docs/cv/gauntlet/G9_stageH.md`)
| Baseline | Correct ID (genuine acceptance) | Wrong ID | Abstain | Negatives accepted |
|---|---|---|---|---|
| G3 wide ID (H0) | 46/99 (0.46) | 10/99 (0.10) | 0.43 | 13/77 (0.17) |
| **H2 v2 in the frozen pipeline (P-a, H-final)** | **9/99 (0.09)** (item-level 9/64) | 0/99 | 0.91 | 0/77 |
| H2 alone with reject | 12/99 (0.12) | 25/99 (0.25) | 0.63 | 21/77 (0.27) |
H2 accepted only 9 of 99 supported items: it is safe by abstaining. H3 exists to raise genuine acceptance without giving up wrong-ID safety.

## 7. Comparison table every arm reports (same verified J-eval items; `h3_compare.py`, E1–E8 unchanged)
| Metric | Definition | Reported for |
|---|---|---|
| Per-class accuracy | top-1 on clean supported items, per priority class (apple, banana, citrus, tomato, carrot) + pooled, with Wilson 95 % CI | B1, B2, C1, (C2) |
| Genuine acceptance | E1: accepted with the correct class / clean supported | all |
| Wrong IDs | E2: accepted with a wrong class / clean supported; plus priority wrong-ID count | all |
| Unsupported rejection | 1 − E3 (unsupported / printed / packaging / cut accepted) and 1 − E4 (other produce taken as priority) | all |
| Abstention | share of clean supported items ending `unable_to_identify` (reported, not a pass criterion on its own) | all |
| Occlusion leakage | E5 synthetic suite (n ≥ 900) + human-tagged real occluded items accepted / graded | all |
| Grading eligibility | share of accepted items that would reach the quality gate (identity verified, not packaged/cut/occluded); grades still never displayed | all |
| End-to-end latency | E6 host p50/p95 (detector + crop + classifier) and, separately, the full debug pipeline (3 stills + crop) with `native/scripts/g9j6_host_pipeline.ts`; phone p50/p95 only from P1 logs, labelled "first phone timing" | all |

## 8. Preregistered acceptance criteria (proposed for the user to freeze; until then v2 binds and these are identical to v2 where v2 speaks)
H3 (C1, or C2 if selected on J-dev) is **accepted** only if ALL hold on the verified J-eval set, opened once:
1. E1 genuine acceptance pooled ≥ 0.60, I-eval-A ≥ 0.60, I-eval-B ≥ 0.50; each priority class ≥ 0.40 (E1 and E2 must hold together).
2. E2 wrong ID ≤ 2 % pooled (Wilson upper bound reported), 0 graded, 0 priority wrong-ID on I-eval-A.
3. E3 ≤ 2 % and E4 ≤ 3 %; 0 graded among unsupported/printed/packaged/cut.
4. E5 occlusion leakage ≤ 3 % overall, ≤ 5 % per type; 0 graded real occluded.
5. E6 (v2 definition: detector + crop + classifier, sandbox CPU) p95 ≤ 60 ms; the 3-still debug burst is reported separately (J6 host p50 158 ms); no phone claim without P1 logs.
6. E7: beats **both** B1 (G3) and B2 (H2 v2: 9/99) on genuine acceptance with wrong ID not higher.
7. Any criterion whose Wilson interval straddles the threshold is **UNCERTAIN = not accepted**. One attempt per arm (+1 infra retry).
Acceptance would only make H3 the experimental close-up verifier; grade display needs its own frozen criteria and stays off.

## 9. Readiness (J6)
Launch blocked: R1–R4/T1–T5 not met (0 human-verified items; see `G9_stageJ6.md` §4–5), no user go file. Do **not** launch Kaggle or any
training. Next step that needs the user: two unexposed annotators + adjudicator, and later a decision whether to freeze this draft as v3.
