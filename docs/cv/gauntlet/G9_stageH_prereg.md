# G9 Stage H prereg: close-up identity verification and occlusion safety

Written and synced **before** any Stage H candidate was run or any Stage H number was produced (2026-10-14, PKT).
Authoritative brief: user, 2026-10-14 22:04 PKT (P1-P6 + deliverables). Starting point: Stage G report `G9_stageG.md` (a144eae, NOT
accepted): close-range ID 6/19 correct, 8/11 grades on a wrong ID, 35/878 degraded CU-check crops graded (24 occlusion), 96 px gated
flip 0.18 / correct 0.73, 3-frame gate acceptance 0.679, 1 unsupported + 2 cut items graded.

## Fixed (not under test)
- **G3 unchanged** (`det_yolo11n_640_raw`, imgsz 480, conf 0.35, NMS 0.7, 1% guard, IouTracker). No detector training, no YOLO
  training of any kind, no new detector classes. 12 classes: banana, apple, mango, citrus, guava, pomegranate, lemon_lime, tomato,
  potato, cucumber, carrot, capsicum (capsicum = a whole bell pepper).
- Condition model E224, rules `rubric-v0.2-g2`, `measure.py`, ripeness chip (separate), official price module G4.6.
- Stage G frozen gate kept as the baseline layer: 96 px of full-res frame side, 3 agreeing frames, blur >= 15, mean V 80-245, no edge
  contact, visible surface >= 0.25, condition max-prob >= 0.7 / margin >= 0.3, JPEG blockiness <= 1.4. Its baseline numbers are
  re-reported unchanged next to every Stage H number.
- Protected scope untouched (nutrition, glucose, diet/exercise, footwear, assistant). Branch `cv-gauntlet` only; no main, merge or PR.
- **No A/B/C grade is displayed in the app in Stage H, whatever the result.** A/B/C needs human-labelled ground truth (P4) first.

## Arms
- **H0** = Stage G pipeline as frozen: wide G3 identification policy (score >= 0.5, >= 3 hits, not citrus-ambiguous) -> tap -> gate -> grade.
- **H1** = H0 + **G3 re-run on the full-resolution close-up crop** (crop padded 8%, letterboxed to 480, G3 post-processing). The
  detection whose box contains the crop centre with the largest area is the H1 class. Question answered: does it correct or repeat the
  wide-scan class error?
- **H2** = H0 + a **separate lightweight close-up classifier with an explicit reject**: MobileNetV3-Small (timm `mobilenetv3_small_100`,
  ImageNet init; fallback EfficientNet-Lite0 if MobileNetV3-S fails to train) with **13 outputs = 12 supported classes + `unknown`**,
  224 px, exported to ONNX (FP32) for the sandbox and the app runtime.
  - **Hypothesis (documented before training):** the wide detector confuses close-range items because it was trained on scene-scale
    boxes; a classifier trained on independent licensed close-ups *plus explicit unsupported negatives* separates the 12 classes from
    look-alikes (persimmon vs citrus/tomato, plum/peach vs apple, papaya vs mango, kiwi vs potato/guava, avocado vs mango/guava) and
    rejects printed fruit and cut items, so that wrong identities at close range drop to ~0 while >= 60% of legitimate whole items are
    still verified.
  - **Training data (independent):** (a) Wikimedia Commons per-file CC / PD photos (new search, licence + author + page per file),
    (b) the permissive Kaggle set Fruits-360 (`moltean/fruits`, CC BY-SA 4.0) for class coverage (studio close-ups), never Pexels /
    Pixabay / Mixkit. `unknown` = persimmon, plum, peach, papaya, kiwi, avocado (+ pear, apricot, lychee, onion, eggplant, other
    produce), printed / drawn fruit, and **cut / sliced / peeled** items of the 12 classes (a cut item is not a gradable whole item).
  - **Training is allowed ONLY for this classifier, ONLY on free Kaggle** (`mfaizannnn`, GPU if a free slot else CPU; never paid).
- **H-final** = the identity policy below + the occlusion check below + the Stage G gate, all frozen on tune splits before eval.

## Identity policy (how H1/H2 combine)
Candidates compared on tune splits only:
- **P-a H2-confirm:** identity verified iff H2 accepts (top class != unknown, top prob >= tau, margin >= m, unknown prob < u) **and**
  the H2 class equals the wide G3 class.
- **P-b H2+H1-veto:** P-a, and additionally H1 must not contradict: if G3 on the full-res crop returns a *different* class with score
  >= 0.5 (and no box of the wide class), the result is "Unable to identify".
- **P-c H1-only:** verified iff G3 on the crop returns the wide class with score >= 0.5 (tests whether a second G3 opinion alone helps;
  the brief states two G3 agreements alone are not proof of correctness, so P-c is a comparison arm and cannot be picked).
- citrus vs lemon_lime: a disagreement between them counts as contradictory -> "Unable to identify".
- **Any** uncertain (H2 below threshold or unknown) or contradictory (H2 class != wide class, H1 veto) result -> **"Unable to
  identify"**: no name, no grade, no price. Uncertain identity is never passed to the grader.
- **User-assisted fallback (separate UX arm, not accuracy):** when the result is "Unable to identify" but H2's top-2 includes a
  supported class, the app may ask "Is this a <class A> / <class B> / something else?". A user confirmation unlocks the **category
  reference price only** (never a grade). Reported as a UX arm with a simulated oracle user and a simulated careless user (always taps
  the first suggestion); never added to identity accuracy.
- Selection rule (frozen now): among P-a / P-b and the (tau, m, u) grid, choose the setting with the **lowest wrong-identity acceptance
  on tune**, subject to correct-item acceptance >= 0.60 on supported whole items; ties -> stricter.

## Occlusion-check candidates (P2)
The Stage G checks stay. New cues, each computed on the analysis crop:
- **O1 mask coverage / shape:** GrabCut foreground mask solidity (mask area / convex hull area) and ellipse fill (mask vs fitted ellipse).
- **O2 visible-boundary completeness:** fraction of the mask contour lying on long straight segments (occluder / frame edges are
  straight; produce outlines are curved) and fraction of the contour supported by an image edge.
- **O3 foreground segmentation consistency:** GrabCut mask vs a second, independent CPU segmentation (Otsu / saturation-based
  foreground); low agreement = something else is inside the "item".
- **O4 part consistency (classifier evidence, not colour):** H2 on 4 half-crops (left / right / top / bottom); a half that H2 calls
  `unknown` or a different class with confidence -> occluded / mixed.
- **O5 texture/flatness:** fraction of the mask that is a flat, low-texture blob with a hard boundary (flat occluders, plastic glare).
- Rule: an OR of a small subset of cues (no single cue of area, confidence or colour alone is allowed to be the only check), thresholds
  chosen on **CU-tune** occluder suite to minimise leakage subject to clean-crop false rejection <= 0.20.
- **Extended degradation suite:** occluders of varied colours (red, green, blue, white, black, grey), skin-coloured blocks (Stage G
  baseline) and skin-coloured finger/hand shapes (synthetic, plus Commons hand photos if licensed ones are found), plastic bag
  (translucent wrinkled overlay with glare), neighbouring produce (another item's crop pasted over 30-50%), partial / truncated objects
  (25% and 40% cut at the frame border), coverage 30% and 50%, random side. Stage G's blur / low-light / JPEG / truncation kept.

## Data and splits (DEV only; M-TEST untouched)
- **H-set (new, independent close-ups):** Commons search per class + unsupported + printed + cut; pHash (imagehash 64-bit) audit
  against G3 train, DEV (val + clips), Stage D/E/F Commons pools, M-DEV / M-TEST hashes (hashes only), CU (191 Stage G candidates)
  and the Kaggle training images; any hit at Hamming <= 10 or title overlap is dropped. Split **by uploader** into **H-train**,
  **H-val** (tuning) and **H-eval** (reported after freezing). Fruits-360 goes to training only.
- **Tune:** H-val + CU-tune (identity thresholds, occlusion thresholds). **Eval (reported once, configs frozen first):** H-eval +
  CU-check (identity, occlusion suite, approach simulation, unsupported/printed/cut stills from the Stage G triage).
- **M-TEST is not opened.** M-DEV is not used for tuning.

## Frozen acceptance criteria (DEV eval splits)
| ID | Criterion | Threshold |
|---|---|---|
| H-A1 | Wrong-identity grading rate (grades issued on a wrong ID / all grades), CU-check approach + H-eval | **0 on CU-check and <= 1% pooled** (≈ 0) |
| H-A2 | Wrong-identity acceptance (verified but wrong, supported items) | <= 3% of supported items |
| H-A3 | Unsupported / printed / cut false acceptance (identity verified) | <= 2%, and **0 graded** |
| H-A4 | Occlusion leakage (graded / occluded-or-truncated crops, extended suite, CU-check, 96 + 192 px) | <= 3% overall and <= 5% per occluder type |
| H-A5 | Minimum correct-item acceptance (anti "safe by rejecting everything") | correct-ID verification >= 0.60 of supported whole items; clean crops wrongly rejected by the occlusion check <= 0.20; clean supported crops reaching a gated grade >= 0.40 |
| H-A6 | Latency (sandbox CPU, ONNX FP32; not phone) | H2 p95 <= 60 ms; close-up path incl. identity + occlusion p95 <= 700 ms |
| H-A7 | Tests | TS + Python pass, Python/TS parity on the new policy + occlusion rule |
| H-A8 | Display contract | no A/B/C, no grade-specific price; category reference price only when identity verified and source verified |

Grading (fresh/rotten agreement with agent labels) is reported but is **not** an acceptance criterion: labels are not human-verified.

## Labelling rule (exploratory only)
All Stage H labels (class, whole/cut, supported/unsupported, fresh/rotten) come from the Commons title / category / search query plus
an agent visual check of contact sheets. **No human annotator is available, so every Stage H metric is exploratory and agent-labelled;
no claim of independently verified accuracy is made.** The human-labelling protocol (P4) defines how a future independent set is built.

## Outputs
Identity comparison (H0/H1/H2/H-final), occlusion analysis (35-leak diagnosis + extended suite), DEV metrics against H-A1..A8,
human-labelling protocol, TS modules + tests, dependency review, Android device plan update, demo video, acceptance decision
(`G9_stageH.md`).
