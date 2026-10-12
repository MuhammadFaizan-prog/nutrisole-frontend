"""WEAK-PROXY evaluation of the grading layer against fresh/rotten labels.

There are NO human grades yet, so this is not a grade validation (proof level 6 needs the
Lahore human panel + Cohen's kappa). Proxy: a 'fresh' item should get A or B, a 'rotten' item
C or Reject. Reported for three ablations on the quality2 TEST split:
  classifier_only    : argmax of calibrated probs (fresh->'A/B', rotten->'C/Reject')
  measurements_only  : rules with neutral probs (fresh 0.69 / rotten 0.31) so only defect %,
                       colour band and shape decide
  classifier+rules   : full rule table (calibrated probs + measurements)
Crops: the item's saturation bounding box on the white paper (+5% margin), like the gauntlet.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from grading.measure import measure  # noqa: E402
from grading.rules import grade  # noqa: E402

BAD = {"C", "Reject"}


def item_crop_box(img):
    """Grading-proxy item box (x1, y1, x2, y2): saturated-or-dark pixels, opened, +5% padding."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 1] > 60) | (hsv[..., 2] < 90)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    ys, xs = np.where(m > 0)
    if len(xs) < 50:
        return 0, 0, img.shape[1], img.shape[0]
    x1, x2, y1, y2 = xs.min(), xs.max(), ys.min(), ys.max()
    pw, ph = int(0.05 * (x2 - x1)), int(0.05 * (y2 - y1))
    return int(max(0, x1 - pw)), int(max(0, y1 - ph)), int(x2 + pw), int(y2 + ph)


def item_crop(img):
    x1, y1, x2, y2 = item_crop_box(img)
    return img[y1:y2, x1:x2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cls", required=True)
    ap.add_argument("--temp", type=float, required=True)
    ap.add_argument("--imgsz", type=int, default=192)
    ap.add_argument("--data", default="/tmp/nsdata/quality2")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from ultralytics import YOLO
    model = YOLO(a.cls)
    names = [model.names[i] for i in range(len(model.names))]
    rows = []
    for lvl in ["fresh", "rotten"]:
        for f in sorted(glob.glob(f"{a.data}/test/{lvl}/*.jpg")):
            produce = os.path.basename(f).split("__")[0]
            crop = item_crop(cv2.imread(f))
            p = model.predict(crop, imgsz=a.imgsz, verbose=False, device="cpu")[0].probs.data.numpy().astype(np.float64)
            lg = np.log(np.clip(p, 1e-12, 1)) / a.temp
            pc = np.exp(lg - lg.max())
            pc /= pc.sum()
            probs = {n: float(v) for n, v in zip(names, pc)}
            c = crop
            s = 160 / max(c.shape[:2])
            if s < 1:
                c = cv2.resize(c, (int(c.shape[1] * s), int(c.shape[0] * s)), interpolation=cv2.INTER_AREA)
            m = measure(cv2.cvtColor(c, cv2.COLOR_BGR2RGB), produce).to_dict()
            full = grade(produce, 0.9, probs, m)
            meas = grade(produce, 0.9, {"fresh": 0.69, "rotten": 0.31}, m)
            rows.append(dict(file=os.path.basename(f), produce=produce, label=lvl, probs=probs, defect=m["defect_area_pct"], shape=m["shape_score"],
                             band=m["colour_band"], seg=m["segmentation"], grade_full=full["grade"], reasons=full["reasons"], grade_meas=meas["grade"]))
    out = {}
    for key, fn in [("classifier_only", lambda r: "rotten" if r["probs"].get("rotten", 0) > r["probs"].get("fresh", 0) else "fresh"),
                    ("measurements_only", lambda r: None if r["grade_meas"] == "ungradable" else ("rotten" if r["grade_meas"] in BAD else "fresh")),
                    ("classifier_plus_rules", lambda r: None if r["grade_full"] == "ungradable" else ("rotten" if r["grade_full"] in BAD else "fresh"))]:
        pred = [fn(r) for r in rows]
        ok = [p == r["label"] for p, r in zip(pred, rows) if p is not None]
        rot = [p == "rotten" for p, r in zip(pred, rows) if r["label"] == "rotten" and p is not None]
        fr = [p == "fresh" for p, r in zip(pred, rows) if r["label"] == "fresh" and p is not None]
        out[key] = dict(n=len(rows), graded=len(ok), ungradable=sum(p is None for p in pred), proxy_acc=round(float(np.mean(ok)), 4) if ok else None,
                        rotten_to_C_or_Reject=round(float(np.mean(rot)), 4) if rot else None, fresh_to_A_or_B=round(float(np.mean(fr)), 4) if fr else None)
    cm = collections.Counter((r["label"], r["grade_full"]) for r in rows)
    out["grade_distribution_full"] = {f"{k[0]}->{k[1]}": v for k, v in sorted(cm.items())}
    cm2 = collections.Counter((r["label"], r["grade_meas"]) for r in rows)
    out["grade_distribution_measurements_only"] = {f"{k[0]}->{k[1]}": v for k, v in sorted(cm2.items())}
    out["defect_pct_by_label"] = {l: dict(median=float(np.median([r["defect"] for r in rows if r["label"] == l])),
                                          p90=float(np.percentile([r["defect"] for r in rows if r["label"] == l], 90))) for l in ["fresh", "rotten"]}
    out["disclaimer"] = "WEAK PROXY: fresh/rotten dataset labels, not human grades. No kappa possible yet."
    out["examples_wrong_full"] = [dict(file=r["file"], label=r["label"], grade=r["grade_full"], reasons=r["reasons"]) for r in rows
                                  if (r["label"] == "fresh" and r["grade_full"] in BAD) or (r["label"] == "rotten" and r["grade_full"] in {"A", "B"})][:25]
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(dict(summary=out, rows=rows), open(a.out, "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "examples_wrong_full"}, indent=1))


if __name__ == "__main__":
    main()
