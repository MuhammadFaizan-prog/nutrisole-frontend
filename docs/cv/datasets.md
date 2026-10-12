# NutriSole CV data register

Status values: **verified** (opened/downloaded in this iteration, counts and checksums measured
here), **unverified** (listed in the master prompt, not opened in G1), **unavailable**.
Raw data lives outside Git (`$NUTRISOLE_DATA`, default `/workspace/work/cv/g1data`);
manifests are versioned in `ml/data/builds/v1/`.

## Admitted in dataset v1 (G1)

### D1 — LVIS Fruits & Vegetables (detection) — verified, ADMITTED (detection v1)
| field | value |
|---|---|
| URL | https://huggingface.co/datasets/henningheyen/LVIS_Fruits_And_Vegetables (revision `51362ad3532292d29e63f9e46c2cd33945ffe6b5`, last modified 2024-06-13); code/test images: https://github.com/henningheyen/Fruits-And-Vegetables-Detection-Dataset |
| creator | Henning Heyen (derived from LVIS v1 / COCO 2017 images; plus 180 manually labelled Roboflow test photos) |
| licence | HF card: Apache-2.0; GitHub repo: MIT. Underlying images: COCO/Flickr per-image licences; LVIS annotations CC BY 4.0. See licences.md |
| files + SHA-256 | `data/train-0000{0,1,2}-of-00003.parquet` 7a77c9f5…, 29f949fc…, 7fc81a95…; `validation` 9dc4d11d…; `test` 7e396ff5… (full hashes in `ml/data/builds/v1/source_checksums.txt`) |
| counts (measured) | train 6721, validation 1500, test 180 (= 8401 incl. one unnamed file without a label); 63 classes |
| format | YOLO txt boxes `labels/{train,val,test}/*.txt`; images inside parquet with original file name |
| v1 classes present | banana, apple, citrus (orange/mandarin/clementine), lemon_lime (lemon/lime), tomato (two casings), potato, cucumber, carrot, capsicum = **9 of 12**. **mango, guava, pomegranate: none** |
| capture | COCO everyday scenes (kitchens, markets, plates, piles), many tiny/crowded instances (up to 458 boxes/image); test split = studio-ish phone photos |
| geography/camera | mostly Western Flickr photos (no Pakistan-specific stalls); mixed consumer cameras |
| label authority | LVIS federated annotation (NOT exhaustive per image: unlabelled instances of a class can exist → missing-label noise); Roboflow test labelled by the dataset author |
| groups | COCO image id (one photo = one group); test: session uuid in file name (20240326_<uuid>_<n>) |
| dedupe | MD5 + pHash<=4 across splits: 1 val + 1 train near-duplicate dropped |
| leakage risk | low between COCO photos; test_rf kept as its own locked split |
| fit score | 3/5 (right classes for 9/12, wrong domain: not Lahore market close-ups) |
| decision | admit for detection v1 (see manifest); other 54 LVIS produce classes dropped as annotations, their images used as hard negatives |

### D2 — Sultana et al. Fresh & Rotten fruits, ORIGINALS (quality) — verified, ADMITTED (quality v1)
| field | value |
|---|---|
| URL | https://huggingface.co/datasets/Project-AgML/fresh_rotten_fruit_classification config `raw` (revision `65d4488931fef98c76bf996180064397fbe7da34`); original: Mendeley Data bdd69gyhv8/1 (unverified page) |
| licence | CC BY 4.0 (HF card) |
| counts (measured) | 3200 originals = 8 fruits x {fresh, rotten} x 200. G1 used apple, banana, guava, orange, pomegranate = 2000 images (13 MP, 4160x3120) |
| label schema | ClassLabel names ['fresh','rotten'] (0/1) + fruit_type string — verified from the dataset-server /info endpoint |
| capture | single fruit on white paper, indoor light, phone camera; Bangladesh (per paper; unverified) |
| SHA-256 | per-file list `ml/data/builds/v1/sultana_sha256.txt` |
| groups | no fruit/session id provided. G1 groups = union of pHash Hamming <= 8 and ImageNet-embedding cosine >= 0.93 (yolo26n-cls backbone). This merged the white-paper shots aggressively (largest group 641 images) and produced 1022 Sultana groups |
| residual leakage | the same physical fruit photographed from a different angle can have cosine < 0.93 and land in another split. Cross-split audit: max NN cosine 0.929 (by construction), 135/270 test images have a train neighbour with cosine >= 0.90 (white-paper backgrounds make all images similar, so this does NOT prove leakage, but it cannot rule it out). Treat Sultana test numbers as optimistic |
| fit score | 2/5 (clean studio shots, no market clutter) |

### D3 — FruQ-DB (quality, Fresh/Mild/Rotten) — verified, ADMITTED ONLY for the 3-level experiment (quarantined from headline)
| field | value |
|---|---|
| URL | https://zenodo.org/records/7224690 file `FruQ-DB.zip` (241,067,015 B; MD5 `1a942c2d49dc302bacef155561e1f9a8` matches Zenodo; SHA-256 `1cc94053…308dd7`) |
| licence | CC BY 4.0 (Zenodo metadata) |
| counts (measured) | 5647 images (Fresh 2182, Mild 1364, Rotten 2101), 224x224; 472 exact MD5 duplicates found across the whole quality pool (mostly FruQ) and removed |
| content | frames from ~11 YouTube fruit time-lapse videos (banana, cucumber, grape, kaki, papaya, peach, pear, pepper, strawberry, tomato, watermelon) |
| groups | **no per-image fruit or video id in FruQ-DB** (FruQ-multi, 4.66 GB, has fruit folders; not downloaded: >1.5 GB limit). G1 proxy: k-means (K=40) on embeddings + pHash/cosine union → 26 groups; whole groups per split |
| leakage risk | HIGH: neighbouring time-lapse frames are near-identical; video identity is only approximated. Results on FruQ are QUARANTINED (not headline) |
| confound | 'mild' exists ONLY in FruQ, so a 3-level model can learn "FruQ look = mild". Reported separately |

### N1 — coco128 (negatives for the video gauntlet only) — verified
https://github.com/ultralytics/assets/releases/download/v0.0.0/coco128.zip (SHA-256 `61e5e302…aeb8e`). Images whose COCO labels include food (ids 46-55), dining table or cup are excluded. Not used for training.

## Listed but not admitted / not yet verified (G1)

| source | status | note / next step |
|---|---|---|
| Open Images V7 produce (FiftyOne zoo) | unverified | G2: top up pomegranate, lemon, mango (OIV7 has Mango, Pomegranate, Lemon classes; guava absent) |
| COCO 2017 apple/banana/orange/carrot/broccoli | unverified | overlaps LVIS images — never use both without image-id dedupe |
| Roboflow banana-ripening-process | unverified | ripeness stages for banana; needs Roboflow API key (env var) |
| Laboro Tomato | unverified | CC BY-NC-SA: academic only |
| FruitVeg Freshness (FAST-NUCES / Air Univ.) | unavailable (no public link) | email authors (user action) |
| sirunchained/fruit-dataset-annotation (HF) | verified in G0 | tiny (apple/banana/carrot); not merged into v1 to keep one clean source |
| FruitNet (Mendeley b6fftwbr2v/3) | unverified | apple/banana/guava/lime/orange/pomegranate x Good/Bad/Mixed, CC BY 4.0 — best next quality source (Indian market produce) |
| AgriFreshNET (Mendeley 42m5tb7yv9/1) | unverified | 24 produce, Fresh/Semi-Fresh/Rotten |
| Fresh and Stale (Kaggle swoyam2609) | unverified | needs Kaggle API token |
| VegNet (Mendeley 73n5hrn8hh/3) | unverified | tomato/capsicum/chilli maturity |
| Pakistani mango / Chaunsa / Larkana guava / guava disease / Sargodha citrus (Mendeley) | unverified | local varieties: highest priority for G2 evaluation sets |
| Indian Vegetable Recognition (Mendeley chv7dmvtfm/1) | unverified | potato/tomato/onion market photos |
| FruitVision, Freshness44/50 | not used | NC-ND licence / merged sets |
| Fruits-360 original-size, Banana Ripeness Stage, MangoDHDS, MinneApple, Roboflow fruit-ripeness | unverified | listed in 8.5 |
| **Lahore test set** | **does not exist yet** | mandatory before any gate can be claimed; capture plan in labelling-handbook.md |

## Dataset builds

| build | manifest | content |
|---|---|---|
| det-v1 | `ml/data/builds/v1/det_manifest.json` | train 2639 (240 neg) / val 439 (40 neg) / test 557 (50 neg) / test_rf 149 (60 neg); 9 classes with data. CPU training used `det_train_sub.txt` = 1378 images (1228 positives with <=15 boxes and largest box >= 1% of image + 150 negatives) |
| quality-v1 | `ml/data/builds/v1/quality_manifest.json`, `quality_index.csv` | quality2 = Sultana fresh/rotten (train 1448 / val 275 / test 270); quality3 = quality2 + FruQ (train 5120 / val 1118 / test 937) |
