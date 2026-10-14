# G9 Stage I: preregistration of a 5-class-focused H2 fine-tune ("H3"). WRITTEN, NOT RUN

**Status:** recommended, **not run in Stage I**. It may only start once its precondition (P0) is met, and it needs the user's go.
Stage H's H2 training limit (2 of 2 attempts) is not reopened. H3 is a separate, newly preregistered experiment, motivated by the
Stage I audit.

## Why (Stage I audit, `G9_stageI.md` §1)
- **No implementation bug:**
  - ONNX equals PyTorch (max |Δp| 2e-6).
  - The class maps agree across the kernel, `verify.py`, `verify.ts` and G3.
  - RGB, ImageNet mean/std and softmax semantics are all correct.
  - The PIL train-eval transform gives the same results as the cv2 inference path.
- **The failure is domain mismatch:**
  - Supported classes were learnt mainly from studio/lab images (Fruits-360 100 px white background, Fruit Recognition trays,
    Vegetable Image Dataset), with only 1-46 real Commons photos per class.
  - The only class with many diverse real photos was `unknown` (89 Commons negatives).
  - Result: real close-ups collapse into `unknown`, `potato` or `cucumber`. On new phone-capture sources, top-1 is 20% on FruitNet and
    0/30 on carrot crops, and citrus is at 5/80 overall.
- **Secondary data issues to fix in any future kernel:**
  - The prefix folder map relabelled Mangostan → mango and Potato Sweet → potato. The corrected map is `ml/eval/h2_labels.py`.
  - The tap_roi patch crops do not match how the model was trained (post-hoc, eval only).

## P0. Precondition (blocking)
The human-labelled Stage I set exists per `G9_stageI_human_labeling_protocol.md`:
- I-dev adjudicated.
- I-eval-A/B adjudicated and frozen (sha256 committed).
- κ(class) ≥ 0.85.

**No GPU is spent before P0.**

## Design (fixed now)
- **Model:** same architecture (timm `mobilenetv3_small_100`, 13 outputs: 12 classes + unknown), initialised from the Stage H v2 `.pt`.
  The 13-way head is kept: **no class is dropped or merged**, and the other 7 classes keep their labels. "Focus" means sampling and
  loss weight, not relabelling.
- **Training data** (sources disjoint from every eval source):
  1. Human-labelled I-dev (Commons uploaders 0-3).
  2. Licensed phone-capture sources not used in any eval split: VegNet Bangladesh (Mendeley 68zgy243yb), Tomato Maturity
     (s42kpg8h37), VegNet India (6nxnjbn9w6), Zenodo 18904638.
  3. The existing Kaggle pools at ≤ 30% of draws, with `h2_labels.folder_to_class`.
  - FruitNet, carrot_m and tomato_m are I-eval-B sources and **never** enter training.
  - Every training image is pHash-checked in-kernel against all eval hashes (Hamming ≤ 10 → drop).
- **Crops:** training samples are made the way the pipeline crops. That means detector-box or tap-ROI crops of the training photos
  (stageH and square modes, sides 96-400 px), and the true box for whole-object crops. `unknown` has real-photo negatives in the same
  proportion as each supported class, to remove the "real photo → unknown" shortcut.
- **Sampling:** the 5 priority classes get 2× class weight. The other 7 classes ≥ 1× (balanced). Unknown is balanced by source.
- **Free Kaggle GPU only, one attempt plus at most one retry** for an infrastructure failure (no change of data or criteria). The
  `.pt` is saved before export.

## Frozen evaluation (I-eval-A and I-eval-B, each opened once; human labels)
- **Policy:** P-a (wide + H3 agree) and H3-only, with thresholds frozen on I-dev.
- **Success requires all of:**
  1. Priority-class correct verification ≥ 0.60 on I-eval-A **and** ≥ 0.50 on I-eval-B.
  2. Wrong-ID acceptance ≤ 3% of supported items, and 0 wrong-ID among the 5 priority classes on I-eval-A.
  3. Unsupported / printed / packaging acceptance ≤ 2%, and 0 graded.
  4. No other-class item (lime, guava, pomegranate, ...) accepted as a priority class above 3%.
  5. H3 p95 ≤ 60 ms (sandbox CPU).
- **Report** genuine-item acceptance, class accuracy (confusion), wrong-ID, unsupported acceptance, abstention and occlusion leakage
  (Stage H synthetic suite + human-tagged real occlusions) separately.
- **No promotion and no user-facing grade** follow from H3 alone. Grade display needs its own frozen criteria and an independent
  validation.
