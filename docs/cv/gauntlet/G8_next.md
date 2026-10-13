# G9 plan (proposed at the G8 closeout, 2026-10-14; not run)

CV camera subsystem only. State after G8: **G3 control stays champion** (yolo11n trained 640, deployed 480 raw + class-wise NMS 0.7; G3 E224 quality classifier T = 0.25; scene guard rule 2 off; IouTracker app default). Every G8 number is sandbox CPU, Kaggle free CPU or Kaggle free T4; nothing is phone, emulator, Lahore footage or box-level human verification.

## Next cycle follows the false-positive elimination brief
**The next cycle is driven by `files/nutrisole-g8-fp-elimination-gpt.md` (Hark project "Nutri sole" files, received 2026-10-14 00:30 PKT)**, which is authoritative over the items below where they differ: (A) FP error register of the 74 absence-check tiles in 6 categories + per-class confidence calibration and tracker / provisional-display policy on DEV, frozen before holdout; (B) independent hard-negative mining from non-holdout videos (flicker-based), empty labels only for verified zero-target frames, fine-tunes HN-1 / HN-2 / HN-3 from G3, one factor at a time, seeds, no generic background class; (C) small crop verifier with selective activation; (D) freeze, run holdout once, promotion decision. Holdout tiles / crops never go into training. It also fixes the showcase flaw (5-class training taught the other 7 supported classes as background): compare 12-class-preserving training vs an ignore policy. Not started at G8 closeout.

## What G8 established that G9 must build on
- **VB8-holdout now has human clip-level truth**: 13 verified positive clips (22 clip-class pairs) from 11 uploaders, 16 reviewed negatives (reviewed-moment level, not certified full-clip absence), 5 excluded with reasons (`ml/runs/G8/review/holdout/clip_level_truth.csv`). It is **presence, not boxes**.
- 69-clip auto-label proposals exist (OWLv2 + G3 + ByteTrack keyframes, 26 132 boxes, `ml/runs/G8/autolabel/`), **0 verified boxes**.
- The showcase 5-class fine-tune (G3-init, val-only class selection) moved per-class pooled AP by at most +0.03 (apple s1) and lost tomato; no class got near the 0.60 target. Re-training on the same photo data does not close the gap.
- 66 human-confirmed false boxes on holdout clips: clothing, umbrellas, signs, printed produce, packaging, sacks, equipment, oil-palm fruit, melons, green chilies, mango called apple (`ml/runs/G8/hard_negatives/`). **FORBIDDEN for training** while those clips are holdout.

## P0 (do first, in this order)
1. **Finish the holdout truth**: user video check of #9, #23, #31 (provisional tiles); decide #8 (pale-green fruit) and #21 potato. Then a small **box-level** pass on the 13 positive clips (5-10 keyframes per clip, boxes proposed by OWLv2 + G3, user accepts/corrects) so object/segment recall, TTFC from object onset and ID switches become measurable. Rule 4 stays provisional until then.
2. **DEV-side verification for training data** (VB8-dev 28 clips + train-only 7): review the G8 hard queue items as box-level verdicts (the 2026-10-13 relayed answers looked AI-generated and were not used). Goal >= 150 human-checked mined frames so H1 (hard-example G3-init fine-tune, recipe already fixed in G8 prereg section 3) can finally run, with two seeds.
3. **Hard negatives for training must come from DEV / train-only / new licensed footage**: mine the same object types (clothing, umbrellas, signage, printed produce, packaging, sacks, oil-palm, melons, green chilies) from VB8-dev clips and new Wikimedia Commons / CC0 recordings (never Pexels / Pixabay / Mixkit), verify them, add as background. The G8 holdout tiles are only a description of what to look for.

## P0 class errors
4. Apple false positives on round non-target fruit (oil-palm, melon, mango) and banana on pods / plantain: per-class error clusters on verified DEV frames; class-balanced replay with G3 floor (G7 rfs recipe) + verified hard negatives.
5. Citrus refiner (G8 H5, never run): coarse-to-fine lemon/orange crop classifier only on uncertain citrus/lemon boxes, tau on OIV7c val only.

## P0 adaptive inference (G8 H3, never run for lack of CPU budget)
6. ROI re-detection at 800 for uncertain / small boxes (cap 4 per frame) + tracker between detector passes + keep-only-latest simulation; run it on Kaggle CPU, not the 2-core sandbox. Judge with prereg rule 6 (<= 1.6x p95 and >= +0.03 recall on test_small6 or VB8).

## P1
7. Tracking: the DEV grid pick (ByteTrack nt 0.25, match 0.8, minHits 1) is the A/B candidate; confirm on box-verified holdout clips only (clip-level replay in G8 is descriptive). App default stays IouTracker behind `trackerKind`.
8. Night classifier (`nutrisole-g7-night`): collect when the Kaggle kernel completes and apply the unchanged G7 section-5 gate.
9. Ripeness / defects: de-duplicated per-fruit ripeness exists (G7, test_cc0); next is an independent capture-session benchmark and a separately labelled visible-defect set; abstain when unsure; no internal-quality or food-safety claim.

## P2
10. Distillation only after a model passes the verified holdout (G8 prereg H8 condition not met).

## Still blocked on the user
- Holdout video checks (#9, #23, #31) and a box-level pass on the positive holdout clips.
- Phone / emulator runs and Lahore clips: nothing in G1-G8 is device- or Lahore-validated.
