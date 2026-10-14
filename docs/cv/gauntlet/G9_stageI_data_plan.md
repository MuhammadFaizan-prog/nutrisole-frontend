# G9 Stage I data plan: source-separated close-up set for apple, banana, citrus/orange, tomato and carrot (I2)

**Status:** candidate set collected, leak-audited and split; review sheets and CSVs are ready for two human annotators.
**No human has labelled anything yet.** Every label below is **source metadata** (a dataset folder or the Commons search intent), so
every number computed on it is **exploratory** and supports no accuracy claim. Nothing was requested from the user, and no image comes
from Pexels, Pixabay or Mixkit.

## 1. Sources (licence verified per source or per file)

| Source id | What | Licence (checked) | Capture | Classes taken | Split rule |
|---|---|---|---|---|---|
| `commons` | Wikimedia Commons, 64 new queries: in hand, on table, cutting board, blemish, bunch; negatives: unsupported produce, packaging/bags, printed/screen/plastic, occlusion/overlap | per file CC BY / CC BY-SA / CC0 / PD (NC/ND rejected), stored per item | mixed; EXIF camera kept (phones such as Samsung SM-A520F, realme GT, Galaxy S25) | 5 priority + negatives | by **uploader** (sha1 % 10: 0-3 I-dev, 4-9 I-eval-A) |
| `fruitnet` | FruitNet, Meshram & Patil 2021, Mendeley [10.17632/b6fftwbr2v](https://data.mendeley.com/datasets/b6fftwbr2v/1), via the HF mirror [Project-AgML/FruitNet_quality_classification](https://huggingface.co/datasets/Project-AgML/FruitNet_quality_classification) | CC BY 4.0 (Mendeley page and HF card) | phone camera, varied backgrounds and light, Good / Bad quality | apple, banana, orange (40 each) + lime / guava / pomegranate (8 each) | whole source → **I-eval-B** |
| `carrot_m` | "Good and bad classification of Fresh CARROT", Mendeley [ww83r63rtr](https://data.mendeley.com/datasets/ww83r63rtr/1) | CC BY 4.0 (public API) | Realme 11x phone, black background, GOOD / BAD | carrot (50) | whole source → **I-eval-B** |
| `tomato_m` | "TOMATO", Mendeley [hfyth5t3gg](https://data.mendeley.com/datasets/hfyth5t3gg/1) | CC BY 4.0 (public API) | Redmi 9 Power phone, black background, Good / Bad | tomato (80) | whole source → **I-eval-B** |

Mendeley files were read straight out of the public zip with HTTP range requests (`i_collect.py mendeley`), so only the sampled images
were downloaded. Images are stored at ≤ 640 px in `/workspace/work/g9i/cands/img` (not committed). The manifest with licence,
uploader, page and query for every item is `/workspace/work/g9i/cands/cands.json`.

**Licensed sources found but not collected yet** (for the next round or a training pool, never in the same split as a source above):
- VegNet Bangladesh (Mendeley 68zgy243yb, CC BY 4.0, smartphone, 40 vegetables incl. tomato).
- Tomato Maturity / Quality (Mendeley s42kpg8h37, CC BY, 3 smartphones, 5.4 GB).
- VegNet India (Mendeley 6nxnjbn9w6 / Kaggle iamdatascientist99, CC BY 4.0, Xiaomi phone: tomato, bell pepper, chilli).
- Zenodo 18904638 (CC BY 4.0, 30 classes, YOLO boxes).

## 2. Leakage audit and split (`ml/runs/G9/stageI/out/i_leak_split.json`)
- **Reference hashes (64-bit pHash, Hamming ≤ 10 = leak):** the Stage H in-kernel list (all eval sets + references, including M-DEV /
  M-TEST hashes, never viewed), the H-set (incl. H-train), G3 train / DEV / clips, Stage D-F pools and CU. Commons titles already used in
  Stage G/H (3,752) were excluded before download.
- **742 candidates downloaded → 42 dropped as leaks → 700 kept.** Near-duplicates inside the new set (≤ 6) were grouped: **656 groups**
  (carrot_m 50 → 30, tomato_m 80 → 62: repeated shots of the same item). A group never spans two splits. Reviewers see one representative.
- **Commons uploaders: 177.**

| Split | Supported groups (source label) | Negative groups | Use |
|---|---|---|---|
| I-dev | 114 (apple 32, banana 14, carrot 24, citrus 27, tomato 17) | 100 (unsupported 38, packaging 21, printed 23, occluded 18) | any tuning |
| I-eval-A (Commons, other uploaders) | 115 (apple 27, banana 28, carrot 19, citrus 13, tomato 28) | 94 (unsupported 62, packaging 12, printed 15, occluded 5) | opened once, after freeze |
| I-eval-B (external phone datasets) | 233 (apple 40, banana 38, carrot 30, citrus 40, tomato 62, + 23 other-class) | 0 | opened once, after freeze; out-of-source test |

**Caveats:**
- The Commons negative queries are noisy: maps, illustrations and shop signs came back, and some "packaging" or "occluded" hits show
  supported produce. Human review decides what each image is. The expected yield after review is lower than the counts above.
- I-eval-B has no negatives and fixed studio-like backgrounds (carrot_m, tomato_m are on black).
- **The training sources of the Kaggle side** (Fruits-360, Fruit Recognition, Vegetable Image Dataset) are not hashed locally. The
  Stage H kernel dropped training images near the eval hashes in-kernel. Any future kernel must also hash against the Stage I
  candidates (`phash` field in `i_leak_split.json`).

## 3. Exploratory check with the unchanged Stage H stack (source labels; `out/i_explore.json`)
H2 top-1 on the Stage H crop, per source (supported groups):

| Source | n | H2 top-1 | H2 says "unknown" | H-final verified correct / wrong |
|---|---|---|---|---|
| commons | 229 | 50 (22%) | 115 | 4 / 3 |
| fruitnet (phone) | 141 | 28 (20%) | 46 | 9 / 3 |
| carrot_m (phone) | 30 | **0** (whole image: 19) | 14 | 0 / 0 |
| tomato_m (phone) | 62 | 31 (50%) | 1 | 22 / 0 |

- By class, H2 top-1 on crops: apple 34/99, banana 14/80, **citrus 5/80**, tomato 48/107, carrot 8/73.
- Citrus goes to unknown, cucumber or potato. Negatives: H-final accepted 3/194 Commons negatives (all unsupported produce).
- These are new, independent sources, including real phone captures, and they confirm the audit's diagnosis: domain mismatch, not a bug.
  The numbers are not accuracy (labels are not human).

## 4. Human review material (for the annotators; agent labels are exploratory only)
- **33 contact sheets** `I_sheet_01..33.jpg` (20 numbered items each, shuffled so source and class are not grouped). Copied to the project
  files under `g9/stageI/review/`.
- **`ml/runs/G9/stageI/review_annotator_blind.csv`**: one row per item (I0001-I0656) with the sheet, page URL, licence and split, plus
  empty columns for the annotator. **No source label**, so the annotators label blind.
- **`ml/runs/G9/stageI/review_adjudicator_key.csv`**: source, uploader, source label, quality folder, camera, duplicate-group size and
  pHash distance. Held by the adjudicator only.
- Protocol: `G9_stageI_human_labeling_protocol.md` (updates the Stage H protocol).

## 5. What counts as "ready for a final accuracy claim"
1. Two annotators label I-dev and I-eval-A/B blind. The adjudicator resolves disagreements. Agreement is reported first.
2. **At least 100 adjudicated supported close-ups in the eval splits, ≥ 20 per priority class, plus ≥ 60 adjudicated negatives**
   (unsupported ≥ 25, printed/screen ≥ 10, packaging ≥ 10, occluded ≥ 10). If Commons yields too few negatives after review, collect
   more before opening eval.
3. Thresholds are frozen on I-dev only. I-eval-A and I-eval-B are each opened once.
