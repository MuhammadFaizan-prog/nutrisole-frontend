# G9 Stage H: human-labelling protocol for an independent close-up set (P4)

Status: **protocol only.** No human annotator was available in Stage H, so every Stage H number is exploratory and agent-labelled. This
protocol defines how a future independent close-up set is built and labelled before any identity, fresh/rotten or A/B/C accuracy claim
is made or any A/B/C grade is shown in the app. M-TEST stays sealed and is not part of this set.

## 1. Scope and set composition
- **Items:** one physical item per record, photographed (or video-framed) at close range: the item side covers >= 96 px of the
  full-resolution frame, and preferably >= 256 px.
- **Pilot (first batch): >= 100 items, balanced.** Each supported group has a minimum count and a target, and fresh / defect / rotten are
  balanced within each showcase class:

  | Group | Pilot min | Target |
  |---|---|---|
  | Showcase classes (apple, banana, citrus, tomato, carrot) | 12 each = 60 | 4 fresh, 4 minor defect, 4 rotten per class |
  | Other supported classes (mango, guava, pomegranate, lemon_lime, potato, cucumber, capsicum) | 3 each = 21 | mixed condition |
  | Unsupported look-alikes (persimmon, plum, peach, papaya, kiwi, avocado, pear, onion, and similar) | 12 | |
  | Cut / sliced / peeled supported items | 5 | |
  | Printed or artificial fruit (poster, sticker, plastic fruit) | 4 | |
  | **Total** | **>= 102** | |

  Occlusion and partial-view versions are recorded as separate **captures of the same item** (see section 4), not as extra items.
- **Sources:** new photos taken by the team in Lahore markets and homes, with consent and no faces, or licensed sources (Wikimedia
  Commons per-file CC, Zenodo CC BY, permissive Kaggle). Never Pexels, Pixabay or Mixkit.
- **Separation:** no image may come from an uploader, session or market visit used in G3 train, DEV, CU-tune / CU-check, H-train /
  H-val / H-eval, M-DEV or M-TEST. Run a pHash audit (64-bit, Hamming <= 10 is a duplicate) against all of those pools before labelling.
- **Split:** by capture session (photographer + day + place), into pilot-tune 40% and pilot-check 60%. Pilot-check is opened once, after
  every threshold is frozen.

## 2. Class definitions (12 supported classes + unknown)
| Class | Includes | Excludes (label `unknown` or a sibling) |
|---|---|---|
| banana | any Musa dessert banana or plantain, single finger or hand, any peel colour | banana flower or leaf, peeled or sliced banana (= cut) |
| apple | Malus domestica, any variety or colour | pear, quince, persimmon, plum, peach, nectarine; apple-shaped toys |
| mango | Mangifera indica, green or ripe | papaya, avocado, mango slices (= cut) |
| citrus | orange, mandarin, kinnow, tangerine, clementine, sweet orange | lemon / lime (own class), grapefruit / pomelo (record as `unknown: grapefruit`), persimmon |
| guava | Psidium guajava, any flesh colour, whole | feijoa, apple guava confusion items: record the scientific name if known |
| pomegranate | whole Punica granatum | opened fruit with seeds exposed (= cut), arils alone |
| lemon_lime | lemon, lime, key lime, sweet lime (mosambi) | orange-coloured citrus (citrus), green mandarin: adjudicate |
| tomato | Solanum lycopersicum, any size incl. cherry tomato | tomatillo, red bell pepper, persimmon |
| potato | whole Solanum tuberosum tuber, washed or soiled | sweet potato, yam, cut potato, fries |
| cucumber | whole Cucumis sativus | zucchini, bitter gourd, sliced cucumber |
| carrot | whole Daucus carota root, any colour | radish, parsnip, grated or sliced carrot |
| capsicum | a **whole bell pepper** (Capsicum annuum, blocky, any colour) | chilli or other hot peppers, sliced pepper |
| unknown | any other produce, any cut / processed supported item, printed / artificial fruit | |

## 3. Item-level attributes
- **whole_or_cut:** `whole` means intact skin, not opened. `cut` means sliced, halved, peeled, bitten, or arils/seeds exposed. A cut item is
  never gradable.
- **condition (fresh / rotten), per item, judged on the visible surface:**
  - `fresh`: no mould, no soft rot, no leaking tissue. Minor cosmetic marks are allowed.
  - `minor_defect`: bruise, scar, russet, sunken spot or blemish covering < 10% of the visible surface. No mould, no rot.
  - `rotten`: any visible mould, soft or wet rot, fungal lesion (for example *Monilinia*, *Penicillium*, anthracnose, blossom-end rot),
    or decay covering >= 10% of the visible surface.
  - `cannot_judge`: too little surface is visible or too dark. The record is kept but excluded from condition metrics.
- **A/B/C (only for whole, supported, visible, non-rotten items; mirrors `rubric-v0.2-g2` semantics so the rubric can be tested):**
  - **A:** fresh, typical colour for the variety and ripeness, defects < 2% of the visible surface, regular shape.
  - **B:** fresh or minor defect, defects 2-10% of the visible surface or slight colour or shape irregularity.
  - **C:** minor defect at the upper end of the range (about 10% of the surface, or several blemishes), noticeably misshapen or
    discoloured, but edible and not rotten.
  - **Reject:** rotten, as above.
  - **ungradable:** cut, unsupported, or too occluded to judge.
- **ripeness** (banana, mango, tomato, apple, citrus only): `unripe` / `ripe` / `overripe` / `cannot_judge`. Recorded separately and
  never merged into A/B/C.

## 4. Capture-level occlusion and visibility tags (one row per capture)
- `occluder`: `none` / `hand` / `finger` / `plastic_bag` / `other_produce` / `object` / `price_tag_or_sticker` / `frame_edge`
- `visible_fraction_est`: estimated share of the item outline that is visible, in buckets 100 / 75-99 / 50-74 / 25-49 / < 25%
- `truncated_by_frame`: yes / no
- `lighting`: good / dim / harsh_glare / backlit
- `blur`: none / slight / strong
- `gradable_capture`: yes or no. **No** if the visible fraction is < 75%, there is any plastic-bag cover, strong blur, or dim light that
  hides the surface.

## 5. Annotation steps
1. **Ingest:** the coordinator assigns `item_id` and `capture_id`, strips EXIF location, runs the pHash audit, and records source,
   licence, author and session.
2. **Blind setup:** annotators see the image only. They never see model output, Commons titles or filenames that carry a label.
   Order is randomised per annotator.
3. **Pass 1 (identity):** class (12 + unknown, with the unknown sub-name), whole_or_cut, supported yes/no.
4. **Pass 2 (condition):** fresh / minor_defect / rotten / cannot_judge, then A/B/C / Reject / ungradable, then ripeness where it
   applies. Each annotator marks the defect area with a rough polygon (optional, used for the 2% / 10% thresholds).
5. **Pass 3 (capture tags):** section 4 fields for every capture of the item.
6. **Confidence:** each label carries `sure` or `unsure`.
7. **Time box:** about 60 s per item. Items over 3 minutes are flagged for adjudication.

## 6. Two annotators plus adjudication
- Two independent annotators (A1, A2) label every item. At least one of them has produce-handling experience, such as a market trader
  or a food-science student.
- **Adjudicator** (a third person, A3) resolves every disagreement on class, whole_or_cut, condition, A/B/C or gradable_capture, and every
  label marked `unsure`. A3 sees both labels and records the final label plus a one-line reason.
- An item stays out of accuracy metrics if A3 cannot decide (`final = unresolved`). The unresolved rate is reported.
- **Calibration:** before the pilot, all three label 20 practice items that are not in the set, then discuss the definitions.

## 7. Agreement metrics (reported before any model metric)
- **Class:** Cohen's kappa (A1 vs A2) and percentage agreement, on all items. **Target kappa >= 0.85.** Below 0.75, the class
  definitions are revised and the batch is re-labelled.
- **whole_or_cut, supported:** kappa, target >= 0.85.
- **Condition (fresh / minor_defect / rotten):** quadratic-weighted kappa, target >= 0.70. Also report kappa for fresh vs rotten alone.
- **A/B/C/Reject:** quadratic-weighted kappa, target >= 0.60. **If it is below 0.60, A/B/C is not a learnable target at this definition
  and stays hidden in the app.**
- **Capture tags:** kappa on gradable_capture (target >= 0.70) and on occluder type.
- **Uncertainty:** report 95% bootstrap CIs (2000 resamples, by item). With about 100 items a per-class rate has CI half-widths near ±15
  points, so the pilot sizes the full set; it is not an acceptance set on its own.

## 8. What the labels unlock
| Use | Needs |
|---|---|
| Identity accuracy and false acceptance claims | Pilot-check with class kappa >= 0.85 |
| Fresh / rotten agreement claims | Condition kappa >= 0.70, with >= 30 adjudicated fresh and >= 30 rotten showcase items |
| A/B/C shown in the app | A/B/C kappa >= 0.60, the model meets the frozen criteria on a full human set (>= 300 items), and a product sign-off |

## 9. CSV template (one row per capture; UTF-8, comma-separated)
File: `ml/runs/G9/stageH/human_label_template.csv`

```
item_id,capture_id,image_file,source,licence,author,session_id,split,annotator,class,unknown_name,whole_or_cut,supported,condition,abc_grade,ripeness,occluder,visible_fraction_est,truncated_by_frame,lighting,blur,gradable_capture,defect_area_pct_est,confidence,notes
H0001,H0001-c1,img/H0001_c1.jpg,own_photo,CC BY 4.0,NutriSole team,S03-2026-11-02-Akbari,pilot-check,A1,apple,,whole,yes,minor_defect,B,ripe,none,100,no,good,none,yes,4,sure,
H0001,H0001-c2,img/H0001_c2.jpg,own_photo,CC BY 4.0,NutriSole team,S03-2026-11-02-Akbari,pilot-check,A1,apple,,whole,yes,cannot_judge,ungradable,cannot_judge,hand,50-74,no,good,none,no,,sure,hand covers left half
H0002,H0002-c1,img/H0002_c1.jpg,commons,CC BY-SA 4.0,<author>,S07-commons-<uploader>,pilot-tune,A1,unknown,persimmon,whole,no,,ungradable,,none,100,no,good,none,no,,sure,
```

Adjudication file: `item_id,field,A1,A2,final,adjudicator,reason`.
