# G9 Stage I plan: targeted recognition recovery and mobile readiness

Written and synced **before** any Stage I result. Brief: user message 2026-10-15 01:40 PKT (project file `nutrisole-g9-stageI-gpt.md`).

## Status going in
- Stage H is **closed and failed** (`G9_stageH.md`, 84a0295). Its results, its frozen configs and its training limit (H2: 2 of 2 attempts
  used) stay as they are. Stage I does **not** retrain H2, does not loosen `FROZEN_VERIFY` / `FROZEN_OCC`, and does not overwrite
  any `ml/runs/G9/stageH/` artefact. Anything re-scored on Stage H data is written to `ml/runs/G9/stageI/` and labelled **post-hoc diagnostic**.
- Stage H H-final: 9/99 correct, 0 wrong, 0/77 negatives accepted. H2 alone: 12 correct, 25 wrong. Inner truncation leak 10.9%.
  Close-up p95 1136 ms (GrabCut ~556 ms).
- Priority classes: **apple, banana, citrus/orange, tomato, carrot**. The other 7 G3 classes stay in every model and list (no silent
  relabelling).

## Ground rules
- Branch `cv-gauntlet` only (draft PR #1 follows it). No main, no merge, no PR edits.
- Preservation: no deletes, resets or history rewrites. G3, H2 (.pt + .onnx), datasets, grading, nutrition, price and APIs untouched.
- M-TEST stays sealed. M-DEV not used for tuning. No promotion. No A/B/C grade and no grade-specific price in the app.
- Agent labels are exploratory only. No accuracy claim before the human-labelled set (protocol in the Stage I data plan).
- No fine-tuning in Stage I. At most a separate prereg, written only if the audit justifies it, and not run.
- Free Kaggle only. No photos or clips requested from the user. No Pexels / Pixabay / Mixkit.

## Work items and audit checklist

### I1. H2 audit (existing weights, no retraining)
- [ ] Reproduce the Stage H eval from `ident_items.jsonl` crops; same numbers as `identity.json`.
- [ ] ONNX vs PyTorch (`h2_mnv3s.pt`, timm `mobilenetv3_small_100`) on every eval crop: max |Δp|, top-1 agreement.
- [ ] Class index map: kernel `C` list vs `verify.py H2_CLASSES` vs `verify.ts` vs G3 `N` (wide classId space).
- [ ] Folder → class map in the kernel (Fruits-360 prefixes, Fruit Recognition, Vegetable Image Dataset): any mislabelled folder.
- [ ] Channel order (cv2 BGR → RGB), mean/std, value range.
- [ ] Resize / crop: train `T.Resize(256)+CenterCrop(224)` (PIL bilinear, antialias) vs inference cv2 short-side 256 + centre crop;
      crop padding vs tap box; centre-crop loss on elongated items (banana, carrot); letterbox alternative.
- [ ] Output semantics: ONNX graph ends in softmax; no double softmax; unknown = index 12 treated as a probability, not a logit.
- [ ] Train vs inference transform gap (RandomResizedCrop scale 0.3-1, white-background swap) vs real tap crops.
- [ ] Per-class confusion (supported eval items) and per-source domain breakdown (CU set, H-eval Commons; train source mix).
- [ ] If a bug is found: minimal fix, regression test, post-hoc re-score of the frozen Stage H eval (new file, labelled).

### I2. Data plan (source-separated, human-reviewable)
- [ ] Close-up candidates for the 5 priority classes + negatives (unsupported produce, packaging, printed images, occluded objects)
      from licensed sources only: Wikimedia Commons (per-file CC/PD), Zenodo CC BY, permissively licensed Kaggle / Roboflow Universe /
      Mendeley phone-capture datasets. License + source recorded per item.
- [ ] pHash leakage audit against all existing train/eval sets; split by uploader / source dataset.
- [ ] `G9_stageI_data_plan.md` + updated human-labelling protocol (≥100 supported + negatives, 2 annotators + adjudication) +
      review sheets and CSV.

### I3. Occlusion (CU-tune / DEV only)
- [ ] Targeted cues for inner truncation, hands, bags and overlap.
- [ ] Fast alternatives to full GrabCut (downscaled GrabCut, colour/saliency threshold, tiny segmenter): leakage, clean rejection,
      latency. The rejection policy is not weakened: a new cue may only be **added** (OR-rejection) or replace GrabCut if it is
      no worse on leakage.

### I4. Android readiness
- [ ] Integration layer + tests: preview → full-frame coordinate mapping, high-res crop extraction, model I/O contract
      (ONNX `images` [n,3,224,224] float32 → `probs` [n,13]; ExecuTorch same shapes).
- [ ] Android test instructions + script, dependency set from `G9_stageH_device_test.md`. No FPS claim.
- [ ] No new app dependencies (test-only allowed).

### I5. Fine-tune decision
- [ ] Prereg for a 5-class-focused fine-tune only if the audit shows domain mismatch, not a bug. Not run in Stage I.

### I6. Report
- [ ] `G9_stageI.md`: diagnosis, code changes, tests (TS / py), metrics (genuine acceptance, class accuracy, wrong-ID, unsupported,
      occlusion leakage, abstention, latency), data plan, Android instructions, next experiment.
