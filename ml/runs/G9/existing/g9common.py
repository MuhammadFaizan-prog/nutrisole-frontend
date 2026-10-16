"""G9 existing-models arm: shared detector wrappers (G3 control vs Roboflow Universe models) for the 2 fps VB8-dev replay and
the still-image val check. Same decode/NMS (class-wise, IoU 0.7, max 300) for every model."""
from __future__ import annotations

import os
import sys
import time

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, os.path.join(REPO, "ml/eval"))
sys.path.insert(0, os.path.join(REPO, "ml"))
from geometry import letterbox, dst_to_src  # noqa: E402
from roboflow_adapter import RoboflowDet, NAMES, MODELS  # noqa: E402

G3_ONNX = "/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx"
G3_IMGSZ = 480


def iou_mat(a, b):
    x1 = np.maximum(a[:, None, 0], b[None, :, 0]); y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2]); y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    aa = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1]); bb = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / np.maximum(aa[:, None] + bb[None] - inter, 1e-9)


def nms_classwise(b, c, s, conf, iou_thr=0.7, max_det=300):
    k = s > conf
    b, c, s = b[k], c[k], s[k]
    o = np.argsort(-s)
    b, c, s = b[o], c[o], s[o]
    keep = []
    for i in range(len(s)):
        if keep:
            kk = np.array(keep)
            same = kk[c[kk] == c[i]]
            if len(same) and iou_mat(b[i:i + 1], b[same]).max() > iou_thr:
                continue
        keep.append(i)
        if len(keep) >= max_det:
            break
    keep = np.array(keep, int)
    return b[keep], c[keep], s[keep]


class Detector:
    """__call__(img_bgr, conf) -> dict(mapped=[(box_px, cls12, score)], unmapped={src_name: n}, ms)."""

    def __init__(self, name):
        self.name = name
        if name == "g3":
            import onnxruntime as ort
            so = ort.SessionOptions(); so.intra_op_num_threads = 2
            self.s = ort.InferenceSession(G3_ONNX, so, providers=["CPUExecutionProvider"])
            self.inp = self.s.get_inputs()[0].name
        else:
            self.rf = RoboflowDet(name)

    def __call__(self, img, conf, unmapped_conf=0.35):
        t0 = time.perf_counter()
        unmapped = {}
        if self.name == "g3":
            x, tf = letterbox(img, G3_IMGSZ)
            o = self.s.run(None, {self.inp: x})[0][0]
            sc = o[4:]; c = sc.argmax(0); s = sc[c, np.arange(o.shape[1])]
            b = np.stack([o[0] - o[2] / 2, o[1] - o[3] / 2, o[0] + o[2] / 2, o[1] + o[3] / 2], 1)
            b, c, s = nms_classwise(b, c, s, conf)
            b = np.array([dst_to_src(bb, tf) for bb in b]).reshape(-1, 4)
        else:
            b, c, s = self.rf.infer_src(img)
            b, c, s = nms_classwise(b, c, s, conf)          # NMS over the model's OWN classes, then map
            tg = self.rf.tgt[c]
            for ci, si in zip(c[tg < 0], s[tg < 0]):
                if si < max(conf, unmapped_conf):
                    continue
                n = MODELS[self.name]["classes"][ci]
                unmapped[n] = unmapped.get(n, 0) + 1
            b, c, s = b[tg >= 0], tg[tg >= 0], s[tg >= 0]
        ms = 1000 * (time.perf_counter() - t0)
        return dict(mapped=[(bb.tolist(), int(cc), float(ss)) for bb, cc, ss in zip(b, c, s)], unmapped=unmapped, ms=ms)
