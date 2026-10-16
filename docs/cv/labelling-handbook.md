# NutriSole labelling handbook — FIRST DRAFT (G1, rubric-v0.1-g1)

Scope: what a human labeller records for the Lahore test set and future fine-tune data. The
app reports VISIBLE condition only. Labellers never record food safety, disease, formalin,
shelf-life, weight, calories or price.

## 1. Output tasks (rule 8.3) — label each separately
1. **Localisation**: one tight axis-aligned box per visible item (include stalk/leaves only if attached).
2. **Produce identity**: one of the 12 v1 classes (banana, apple, mango, citrus, guava, pomegranate,
   lemon_lime, tomato, potato, cucumber, carrot, capsicum) or `unsupported` (any other produce/object).
   Variety is optional free text (e.g. kinnow, malta, mosambi; chaunsa, sindhri; desi/hybrid tomato).
3. **Ripeness stage** (species-specific, or `unknown`):
   - banana: green / yellow-green / yellow / yellow-with-brown-spots / mostly-brown
   - mango, guava, tomato, citrus, capsicum: unripe / turning / ripe / overripe
   - apple, potato, cucumber, carrot, pomegranate, lemon_lime: `not_applicable` unless obvious
   Ripeness is NOT quality: a green banana can be grade A for its stage.
4. **Visible surface defects** (only what you can see): `dark_spot`, `bruise`, `mould`, `rot_soft_area`,
   `cut_or_crack`, `shrivel`, `insect_hole`, `sprout` (potato), `greening` (potato). Mark each with an
   approximate % of the visible surface: <2, 2-10, 10-25, >25.
5. **Visual grade** A / B / C / Reject / ungradable (section 3).
6. **Capture/rejection reasons** for the whole image: blurry, low_light, overexposed, obstructed,
   too_small, multiple_objects, indeterminate_view, unsupported.

## 2. Conventions
- Occlusion: box the visible extent; tick `occluded` if <70% of the item is visible. Do not grade an
  item that is more than half hidden (grade = ungradable, reason obstructed).
- Piles/bunches: box each separable item; for banana hands box the whole hand as ONE banana item
  (G1 convention, revisit in G2). Items cut by the image edge: box what is visible, tick `truncated`.
- Hands in frame are fine; do not box hands. Plastic bags: box the produce if visible through it,
  else `unsupported`.
- Printed fruit pictures, toys, packaging photos: `unsupported` (they are OOD test cases).
- Model-assisted pre-labels (CVAT / Label Studio) are suggestions; a human must confirm or fix every
  box and label. Pseudo-labels are never ground truth until reviewed (rule 8.6).

## 3. Grade rubric v0.1 (PROPOSAL — calibrate with 2-3 graders, report weighted Cohen's kappa)
| grade | visible condition | positive example | negative example |
|---|---|---|---|
| A | no mould/rot, dark marks < 2% of visible surface, colour in the normal ripe range for the variety, normal shape | clean red or green apple, firm yellow banana | banana with several brown speckles (→ B) |
| B | small marks 2-10%, or ripeness slightly off target (still green), or irregular shape | apple with a small bruise; green tomato | soft brown patch ~15% (→ C) |
| C | marks 10-25%, or clearly overripe colour (e.g. banana mostly brown), or mild deterioration (wrinkling) | heavily speckled banana; wrinkled guava | visible mould (→ Reject) |
| Reject | any visible mould or rot, or marks >= 25%, or broken flesh | mouldy orange, collapsed tomato | — |
| ungradable | blurry, dark, glare, too small, mostly hidden, or not a supported item | — | — |

Defect severity thresholds (2 / 10 / 25 %) mirror `ml/grading/rubric_v0.json`; change them only from
measured grader agreement, never by eye.

## 4. Agreement protocol
- 2-3 graders label the same 100-200 Lahore items independently (no model output shown).
- Report weighted Cohen's kappa (linear weights over A<B<C<Reject) per pair and per produce, plus
  % "ungradable" disagreements. Target kappa >= 0.70 before the rubric is used as ground truth.
- Adjudicate disagreements in a short session; log decisions here as rubric v0.2.

## 5. Lahore capture plan (needed before any gate can pass)
- Places: 2-3 sabzi mandis/bazaar stalls + 2 home kitchens. Lighting: daylight, tube light, night stall
  bulb. Phones: one budget (Infinix/Tecno/Redmi) + one Samsung.
- Per class: 150-300 photos (single items, piles, hands in frame), plus >= 40 short videos (10-20 s)
  in total: entering/leaving, hand shake, rotation, near/far, two adjacent items, occlusion and
  recovery, light change, glare, empty stall frames, unsupported items (onion, brinjal, okra, chilli).
- Consent: no faces (crop/blur), no GPS EXIF (strip on import), shopkeeper permission. Store outside Git.
- Split by stall/session/phone: a whole capture session is in ONE split. Lahore test is LOCKED.

## 6. Validators to run on every import (G2 implementation)
class-id outside 0-11, zero-area or out-of-bounds boxes, missing label file, corrupt image, duplicate
MD5/pHash across splits, EXIF GPS present.
