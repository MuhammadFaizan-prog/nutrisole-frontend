# G9 H3 plan, version 3: DRAFT (Stage J5, 2026-10-15 PKT). PREPARED, NOT FROZEN, NOT LAUNCHED

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
