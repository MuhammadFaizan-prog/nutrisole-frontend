"""Quality classifier evaluation: macro-F1, per-level recall (rotten recall = safety metric),
confusion matrix, temperature scaling fitted on VAL only, ECE/Brier before/after on TEST,
reliability diagram, selective-risk/coverage curve, per-produce breakdown, robustness sweep.

  python ml/eval/eval_cls.py --model runs/.../best.pt --data <quality dir> --imgsz 192 --out ml/runs/G1/eval_cls_q2
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from corruptions import CORRUPTIONS  # noqa: E402


def load_split(root, split, names):
    items = []
    for i, n in enumerate(names):
        for f in sorted(glob.glob(f"{root}/{split}/{n}/*.jpg")):
            items.append((f, i, os.path.basename(f).split("__")[0]))
    return items


def predict(model, files, imgsz, corrupt=None, bs=64):
    probs = []
    for i in range(0, len(files), bs):
        ims = [cv2.imread(f) for f in files[i:i + bs]]
        if corrupt:
            ims = [corrupt(im) for im in ims]
        rs = model.predict(ims, imgsz=imgsz, verbose=False, device="cpu")
        probs += [r.probs.data.cpu().numpy() for r in rs]
    return np.array(probs, np.float64)


def temp_scale(p, T):
    lg = np.log(np.clip(p, 1e-12, 1)) / T
    lg -= lg.max(1, keepdims=True)
    e = np.exp(lg)
    return e / e.sum(1, keepdims=True)


def nll(p, y):
    return float(-np.mean(np.log(np.clip(p[np.arange(len(y)), y], 1e-12, 1))))


def fit_T(p, y):
    grid = np.exp(np.linspace(np.log(0.25), np.log(8), 400))
    vals = [nll(temp_scale(p, T), y) for T in grid]
    return float(grid[int(np.argmin(vals))])


def ece(p, y, bins=15):
    conf, pred = p.max(1), p.argmax(1)
    e, rows = 0.0, []
    edges = np.linspace(0, 1, bins + 1)
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.sum():
            acc, c = float((pred[m] == y[m]).mean()), float(conf[m].mean())
            e += m.mean() * abs(acc - c)
            rows.append(dict(lo=float(lo), hi=float(hi), n=int(m.sum()), acc=acc, conf=c))
    return float(e), rows


def brier(p, y):
    oh = np.eye(p.shape[1])[y]
    return float(np.mean(np.sum((p - oh) ** 2, 1)))


def cls_metrics(p, y, names):
    pred = p.argmax(1)
    k = len(names)
    cm = np.zeros((k, k), int)
    for t, q in zip(y, pred):
        cm[t, q] += 1
    rec = {n: (cm[i, i] / cm[i].sum() if cm[i].sum() else None) for i, n in enumerate(names)}
    prec = {n: (cm[i, i] / cm[:, i].sum() if cm[:, i].sum() else None) for i, n in enumerate(names)}
    f1 = {n: (2 * prec[n] * rec[n] / (prec[n] + rec[n]) if prec[n] and rec[n] else 0.0) for n in names}
    return dict(n=int(len(y)), acc=float((pred == y).mean()), macro_f1=float(np.mean(list(f1.values()))),
                recall=rec, precision=prec, f1=f1, confusion=cm.tolist())


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    s = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round((c - s) / d, 4), round((c + s) / d, 4)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--imgsz", type=int, default=192)
    ap.add_argument("--out", required=True)
    ap.add_argument("--robust", action="store_true")
    ap.add_argument("--val-split", default="val", help="G4: split used to fit the temperature (val_hard = harder held-out crop VAL)")
    a = ap.parse_args()
    from ultralytics import YOLO
    os.makedirs(a.out, exist_ok=True)
    model = YOLO(a.model)
    names = [model.names[i] for i in range(len(model.names))]
    val = load_split(a.data, a.val_split, names)
    test = load_split(a.data, "test", names)
    pv = predict(model, [f for f, _, _ in val], a.imgsz)
    yv = np.array([c for _, c, _ in val])
    pt = predict(model, [f for f, _, _ in test], a.imgsz)
    yt = np.array([c for _, c, _ in test])
    T = fit_T(pv, yv)
    pt_cal = temp_scale(pt, T)
    e0, rel0 = ece(pt, yt)
    e1, rel1 = ece(pt_cal, yt)
    m = cls_metrics(pt, yt, names)
    if "rotten" in names:
        ri = names.index("rotten")
        k = int(m["confusion"][ri][ri])
        m["rotten_recall_ci95"] = wilson(k, int(sum(m["confusion"][ri])))
    per_prod = {}
    prods = np.array([p for _, _, p in test])
    for pr in sorted(set(prods)):
        sel = prods == pr
        per_prod[pr] = cls_metrics(pt[sel], yt[sel], names)
    # selective risk / coverage on calibrated test probs
    conf = pt_cal.max(1)
    order = np.argsort(-conf)
    correct = (pt_cal.argmax(1) == yt)[order]
    cov_rows = []
    for cov in [1.0, 0.95, 0.9, 0.8, 0.7, 0.5]:
        n = max(1, int(round(cov * len(order))))
        cov_rows.append(dict(coverage=cov, risk=round(1 - float(correct[:n].mean()), 4), min_conf=round(float(conf[order][n - 1]), 4)))
    abst = dict(threshold=0.5, abstain_frac=float((conf < 0.5).mean()))
    rep = dict(model=a.model, data=a.data, imgsz=a.imgsz, device="cpu", names=names, temp_fit_split=a.val_split, n_val=len(yv), n_test=len(yt),
               test=m, per_produce=per_prod, temperature=T, nll_test_before=nll(pt, yt), nll_test_after=nll(pt_cal, yt),
               ece_test_before=e0, ece_test_after=e1, brier_before=brier(pt, yt), brier_after=brier(pt_cal, yt),
               reliability_before=rel0, reliability_after=rel1, selective=cov_rows, abstain_at_0_5=abst)
    if a.robust:
        rob = {}
        for cname, fn in CORRUPTIONS.items():
            pr = temp_scale(predict(model, [f for f, _, _ in test], a.imgsz, corrupt=fn), T)
            mm = cls_metrics(pr, yt, names)
            rob[cname] = dict(acc=mm["acc"], macro_f1=mm["macro_f1"], rotten_recall=mm["recall"].get("rotten"))
        rep["robustness"] = rob
    json.dump(rep, open(f"{a.out}/eval_cls.json", "w"), indent=1, default=float)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(4, 4))
        for rows, lab in [(rel0, f"before ECE={e0:.3f}"), (rel1, f"after T={T:.2f} ECE={e1:.3f}")]:
            ax.plot([r["conf"] for r in rows], [r["acc"] for r in rows], "o-", label=lab)
        ax.plot([0, 1], [0, 1], "k--", lw=0.8)
        ax.set_xlabel("confidence")
        ax.set_ylabel("accuracy")
        ax.set_title("Reliability (test)")
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(f"{a.out}/reliability.png", dpi=110)
    except Exception as ex:  # plotting is optional
        print("plot failed", ex)
    print(json.dumps(dict(T=T, acc=m["acc"], macro_f1=m["macro_f1"], recall=m["recall"], ece_before=e0, ece_after=e1,
                          robust=rep.get("robustness")), default=float))


if __name__ == "__main__":
    main()
