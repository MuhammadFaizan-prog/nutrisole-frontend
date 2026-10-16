"""G7 (prereg addendum A item 5): hue-shift sensitivity of colour-dependent heads.

Shifts hue by d degrees in OpenCV HSV (H stored 0..179, so d/2 units, wrapped), saturation/value untouched, then classifies.
Modes:
  quality  : G3 E224 fresh/rotten ONNX on a folder split DIR/{fresh,rotten}/*.jpg (locked G3 quality test), optional
             night_sodium_hard corruption (ml/eval/corruptions.py) applied BEFORE the hue shift (lighting family x hue).
  ripeness : G7 per-fruit ripeness ONNX (15 classes <fruit>_<stage>) on a folder DIR/<FruitStage>/*.jpg; conditional per-fruit
             argmax over the true fruit's 3 stages (as in ripeness_per_fruit), reported as stage accuracy.
Decision = argmax (temperature does not change it). Output: per shift accuracy, rotten recall (quality) / overripe recall (ripeness).
  python ml/eval/hue_shift.py quality --model M.onnx --data DIR [--night] --out OUT.json
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
from geometry import cls_preprocess  # noqa: E402

SHIFTS = [0, -5, 5, -10, 10, -20, 20]


def hue(im, d):
    if d == 0:
        return im
    h = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    h[..., 0] = ((h[..., 0].astype(np.int32) + int(round(d / 2))) % 180).astype(np.uint8)
    return cv2.cvtColor(h, cv2.COLOR_HSV2BGR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["quality", "ripeness"]); ap.add_argument("--model", required=True)
    ap.add_argument("--data", required=True); ap.add_argument("--imgsz", type=int, default=224)
    ap.add_argument("--night", action="store_true"); ap.add_argument("--out", required=True)
    ap.add_argument("--classes", default="", help="ripeness: comma list of the 15 model classes in index order")
    a = ap.parse_args()
    s = ort.InferenceSession(a.model, providers=["CPUExecutionProvider"]); inp = s.get_inputs()[0].name
    items = []
    if a.mode == "quality":
        for i, c in enumerate(["fresh", "rotten"]):
            items += [(f, i) for f in sorted(glob.glob(f"{a.data}/{c}/*.jpg"))]
    else:
        names = a.classes.split(",")
        for d in sorted(glob.glob(f"{a.data}/*/")):
            k = os.path.basename(d.rstrip("/")).lower().replace(" ", "")
            for n in names:
                fr, st = n.split("_")
                if k.startswith(fr) and k.endswith(st):
                    items += [(f, names.index(n)) for f in sorted(glob.glob(d + "*")) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    night = None
    if a.night:
        from corruptions import CORRUPTIONS
        night = CORRUPTIONS["night_sodium_hard"]
    ims = []
    for f, y in items:
        im = cv2.imread(f)
        if im is None:
            continue
        if night is not None:
            im = night(im)
        ims.append((im, y))
    out = dict(mode=a.mode, model=a.model, data=a.data, n=len(ims), night_sodium_hard=a.night, imgsz=a.imgsz,
               device="sandbox/Kaggle CPU, ONNX Runtime", decision="argmax", rows=[])
    for d in SHIFTS:
        ok, pos, tp = 0, 0, 0
        for im, y in ims:
            p = s.run(None, {inp: cls_preprocess(hue(im, d), a.imgsz)})[0][0]
            if a.mode == "quality":
                pred = int(np.argmax(p)); target_pos = y == 1
            else:
                names = a.classes.split(","); fr = names[y].split("_")[0]
                idx = [i for i, n in enumerate(names) if n.startswith(fr + "_")]
                pred = idx[int(np.argmax(p[idx]))]; target_pos = names[y].endswith("overripe")
            ok += pred == y
            if target_pos:
                pos += 1; tp += pred == y
        out["rows"].append(dict(hue_shift_deg=d, acc=round(ok / max(1, len(ims)), 4),
                                pos_recall=round(tp / max(1, pos), 4), n_pos=pos))
        print(d, out["rows"][-1], flush=True)
    out["pos_class"] = "rotten" if a.mode == "quality" else "overripe (conditional per-fruit)"
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True); json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
