# G4 plan

Rule (unchanged): the locked test, test_rf, neg_test, test_oiv7, the G1 clips and the G2 negtest clip stay byte-identical. New material goes into new, separate splits. DEV material is for tuning only. Kaggle free tier only (T4, at most 2 GPU sessions at once). No paid services.

## Result-driven items from G3 (G3.md, G3_failures.md)

### 0. Promotion rule for G4 (decided in G3)
- Report both views every iteration: the strict G2 rule (test_rf + gauntlet, no per-class regression > 1 pt, no worse negtest FA) and the combined view (pooled test+test_rf+test_oiv7 mAP50 over all classes with GT, video gauntlet, negatives). G3 promoted yolo11n@480 under the combined view only.
- First step: adopt the DEV-tuned tracker for yolo11n@480 (scoreAlpha 0.5, switchMargin 0.1, minHits 3) only if the TEST gauntlet confirms lower flicker without losing segments; regenerate the TS/Python tracker parity fixture.

### A. Fix the per-class detector regressions before anything else
- **capsicum:** inspect all 110 test_rf capsicum boxes against OIV7 "Bell pepper" (0.76 mAP50 on test_oiv7, 0.00 recall on test_rf). If test_rf capsicum is mostly green/long chilli-like peppers or crowded market crates, add matching train data (new split, never test_rf) rather than more bell peppers.
- **citrus / lemon_lime:** re-balance (452 lemon_lime vs 1 543 citrus train instances) and run the two-stage experiment (item 2 below), since a crop type classifier attacks the citrus/lime confusion directly.
- **Locked test:** ablate the two det-v3 changes on the same yolo11n recipe (hygiene off vs on; backgrounds 28% vs ~15%) to separate their effect on the crowded locked test (0.315 G2 -> 0.224 G3) from their FA benefit. Try LVIS ignore-masking (unknown-status classes masked out of the loss) instead of dropping images.
- Keep the deploy-size rule, but break ties within 0.01 test_rf by CPU latency (the G3 rule picked 640 px by 0.001).

### B. Make the gauntlet comparison deterministic
- Add a fixed-frame mode (`--no-realtime`, every frame processed) for promotion comparisons, and report latency/dropped frames from a separate run on an idle CPU. Run each promotion-relevant gauntlet twice and report the spread. G3 showed ~1 FA/min and ~2.5 flicker/10s run-to-run noise with identical configs.
- Decide scene-guard rule 2 (maxSameClass 6 vs off) on the deterministic replay: DEV prefers off, the locked clips showed no measurable cost or benefit.

### C. Classifier calibration and low light
- Build a harder held-out crop VAL (detector crops from det-v3 val images of rotten/fresh-looking produce, plus low_light_hard / tube_light_hard copies) so model selection and temperature fitting are not saturated. Refit T for the promoted G3 E224 classifier (T = 0.25 now; ECE got worse).
- Low-light rotten recall 0.941 is still below the 0.95 gate: add a stronger low-light family to training and check that rotten recall on item crops stays >= 0.983.

### D. Carry-over
- yolo11n 480 multi-scale finished in G3 (rule candidate at 384); see G3.md for its gauntlet. A yolo26n 480 multi-scale kernel (`kaggle/g3/k_nutrisole-g3-det-yolo26n-480ms`) was prepared but not run in G3.
- LiteRT export is still blocked on aarch64 (unchanged).

## User-approved additions (2026-10-12)
These were approved by the user for G4. Each item needs its own design note in `docs/cv/` before any code is written.

### 1. Open-vocabulary teacher for Lahore market videos (human review required)
- **Teacher:** Grounding DINO or OWLv2. Use open weights only: Grounding DINO (Apache-2.0, IDEA-Research) or OWLv2 (Apache-2.0, google/owlv2 on Hugging Face). Re-check each licence at download.
- **Labelling flow:**
  1. The teacher runs offline (Kaggle T4) on phone videos recorded in Lahore markets.
  2. It samples frames at about 2 fps and prompts with the 12 class names plus Urdu/local aliases (kela, saib, aam, kinnow/malta, amrood, anaar, leemu, tamatar, aloo, kheera, gajar, shimla mirch).
  3. It writes **proposals** only.
- **Review is mandatory.** Every proposal is accepted, fixed or rejected in a labelling tool, following `docs/cv/labelling-handbook.md`. Nothing goes into a train or test split unreviewed.
- **Reporting:** report teacher precision/recall against the reviewed labels, so the reviewers' corrections can be measured.
- **Splits:** a Lahore TEST split is collected from markets and days that never appear in train. This is the first real-domain test and is required before any product claim.
- **Guava:** this is the realistic route for guava, which has no OIV7 class.

### 2. Two-stage pipeline experiment
- **Stage 1:** a class-agnostic "produce" detector (all 12 classes merged into one, plus OIV7/LVIS produce boxes from other classes as the same "produce" class).
- **Stage 2:** a crop classifier that outputs **type** (12 classes + "other/unsupported") and **quality** (fresh/rotten). Quality is either a multi-head output or the existing quality classifier.
- **Compare against the single-stage detector** on test_rf, test_oiv7 and the gauntlet. Use the same promotion rule, plus CPU latency for detector + classifier per frame.
- **Motivation (G2/G3 failures):** class confusions (citrus vs lemon_lime, tomato vs capsicum/pomegranate) on whole scenes. A crop classifier sees the item at higher resolution and can be trained on far more single-item photos than box-labelled scenes.

### 3. Separate ripeness output
- **New head/classifier:** unripe / ripe / overripe, kept separate from fresh/rotten quality. Only for classes where ripeness matters to a buyer: banana, mango, tomato, guava, and optionally citrus/kinnow colour.
- **Data:**
  - Lahore panel labels (handbook extension).
  - Public ripeness sets only after a licence check.
  - The quarantined 3-level "mild" experiment showed that fresh/rotten labels cannot be stretched into a middle level (mild recall 0.24). Ripeness needs its own labels.
- **Display:** shown as a separate chip, never merged into the A/B/C grade until human graders validate a mapping.

### 4. Segmentation model for defect area
- **Model:** the proposal lists a segmentation model for defect area. Candidates are a YOLO-seg nano (yolo11n-seg / yolo26n-seg) trained on defect masks, or a small U-Net/DeepLab-MobileNet. Pick whichever exports to ONNX/LiteRT under the latency budget.
- **What it replaces:** the hand-tuned colour/shadow mask in `ml/grading/measure.py` (measure v0.3) for `defect_area_pct`.
- **Data:** about 300-500 defect masks (Sultana rotten images + Lahore photos), labelled per the handbook.
- **Metrics:** report mask IoU and the error in defect-area % against human masks. Rubric thresholds stay untuned until a human panel exists.

### 5. Market-price reference range from official Pakistani government prices only
- **Sources, in priority order.** Only official sources are allowed; no scraping of private apps or marketplaces.
  1. **Market Committee Lahore / PAMRA daily retail rate lists, grade 1 and grade 2**, published by District Lahore:
     - fruits: https://lahore.punjab.gov.pk/fruits-rate-list
     - vegetables: https://lahore.punjab.gov.pk/vegetables-rate-list

     Checked 2026-10-12: both pages list one entry per date (Oct 7-12, 2026), and the retail list is a **JPEG image** (WhatsApp photo) linked under "Retail Price". The "Wholesale Price" column was empty. This needs **OCR** (e.g. Tesseract/PaddleOCR with Urdu+English, which are open source) plus a per-row human check of the parser on the first weeks of lists.
  2. **Punjab AMIS wholesale prices**, http://www.amis.pk/. The site responded HTTP 200 from the sandbox on 2026-10-12. Prices are reported in Rs/100 kg (as the user specified; the unit still has to be confirmed on the page). Convert to Rs/kg and label them "wholesale".
  3. **Pakistan Bureau of Statistics weekly SPI**, a fallback only when 1 and 2 are stale or missing. Source: https://www.pbs.gov.pk/price-statistics/ (weekly SPI report + annexure PDF/Excel, 51 essential items in 17 cities). Label it "national weekly average".
- **Mapping:**
  - Grade **A** -> grade-1 price.
  - Grade **B** -> grade-2 price.
  - Grade **C** / **Reject** -> no price, or a note: "below market grade; expect a discount".
  - The range is shown as a reference, never as an offer or a valuation.
- **Date and staleness:**
  - Always show the rate-list date and the source name.
  - Flag the price as **stale** when the list is older than 2 days (retail) or 7 days (SPI).
  - Never show a price for a class or variety missing from the list (e.g. kinnow vs malta must be matched explicitly).
- **Engineering:**
  - A daily fetch job writes a dated JSON with source URL, fetch time, OCR text, parsed rows and a confidence score per row.
  - The app reads the newest valid JSON.
  - Rows the OCR cannot parse are dropped, not guessed.
- **Docs:** cite every source URL in `docs/cv/prices.md` (to be created) with the date checked. Respect each site's terms and fetch at most once a day.

## Gates that remain unverified
These cannot be closed in the sandbox: phone/emulator run, Lahore data, human grading panel/kappa, and real-world latency.
