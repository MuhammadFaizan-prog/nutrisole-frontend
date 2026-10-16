"""G10: inference-only benchmark of a detector checkpoint (G3 or an EXTERNAL checkpoint) on a NutriSole split, with the
candidate's own class names remapped to the 12 NutriSole ids (ml/data/class_map.csv semantics). No training.

Why a separate script: Ultralytics model.val() needs the model's class list to equal the dataset's, which is not true for
external checkpoints (4 / 63 classes). Everything else is reused: Ultralytics predict (conf 0.001, NMS iou 0.7, max_det 300),
BaseValidator.match_predictions (greedy, IoU 0.50:0.95) and utils.metrics.ap_per_class -- the same functions model.val() uses.
G3 is run through this script too, and the result is compared with eval_det.py on the same split (parity row in the report).

Outputs (JSON): mAP50 / mAP50-95 / P / R over the classes that have GT in the split, per-class AP50 / AP50-95 / P / R / GT count,
per-class recall at conf >= 0.35 (rubric detectorMinScore), size-bucket recall (GT shorter side at the 480 scale, as
size_buckets.py), and the image-level false-alarm rate (any MAPPED box >= 0.35) on a negative image list.
Labels are the existing agent-labelled / dataset labels: EXPLORATORY, not human-verified ground truth.

  python ml/eval/g10_ext_bench.py --model best.pt --map g3 --imgsz 480 --list val.txt --neg negval.txt --out out.json
  python ml/eval/g10_ext_bench.py --model Yolo11.pt --map mark360 --imgsz 640 ...
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from size_buckets import B, BN, gt_of  # noqa: E402

NS = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
# candidate class name -> NutriSole id. Unlisted names are dropped (unsupported produce = background, as in class_map.csv).
MAPS = {
    "g3": {n: i for i, n in enumerate(NS)},
    "mark360": {"apple": 1, "mango": 2, "banana": 0, "orange": 3},
    "lvis63": {"banana": 0, "apple": 1, "orange/orange fruit": 3, "mandarin orange": 3, "clementine": 3, "lemon": 6, "lime": 6,
               "Tomato": 7, "tomato": 7, "potato": 8, "cucumber/cuke": 9, "carrot": 10, "bell pepper/capsicum": 11},
}
IOUV = torch.linspace(0.5, 0.95, 10)


def match(pred_cls, true_cls, iou):
    from ultralytics.engine.validator import BaseValidator
    v = BaseValidator.__new__(BaseValidator); v.iouv = IOUV
    return BaseValidator.match_predictions(v, torch.tensor(pred_cls), torch.tensor(true_cls), torch.tensor(iou)).numpy()


def box_iou(a, b):
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)))
    ix = np.clip(np.minimum(a[:, None, 2], b[None, :, 2]) - np.maximum(a[:, None, 0], b[None, :, 0]), 0, None)
    iy = np.clip(np.minimum(a[:, None, 3], b[None, :, 3]) - np.maximum(a[:, None, 1], b[None, :, 1]), 0, None)
    inter = ix * iy
    ar = lambda x: (x[:, 2] - x[:, 0]) * (x[:, 3] - x[:, 1])
    return inter / (ar(a)[:, None] + ar(b)[None, :] - inter + 1e-9)


def predict(m, path, imgsz, cmap, conf):
    r = m.predict(path, imgsz=imgsz, conf=conf, iou=0.7, max_det=300, verbose=False, device="cpu")[0]
    bx, sc, cl = r.boxes.xyxy.numpy(), r.boxes.conf.numpy(), r.boxes.cls.numpy().astype(int)
    keep = np.array([m.names[c] in cmap for c in cl], dtype=bool) if len(cl) else np.zeros(0, bool)
    ncl = np.array([cmap[m.names[c]] for c in cl[keep]], dtype=int)
    return bx[keep], sc[keep], ncl, r.orig_shape


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True); ap.add_argument("--map", required=True, choices=list(MAPS))
    ap.add_argument("--imgsz", type=int, default=640); ap.add_argument("--list", required=True)
    ap.add_argument("--neg", default=None); ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    from ultralytics import YOLO
    from ultralytics.utils.metrics import ap_per_class
    m = YOLO(a.model); cmap = MAPS[a.map]
    files = [l.strip() for l in open(a.list) if l.strip()]
    if a.limit: files = files[:a.limit]
    stats = dict(tp=[], conf=[], pred_cls=[], target_cls=[])
    sz_hit = {n: [0, 0] for n in BN}; rec35 = {i: [0, 0] for i in range(12)}; lat = []
    for f in files:
        t0 = time.perf_counter(); bx, sc, cl, (H, W) = predict(m, f, a.imgsz, cmap, 0.001); lat.append((time.perf_counter() - t0) * 1e3)
        gt = gt_of(f, W, H); tc = np.array([g[0] for g in gt], int); tb = np.array([g[1] for g in gt]).reshape(-1, 4)
        iou = box_iou(tb, bx)
        corr = match(cl, tc, iou) if len(cl) else np.zeros((0, 10), bool)
        stats["tp"].append(corr); stats["conf"].append(sc); stats["pred_cls"].append(cl); stats["target_cls"].append(tc)
        # recall at the rubric score 0.35, class-aware, IoU 0.5, greedy by score; size buckets on the same matches
        k = sc >= 0.35; used = set(); s = 480 / max(W, H)
        hit = np.zeros(len(gt), bool)
        for j in np.argsort(-sc[k]):
            pj = np.where(k)[0][j]; best, bi = 0.5, -1
            for gi in range(len(gt)):
                if gi in used or tc[gi] != cl[pj]: continue
                if iou[gi, pj] >= best: best, bi = iou[gi, pj], gi
            if bi >= 0: used.add(bi); hit[bi] = True
        for gi in range(len(gt)):
            rec35[int(tc[gi])][1] += 1; rec35[int(tc[gi])][0] += int(hit[gi])
            side = min(tb[gi, 2] - tb[gi, 0], tb[gi, 3] - tb[gi, 1]) * s
            bn = BN[[lo <= side < hi for lo, hi in B].index(True)]
            sz_hit[bn][1] += 1; sz_hit[bn][0] += int(hit[gi])
    cat = {k: np.concatenate(v, 0) if len(v) else np.zeros(0) for k, v in stats.items()}
    names = {i: n for i, n in enumerate(NS)}
    res = ap_per_class(cat["tp"], cat["conf"], cat["pred_cls"], cat["target_cls"], plot=False, names=names)
    tp, fp, p, r, f1, ap_, unique = res[:7]
    per = {}
    for j, c in enumerate(unique):
        c = int(c); per[NS[c]] = dict(P=round(float(p[j]), 4), R=round(float(r[j]), 4), AP50=round(float(ap_[j, 0]), 4),
                                      AP50_95=round(float(ap_[j].mean()), 4), gt=int((cat["target_cls"] == c).sum()),
                                      recall_at_035=round(rec35[c][0] / max(1, rec35[c][1]), 4),
                                      model_predicts_class=c in set(cmap.values()))
    out = dict(model=a.model, map=a.map, imgsz=a.imgsz, list=a.list, n_images=len(files), device="sandbox CPU (2 vCPU aarch64), PyTorch/Ultralytics predict",
               label_status="existing dataset / agent-curated labels; EXPLORATORY, not human-verified",
               mAP50=round(float(ap_[:, 0].mean()), 4) if len(unique) else 0.0, mAP50_95=round(float(ap_.mean()), 4) if len(unique) else 0.0,
               P=round(float(p.mean()), 4) if len(unique) else 0.0, R=round(float(r.mean()), 4) if len(unique) else 0.0,
               per_class=per, size_bucket_recall_at_035={k: dict(hit=v[0], gt=v[1], recall=round(v[0] / max(1, v[1]), 4)) for k, v in sz_hit.items()},
               predict_ms_p50=round(float(np.percentile(lat, 50)), 1), predict_ms_p95=round(float(np.percentile(lat, 95)), 1))
    if a.neg:
        nf = [l.strip() for l in open(a.neg) if l.strip()]; n_img = 0; n_box = 0
        for f in nf:
            bx, sc, cl, _ = predict(m, f, a.imgsz, cmap, 0.35); n_img += len(sc) > 0; n_box += len(sc)
        out["neg"] = dict(list=a.neg, n=len(nf), images_with_mapped_box_ge_035=n_img, fa_image_rate=round(n_img / max(1, len(nf)), 4), boxes=n_box)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, "w"), indent=1)
    print(a.model, a.imgsz, out["mAP50"], out["mAP50_95"], out.get("neg", {}).get("fa_image_rate"), flush=True)


if __name__ == "__main__":
    main()
