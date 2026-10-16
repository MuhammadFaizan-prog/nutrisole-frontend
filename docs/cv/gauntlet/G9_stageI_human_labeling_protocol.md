# G9 Stage I: human-labelling protocol (update of `G9_stageH_human_labeling_protocol.md`)

The Stage H protocol still applies in full: class definitions, item and capture attributes, agreement metrics. This update adds
the Stage I candidate set, blind labelling, and the minimum counts needed before any accuracy claim.

## 1. What is labelled
- **Stage I candidates** (656 group representatives, I0001-I0656; `G9_stageI_data_plan.md`), **plus** the own-photo pilot defined
  in the Stage H protocol, if the team collects one. Own photos are a separate source: their own session ids and their own split.
- **Minimum before any final accuracy claim** (adjudicated, eval splits only):
  - ≥ 100 supported close-ups, with ≥ 20 each for apple, banana, citrus/orange, tomato and carrot.
  - ≥ 60 negatives: unsupported produce ≥ 25, printed/screen/plastic ≥ 10, packaging/bag ≥ 10, occluded/overlapping ≥ 10.
  - Plus 23 other-class supported items (lime, guava, pomegranate) to check that they are not called a priority class.
- Agent labels (source metadata, contact-sheet triage) are **exploratory only** and are never used as ground truth.

## 2. Roles and blinding
- **Annotator A and Annotator B** each label every item on their own, from `review_annotator_blind.csv` and the contact sheets (or the
  linked page, for full resolution). They do not see the source label, the model output or each other's file.
- **Adjudicator** (a third person; the project supervisor or a team member who did not annotate). They hold
  `review_adjudicator_key.csv`, resolve every disagreement and every `unsure`, and write the final label with a one-line reason.
- Neither annotator may be the person who collected the images. The agent never acts as an annotator.

## 3. Columns (blind CSV; one row per item)
`class` (12 supported classes or `unknown`), `unknown_name` (e.g. persimmon), `whole_or_cut`, `supported` (yes/no),
`is_real_produce` (no = printed, screen, plastic, drawing), `printed_or_screen`, `packaging` (none / bag / net / film / tray),
`occluder` (none / hand / bag / other_produce / object), `visible_fraction_est` (100, 75-99, 50-74, < 50), `truncated_by_frame`,
`overlap_other_produce`, `multiple_items` (single / pile / bunch), `condition` (fresh / minor_defect / rotten / cannot_judge),
`ripeness`, `lighting`, `blur`, `phone_style_closeup` (yes = hand-held close range, the item ≥ 30% of the frame),
`confidence` (sure / unsure), `notes`.

**Rules:**
- An image with several items gets `multiple_items` = pile and the class of the **centre** item (the tap point the pipeline uses).
- Maps, illustrations and signs: `is_real_produce` = no and `class` = unknown. They are excluded from the negative counts unless they
  are printed fruit.
- A **bagged or partly occluded** supported item keeps its class (e.g. apple). The bag or occluder goes in its own columns. The pipeline
  must then answer "Not graded" or unable; it must never grade it.

## 4. Steps
1. **Pilot calibration:** 40 items from I-dev (2 sheets). Both annotators label them, compare with the adjudicator, and refine their
   reading of the definitions. These labels are kept but flagged `calibration`.
2. Label I-dev, then I-eval-A, then I-eval-B. Eval rows are labelled only after the I-dev decision rules are written down.
3. Adjudicate. Report agreement **before** any model metric:
   - Cohen's κ for `class`, `supported`, `whole_or_cut`, `occluder`, `condition`.
   - Percent agreement for the rest.
   - **Floor:** κ(class) ≥ 0.85 and κ(supported) ≥ 0.80, otherwise re-train the annotators on the definitions and re-label.
4. Freeze: commit the adjudicated CSV with its sha256 before running any model on I-eval-A/B.

## 5. What the labels unlock
- Genuine-item acceptance, class accuracy, wrong-ID, unsupported acceptance and abstention can be reported as **independently labelled**
  numbers on I-eval-A/B.
- Occlusion leakage on real occluded images (the `occluder` / `packaging` columns), alongside the synthetic suite.
- The I-dev labelled items are the only Stage I images that may enter a future H2 training split (`G9_stageI_finetune_prereg.md`).
  I-eval-A/B and their sources never do.
