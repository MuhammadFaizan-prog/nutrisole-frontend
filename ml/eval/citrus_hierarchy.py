"""G7 Phase 5 (citrus): hierarchical citrus output vs flat, per model.

Flat: the detector's citrus (3) / lemon_lime (6) label is shown as is.
Hierarchical: level 1 = "citrus family" (any box whose top class is 3 or 6). Level 2 (subtype) is committed only when the
subtype is confident: top score >= tau AND the other family score at the same anchor < 0.5 x top; otherwise the box is shown as
generic "citrus (type uncertain)". tau is chosen on OIV7c VAL only from {0.4,0.5,0.6,0.7} (max family-weighted subtype
precision subject to coverage >= 0.70), then measured once on test_oiv7c. Reported per GT class: family recall (box found
as either citrus class, IoU >= 0.5), subtype committed / correct / wrong, generic share, and the flat wrong rate.
Exploratory (G7 Phase 5, written 2026-10-13 ~13:40 PKT before running it; the earlier score-tau grid in
ml/runs/G7/citrus/exploratory_score_tau_val.json was val-only).
  python ml/eval/citrus_hierarchy.py --models G3=det.onnx G7sA=... --out ml/runs/G7/citrus_hierarchy.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from citrus_ambiguity import collect, CITRUS, LEMON  # noqa: E402

TAUS = [0.4, 0.5, 0.6, 0.7]


def evaluate(items, tau):
    out = {}
    for g, name in [(LEMON, "lemon_lime"), (CITRUS, "citrus")]:
        it = [i for i in items if i["gt"] == g]; fam = [i for i in it if i["pred"] in (CITRUS, LEMON)]
        com, cor, gen = 0, 0, 0
        for i in fam:
            top = i["scores"][i["pred"]]; oth = i["scores"][LEMON if i["pred"] == CITRUS else CITRUS]
            if tau is None or (top >= tau and oth < 0.5 * top):
                com += 1; cor += i["pred"] == g
            else:
                gen += 1
        out[name] = dict(n_gt=len(it), family_recall=round(len(fam) / max(1, len(it)), 4), committed=com, correct=cor, wrong=com - cor, generic=gen,
                         subtype_precision=round(cor / max(1, com), 4), wrong_rate_of_family=round((com - cor) / max(1, len(fam)), 4))
    c = out["lemon_lime"]["committed"] + out["citrus"]["committed"]; f = sum(out[k]["committed"] + out[k]["generic"] for k in ("lemon_lime", "citrus"))
    out["pooled"] = dict(coverage=round(c / max(1, f), 4), subtype_precision=round((out["lemon_lime"]["correct"] + out["citrus"]["correct"]) / max(1, c), 4),
                         wrong=out["lemon_lime"]["wrong"] + out["citrus"]["wrong"])
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--models", nargs="+", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--conf", type=float, default=0.35)
    a = ap.parse_args()
    import onnxruntime as ort
    res = dict(conf=a.conf, imgsz=480, iou_match=0.5, device="sandbox CPU, onnxruntime", val="OIV7c val (selection)", test="test_oiv7c (n=181 images)", models={})
    if os.path.exists(a.out):
        res = json.load(open(a.out))
    for spec in a.models:
        tag, path = spec.split("=", 1)
        if tag in res["models"]:
            continue
        s = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
        _, val = collect(s, "/workspace/work/cv/g4data/oiv7c/images/val", a.conf)
        grid = {str(t): evaluate(val, t)["pooled"] for t in TAUS}
        ok = [t for t in TAUS if grid[str(t)]["coverage"] >= 0.70]
        pick = max(ok, key=lambda t: (grid[str(t)]["subtype_precision"], grid[str(t)]["coverage"])) if ok else None
        nt, test = collect(s, "/workspace/work/cv/g4data/test_oiv7c.txt", a.conf)
        res["models"][tag] = dict(model=path, val_grid=grid, picked_tau=pick, flat=evaluate(test, None), hierarchical=evaluate(test, pick) if pick else None)
        print(tag, pick, res["models"][tag]["flat"]["pooled"], res["models"][tag]["hierarchical"] and res["models"][tag]["hierarchical"]["pooled"], flush=True)
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True); json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
