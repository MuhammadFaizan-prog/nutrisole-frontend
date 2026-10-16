# G5 plan

Rule (unchanged): the locked test, test_rf, neg_test, test_oiv7, the new test_oiv7c, the G1 clips and the G2 negtest clip stay byte-identical (hashes in `ml/runs/G4/locked_hashes.json`). New material goes into new splits. DEV material is for tuning only. Kaggle free tier only (T4, at most 2 GPU sessions; CPU kernels as fallback). No paid services.

## 0. Promotion rule for G5 (unchanged from G4, now on the deterministic gauntlet)
- Report both views: **strict** (test_rf better, no test_rf per-class regression > 1 pt vs the strict reference, fixed-frame gauntlet det segments not worse, no worse negtest FA) and **combined** (pooled n=829 mAP50 + fixed-frame gauntlet + both negative clips + neg_test image rate).
- The gauntlet comparison is always fixed-frame (`--no-realtime --stride 1`), two runs per candidate; latency is a separate, labelled measurement.
- A candidate that wins the still-image metrics but loses the gauntlet is not promoted (A1 in G4); write down why before looking at the next result.

## 1. Deferred from G4 (cutoff 14:05 UTC 2026-10-12)
- **Evaluate det-v4 and det-v4hyg** as soon as their Kaggle outputs are downloaded (`kaggle kernels output mfaizannnn/nutrisole-g4-det-v4[hyg]`): pooled n=829, test_oiv7c n=181, strict per-class vs G1, neg_test FA, fixed-frame gauntlet r1/r2 vs the G3 control. Label det-v4hyg as test-informed in every table; it can only be promoted if it also wins on a split it was not designed against (the gauntlet and negatives).
- **Ripeness rerun:** map `Overipe` -> overripe in `lab()`, assert every class has >= 50 train images before training, fix the Mendeley download, report test_cc0 (n=180) per-class recall.
- **Two-stage v2:** train a real 1-class produce detector as stage 1 and a type classifier on more single-item crops; compare with the same AP code and report CPU latency per frame (G4: 49 -> 122 ms p50).

## 2. Make the image and video signals agree (G4 failure 1)
- **Hygiene as a weight, not a switch:** keep the LVIS crowded images but mask unlabelled regions (grey fill, as in the OIV7 audit) or down-weight them, instead of dropping (G3) or keeping raw (A1). One ablation, same recipe, evaluated on both views.
- **Use reviewed OWLv2 labels to fix the crowded images:** review the 1 172 queued proposals (`docs/cv/teacher_review.md`; 10% double review, agreement >= 0.8), then retrain with hygiene off on the *completed* labels. This attacks the cause inferred in G4 (unlabelled produce in piles) directly.
- **More gauntlet coverage:** add one more synthetic det clip and one more negative clip built only from locked test images (new, separately hashed), so 24 segments is no longer the whole gauntlet signal.

## 3. Classes: lemon_lime, citrus, guava
- Two-stage pipeline: finish the type classifier (12 classes + other) on single-item crops (`ml/data/build_type_crops.py`) and compare detector+type vs single-stage on test_rf, test_oiv7, test_oiv7c and the gauntlet, with CPU latency per frame.
- Guava: find a licence-clean box-labelled source or label Lahore photos; until then guava stays "unsupported" in the app.
- Capsicum on test_rf is sliced strips (non-target); report it but do not chase it.

## 4. Classifier robustness
- Do not promote on test accuracy (saturated). Pick on the held-out synthetic conditions (low_light, low_light_hard, tube_light_hard, night_sodium_hard) with rotten recall as the primary metric, stated before training.
- Train with a mix of low-light families (tube, sodium, generic) and keep one family fully held out per run, rotating, so G4's "fixed one family, broke the neighbour" shows up in selection.

## 5. Ripeness, segmentation, prices
- Ripeness: interface is in (`ml/grading/ripeness.py`, `native/src/cv/pipeline/ripeness.ts`); train on the licence-checked public sets (CC0 Kaggle ripeness set, Mendeley banana CC BY 4.0) and report test accuracy per class; display only as a separate chip.
- Defect segmentation (yolo11n-seg or small U-Net) for `defect_area_pct`: label ~300 masks first.
- Prices: extend the OCR lexicon with held-out dates before trusting it; keep "drop, never guess" for unmatched rows.

## Gates that remain unverified
Phone/emulator run, Lahore data, human grading panel/kappa, real-world latency. CAPA data stays research-only pending ULG consent.
