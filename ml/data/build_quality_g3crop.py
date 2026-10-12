"""quality2-g3crop (G3): attacks the classifier crop/lighting gap (G2 failure mode 3).

TRAIN = quality2-g2aug train (originals + one phone-camera aug copy each, unchanged)
        + ONE detector-style crop copy of every original TRAIN image:
            item_crop (ml/grading/eval_proxy.item_crop, the grading-proxy crop) with box jitter
            scale U(0.85,1.15) and centre shift U(-0.15,0.15) x box size, padding by background
            bleed from the full frame (BORDER_REFLECT outside the image), then photometric:
            p=0.35 tube-light/fluorescent family, p=0.35 low-light (G2 family), else none.
        Tube-light family: B gain U(1.00,1.12), G U(1.04,1.18), R U(0.75,0.92), exposure U(0.7,1.05).
        The fixed eval corruption tube_light (B1.05 G1.12 R0.82) lies INSIDE this family, so the
        G3 tube-light number is in-distribution; corruptions.tube_light_hard is held out.
VAL   = quality2 val originals + a deterministic item_crop copy (no jitter) of each, so val-based
        model selection sees the crop domain. TEST is copied unchanged (never augmented, never cropped).
  python ml/data/build_quality_g3crop.py --g2aug /workspace/work/cv/g2data/quality2_aug --dst /workspace/work/cv/g3data/quality2_g3crop
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from grading.eval_proxy import item_crop_box  # noqa: E402


def tube(im, rng):
    g = np.array([rng.uniform(1.0, 1.12), rng.uniform(1.04, 1.18), rng.uniform(0.75, 0.92)], np.float32) * rng.uniform(0.7, 1.05)
    return np.clip(im.astype(np.float32) * g, 0, 255).astype(np.uint8)


def jitter_crop(img, box, rng):
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    s = rng.uniform(0.85, 1.15)
    cx = (x1 + x2) / 2 + rng.uniform(-0.15, 0.15) * w
    cy = (y1 + y2) / 2 + rng.uniform(-0.15, 0.15) * h
    nw, nh = w * s, h * s
    X1, Y1, X2, Y2 = int(cx - nw / 2), int(cy - nh / 2), int(cx + nw / 2), int(cy + nh / 2)
    H, W = img.shape[:2]
    pad = max(0, -X1, -Y1, X2 - W, Y2 - H)
    if pad:
        img = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_REFLECT)
        X1, Y1, X2, Y2 = X1 + pad, Y1 + pad, X2 + pad, Y2 + pad
    return img[max(0, Y1):Y2, max(0, X1):X2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--g2aug", required=True)
    ap.add_argument("--dst", required=True)
    a = ap.parse_args()
    rng = np.random.default_rng(3)
    counts = {}
    for sp in ["train", "val", "test"]:
        for lvl in ["fresh", "rotten"]:
            os.makedirs(f"{a.dst}/{sp}/{lvl}", exist_ok=True)
            for f in sorted(glob.glob(f"{a.g2aug}/{sp}/{lvl}/*.jpg")):
                b = os.path.basename(f)
                d = f"{a.dst}/{sp}/{lvl}/{b}"
                if not os.path.exists(d):
                    os.link(f, d)
                counts[f"{sp}/{lvl}"] = counts.get(f"{sp}/{lvl}", 0) + 1
                if b.startswith("aug_") or sp == "test":
                    continue
                im = cv2.imread(f)
                box = item_crop_box(im)
                if sp == "train":
                    c = jitter_crop(im, box, rng)
                    r = rng.random()
                    kind = "tube" if r < 0.35 else "low" if r < 0.7 else "none"
                    if kind == "tube":
                        c = tube(c, rng)
                    elif kind == "low":
                        c, _ = _low(c, rng)
                    out = f"{a.dst}/{sp}/{lvl}/crop_{kind}__{b}"
                else:
                    x1, y1, x2, y2 = box
                    c, kind = im[y1:y2, x1:x2], "val"
                    out = f"{a.dst}/{sp}/{lvl}/crop__{b}"
                if not os.path.exists(out):
                    cv2.imwrite(out, c, [cv2.IMWRITE_JPEG_QUALITY, 92])
                counts[f"{sp}/{lvl}/crop_{kind}"] = counts.get(f"{sp}/{lvl}/crop_{kind}", 0) + 1
    json.dump(dict(build="quality2-g3crop", seed=3, counts=counts, doc=__doc__), open(f"{a.dst}/manifest.json", "w"), indent=1)
    print(json.dumps(counts, indent=1))


def _low(im, rng):
    """G2 low-light family (same parameters as build_quality_g2aug.augment low_light branch)."""
    f = im.astype(np.float32)
    g, gam = rng.uniform(0.2, 0.6), rng.uniform(1.0, 1.5)
    f = (f / 255.0) ** gam * g * 255.0
    f += rng.normal(0, rng.uniform(2, 9), im.shape[:2])[..., None]
    f += rng.normal(0, rng.uniform(0, 5), im.shape)
    return np.clip(f, 0, 255).astype(np.uint8), "low_light"


if __name__ == "__main__":
    main()
