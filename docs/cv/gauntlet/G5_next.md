# G6 plan (proposed; not run)

Priority is data, not more model variants.

1. **Real Lahore clips (user):** 15-20 phone clips, 10-20 s, mandi/cart/shop; banana, apple, tomato, citrus, capsicum, cucumber, carrot, guava; mixed piles, in hand, some rotten; half daylight, half shop/sodium light. Split by location: train vs a locked Lahore test.
2. **External web test `web-mandi`** (in progress in `/workspace/work/cv/g6src`): only Wikimedia Commons clips with CC0/CC BY/CC BY-SA/PD licences, split by uploader with >= 40% locked. Pexels, Pixabay and Mixkit are **rejected** (Pexels/Pixabay ToS s.8 forbid scraping for machine learning; Mixkit grants no ML use). CC BY YouTube clips are verified but not downloadable from the sandbox (HTTP 403). Label honestly as externally sourced, never as Lahore data.
3. **Licensed quality datasets:** FruQ-DB (Zenodo 7224690, CC BY 4.0; frames derived from YouTube time-lapses, provenance caveat) and Zenodo 17609211 (CC BY 4.0, FruitNet-derived) for the quality classifier, with lighting held out.
4. **Detector:** fine-tune from the **G3 control** (not A1) at full data on a GPU slot, with tomato-weighted sampling; then hard negatives mined from web-mandi TRAIN clips only, human-reviewed.
5. **Bigger video test:** >= 60 segments so one segment is < 2 pts; r1/r2 for any candidate.
6. Finish ripeness (Kaggle run in flight at G5 close) and the OWLv2 review queue (needs human review).
7. Class-specific thresholds on the G3 control, chosen on DEV, checked once on TEST.

## Merged with the user's external review (GPT, 2026-10-13)
Adopted: dataset audit first (FiftyOne near-duplicates, one label dictionary, whole vs cut produce, OWLv2 boxes checked, splits by source/session/video); >= 60-clip independent video benchmark, no single uploader > 25%, rules frozen before results; fine-tune **G3** with replay of its original training mix, low LR, class-balanced sampling, 2-3 seeds, close_mosaic; ByteTrack / BoT-SORT vs the current tracker (grade needs consecutive evidence, reset on scene change), measuring missed-object time and display delay too; Albumentations lighting (RandomGamma, PlanckianJitter, ISONoise, mild MotionBlur) with a reduced-colour arm for ripeness; SAHI only offline / opt-in high-res mode; separate ripeness, defect and freshness heads with an "unable to assess" state; bootstrap CIs over recordings, day/night split; new final holdout if a locked split influenced selection (G5 test_rf_nostrips stays a labelled VIEW).
Corrections to the review: the held-out night_sodium_hard rotten recall of the **champion** is 0.983 (it passes); 0.941 was G4 cls4. Android/ONNX Runtime Mobile/XNNPACK/quantization benchmarks cannot run in the sandbox (no phone, no emulator); they need the user's device. FruQ-DB upstream YouTube rights stay a provenance caveat.
