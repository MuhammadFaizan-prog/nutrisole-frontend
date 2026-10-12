# Licence log (CV)

| item | licence (as stated by the source) | where verified | obligations / risk |
|---|---|---|---|
| Ultralytics 8.4.175 (YOLO26 / YOLO11 code + weights) | AGPL-3.0 (or Ultralytics Enterprise licence) | PyPI / Ultralytics repo (from G0) | Fine for an open-source FYP. Distributing an app that embeds Ultralytics-trained weights triggers AGPL source obligations; **flag before any commercial release** |
| LVIS Fruits & Vegetables (HF henningheyen) | Apache-2.0 (HF card); GitHub repo MIT | HF API card_data (2026-10-12), GitHub API | Images are COCO/Flickr photos with per-image Creative Commons licences (COCO terms of use); LVIS annotations CC BY 4.0. Attribute LVIS + COCO + dataset author. Do not redistribute the images themselves |
| Sultana et al. Fresh & Rotten (HF Project-AgML) | CC BY 4.0 | HF API card_data | attribution to Sultana et al. (Mendeley Data bdd69gyhv8) |
| FruQ-DB (Zenodo 7224690) | CC BY 4.0 | Zenodo API metadata | attribution; frames derive from YouTube time-lapse videos (third-party copyright on the videos themselves is not cleared by the dataset licence — research use only, do not redistribute frames) |
| Open Images V7 produce subset (G3, det-v3) | annotations CC BY 4.0 (Google); images: all 1 028 kept images list CC BY 2.0 (per-image row in `ml/data/builds/v3/oiv7_licences.csv`, author + Flickr URL) | Kaggle kernel `mfaizannnn/nutrisole-oiv7-produce` read the official OIV7 image metadata CSVs; audit `ml/data/sources/oiv7_audit.py` checked every kept image has a CC row (2026-10-12) | attribute each author (CC BY 2.0) + Open Images; images were resized (<=1024 px) and some regions grey-filled (group-of / suspected unlabelled boxes), so they are modified works; private Kaggle dataset only, do not redistribute |
| COCO 2017 hard negatives (G3) | COCO images (Flickr CC licences per image, COCO terms of use); COCO labels CC BY 4.0 | images.cocodataset.org + Ultralytics coco2017labels.zip | used as unlabelled background images only; ids in `ml/data/builds/v3/hardneg.json` |
| Synthetic textures (G3) | generated in this repo (`ml/data/sources/hard_negatives.py`) | n/a | none |
| coco128 (Ultralytics asset) | COCO images (Flickr CC licences), Ultralytics packaging | download only | used only as negative video frames, not trained on |
| react-native-vision-camera / executorch / fast-tflite / onnxruntime-react-native | MIT (per npm package metadata; re-check at install) | npm | none beyond notice |

Weights trained in G1 inherit the most restrictive input terms that apply (LVIS/COCO images: research use; FruQ: CC BY with third-party video caveat). G1/G2/G3 weights are **research/FYP-only**; do not publish them as a commercial product.
