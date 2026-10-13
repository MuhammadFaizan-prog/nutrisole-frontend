"""G7 Phase 5: independent guava evaluation (image level).

Source: Mendeley 10.17632/w3fg8jjmzr.1 "Guava Fruit Dataset for Classification" (Maitlo et al., SZABIST Larkana, Sindh, Pakistan;
CC BY 4.0). 2 309 studio photos, one guava per image on a white background, 3 varieties (Local Sindhi / Thadhrami / Riyali) x
3 maturity folders (Green / Mature Green / Ripe). It has NO boxes, so this is an image-level test of "does the detector say guava":
  hit@0.35   : any kept guava box with score >= 0.35 (rubric detectorMinScore)
  top=guava  : the highest-scoring kept box (score >= 0.35) is guava
  none       : no kept box of any class >= 0.35
plus the class of the top box when it is not guava (confusions). Never used for training by any NutriSole model (the G6/G7 rpx
guava data is Kaggle hosythao/guava-fruit-dataset-yolo8). Not a market scene and not Lahore. Images per physical fruit are not
documented, so the bootstrap CI (resampling images) may be too narrow.
  python ml/eval/guava_independent.py --root DIR --models TAG=path.onnx ... --per-cell 30 --out ml/runs/G7/guava_independent.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from video_gauntlet import sess, letterbox, decode  # noqa: E402

NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]


def boot(x, B=1000, seed=0):
    x = np.asarray(x, float)
    if len(x) == 0:
        return [None, None]
    r = np.random.default_rng(seed)
    m = x[r.integers(0, len(x), (B, len(x)))].mean(1)
    return [round(float(np.percentile(m, 2.5)), 3), round(float(np.percentile(m, 97.5)), 3)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True); ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--per-cell", type=int, default=30); ap.add_argument("--imgsz", type=int, default=480)
    ap.add_argument("--conf", type=float, default=0.35); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cells = sorted({os.path.dirname(p) for p in glob.glob(f"{a.root}/*/*/*.jpg")})
    rnd = random.Random(0); files = []
    for c in cells:
        fs = sorted(glob.glob(f"{c}/*.jpg")); files += [(c, f) for f in rnd.sample(fs, min(a.per_cell, len(fs)))]
    res = dict(source="Mendeley 10.17632/w3fg8jjmzr.1 (CC BY 4.0), Larkana Sindh PK, studio single-fruit photos",
               n_images=len(files), sample=f"{a.per_cell} per variety x maturity cell, random seed 0", imgsz=a.imgsz, conf=a.conf,
               device="sandbox CPU, ONNX Runtime", models={})
    imgs = [(c, f, cv2.imread(f)) for c, f in files]
    for spec in a.models:
        tag, path = spec.split("=", 1); s = sess(path); di = s.get_inputs()[0].name
        hit, top, none, conf_top, per_cell = [], [], [], {}, {}
        for c, f, im in imgs:
            x, _ = letterbox(im, a.imgsz); o = s.run(None, {di: x})[0]
            d = [z for z in decode(o, "raw", a.conf)]
            h = any(int(z["classId"]) == 4 for z in d)
            t = max(d, key=lambda z: z["score"]) if d else None
            tg = t is not None and int(t["classId"]) == 4
            hit.append(h); top.append(tg); none.append(t is None)
            if t is not None and not tg:
                conf_top[NAMES[int(t["classId"])]] = conf_top.get(NAMES[int(t["classId"])], 0) + 1
            k = os.path.relpath(c, a.root); pc = per_cell.setdefault(k, [0, 0]); pc[0] += int(h); pc[1] += 1
        res["models"][tag] = dict(model=path, hit_rate=round(float(np.mean(hit)), 3), hit_ci95=boot(hit),
                                  top_is_guava=round(float(np.mean(top)), 3), top_ci95=boot(top), no_detection=round(float(np.mean(none)), 3),
                                  top_class_when_not_guava=dict(sorted(conf_top.items(), key=lambda z: -z[1])),
                                  hit_rate_per_cell={k: f"{v[0]}/{v[1]}" for k, v in sorted(per_cell.items())})
        print(tag, res["models"][tag]["hit_rate"], res["models"][tag]["top_is_guava"], flush=True)
    os.makedirs(os.path.dirname(a.out), exist_ok=True); json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
