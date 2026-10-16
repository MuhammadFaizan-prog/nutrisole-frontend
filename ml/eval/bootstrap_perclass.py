"""G8 showcase: per-class AP50 / P / R per split from bootstrap_det.py stats pickles, plus a paired source-level
bootstrap CI of the per-class AP50 difference (candidate - reference), same units as bootstrap_det.py
(images for test / test_oiv7 / test_oiv7c, capture UUID for test_rf, pooled stratified), B=1000, seed 0.

  python ml/eval/bootstrap_perclass.py --ref G3 --cand show_s0 --classes 3 1 0 7 10 --out x.json
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bootstrap_det import unit_of  # noqa: E402

NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]


def per_class(imgs, classes):
    from ultralytics.utils.metrics import ap_per_class
    tp = np.concatenate([i["tp"].reshape(-1, 10) for i in imgs]); conf = np.concatenate([i["conf"].reshape(-1) for i in imgs])
    pc = np.concatenate([i["pred_cls"].reshape(-1) for i in imgs]); tc = np.concatenate([i["target_cls"].reshape(-1) for i in imgs])
    out = ap_per_class(tp, conf, pc, tc, plot=False)
    # out: tp, fp, p, r, f1, ap, unique_classes, ...
    p, r, ap, uc = out[2], out[3], out[5], out[6].astype(int)
    res = {}
    for c in classes:
        if c in uc:
            k = int(np.where(uc == c)[0][0])
            res[c] = dict(P=float(p[k]), R=float(r[k]), mAP50=float(ap[k, 0]), mAP50_95=float(ap[k].mean()), instances=int((tc == c).sum()))
        else:
            res[c] = dict(P=float("nan"), R=float("nan"), mAP50=float("nan"), mAP50_95=float("nan"), instances=int((tc == c).sum()))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="G3"); ap.add_argument("--cand", required=True)
    ap.add_argument("--ref-stats", default="/workspace/work/cv/g7models/boot"); ap.add_argument("--cand-stats", default="/workspace/work/cv/g8show/boot")
    ap.add_argument("--classes", type=int, nargs="+", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("-B", type=int, default=1000); ap.add_argument("--boot-splits", nargs="*", default=["pooled"])
    a = ap.parse_args()
    S = {a.ref: pickle.load(open(os.path.join(a.ref_stats, f"stats_{a.ref}.pkl"), "rb")),
         a.cand: pickle.load(open(os.path.join(a.cand_stats, f"stats_{a.cand}.pkl"), "rb"))}
    res = dict(ref=a.ref, cand=a.cand, classes=[NAMES[c] for c in a.classes],
               method=f"per-class AP from Ultralytics ap_per_class on per-image val stats (CPU, 480, conf 0.001, iou 0.7); paired percentile bootstrap B={a.B} seed 0 over bootstrap_det units",
               splits={})
    for sp in S[a.ref]:
        if sp not in S[a.cand]:
            continue
        names = [i["im_name"] for i in S[a.ref][sp]["images"]]
        idx = {t: {i["im_name"]: i for i in S[t][sp]["images"]} for t in S}
        missing = [n for n in names if n not in idx[a.cand]]
        row = dict(n_images=len(names), missing_in_cand=len(missing), point={})
        for t in S:
            pcs = per_class([idx[t][n] for n in names if n in idx[t]], a.classes)
            row["point"][t] = {NAMES[c]: {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()} for c, d in pcs.items()}
        if sp in a.boot_splits and not missing:
            units = {}
            for n in names:
                st, u = unit_of(n)
                units.setdefault(st, {}).setdefault(u, []).append(n)
            strata = {st: list(v.values()) for st, v in units.items()}
            rng = np.random.default_rng(0); diffs = {c: [] for c in a.classes}
            for _ in range(a.B):
                pick = []
                for st, groups in strata.items():
                    for j in rng.integers(0, len(groups), len(groups)):
                        pick.extend(groups[j])
                pr = per_class([idx[a.ref][n] for n in pick], a.classes); pcd = per_class([idx[a.cand][n] for n in pick], a.classes)
                for c in a.classes:
                    diffs[c].append(pcd[c]["mAP50"] - pr[c]["mAP50"])
            row["diff_ci95"] = {NAMES[c]: dict(point=round(row["point"][a.cand][NAMES[c]]["mAP50"] - row["point"][a.ref][NAMES[c]]["mAP50"], 4),
                                               ci95=[round(float(np.nanpercentile(diffs[c], 2.5)), 4), round(float(np.nanpercentile(diffs[c], 97.5)), 4)],
                                               p_le_0=round(float(np.mean(np.array(diffs[c]) <= 0)), 4)) for c in a.classes}
            row["units"] = {st: len(g) for st, g in strata.items()}
        res["splits"][sp] = row
        print(sp, json.dumps(row.get("diff_ci95", row["point"][a.cand]))[:500], flush=True)
        json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
