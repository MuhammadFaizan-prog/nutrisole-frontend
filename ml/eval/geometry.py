"""Letterbox geometry identical to native/src/cv/pipeline/preprocess.ts (computeTransform
'letterbox') and to Ultralytics LetterBox(auto=False, center=True, padding value 114)."""
from __future__ import annotations

import cv2
import numpy as np


def letterbox(img_bgr: np.ndarray, size: int):
    """Return (CHW float32 RGB tensor in [0,1] with batch dim, transform dict)."""
    h, w = img_bgr.shape[:2]
    r = min(size / h, size / w)
    nw, nh = int(round(w * r)), int(round(h * r))
    dw, dh = (size - nw) / 2, (size - nh) / 2
    im = cv2.resize(img_bgr, (nw, nh), interpolation=cv2.INTER_LINEAR) if (nw, nh) != (w, h) else img_bgr
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    im = cv2.copyMakeBorder(im, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
    x = im[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255.0
    t = dict(srcW=w, srcH=h, scaleX=nw / w, scaleY=nh / h, padX=left, padY=top, dstW=size, dstH=size)
    return np.ascontiguousarray(x), t


def dst_to_src(b, t, clip=True):
    x1 = (b[0] - t["padX"]) / t["scaleX"]
    y1 = (b[1] - t["padY"]) / t["scaleY"]
    x2 = (b[2] - t["padX"]) / t["scaleX"]
    y2 = (b[3] - t["padY"]) / t["scaleY"]
    if clip:
        x1, x2 = min(max(x1, 0), t["srcW"]), min(max(x2, 0), t["srcW"])
        y1, y2 = min(max(y1, 0), t["srcH"]), min(max(y2, 0), t["srcH"])
    return [x1, y1, x2, y2]


def cls_preprocess(crop_bgr: np.ndarray, size: int):
    """Ultralytics classify eval transform: resize shorter side to size, centre crop, /255."""
    h, w = crop_bgr.shape[:2]
    s = size / min(h, w)
    nh, nw = max(size, int(round(h * s))), max(size, int(round(w * s)))
    im = cv2.resize(crop_bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
    y0, x0 = (nh - size) // 2, (nw - size) // 2
    im = im[y0:y0 + size, x0:x0 + size]
    return np.ascontiguousarray(im[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255.0)


def decode(out: np.ndarray, kind: str, conf: float, iou_thr: float = 0.7):
    """kind 'e2e': (1,300,6) x1,y1,x2,y2,score,cls  |  kind 'raw': (1,4+nc,N) cx,cy,w,h,scores (class-wise NMS)."""
    if kind == "e2e":
        o = out[0]
        o = o[o[:, 4] >= conf]
        return [dict(box=[float(v) for v in r[:4]], score=float(r[4]), classId=int(round(r[5]))) for r in o[np.argsort(-o[:, 4])]]
    o = out[0]
    nc = o.shape[0] - 4
    scores = o[4:]
    cls = scores.argmax(0)
    sc = scores[cls, np.arange(o.shape[1])]
    keep = sc > conf
    cx, cy, w, h = o[0][keep], o[1][keep], o[2][keep], o[3][keep]
    cands = sorted([dict(box=[float(cx[i] - w[i] / 2), float(cy[i] - h[i] / 2), float(cx[i] + w[i] / 2), float(cy[i] + h[i] / 2)],
                         score=float(sc[keep][i]), classId=int(cls[keep][i])) for i in range(len(cx))], key=lambda d: -d["score"])
    from tracker import iou
    kept = []
    for d in cands:
        if any(k["classId"] == d["classId"] and iou(k["box"], d["box"]) > iou_thr for k in kept):
            continue
        kept.append(d)
        if len(kept) >= 300:
            break
    return kept
