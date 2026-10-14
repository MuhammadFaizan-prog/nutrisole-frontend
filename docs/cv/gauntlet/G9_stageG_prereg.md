# G9 Stage G prereg: end-to-end mobile CV and quality-grading validation

Written and synced **before** any Stage G candidate code was run or any Stage G number was produced (2026-10-14, PKT).
Authoritative brief: user, 2026-10-14 20:35 PKT (14 items + demo story). Stage F P6 (`G9_stageF.md` section 6) is the starting
point: identification works at market scale, grading does not; P6 proposed a move-closer gate (96 px on the full-resolution frame,
3 stable frames). **That gate is a candidate, not a result.**

## Fixed (not under test)
- Detector: **G3 unchanged** (`det_yolo11n_640_raw`, imgsz 480, conf 0.35, class-wise NMS 0.7, 1% source-frame area guard,
  IouTracker defaults). No detector training, no new classes, 12 classes kept; showcase citrus / apple / banana / tomato / carrot.
- Condition model `E_224_e15_b64_sgd01` (fresh/rotten), rules `rubric-v0.2-g2` (`ml/grading/rules.py`, `native/src/cv/pipeline/rules.ts`),
  measurements `ml/grading/measure.py`, ripeness chip as shipped (separate, never merged into A/B/C).
- Official price module G4.6 (`native/src/cv/prices/reference.ts`, `ml/prices/reference.py`): Lahore Market Committee / PAMRA, AMIS, PBS SPI.
- Protected scope: nutrition, glucose, diet/exercise, footwear and assistant code are not touched (checked by `git diff --stat` on those paths).
- No Supabase, no production, no `main`, no merge, no PR. Branch `cv-gauntlet` only.

## Data and splits (DEV-only tuning; M-TEST untouched)
- **CU (close-up set, new):** independent licensed close-up produce photos from **Wikimedia Commons** (fresh and visibly rotten/
  mouldy categories), never Pexels / Pixabay / Mixkit. Licence, author and page per image in a manifest. Split **by source
  (uploader)** into **CU-tune** (gate selection) and **CU-check** (reported after the gate is frozen). pHash check against
  G3 train / DEV / M-DEV / M-TEST / MT pools; any hit within distance 10 is dropped.
  Label provenance: the Commons category / title states fresh vs rotten; the agent verifies each item visually.
  **Labels are agent-verified, not human-verified.** FruQ-DB is not used for correctness (224 px only, third-party video
  frames, and part of the condition model's history).
- **DEV material for the e2e harness:** DEV clips (`g3clips_dev` det / quality / neg, `g3clips_devneg`), M-DEV v2 stills
  (`ml/runs/G9/stageF/m_labels_v2.json`), CU stills for simulated approach sequences. **M-TEST is not opened.**
- Unsupported / adversarial inputs: box-free M-DEV negatives (persimmon, kiwi, printed fruit, etc.), DEV-neg clip,
  synthetic partial objects (edge-truncated crops) and poor-light versions.

## Candidate gate and alternatives (compared on CU-tune only)
- Size: crop side on **full-resolution source pixels** (not the 480 input) in {32, 64, **96**, 128, 192, 256}.
- Temporal: N consecutive accepted assessments in {1, **3**, 5}, versus a **quality-score stability** rule (quality score
  within tolerance over the last frames instead of a fixed count).
- Quality checks (each can return "Not graded"): Laplacian blur variance, exposure (mean V too low / high), occlusion /
  edge truncation (box touching the frame border, visible-surface fraction from the object mask), native crop size,
  model uncertainty (max-prob and margin), disagreement between consecutive assessments.
- **Selection rule (frozen now):** choose the smallest size threshold whose grade flip rate vs the clean native reference
  is **<= 10%** on CU-tune under the clean condition and **<= 15%** after the quality checks under the degraded conditions,
  with gated correctness (where labelled) not lower than ungated correctness at the same size. Then the smallest N
  (or the stability rule) whose consecutive-frame grade flip rate is <= 5%. Ties -> the stricter (larger) setting.
  If no size meets the rule, the decision is "grading not supported at any tested size" and the app shows only ID + price.

## Metrics (brief item 11)
ID accuracy, ID false positives (per image / per minute), time to ID, time to grade (frames and ms in the simulated approach),
gate acceptance rate, abstention rate ("Unable to identify", "Not graded"), grade stability (flip rate across consecutive
frames and across sizes), grade correctness **only where labels are independent**, p50/p95 latency per stage (detect, track,
crop, quality checks, condition, ripeness, rules, price) and end to end.

## Acceptance criteria (all must hold for "accept the gated workflow")
- **G-A1** No grade is emitted on any sub-threshold or degraded crop in the DEV degradation suite (crops below the chosen size,
  or failing blur / exposure / occlusion / uncertainty / disagreement checks). Naive grading is reported for contrast.
- **G-A2** Abstention ("Unable to identify" or "Not graded", never a grade) on >= 95% of unsupported, printed, partial and
  poor-light inputs; no grade on any unsupported item.
- **G-A3** ID false positives with the confidence policy not worse than G3 alone on the same DEV material.
- **G-A4** Grade stability: consecutive accepted assessments of the same item flip <= 5% (consistency, not correctness).
- **G-A5** Gate acceptance >= 70% on good-quality close-ups at >= the chosen size (the gate must not refuse everything).
- **G-A6** End-to-end close-up path (crop + quality + condition + ripeness + rules + price) **p95 <= 600 ms** and wide-scan
  detector frame **p95 <= 250 ms** on the sandbox CPU (2 vCPU, ONNX Runtime FP32). This is a sandbox budget only;
  **phone FPS and camera latency are not measured in Stage G.**
- **G-A7** TypeScript unit / integration tests and Python harness tests pass; Python and TS agree on shared fixtures
  (coordinate mapping, gate, ID policy, price display).
- **G-A8** Price display contract: a price is shown only for a verified category with a current applicable official row,
  always with source, list date, location and unit; never invented; never labelled as a seller price or as a grade-adjusted value.

## Consistency vs correctness reporting rules
- "Stability" / "flip rate" / "consistency" = agreement between assessments; never called accuracy.
- "Correctness" is reported only on CU items whose fresh/rotten label comes from the source (category/title) and was
  agent-verified, with the provenance stated; no A/B/C correctness is claimed (no independent A/B/C labels exist).
- Any accuracy claim carries "agent-verified labels; human review needed before claims".

## Deliverables
Prereg (this file), TS modules + tests, Python reference harness, feasibility table, e2e metrics JSON, demo walkthrough video
and naive-vs-gated comparison video (ffmpeg, licensed stills/footage), emulator/device test plan and script for the user's PC,
report `G9_stageG.md` with an honest acceptance decision.
