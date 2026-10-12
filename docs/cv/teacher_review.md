# Open-vocabulary teacher: pseudo-label review protocol (G4.3 design note)

**Rule: no teacher output enters a train or test split until a person has reviewed it.** The teacher only writes *proposals*. G4 put nothing from the teacher into training.

## Teacher
- **Model:** OWLv2 `google/owlv2-base-patch16-ensemble` (Apache-2.0, Hugging Face; licence re-checked at download on the Kaggle run). Grounding DINO (Apache-2.0) is the alternative and has not been run yet.
- **Prompts:** English, one or more per class:
  - "a bell pepper" / "a capsicum";
  - "an orange" / "a kinnow mandarin" / "a malta orange";
  - "a lemon" / "a lime";
  - one prompt per remaining class (see `ml/runs/G4/teacher_owlv2/teacher_eval.json`).
- **Urdu/roman aliases** (kela, saib, aam, kinnow/malta, amrood, anaar, leemu, tamatar, aloo, kheera, gajar, shimla mirch) go into the *review UI labels*, not the prompts. OWLv2's text encoder is English CLIP, so roman-Urdu prompts are untested and likely weak.
- **Output:** per image, boxes with class, prompt and score (score floor 0.05), after per-class NMS at 0.5.

## Where proposals come from (G4 pilot)
- **Measurement only:** `test_rf` and `test_oiv7`, the locked splits. Here the teacher is *scored* against existing GT and nothing is written back.
- **Review queue:** the 144 LVIS val images that the G3 hygiene step dropped because their labels are not exhaustive. A queue item is a proposal with score >= 0.3 that does not overlap (IoU >= 0.5) an existing LVIS box of the same class. These are candidate *missing* labels.
- **Next (G5):** Lahore phone videos sampled at about 2 fps, with the same queue.

## Review steps (each queue item: `ml/runs/G4/teacher_owlv2/review_queue.jsonl`)
1. The reviewer opens the image with the proposal box. A CVAT/Label Studio import of the JSONL boxes as pre-annotations works; any tool that records accept/fix/reject will do.
2. The reviewer sets `decision` to one of:
   - `accept`: box and class are right;
   - `fix`: the box is right after an edit, or the class needs changing (record the new box/class);
   - `reject`: not produce, a depiction, or a group/pile box;
   - `unsure`: escalate.
3. The reviewer follows `labelling-handbook.md` for what counts as one item, occlusion, cut produce and piles. Cut/sliced produce is **not** a grading target, for example the sliced red-pepper strips that make up all 110 test_rf capsicum boxes (`ml/runs/G4/capsicum_testrf_inspect.json`).
4. The reviewer also adds any *missed* items in the same image. Teacher recall is measured against the reviewed image, not against the proposals.
5. Each record keeps `reviewer` (initials) and a timestamp. 10% of items are double-reviewed. If inter-reviewer agreement on accept/reject is below 0.8, the batch is re-reviewed.
6. Only images whose every proposal is resolved, and which a reviewer has checked for missed items, can enter a **new** train split (never test_rf/test/test_oiv7/neg_test). The import script must refuse any item whose status is still `pending_review`.
7. Teacher precision/recall is reported against the reviewed labels each iteration, so the reviewers' corrections can be measured.

## Lahore TEST
A Lahore TEST split comes from markets and days that never appear in train, and is labelled by people, not by the teacher. It is required before any product claim.
