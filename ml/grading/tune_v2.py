"""G2 grading tune on the quality2 VAL split ONLY (never test).

Searches (1) surface-mask options (shadow ring, specular removal), (2) per-class L*
baseline weight, (3) dark-defect rel_drop / chroma gate, and (4) the rubric's
measurementAgreement.pRottenMin gate (classifier must agree before a measurement-only
C/Reject). Objective: proxy accuracy of classifier+rules on VAL (fresh->A/B,
rotten->C/Reject) subject to rotten->C/Reject >= classifier-only rotten recall on VAL
(the rules must never cost safety). Ties -> simpler setting (gate first, fewer options).
The rubric grade thresholds (2/10/25 %) are NOT tuned: they await human graders.

Writes measure_params.json (measure-v0.3-g2), rubric_v0.json measurementAgreement, and the
grid to <out>/grid.json. class_baseline_L is the median item L* of FRESH TRAIN items per class.

  python ml/grading/tune_v2.py --cls <weights> --temp 0.889 --out ml/runs/G2/grading_tune
"""
from __future__ import annotations

import argparse
import glob
import itertools
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from grading import measure as M  # noqa: E402
from grading import rules as RL  # noqa: E402
from grading.eval_proxy import item_crop  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BAD = {"C", "Reject"}


def load_items(data, split, levels=("fresh", "rotten"), limit=None):
    items = []
    for lvl in levels:
        files = sorted(glob.glob(f"{data}/{split}/{lvl}/*.jpg"))
        if limit:
            files = files[::max(1, len(files) // limit)][:limit]
        for f in files:
            img = cv2.imread(f)
            c = item_crop(img)
            s = 160 / max(c.shape[:2])
            cs = cv2.resize(c, (int(c.shape[1] * s), int(c.shape[0] * s)), interpolation=cv2.INTER_AREA) if s < 1 else c
            rgb = cv2.cvtColor(cs, cv2.COLOR_BGR2RGB)
            m, seg = M.object_mask(rgb)
            items.append(dict(f=f, crop=c, rgb=rgb, mask=m, label=lvl, produce=os.path.basename(f).split("__")[0]))
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cls", required=True)
    ap.add_argument("--temp", type=float, required=True)
    ap.add_argument("--imgsz", type=int, default=192)
    ap.add_argument("--data", default="/workspace/work/cv/g1data/builds/v1/quality2")
    ap.add_argument("--out", required=True)
    ap.add_argument("--write", action="store_true", help="write the chosen params into measure_params.json / rubric_v0.json")
    a = ap.parse_args()
    from ultralytics import YOLO
    os.makedirs(a.out, exist_ok=True)
    # per-class fresh baseline from TRAIN (40 per class is plenty for a median)
    base = {}
    tr = load_items(a.data, "train", levels=("fresh",), limit=200)
    for p in sorted({i["produce"] for i in tr}):
        Ls = []
        for it in [i for i in tr if i["produce"] == p]:
            L = cv2.cvtColor(it["rgb"], cv2.COLOR_RGB2LAB)[..., 0].astype(np.float32) * (100 / 255)
            Ls.append(float(np.median(L[it["mask"]])))
        base[p] = round(float(np.median(Ls)), 2)
    M.MEASURE_PARAMS["class_baseline_L"] = base
    model = YOLO(a.cls)
    names = [model.names[i] for i in range(len(model.names))]
    val = load_items(a.data, "val")
    for it in val:
        p = model.predict(it["crop"], imgsz=a.imgsz, verbose=False, device="cpu")[0].probs.data.numpy().astype(np.float64)
        lg = np.log(np.clip(p, 1e-12, 1)) / a.temp
        pc = np.exp(lg - lg.max()); pc /= pc.sum()
        it["probs"] = {n: float(v) for n, v in zip(names, pc)}
        bands, _ = M.colour_bands(it["rgb"], it["mask"], it["produce"])
        sol, ell = M.shape_metrics(it["mask"])
        elong = M.COLOUR_BANDS.get(it["produce"], {}).get("elongated", False)
        ell_reg = 1.0 - min(1.0, abs(1.0 - ell)) if ell > 0 else 0.0
        gray = cv2.cvtColor(it["rgb"], cv2.COLOR_RGB2GRAY)
        v = cv2.cvtColor(it["rgb"], cv2.COLOR_RGB2HSV)[..., 2][it["mask"]]
        it["m"] = dict(mask_fraction=float(it["mask"].mean()), colour_bands=bands, shape_score=sol if elong else min(sol, ell_reg),
                       blur_var=float(cv2.Laplacian(gray, cv2.CV_64F).var()), mean_v=float(v.mean()) if v.size else 0.0)
    y = np.array([it["label"] == "rotten" for it in val])
    cls_pred = np.array([it["probs"].get("rotten", 0) > it["probs"].get("fresh", 0) for it in val])
    cls_rot_recall = float(cls_pred[y].mean())
    grid = []
    surf_opts = list(itertools.product([0.0, 0.15, 0.3], [10.0, 16.0], [256, 235]))
    for ring, sch, spv in surf_opts:
        surfs = [M.surface_mask(it["rgb"], it["mask"], ring_frac=ring, shadow_chroma=sch, spec_v=spv, spec_s=40) for it in val]
        for bw, rel, cmax in itertools.product([0.0, 0.5, 1.0], [30.0, 38.0, 45.0], [None, 25.0]):
            d = [M.dark_defect_area(it["rgb"], s_, rel_drop=rel, abs_floor=35.0, chroma_max=cmax, produce=it["produce"], baseline_weight=bw)
                 for it, s_ in zip(val, surfs)]
            for gate in [0.0, 0.05, 0.1, 0.2, 0.3]:
                RL.RUBRIC.setdefault("measurementAgreement", {})["pRottenMin"] = gate
                g = [RL.grade(it["produce"], 0.9, it["probs"], {**it["m"], "defect_area_pct": di})["grade"] for it, di in zip(val, d)]
                graded = np.array([x != "ungradable" for x in g])
                pred = np.array([x in BAD for x in g])
                acc = float((pred[graded] == y[graded]).mean())
                rr = float(pred[y & graded].mean())
                fr = float((~pred[~y & graded]).mean())
                nopt = (ring > 0) + (spv < 256) + (bw > 0) + (cmax is not None) + (gate > 0)
                grid.append(dict(ring_frac=ring, shadow_chroma=sch, spec_v=spv, baseline_weight=bw, rel_drop=rel, chroma_max=cmax, gate=gate,
                                 proxy_acc=round(acc, 4), rotten_to_CR=round(rr, 4), fresh_to_AB=round(fr, 4), ungradable=int((~graded).sum()),
                                 defect_med_fresh=float(np.median(np.array(d)[~y])), defect_med_rotten=float(np.median(np.array(d)[y])), n_opts=int(nopt)))
    ok = [g for g in grid if g["rotten_to_CR"] >= cls_rot_recall] or grid
    # Two-step selection (stated before looking at test): (1) measurement params that best
    # grade WITHOUT the agreement gate (so the defect % itself is meaningful and explainable),
    # (2) for those params, the gate that maximises val proxy accuracy.
    keys = ("ring_frac", "shadow_chroma", "spec_v", "baseline_weight", "rel_drop", "chroma_max")
    step1 = max([g for g in ok if g["gate"] == 0] or ok, key=lambda g: (g["proxy_acc"], -g["n_opts"]))
    best = max([g for g in ok if all(g[k] == step1[k] for k in keys)] or [step1], key=lambda g: (g["proxy_acc"], -g["gate"]))
    best_any = max(ok, key=lambda g: (g["proxy_acc"], -g["n_opts"]))
    g1 = [g for g in grid if g["ring_frac"] == 0 and g["spec_v"] == 256 and g["baseline_weight"] == 0 and g["rel_drop"] == 38 and g["chroma_max"] is None and g["gate"] == 0 and g["shadow_chroma"] == 10.0][0]
    best_nogate = max([g for g in ok if g["gate"] == 0] or [g1], key=lambda g: (g["proxy_acc"], -g["n_opts"]))
    res = dict(n_val=len(val), classifier=a.cls, temp=a.temp, classifier_only_val_rotten_recall=cls_rot_recall,
               classifier_only_val_acc=float((cls_pred == y).mean()), class_baseline_L=base, best=best, best_any_single_step=best_any, best_without_gate=best_nogate,
               g1_settings_on_val=g1, grid=sorted(grid, key=lambda g: -g["proxy_acc"]))
    json.dump(res, open(f"{a.out}/grid.json", "w"), indent=1)
    if a.write:
        params = dict(version="measure-v0.3-g2",
                      _comment=f"Tuned on quality2 VAL (n={len(val)}) by ml/grading/tune_v2.py with {os.path.basename(a.cls)}; G1 was rel_drop 38 / floor 35 / no chroma gate / no surface mask.",
                      dark_defect=dict(rel_drop=best["rel_drop"], abs_floor=35.0, chroma_max=best["chroma_max"], baseline_weight=best["baseline_weight"]),
                      surface=dict(ring_frac=best["ring_frac"], shadow_chroma=best["shadow_chroma"], spec_v=best["spec_v"], spec_s=40),
                      class_baseline_L=base)
        json.dump(params, open(os.path.join(HERE, "measure_params.json"), "w"), indent=1)
        rub = json.load(open(os.path.join(HERE, "rubric_v0.json")))
        rub["rubricVersion"] = "rubric-v0.2-g2"
        rub["measurementAgreement"] = {"pRottenMin": best["gate"]}
        json.dump(rub, open(os.path.join(HERE, "rubric_v0.json"), "w"), indent=2)
    print(json.dumps({k: v for k, v in res.items() if k != "grid"}, indent=1))


if __name__ == "__main__":
    main()
