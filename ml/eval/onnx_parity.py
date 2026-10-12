"""Export parity (rule 8.12): PyTorch vs ONNX on the same fixture images with stated tolerances.

Fix for the G0 mismatch: G0 compared Ultralytics PyTorch predict (rect letterbox, minimal
padding) with a square ONNX letterbox. Here BOTH paths use the identical square letterbox:
  A) PyTorch: YOLO(pt).predict(rect=False, imgsz=S)  (Ultralytics LetterBox auto=False)
  B) ONNX via the APP pipeline: ml/eval/geometry.letterbox -> onnxruntime -> decode -> dst_to_src
Detections (conf >= 0.35) are matched greedily by IoU. Tolerances (stated before running):
  class agreement 100% of matched pairs, matched IoU >= 0.98, |dconf| <= 0.02,
  unmatched detections allowed only when the other side's score is within 0.02 of 0.35.
Classifier: same crop preprocessing (resize short side + centre crop), max |dprob| <= 1e-3, top-1 equal.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import cv2
import numpy as np
import onnxruntime as ort

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geometry import letterbox, dst_to_src, decode, cls_preprocess  # noqa: E402
from tracker import iou  # noqa: E402

CONF = 0.35


def det_parity(pt, onnx, kind, imgs, S):
    from ultralytics import YOLO
    m = YOLO(pt)
    s = ort.InferenceSession(onnx, providers=["CPUExecutionProvider"])
    name = s.get_inputs()[0].name
    rows, ious, dconf, cls_dis, unmatched_bad, unmatched_ok, n_pairs = [], [], [], 0, 0, 0, 0
    raw_diff = []
    for p in imgs:
        im = cv2.imread(p)
        # Ultralytics 8.4.175: nms=False selects the NMS-free one2one head in PyTorch too (default = one2many + NMS)
        kw = dict(nms=False) if kind == "e2e" else {}
        r = m.predict(im, imgsz=S, rect=False, conf=0.25, verbose=False, device="cpu", **kw)[0]
        A = [dict(box=b.tolist(), score=float(c), cls=int(k)) for b, c, k in zip(r.boxes.xyxy.numpy(), r.boxes.conf.numpy(), r.boxes.cls.numpy())]
        x, t = letterbox(im, S)
        out = s.run(None, {name: x})[0]
        B = []
        for d in decode(out, kind, 0.25):
            B.append(dict(box=dst_to_src(d["box"], t), score=d["score"], cls=d["classId"]))
        A = [a for a in A if a["score"] >= CONF - 0.02]
        B = [b for b in B if b["score"] >= CONF - 0.02]
        used = set()
        for a in sorted(A, key=lambda z: -z["score"]):
            best, bj = 0.0, -1
            for j, b in enumerate(B):
                if j in used:
                    continue
                v = iou(a["box"], b["box"])
                if v > best:
                    best, bj = v, j
            if bj >= 0 and best >= 0.5:
                used.add(bj)
                b = B[bj]
                n_pairs += 1
                ious.append(best)
                dconf.append(abs(a["score"] - b["score"]))
                cls_dis += a["cls"] != b["cls"]
            elif a["score"] >= CONF + 0.02:
                unmatched_bad += 1
            else:
                unmatched_ok += 1
        for j, b in enumerate(B):
            if j not in used:
                if b["score"] >= CONF + 0.02:
                    unmatched_bad += 1
                else:
                    unmatched_ok += 1
    res = dict(images=len(imgs), imgsz=S, matched_pairs=n_pairs, class_disagreements=cls_dis,
               min_iou=float(min(ious)) if ious else None, mean_iou=float(np.mean(ious)) if ious else None,
               max_dconf=float(max(dconf)) if dconf else None, mean_dconf=float(np.mean(dconf)) if dconf else None,
               unmatched_beyond_tolerance=unmatched_bad, unmatched_near_threshold=unmatched_ok)
    res["pass"] = bool(n_pairs > 0 and cls_dis == 0 and res["min_iou"] >= 0.98 and res["max_dconf"] <= 0.02 and unmatched_bad == 0)
    return res


def cls_parity(pt, onnx, imgs, S):
    from ultralytics import YOLO
    m = YOLO(pt)
    s = ort.InferenceSession(onnx, providers=["CPUExecutionProvider"])
    name = s.get_inputs()[0].name
    diffs, top_dis = [], 0
    import torch
    net = m.model.eval()
    for p in imgs:
        x = cls_preprocess(cv2.imread(p), S)
        po = s.run(None, {name: x})[0][0]
        with torch.no_grad():
            pp = net(torch.from_numpy(x))
            pp = (pp[0] if isinstance(pp, (list, tuple)) else pp)[0].numpy()
        diffs.append(float(np.abs(po - pp).max()))
        top_dis += int(po.argmax() != pp.argmax())
    res = dict(images=len(imgs), imgsz=S, max_abs_prob_diff=max(diffs), mean_abs_prob_diff=float(np.mean(diffs)), top1_disagreements=top_dis,
               note="same tensor fed to PyTorch module and ONNX (cls_preprocess = app crop preprocessing)")
    res["pass"] = bool(res["max_abs_prob_diff"] <= 1e-3 and top_dis == 0)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--det-pt")
    ap.add_argument("--det-onnx")
    ap.add_argument("--det-kind", choices=["e2e", "raw"])
    ap.add_argument("--det-imgs", default="/tmp/nsdata/det/images/test/*.jpg")
    ap.add_argument("--cls-pt")
    ap.add_argument("--cls-onnx")
    ap.add_argument("--cls-imgs", default="/tmp/nsdata/quality2/test/*/*.jpg")
    ap.add_argument("--imgsz", type=int, default=320)
    ap.add_argument("--cls-imgsz", type=int, default=192)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rep = {}
    if a.det_pt:
        imgs = sorted(glob.glob(a.det_imgs))[:a.n]
        rep["detector"] = dict(pt=a.det_pt, onnx=a.det_onnx, **det_parity(a.det_pt, a.det_onnx, a.det_kind, imgs, a.imgsz))
    if a.cls_pt:
        imgs = sorted(glob.glob(a.cls_imgs))[::7][:a.n]
        rep["classifier"] = dict(pt=a.cls_pt, onnx=a.cls_onnx, **cls_parity(a.cls_pt, a.cls_onnx, imgs, a.cls_imgsz))
    json.dump(rep, open(a.out, "w"), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
