"""G9 Arm "existing models": adapter that runs a public Roboflow Universe detector (ONNX weights cached locally, CPU)
inside the NutriSole eval harnesses and maps its classes into our 12-class order.

No weights and no API key live in the repo. Weights are expected at $RF_WEIGHTS_DIR/<model>_model.onnx
(default /workspace/work/cv/g9existing), fetched once from api.roboflow.com/ort/<project>/<version> (signed URL).

Mapping rule (written BEFORE any scoring, G9 brief 2026-10-14): per anchor, take the argmax over the model's OWN classes;
if that source class is in the map, its score goes to the mapped NutriSole channel; otherwise the anchor is dropped
(unmatched classes ignored, never re-routed to a lower-scoring mapped class). No silent mapping: see CLASS_MAPS.
"""
from __future__ import annotations

import os

import cv2
import numpy as np
import onnxruntime as ort

NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
WEIGHTS_DIR = os.environ.get("RF_WEIGHTS_DIR", "/workspace/work/cv/g9existing")

# Source class order = ONNX output order (from api.roboflow.com/ort/... "classes" / environment.json CLASS_MAP).
MODELS = {
    "snapml": dict(
        universe="snapml-4ubnx/veggies-and-fruits-balanced-0g1ss/1", arch="yolov5v6n (Roboflow 2.0 Fast)", head="yolov5",
        size=416, prep="fit_black", licence_model="GPL-3.0 (YOLOv5 family)", licence_data="CC BY 4.0",
        classes=["Apple", "Artichoke", "Banana", "Bell pepper", "Broccoli", "Cabbage", "Cantaloupe", "Carrot", "Coconut", "Common fig",
                 "Cucumber", "Grape", "Grapefruit", "Lemon", "Mango", "Orange", "Peach", "Pear", "Pineapple", "Pomegranate", "Potato",
                 "Radish", "Salad", "Strawberry", "Tomato", "Watermelon", "Winter melon"]),
    "calories": dict(
        universe="calories/fruits-and-veg-2-x027v/2", arch="YOLOv8s (Ultralytics 8.0.196, uploaded weights)", head="yolov8",
        size=640, prep="stretch", licence_model="AGPL-3.0 (Ultralytics YOLOv8)", licence_data="CC BY 4.0",
        classes=["Bitter melon", "Brinjal", "Cabbage", "Calabash", "Capsicum", "Cauliflower", "Cherry", "Garlic", "Ginger", "Green Chili",
                 "Kiwi", "Lady finger", "Onion", "Potato", "Sponge Gourd", "Tomato", "apple", "avocado", "banana", "cucumber",
                 "dragon fruit", "egg", "guava", "mango", "orange", "oren", "peach", "pear", "pineapple", "strawberry", "sugar apple",
                 "watermelon"]),
}

# Explicit class maps (source -> NutriSole). Anything not listed is ignored at scoring (logged as out-of-taxonomy).
CLASS_MAPS = {
    "snapml": {"Apple": "apple", "Banana": "banana", "Mango": "mango", "Orange": "citrus", "Lemon": "lemon_lime",
               "Pomegranate": "pomegranate", "Tomato": "tomato", "Potato": "potato", "Cucumber": "cucumber", "Carrot": "carrot",
               "Bell pepper": "capsicum"},
    # Capsicum: 12/12 sampled training images (search API, class Capsicum) are whole green bell peppers -> mapped.
    "calories": {"apple": "apple", "banana": "banana", "mango": "mango", "orange": "citrus", "guava": "guava", "Tomato": "tomato",
                 "Potato": "potato", "cucumber": "cucumber", "Capsicum": "capsicum"},
}
EXPLICITLY_UNMAPPED = {
    "snapml": {"Grapefruit": "brief: do not count Grapefruit"},
    "calories": {"Green Chili": "brief: chilli is not capsicum", "oren": "brief: unmapped (samples look like orange; strict rule kept)"},
}


def coverage(name):
    m = CLASS_MAPS[name]
    got = sorted(set(m.values()), key=NAMES.index)
    return dict(mapped=got, missing=[n for n in NAMES if n not in got], n=len(got))


class RoboflowDet:
    """Duck-types the onnxruntime session used by video_gauntlet.py: get_inputs(), set_frame(frame, tf), run(None, feeds).
    run() ignores the harness's letterboxed tensor and builds the model's NATIVE input from the original frame (Roboflow
    preprocessing: 416 fit-with-black-edges for snapml, 640 stretch for calories), then returns a 'raw'-format tensor
    (1, 4+12, N) in the harness letterbox coordinate frame so geometry.decode(..., 'raw') + dst_to_src work unchanged."""

    def __init__(self, name, threads=2, weights=None):
        self.name, self.spec = name, MODELS[name]
        so = ort.SessionOptions()
        so.intra_op_num_threads = threads
        self.s = ort.InferenceSession(weights or os.path.join(WEIGHTS_DIR, f"{name}_model.onnx"), so, providers=["CPUExecutionProvider"])
        self.inp = self.s.get_inputs()[0].name
        self.out = self.s.get_outputs()[0].name
        cl = self.spec["classes"]
        self.tgt = np.array([NAMES.index(CLASS_MAPS[name][c]) if c in CLASS_MAPS[name] else -1 for c in cl])
        self._frame, self._tf = None, None

    def get_inputs(self):
        return self.s.get_inputs()

    def set_frame(self, frame, tf):
        self._frame, self._tf = frame, tf

    def _native(self, img):
        S, h, w = self.spec["size"], img.shape[0], img.shape[1]
        if self.spec["prep"] == "stretch":
            im = cv2.resize(img, (S, S), interpolation=cv2.INTER_LINEAR)
            sx, sy, px, py = S / w, S / h, 0.0, 0.0
        else:  # fit (black edges), centred
            r = min(S / w, S / h)
            nw, nh = int(round(w * r)), int(round(h * r))
            im = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
            px, py = (S - nw) // 2, (S - nh) // 2
            im = cv2.copyMakeBorder(im, py, S - nh - py, px, S - nw - px, cv2.BORDER_CONSTANT, value=(0, 0, 0))
            sx, sy = nw / w, nh / h
        x = np.ascontiguousarray(im[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255.0)
        return x, (sx, sy, px, py)

    def infer_src(self, img):
        """Return (boxes_xyxy_src_px [N,4], src_cls [N], score [N]) for every anchor (no threshold, no NMS)."""
        x, (sx, sy, px, py) = self._native(img)
        o = self.s.run([self.out], {self.inp: x})[0]
        if self.spec["head"] == "yolov5":
            o = o[0]                                  # (N, 5+nc): cx,cy,w,h,obj,cls...
            cxcywh, sc = o[:, :4], o[:, 4:5] * o[:, 5:]
        else:
            o = o[0].T                                # (N, 4+nc)
            cxcywh, sc = o[:, :4], o[:, 4:]
        c = sc.argmax(1)
        s = sc[np.arange(len(c)), c]
        b = np.stack([cxcywh[:, 0] - cxcywh[:, 2] / 2, cxcywh[:, 1] - cxcywh[:, 3] / 2,
                      cxcywh[:, 0] + cxcywh[:, 2] / 2, cxcywh[:, 1] + cxcywh[:, 3] / 2], 1)
        b[:, [0, 2]] = (b[:, [0, 2]] - px) / sx
        b[:, [1, 3]] = (b[:, [1, 3]] - py) / sy
        b[:, [0, 2]] = b[:, [0, 2]].clip(0, img.shape[1])
        b[:, [1, 3]] = b[:, [1, 3]].clip(0, img.shape[0])
        return b, c, s

    def run(self, _names, _feeds):
        b, c, s = self.infer_src(self._frame)
        tf = self._tf
        tg = self.tgt[c]
        keep = tg >= 0
        b, s, tg = b[keep], s[keep], tg[keep]
        # source-frame px -> harness letterbox px
        x1, x2 = b[:, 0] * tf["scaleX"] + tf["padX"], b[:, 2] * tf["scaleX"] + tf["padX"]
        y1, y2 = b[:, 1] * tf["scaleY"] + tf["padY"], b[:, 3] * tf["scaleY"] + tf["padY"]
        out = np.zeros((1, 4 + len(NAMES), len(s)), np.float32)
        out[0, 0], out[0, 1], out[0, 2], out[0, 3] = (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1
        out[0, 4 + tg, np.arange(len(s))] = s
        return [out]
