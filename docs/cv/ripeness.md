# Ripeness output (G4.5 design note)

**What:** a separate **unripe / ripe / overripe** chip. It is not the fresh/rotten quality output and is never merged into the A/B/C grade until human graders validate a mapping. The G1-G3 "mild" experiment showed that fresh/rotten labels cannot be stretched into a middle level (mild recall 0.24), so ripeness needs its own labels and its own model.

**Which classes:** banana, mango, tomato and guava (and citrus colour, opt-in through `includeCitrus`). Every other class gets **no** ripeness field at all, which is different from `unknown`.

**Interface:**
- Python `ml/grading/ripeness.py: ripeness_from_probs(class, probs[3], params)` and TS `native/src/cv/pipeline/ripeness.ts: ripenessFromProbs(...)` are exact mirrors (parity fixture `ml/eval/fixtures/ripeness_parity.json`, 170 cases, `native/tests/cvRipeness.test.ts`).
- The output fills the existing `CvObject.ripeness = {stage, status, confidence}` contract field.
- The model abstains (`status: 'unknown'`) when the top probability is < 0.6 or the margin to the runner-up is < 0.15. These thresholds are placeholders until a calibration set exists.

**Model (G4 pilot):** a 3-class crop classifier (yolo11n-cls, 224 px) on the detector's item crop, the same crop the quality classifier uses. It is one model shared across fruits; whether to use per-fruit heads is a G5 question.

**Data (licences checked 2026-10-12, see `licences.md`):**

| set | use | licence | classes |
|---|---|---|---|
| Kaggle `asadullahprl/fruits-ripeness-classification-dataset` | train/val (85/15, seed 0) + its own test | CC0 | apple, banana, mango, orange, tomato x unripe/ripe/overripe (300x300) |
| Mendeley 10.17632/56c75hvm7r.2 Annotated Banana Ripeness Stage | external test (its test split, YOLO boxes cropped) | CC BY 4.0 | banana unripe/ripe/overripe |
| Mendeley 10.17632/x4s2jz55dx.1 Tomato fruits (market tomatoes) | external test (ripe/unripe only; "reject" excluded) | CC BY 4.0 | tomato |
| Candidates not used yet | | | BananaImageBD (Mendeley ptfscwtnyz, licence to check), OpenField-BD tomato maturity (Zenodo 20176021, CC BY 4.0, field images), Harumanis mango maturity (Mendeley x6bcr3fkj5), tomatOD / Laboro Tomato (**CC BY-NC-SA**: research only) |

**No guava ripeness data** with a clear open licence was found. Guava needs Lahore panel labels (handbook extension). The labelling-handbook extension for ripeness is:
- one label per visible item;
- unripe = mostly green and firm-looking;
- ripe = species-typical colour;
- overripe = dark spotting or softening without rot;
- rot always goes to the quality label instead.

**Gates before the chip is shown in the product:** a Lahore ripeness TEST, labelled by people, with per-fruit recall >= 0.8 and calibrated abstention. Until then the chip stays behind a debug flag.
