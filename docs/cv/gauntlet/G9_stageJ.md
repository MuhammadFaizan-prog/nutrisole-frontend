# G9 Stage J: human-verified close-up dataset preparation (report)

**Brief:** `files/nutrisole-g9-stageJ-gpt.md` (authoritative). **Nothing was trained, no GPU and no Kaggle were used.** G3, H2, the grading
models, datasets, eval scripts, pricing/nutrition, PR #1 and git history are untouched; nothing was deleted or merged.

**Outcome:** everything the two human annotators need is ready: guide, offline labelling tool, blind packs, fallback sheets, agreement and
adjudication scripts, partitions and frozen readiness gates. **No human has labelled anything yet**, so every class count below is
**source metadata** (exploratory) and **H3 is NOT READY** (`G9_stageJ_readiness.md`).

| Deliverable | Where |
|---|---|
| Annotation guide (plain language) | `docs/cv/gauntlet/G9_stageJ_annotation_guide.md` |
| Readiness criteria (frozen gates) | `docs/cv/gauntlet/G9_stageJ_readiness.md` |
| Labelling packs (4 zips) | `ml/runs/G9/stageJ/labeling/` (not committed: images) → project files `g9/stageJ/labeling/` |
| Licence audit (742 + 276 per file) | `ml/runs/G9/stageJ/out/j_licence.csv`, `j_licence_train.csv` (+ `.json` summaries) |
| Partitions + near-dup audit | `ml/runs/G9/stageJ/out/j_partitions.json`, `j_manifest_candidates.csv` |
| Blind key (adjudicator only) | `ml/runs/G9/stageJ/out/j_blind_key.csv` |
| Scripts + tests | `ml/runs/G9/stageJ/scripts/` (`j_licence*.py`, `j_collect.py`, `j_partition.py`, `j_select.py`, `j_pack.py`, `j_tool_test.py`, `j_agree.py`, `j_gates.py`, `test_j_agree.py` 8/8) |

## 1. Class definitions (decided from the existing 13-way class map)
- `citrus_orange` = the app's **citrus** class (`ml/eval/h2_labels.py`: Orange, Mandarine, Clementine, Tangelo) plus kinnow and malta.
  **Lemon and lime are a separate app class (`lemon_lime`)**, so annotators label them `other_produce` + name `lemon_or_lime`.
  Grapefruit, pomelo and kumquat are excluded from citrus in the class map, so they are `other_produce` too.
- **Capsicum = a whole bell pepper. Chilies are not capsicum**: both are `other_produce`, with the names `capsicum_bell_pepper` / `chili`.
- The 9 label options (keys 1-9): apple / banana / citrus_orange / tomato / carrot / other_produce / printed_or_screen / occluded /
  uncertain, plus tags (cut, bag, many items, rotten) and a free note. `j_agree.py` maps every verified label back to the 13 app classes
  (`class13`), so 13-way compatibility is kept.

## 2. Licence audit
- **Stage I candidates (742):** Commons metadata was **re-fetched per file** (LicenseShortName, Artist, Credit, description, NonFree flag),
  not taken from the collection-time values. **736 compliant, 6 excluded:**
  - `c0350` *Radishes-6997 - Hans Braxmeier*: credit is pixabay.com (banned source).
  - `c0031`, `c0119`, `c0187`, `c0222`, `c0326`: Commons copies of **Unsplash** photos. Unsplash is not named in the ban, but it is the
    same stock-site family and its licence restricts compilations, so they are excluded conservatively.
  - Licences of the kept files: CC BY 4.0 283, Public domain 138, CC BY-SA 4.0 130, CC BY 2.0 67, CC0 45, CC BY-SA 3.0 35(+3 it),
    CC BY-SA 2.0 18, CC BY 3.0 us 12, CC BY 2.5 11. No NC/ND, no missing authors. Dataset sources (FruitNet, carrot_m, tomato_m) are
    CC BY 4.0 per their Mendeley pages.
- **New training candidates (276):** all compliant (CC BY 4.0 152, CC BY-SA 4.0 55, PD 19, CC BY-SA 3.0 18, CC0 14, CC BY 2.0 13,
  CC BY-SA 2.0 4, CC BY 2.5 1). Stock-site credits were filtered at search time as well.
- **No image from Pexels, Pixabay or Mixkit is used anywhere.**

## 3. New licensed training candidates (weak classes: citrus, carrot)
| Source | Licence (checked via Mendeley public API) | Capture | Taken |
|---|---|---|---|
| `citrus_tw` *A Dataset of Citrus Fruit Images* (Huang & Chen), [bxfgvsn9kw](https://data.mendeley.com/datasets/bxfgvsn9kw) | CC BY 4.0 (dataset) | Sony DSC-HX300 compact at 200-500 mm, orchards; **originals only** (augmented folders skipped) | 60 citrus (52 groups) |
| `veg_in` *Vegetable Recognition Dataset* (Karwal, Som, Patel, Sisodia), [chv7dmvtfm](https://data.mendeley.com/datasets/chv7dmvtfm/1) | CC BY 4.0 | self-shot in markets, fields, households | 60 carrot, 3 tomato |
| `veg_bd` *A Comprehensive Image Dataset of Vegetables Grown in Bangladesh* (Sumona et al.), [rtx9ngb68j](https://data.mendeley.com/datasets/rtx9ngb68j/2) | CC BY 4.0 | Poco F3 phone, Dhaka street stalls | 26 carrot, 3 lime |
| `commons_t` Wikimedia Commons, 24 new citrus/carrot queries | per file CC/PD | mixed | 124 (40 more dropped because their uploader is already in J-dev/J-eval) |

**Rejected:** *Orange fruits Dataset* 3x8jjd2f72 (CC BY, phone) ships as one 6 GB RAR inside the zip, which cannot be range-read;
*Oranges in the field* 93f32zgkxz is **CC BY-NC 3.0**; *Indian Fruits-40* bg3js4z2xt is about 2 KB per image (thumbnails); Zenodo
18904638 is a Roboflow aggregate with mixed provenance; *FruitVision* xkbjx8959c is **CC BY-NC-ND**.

## 4. Partitions (`j_partition.py`, rules frozen in the script header)
- **J-eval** = Stage I I-eval-A (Commons uploaders sha1 % 10 in 4-9) ∪ I-eval-B (FruitNet, carrot_m, tomato_m whole). **Membership
  unchanged from Stage I.**
- **J-dev** = I-dev items whose uploader has sha1 % 10 in 2-3 (threshold tuning only). **J-train** = I-dev uploaders 0-1 + the new sources.
  *This refines the Stage I prereg, which planned to train on all of I-dev and tune on I-dev: training and tuning are now kept apart.*
- **Grouping:** Commons uploader **and** artist (union across splits; a person in two splits is a leak; "unknown author" is not treated as
  a person), each dataset as one group. Near-duplicates: 64-bit pHash, Hamming ≤ 10 across splits and against every earlier reference
  set (Stage H in-kernel list incl. M-DEV/M-TEST **hashes only**, H-set, G3 train/DEV/clips, Stage D-F pools, CU). Eval never changes:
  the non-eval item is quarantined.
- **Audit result:** 0 cross-split near-duplicates; **14 quarantined**: 9 new Commons files identical (Hamming 0) to earlier-set images,
  3 veg_in files at Hamming 10 to earlier references, 2 Stage I items whose artist also appears in J-eval (Joachim Beuckelaer, Nenad
  Stojković). M-TEST content was never opened.

**Per split (group representatives = what reviewers see; source labels, exploratory):**

| | J-train | J-dev | J-eval |
|---|---|---|---|
| Groups / images | 382 / 392 | 79 / 79 | 441 / 485 |
| apple / banana / citrus / tomato / carrot | 20 / 7 / 135 / 14 / 138 | 10 / 7 / 15 / 4 / 9 | 67 / 66 / 53 / 90 / 49 |
| other supported classes | lime 3 | - | lime 7, guava 8, pomegranate 8 |
| negatives (unsupported / packaging / printed / occluded) | 22 / 15 / 12 / 16 | 15 / 6 / 11 / 2 | 61 / 12 / 15 / 5 |
| sources | Commons 128, commons_t 114 (91 Commons uploaders in all), veg_in 59, citrus_tw 52, veg_bd 29 | Commons 79 (42 uploaders) | Commons 208 (101 uploaders), FruitNet 141, tomato_m 62, carrot_m 30 |
| lighting proxy (dark / normal / bright) | 24 / 313 / 45 | 11 / 64 / 4 | 49 / 334 / 58 |
| background proxy (textured / plain dark / light / mid) | 341 / 10 / 10 / 21 | 74 / 1 / 2 / 2 | 393 / 13 / 21 / 14 |

Proxies: mean luminance (< 75 dark, > 175 bright); border-ring std < 22 = plain (split by ring mean), else textured. Exact per-item values
are in `j_manifest_candidates.csv`.

## 5. Pilot labelling pack (J-eval only)
**265 photos** (`j_select.py`, seed 11): 32 supported group representatives per priority class (Commons first up to 16, the rest from that
class's phone dataset; citrus has only 13 Commons eval items, so 13 + 19 FruitNet); **all 93 J-eval negatives** (61 unsupported,
15 printed, 12 packaging, 5 occluded), because the Commons negative queries are noisy (streets, paintings, carvings came back); 12
other-class checks (4 lime, 4 guava, 4 pomegranate).

- **Expected yield:** about 55% of Commons supported items and 90-95% of dataset items survive review, so about 22-25 clean items per
  class, enough for ≥ 20/class with little margin. Negatives: the 93 candidates plus the cut, bagged and other-produce items found among
  the supported draws should give ≥ 60, but **packaging (12 candidates) and especially occluded (5) will probably miss their ≥ 10
  sub-quotas**. Recommended fix: the team shoots about 20 bagged and 20 partly hidden fruit photos on their own phones as a new
  eval-only source.
- **Training batch:** 461 photos (all J-train + J-dev representatives) in separate packs, also double-annotated.

**Packs** (`ml/runs/G9/stageJ/labeling/`), one zip per annotator per batch, the same photos in a different random order per copy
(seeds 101 / 202), blind ids only (P### / T###), photos re-encoded without metadata, no source, label, licence or split shown:

| Zip | Size | Photos |
|---|---|---|
| `nutrisole_G9J_pilot_annotator1.zip` | 20.3 MB | 265 |
| `nutrisole_G9J_pilot_annotator2.zip` | 20.3 MB | 265 |
| `nutrisole_G9J_train_annotator1.zip` | 37.5 MB | 461 |
| `nutrisole_G9J_train_annotator2.zip` | 37.5 MB | 461 |

Each zip contains `START_HERE.txt`, a **single self-contained HTML tool** (photos embedded, works offline from a double-click), the guide,
a fallback blind CSV in that copy's order, and numbered contact sheets (20 photos per sheet).

**Tool:** one photo at a time; keys 1-9 choose the label, C/B/M/X toggle tags, N opens the note, ← → move, U jumps to the next unlabelled
photo, E exports the CSV, ? shows the guide. It records the annotator's name, autosaves to localStorage after every action (namespaced per
pack and copy), can re-import an exported CSV, and records seconds per item.
**Headless Chromium test** (`j_tool_test.py`, all 4 packs): open, enter a name, label 3 items (apple; citrus + cut tag; other produce +
lemon_or_lime + a note containing a comma), reload (3/N restored, no name prompt), export: CSV has N rows, the 3 labels, tags, note and
name are correct, no page errors. Screenshots and the test exports: `out/tool_test/`.

## 6. Agreement and verification workflow
1. Each annotator labels their copy on their own and sends the exported CSV.
2. `python3 j_agree.py agree A.csv B.csv --batch pilot --out agree_pilot --sheets` → `agreement.md/json` (κ(class), κ(supported), κ(cut),
   κ(bag), per-label one-vs-rest κ, percent agreement, 9×9 confusion), `disagreements.csv`, `adjudication_sheet.csv`, and photo sheets of
   the disputed items with both answers printed.
3. The adjudicator (a third person, for example the FYP supervisor; **not** Faizi or the teammate) fills `final_label` (+ reason) for every
   row: label differs, either said uncertain, cut/bag tag differs, or missing.
4. `python3 j_agree.py verify --batch pilot --agree-dir agree_pilot --adjudicated agree_pilot/adjudication_sheet.csv --out verified` →
   `verified_manifest_pilot.csv` (final label, 13-way class, role, licence, author, source URL, image sha256) + `.sha256` freeze +
   readiness counts (R2 / T1).
Stdlib only (Pillow optional for the sheets). Tests: `test_j_agree.py` 8/8 (κ against a hand-computed 2×2 table, aliases, 13-way roles
incl. chili ≠ capsicum, full agree → adjudicate → verify flow, gate counts, minimal fallback CSV, Wilson rules).

## 7. Training-data gap (target T1: ≥ 150 verified clean images per priority class)
| Class | J-train candidates | Expected verified | Shortfall | Licensed sources to close it (CC BY 4.0, Mendeley API checked 2026-10-15) |
|---|---|---|---|---|
| apple | 20 | ~11 | **~139** | *Multispectral images of apples* y5h6v8w6ms; *Multi-Stage Apple Dataset* gfcmdbvw65 (orchard); more Commons (train-side uploaders) |
| banana | 7 | ~4 | **~146** | *Mango and Banana (Ripe/Unripe)* y3649cmgg6; *Banana Prata Catarina* 7vb4djkbrc (smartphones, varied backgrounds); *Banana and Guava* 56td5w4wz2 (Redmi Note 10 Pro); *Ripen Banana* j9sp322drp (phone) |
| citrus | 135 | ~92 | **~58** | more `citrus_tw` originals; *Spoiled and fresh fruit inspection* 6ps7gtp2wg (orange, lemon, tomato, banana) |
| tomato | 14 | ~8 | **~142** | `veg_in` (814 tomato), `veg_bd` (76), *Vegetable Image Dataset Bangladesh* b9rvg4f2st (phone, natural backgrounds), *Tomato Maturity* s42kpg8h37, VegNet India 6nxnjbn9w6 |
| carrot | 138 | ~105 | **~45** | more `veg_in` (815 carrot) |

Expected yield is an assumption (Commons 0.55, datasets 0.9). Real-photo negatives in J-train: 65 candidate groups vs T2 ≥ 150, so more
are needed. J-dev is also short for T3 (banana 7, tomato 4, carrot 9 vs ≥ 10). **Datasets that are a single source per class (like
`veg_in` for tomato) add volume but not source diversity: T1 also needs ≥ 2 sources per class.** None of these sources may ever enter
eval, since they are training-side sources now.

## 8. What is needed from people (not something the agent can supply)
1. Faizi and the teammate each label **their own** pilot copy (about 25 minutes), then the training copy (about 40 minutes), and send
   the CSVs.
2. A third person adjudicates (`adjudication_sheet.csv`).
3. Optional but recommended: about 40 own-phone photos of bagged and partly hidden produce, for the packaging/occluded sub-quotas (a new
   eval-only source).
