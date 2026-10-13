# G8 failures, gaps and things that did not run (2026-10-14 closeout)

Listed so nothing is dropped silently. "Not run" means no number exists; nothing below is estimated.

## Results that failed their pre-registered rule
1. **Showcase track (Addendum 2026-10-13 S3): FAIL.** 0 / 5 selected classes reach pooled mAP50 >= 0.60 for either seed (best: citrus s0 0.462, n=829 pooled, CPU, 480). Per-class change vs G3 is small: s0 citrus +0.010, apple +0.016, banana +0.001, carrot +0.015, tomato -0.022; s1 apple +0.035, tomato -0.040, banana -0.010. The 0.60 target was the user's suggested value, fixed before selection; it was far above every G3 pooled per-class AP for these classes (0.25-0.45), so the fail is a data/domain limit, not a near miss. Nothing was re-run or re-thresholded.
1b. **Showcase design flaw (user-identified 2026-10-14 00:30 PKT): the 5-class head was trained with labels for citrus / apple / banana / tomato / carrot only, so every visible but unlabelled guava, mango, pomegranate, potato, cucumber, capsicum and lemon_lime box in the G3 training images was implicitly taught as background.** Those classes are visually close to the selected ones (lemon_lime vs citrus, mango / guava / pomegranate vs apple, capsicum vs tomato), so the model was pushed to suppress real produce that resembles its own classes. This likely explains part of the S3 failure (it is an inference, not measured in G8). Must be fixed before any future subset model: either keep all 12 classes in training and only select / display the subset at inference, or use an ignore policy (mask the loss for unlabelled-class boxes instead of treating them as negatives); compare both, one factor at a time.
2. **No general detector candidate (H1 / H2) existed** at closeout: H1 needs >= 150 human-checked mined frames and G8 produced **0 verified boxes** (26 132 auto-label proposals only). Rules 1-8 therefore had nothing to judge except the showcase model, which is not a 12-class replacement.

## Pre-registered work that did not run (with reason)
3. **H1 hard-example fine-tune, H2 Albumentations ablation**: blocked by item 2 (no verified mined frames).
4. **H3 adaptive ROI re-detection / SAHI on uncertain crops / keep-only-latest simulation**: not run. The 2-core shared sandbox was saturated by auto-label stage 1, the tracker grid, the showcase evaluation and repeated OOM restarts; it was not moved to Kaggle in time.
5. **H5 citrus refiner**: not run (same budget reason; depends on a tau chosen on OIV7c val, not done).
6. **H6 night classifier**: Kaggle `nutrisole-g7-night` still RUNNING at closeout (started in G7); collector `g7_night_post.sh` left running; no gate result. Note: that collector logs path errors (`g7logs/progress.md: No such file or directory`) from an older running copy; check its output when the kernel completes.
7. **H7 visible-defect agreement**: not measured (no independently labelled defect set in G8). Ripeness: only the G7 de-duplicated numbers and the G8 hue-shift sweep exist (no new ripeness model).
8. **H8 distillation**: deferred by its own precondition (no promoted / near-pass H1 model).
9. **Rule 3 historical TEST gauntlet and rule 5 neg_test FA for the showcase model**: rule 3 not run (the showcase had already failed S3 rule 1; S3 does not require it); neg_test FA run at closeout only as a report item.

## Human-review gaps
10. Holdout truth is **clip-level presence, not box-level** -> object/segment recall, TTFC from object onset and ID switches on VB8-holdout are **not measurable**; G8 reports clip presence recall, FA/min on negatives, a TTFC proxy from clip start, track births and label changes instead.
11. Negatives are "no supported produce in the reviewed moments" (top-4 detector moments + 6 sampled frames per clip), **not certified full-clip absence**; two clips (#13, #32) had zero detector hits.
12. Pending: #9 (c32085ee7), #23 (c6473db48), #31 (c82e63d5a) - provisional tiles, video check pending; excluded. Uncertain: #8 (pale-green fruit, apple or guava) and #28 (chilies; capsicum = whole bell pepper); excluded. #21 potato "to confirm" excluded from recall.
13. The 30-item hard-queue verdicts relayed on 2026-10-13 appeared AI-generated; logged as proposals-level only and not used anywhere.

## Engineering failures (all recovered or recorded)
14. Sandbox OOM / restarts (several per hour on 2026-10-13): auto-label merge killed twice (rc 137) -> moved to a Kaggle CPU kernel; showcase pooled eval restarted once.
15. Tracker DEV grid: config nt0.35_mt0.9_mh2 failed three watchdog retries (log never written; jobs killed by restarts); one final closeout attempt was made (see G8.md for its result). The TEST run of the pick (g1clips) had an empty log after restarts; one closeout attempt was queued.
16. Holdout replay kernel v1 failed (Kaggle auto-extracts uploaded tar files, so the code-tar lookup found nothing); v2 fixed the lookup; no clip had been processed by v1.
17. The showcase collector's own gh sync runs without GitHub credentials and may log a sync failure; the closeout synced with credentials instead.

## Failure modes seen in the footage (from the human absence check; DEV-only use)
18. G3 / OWLv2 fire on clothing, umbrellas, signs, printed produce and packaging, sacks, equipment / utensil handles, oil-palm fruit (as apple), melons (as apple), green chilies (as capsicum), mango (as apple), pods / plantain (as banana). 66 tiles, `ml/runs/G8/hard_negatives/g9_hard_negative_list.csv`, **forbidden for training while the clips remain holdout**.
