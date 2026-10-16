"""G7 Phase 5 (tiny objects): size-bucketed recall/precision of a detector at several input sizes and with 2x2 tiling,
plus per-image CPU latency. Locked split images are only READ (no training).

Buckets = GT box shorter side measured at the 480 eval scale (longest image side -> 480): <6, 6-12, 12-24, 24-48, >=48 px.
Matching: greedy by score, IoU >= 0.5, class-aware ("cls") and class-agnostic ("any"); conf >= 0.25 (G6 audit setting).
Modes: plain imgsz in --sizes; "tile480": 2x2 tiles with 20% overlap at 480 each + the full image at 480, merged with
class-wise NMS 0.6 (5 forward passes). Latency = wall time per image of predict(), sandbox CPU, batch 1, PyTorch (Ultralytics).
  python ml/eval/size_buckets.py --model best.pt --list /workspace/work/cv/g3data/det_v3/test.txt --sizes 480 640 800 --tile --out OUT.json
"""
from __future__ import annotations

import argparse
import json
import os
import time

import cv2
import numpy as np
import torch
import torchvision
from ultralytics import YOLO

B = [(0, 6), (6, 12), (12, 24), (24, 48), (48, 1e9)]
BN = ["<6", "6-12", "12-24", "24-48", ">=48"]


def gt_of(img_path, W, H):
    lp = img_path.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"
    out = []
    if os.path.exists(lp):
        for l in open(lp):
            v = l.split()
            if len(v) == 5:
                c, x, y, w, h = int(v[0]), *map(float, v[1:])
                out.append((c, np.array([(x - w / 2) * W, (y - h / 2) * H, (x + w / 2) * W, (y + h / 2) * H])))
    return out


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i + 1e-9)


def predict(m, im, sz, conf):
    r = m.predict(im, imgsz=sz, conf=conf, iou=0.7, verbose=False, device="cpu")[0]
    return r.boxes.xyxy.numpy(), r.boxes.conf.numpy(), r.boxes.cls.numpy().astype(int)


def predict_tiles(m, im, conf):
    H, W = im.shape[:2]; bx, sc, cl = [*predict(m, im, 480, conf)][0:3]
    bx, sc, cl = [bx], [sc], [cl]
    tw, th = int(W * 0.6), int(H * 0.6)
    for x0 in (0, W - tw):
        for y0 in (0, H - th):
            b, s, c = predict(m, im[y0:y0 + th, x0:x0 + tw], 480, conf)
            bx.append(b + np.array([x0, y0, x0, y0])); sc.append(s); cl.append(c)
    bx, sc, cl = np.concatenate(bx), np.concatenate(sc), np.concatenate(cl)
    if len(bx) == 0:
        return bx, sc, cl
    k = torchvision.ops.batched_nms(torch.tensor(bx, dtype=torch.float32), torch.tensor(sc), torch.tensor(cl), 0.6).numpy()
    return bx[k], sc[k], cl[k]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True); ap.add_argument("--list", required=True); ap.add_argument("--sizes", nargs="+", type=int, default=[480])
    ap.add_argument("--tile", action="store_true"); ap.add_argument("--conf", type=float, default=0.25); ap.add_argument("--out", required=True)
    a = ap.parse_args(); torch.set_num_threads(2)
    m = YOLO(a.model)
    imgs = [l.strip() for l in open(a.list) if l.strip()]
    modes = [str(s) for s in a.sizes] + (["tile480"] if a.tile else [])
    res = dict(model=a.model, split=a.list, n_images=len(imgs), conf=a.conf, iou_match=0.5, device="sandbox CPU (2 threads), PyTorch", modes={})
    data = []
    for p in imgs:
        im = cv2.imread(p)
        if im is None:
            continue
        H, W = im.shape[:2]; s480 = 480 / max(H, W)
        g = [(c, b, min(b[2] - b[0], b[3] - b[1]) * s480) for c, b in gt_of(p, W, H)]
        data.append((p, g))
    for mode in modes:
        tp = {k: np.zeros(len(B)) for k in ("cls", "any")}; n = np.zeros(len(B)); lat = []; npred = 0; ntp_pred = 0
        for p, g in data:
            im = cv2.imread(p)
            t = time.perf_counter()
            bx, sc, cl = predict_tiles(m, im, a.conf) if mode == "tile480" else predict(m, im, int(mode), a.conf)
            lat.append(time.perf_counter() - t)
            o = np.argsort(-sc); npred += len(o)
            for kind in ("cls", "any"):
                used = set()
                for i in o:
                    best, bj = 0.5, -1
                    for j, (c, b, _) in enumerate(g):
                        if j in used or (kind == "cls" and c != cl[i]):
                            continue
                        v = iou(bx[i], b)
                        if v >= best:
                            best, bj = v, j
                    if bj >= 0:
                        used.add(bj)
                        if kind == "cls":
                            ntp_pred += 1
                for j in used:
                    tp[kind][next(k for k, (lo, hi) in enumerate(B) if lo <= g[j][2] < hi)] += 1
            for c, b, s in g:
                n[next(k for k, (lo, hi) in enumerate(B) if lo <= s < hi)] += 1
        res["modes"][mode] = dict(
            buckets={BN[k]: dict(n_gt=int(n[k]), recall_cls=round(tp["cls"][k] / max(1, n[k]), 3), recall_any=round(tp["any"][k] / max(1, n[k]), 3)) for k in range(len(B))},
            recall_cls_all=round(tp["cls"].sum() / max(1, n.sum()), 3), precision_cls=round(ntp_pred / max(1, npred), 3), n_pred=int(npred),
            latency_ms_p50=round(1000 * float(np.percentile(lat, 50)), 1), latency_ms_p90=round(1000 * float(np.percentile(lat, 90)), 1))
        print(mode, json.dumps(res["modes"][mode]), flush=True)
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True); json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
