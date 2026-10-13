"""G9 existing-models arm: still-image check on the G3 VAL split (det_v3 val.txt, n=402 = 295 COCO/LVIS + 50 negatives + 57 OIV7).
AP50 per NutriSole class (101-point interpolation, Ultralytics-style; conf>=0.001, class-wise NMS 0.7, max 300), same evaluator
for G3 and both Roboflow models. Reported on (a) all 402 and (b) 345 non-OIV7 images, because snapml is very likely built
from Open Images (class vocabulary) and could have seen the 57 OIV7 val images. VAL only; no test split is touched."""
from __future__ import annotations

import argparse
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from g9common import Detector, NAMES, iou_mat  # noqa: E402

VAL = "/workspace/work/cv/g3data/det_v3/val.txt"


def labels_for(img):
    lp = img.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"
    if not os.path.exists(lp):
        return np.zeros((0, 5))
    a = np.loadtxt(lp, ndmin=2)
    return a if a.size else np.zeros((0, 5))


def ap101(tp, conf, npos):
    if npos == 0:
        return None
    if len(tp) == 0:
        return 0.0
    o = np.argsort(-conf); tp = tp[o]
    ctp = np.cumsum(tp); cfp = np.cumsum(1 - tp)
    rec = ctp / npos; prec = ctp / np.maximum(ctp + cfp, 1e-9)
    mrec = np.concatenate([[0.0], rec, [1.0]]); mpre = np.concatenate([[1.0], prec, [0.0]])
    mpre = np.flip(np.maximum.accumulate(np.flip(mpre)))
    x = np.linspace(0, 1, 101)
    return float(np.trapezoid(np.interp(x, mrec, mpre), x))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=["g3", "snapml", "calories"])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    det = Detector(a.model)
    imgs = [l.strip() for l in open(VAL) if l.strip()]
    rec = {"all": {c: dict(tp=[], conf=[], npos=0) for c in range(12)}, "non_oiv7": {c: dict(tp=[], conf=[], npos=0) for c in range(12)}}
    lat, unm = [], {}
    for p in imgs:
        im = cv2.imread(p)
        H, W = im.shape[:2]
        lab = labels_for(p)
        gt = np.stack([(lab[:, 1] - lab[:, 3] / 2) * W, (lab[:, 2] - lab[:, 4] / 2) * H, (lab[:, 1] + lab[:, 3] / 2) * W, (lab[:, 2] + lab[:, 4] / 2) * H], 1) if len(lab) else np.zeros((0, 4))
        gc = lab[:, 0].astype(int) if len(lab) else np.zeros(0, int)
        r = det(im, 0.001)
        lat.append(r["ms"])
        for k, v in r["unmapped"].items():
            unm[k] = unm.get(k, 0) + v
        subsets = ["all"] + ([] if "/oiv7/" in p or os.path.basename(p).startswith("oiv7_") else ["non_oiv7"])
        for c in range(12):
            g = gt[gc == c]
            d = [(b, s) for b, cc, s in r["mapped"] if cc == c]
            d.sort(key=lambda t: -t[1])
            used = np.zeros(len(g), bool)
            tps = []
            for b, s in d:
                ok = 0
                if len(g):
                    iu = iou_mat(np.array([b]), g)[0]
                    iu[used] = -1
                    j = int(iu.argmax())
                    if iu[j] >= 0.5:
                        used[j] = True; ok = 1
                tps.append(ok)
            for sname in subsets:
                rec[sname][c]["tp"] += tps; rec[sname][c]["conf"] += [s for _, s in d]; rec[sname][c]["npos"] += len(g)
    out = dict(model=a.model, n_images=len(imgs), evaluator="AP50 101-pt, conf>=0.001, classwise NMS 0.7, max 300", subsets={},
               latency_ms=dict(p50=float(np.percentile(lat, 50)), p95=float(np.percentile(lat, 95))), unmapped_src_dets_conf001=unm)
    for sname, rr in rec.items():
        pcs = {}
        for c in range(12):
            v = ap101(np.array(rr[c]["tp"], float), np.array(rr[c]["conf"], float), rr[c]["npos"])
            pcs[NAMES[c]] = dict(ap50=None if v is None else round(v, 4), npos=rr[c]["npos"])
        out["subsets"][sname] = pcs
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps({s: {k: v["ap50"] for k, v in d.items()} for s, d in out["subsets"].items()}))


if __name__ == "__main__":
    main()
