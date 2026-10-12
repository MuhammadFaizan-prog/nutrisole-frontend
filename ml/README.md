# NutriSole CV (`ml/`)

Gauntlet loop code for real-time produce detection + visible-quality grading. Start with
`docs/cv/DASHBOARD.md` (state, metrics, next step) and `docs/cv/gauntlet/G1.md`.

| path | what |
|---|---|
| `data/class_map.csv` | source label -> NutriSole class (12 v1 ids, fixed order) + quality level |
| `data/sources/*.py` | one idempotent downloader per source (checksums logged) |
| `data/build_det_v1.py`, `data/build_quality_v1.py` | dedupe (MD5 + pHash/embeddings), grouped splits, manifests |
| `data/builds/v1/*.json|csv|txt` | versioned manifests (counts, hashes, leakage audit); images are NOT in Git |
| `configs/det_v1.yaml` | detector dataset config (class order = `native/src/cv/models/labels.ts`) |
| `train/train.py` | seeded, resumable Ultralytics training + `run_meta.json` |
| `eval/eval_det.py`, `eval/eval_cls.py` | image metrics, calibration (ECE/Brier), robustness sweep |
| `eval/make_videos.py`, `eval/video_gauntlet.py` | synthetic regression clips + app-pipeline replay |
| `eval/onnx_parity.py` | PyTorch vs exported parity with stated tolerances |
| `eval/tracker.py`, `eval/geometry.py` | Python mirrors of `native/src/cv/pipeline/{tracker,preprocess}.ts` (parity fixtures in `eval/fixtures/`) |
| `grading/` | measurements (colour band, dark-defect %, shape), rule table, rubric JSON, pytest tests, weak-proxy eval |
| `export/export_models.py` | ONNX / ExecuTorch / LiteRT export + `models/G*/model_manifest.json` |
| `runs/G1/` | metrics JSON/CSV/plots (weights + videos git-ignored) |

Environment: Python 3.12, `pip install -r ml/requirements.txt`; `export NUTRISOLE_DATA=...` (raw data
root) and `YOLO_CONFIG_DIR=/tmp/Ultralytics`. Tests: `cd ml && python -m pytest -q grading/tests`.
