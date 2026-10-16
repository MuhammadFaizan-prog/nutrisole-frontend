# G9 Stage J labelling packs (zips are NOT committed: they embed images)

Built by `ml/runs/G9/stageJ/scripts/j_pack.py` from `out/j_blind_key.csv`; sizes and sha256 in `out/j_packs.json`.
Delivered to the team via the project files (`files/g9/stageJ/labeling/`).

| Zip | Photos | For |
|---|---|---|
| nutrisole_G9J_pilot_annotator1.zip | 265 | annotator 1, pilot (J-eval) |
| nutrisole_G9J_pilot_annotator2.zip | 265 | annotator 2, pilot (same photos, other order) |
| nutrisole_G9J_train_annotator1.zip | 461 | annotator 1, training batch (J-train + J-dev) |
| nutrisole_G9J_train_annotator2.zip | 461 | annotator 2, training batch |

Rebuild: `cvenv/bin/python j_pack.py all` (deterministic order; photos from /workspace/work/g9i/cands/img and /workspace/work/g9j/train/img).
