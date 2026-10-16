"""Tune dark-defect parameters on the quality2 VAL split ONLY (never test).

Objective: balanced accuracy of the measurements-only proxy (defect >= C threshold -> 'rotten'
side) on val, i.e. how well defect % alone separates fresh from rotten items. The rubric
thresholds (2/10/25 %) are NOT tuned here — they await human graders.
Writes the chosen parameters to measure_params.json (version measure-v0.2-g1) and the grid
to ml/runs/G1/grading_tune/grid.json.
"""
import glob
import itertools
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from grading.measure import object_mask, dark_defect_area  # noqa: E402
from grading.eval_proxy import item_crop  # noqa: E402
from grading.rules import RUBRIC  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def main(data="/tmp/nsdata/quality2", out=os.path.join(HERE, "..", "runs", "G1", "grading_tune")):
    items = []
    for lvl in ["fresh", "rotten"]:
        for f in sorted(glob.glob(f"{data}/val/{lvl}/*.jpg")):
            c = item_crop(cv2.imread(f))
            s = 160 / max(c.shape[:2])
            if s < 1:
                c = cv2.resize(c, (int(c.shape[1] * s), int(c.shape[0] * s)), interpolation=cv2.INTER_AREA)
            rgb = cv2.cvtColor(c, cv2.COLOR_BGR2RGB)
            m, _ = object_mask(rgb)
            items.append((rgb, m, lvl == "rotten", os.path.basename(f).split("__")[0]))
    thr = RUBRIC["c"]["defectPct"]
    grid = []
    for rel, floor, cmax in itertools.product([25, 30, 38, 45, 55], [20, 25, 35], [None, 15, 20, 25, 30, 40]):
        d = np.array([dark_defect_area(rgb, m, rel_drop=rel, abs_floor=floor, chroma_max=cmax) for rgb, m, _, _ in items])
        y = np.array([r for _, _, r, _ in items])
        pred = d >= thr
        tpr = float(pred[y].mean())
        tnr = float((~pred[~y]).mean())
        grid.append(dict(rel_drop=rel, abs_floor=floor, chroma_max=cmax, bal_acc=round((tpr + tnr) / 2, 4), rotten_flagged=round(tpr, 4),
                         fresh_clean=round(tnr, 4), fresh_median=float(np.median(d[~y])), rotten_median=float(np.median(d[y]))))
    # prefer high rotten recall: maximise balanced accuracy subject to rotten_flagged >= 0.85
    ok = [g for g in grid if g["rotten_flagged"] >= 0.85] or grid
    best = max(ok, key=lambda g: (g["bal_acc"], g["rotten_flagged"]))
    os.makedirs(out, exist_ok=True)
    json.dump(dict(n_val=len(items), objective="balanced accuracy of defect>=10% vs fresh/rotten on VAL, s.t. rotten_flagged>=0.85",
                   best=best, grid=sorted(grid, key=lambda g: -g["bal_acc"])), open(f"{out}/grid.json", "w"), indent=1)
    params = dict(version="measure-v0.2-g1",
                  _comment=f"dark_defect tuned on quality2 VAL (n={len(items)}) by ml/grading/tune_defect.py; v0.1 was rel_drop 38 / floor 35 / no chroma gate",
                  dark_defect=dict(rel_drop=best["rel_drop"], abs_floor=best["abs_floor"], chroma_max=best["chroma_max"]))
    json.dump(params, open(os.path.join(HERE, "measure_params.json"), "w"), indent=1)
    v01 = [g for g in grid if g["rel_drop"] == 38 and g["abs_floor"] == 35 and g["chroma_max"] is None][0]
    print(json.dumps(dict(best=best, v0_1_on_val=v01), indent=1))


if __name__ == "__main__":
    main()
