# G5 failures (sandbox CPU numbers; not phone/emulator/Lahore)

1. **Pooled gains don't survive video.** ft0 gets pooled mAP50 0.348 vs the G3 control's 0.314, but on the fixed-frame gauntlet it drops det segments 0.667 -> 0.542 and false alarms on the G1 negative clip jump 1.25 -> 17.5/min. Same pattern as A1 in G4: training from A1 (hygiene off) makes the detector fire on clutter.
2. **Video hard negatives didn't help.** fthn (53 agent-reviewed crops x4) raised neg_test image FA to 3.75% and lowered pooled mAP50 vs ft0. 53 crops from 10 non-South-Asian Wikimedia videos is too few and too far from the target scenes; the review was not human.
3. **Tomato regression.** All fine-tunes lose tomato on test_rf (G3 0.68 -> 0.54-0.59); fthnc collapses to 0.17 on test_oiv7c tomato. The 1.5-2.1k subset fine-tune at 480 on CPU, starting from A1, forgets tomato. Strict per-class rule fails.
4. **Temporal smoothing tuned on DEV hurts TEST.** w3 cost one det segment and added static flicker on TEST; with 24 segments one segment is 4 pts, so DEV/TEST disagreement is within noise of this tiny video test.
5. **Low-light classifier misses held-out lighting.** cls5 tube_light_hard rotten recall 0.941 and night_sodium_hard 0.975 (gates 0.992 / 0.983). Synthetic Retinex/colour-cast augmentation does not transfer to the held-out families.
6. **Compute/infra.** GPU kernels g5hn/g5hnc never started (2-session limit); det-v4/v4hyg ended in ERROR; a sandbox restart killed evals mid-run; two closeout agents died before writing. Fine-tunes had to run on Kaggle CPU (~2.5 h each) with reduced data.
7. **No real-world test.** Gauntlet clips are synthetic from locked TEST images (24 segments). Nothing measures Lahore mandi scenes, sodium lighting or a phone camera.
