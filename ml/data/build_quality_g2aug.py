"""quality2-g2aug: quality-v1 2-level (fresh/rotten) set + ONE phone-camera augmented copy
of every TRAIN image (val/test copied unchanged, never augmented).

Augmentation policy (seeded, per image; G1 failure mode: low-light rotten recall 0.857):
  p=0.5  low light : gain U(0.2,0.6) (~-0.7..-2.3 EV), gamma U(1.0,1.5), luminance noise
                     sigma U(2,9) + chroma noise sigma U(0,5), optional (p=.3) defocus blur
  p=0.2  white balance: per-channel gains U(0.7,1.25) (tube-light / sodium-like casts)
  p=0.15 blur: motion (k 3..11, random angle) or Gaussian defocus
  p=0.15 JPEG quality U(35,90) + mild noise
The fixed G1 eval corruption low_light (gain .35, gamma 1.2, sigma 4) lies INSIDE this
family, so the G2 low-light robustness number is in-distribution for training; G2 also
reports a harder held-out variant (corruptions.low_light_hard) that is outside it.

  python ml/data/build_quality_g2aug.py --src /workspace/work/cv/g1data/builds/v1/quality2 --dst /workspace/work/cv/g2data/quality2_aug
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil

import cv2
import numpy as np


def augment(im, rng):
    r = rng.random()
    f = im.astype(np.float32)
    kind = None
    if r < 0.5:
        kind = "low_light"
        g, gam = rng.uniform(0.2, 0.6), rng.uniform(1.0, 1.5)
        f = (f / 255.0) ** gam * g * 255.0
        f += rng.normal(0, rng.uniform(2, 9), im.shape[:2])[..., None]
        f += rng.normal(0, rng.uniform(0, 5), im.shape)
        if rng.random() < 0.3:
            f = cv2.GaussianBlur(np.clip(f, 0, 255), (0, 0), rng.uniform(0.6, 1.6))
    elif r < 0.7:
        kind = "wb"
        f = f * rng.uniform(0.7, 1.25, 3)[None, None, :]
    elif r < 0.85:
        kind = "blur"
        if rng.random() < 0.5:
            k = int(rng.integers(3, 12)) | 1
            kern = np.zeros((k, k), np.float32); kern[k // 2, :] = 1.0 / k
            M = cv2.getRotationMatrix2D((k / 2 - 0.5, k / 2 - 0.5), float(rng.uniform(0, 180)), 1.0)
            kern = cv2.warpAffine(kern, M, (k, k)); kern /= max(kern.sum(), 1e-6)
            f = cv2.filter2D(f, -1, kern)
        else:
            f = cv2.GaussianBlur(f, (0, 0), rng.uniform(0.8, 2.5))
    else:
        kind = "jpeg"
        f += rng.normal(0, 2, im.shape)
        ok, b = cv2.imencode(".jpg", np.clip(f, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, int(rng.integers(35, 91))])
        f = cv2.imdecode(b, cv2.IMREAD_COLOR).astype(np.float32)
    return np.clip(f, 0, 255).astype(np.uint8), kind


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    a = ap.parse_args()
    rng = np.random.default_rng(0)
    counts = {}
    for sp in ["train", "val", "test"]:
        for lvl in sorted(os.listdir(f"{a.src}/{sp}")):
            os.makedirs(f"{a.dst}/{sp}/{lvl}", exist_ok=True)
            for f in sorted(glob.glob(f"{a.src}/{sp}/{lvl}/*.jpg")):
                dst = f"{a.dst}/{sp}/{lvl}/{os.path.basename(f)}"
                if not os.path.exists(dst):
                    shutil.copyfile(f, dst)
                counts[f"{sp}/{lvl}"] = counts.get(f"{sp}/{lvl}", 0) + 1
                if sp == "train":
                    im = cv2.imread(f)
                    out, kind = augment(im, rng)  # rng advanced even if file exists -> deterministic
                    ad = f"{a.dst}/{sp}/{lvl}/aug_{kind}__{os.path.basename(f)}"
                    if not glob.glob(f"{a.dst}/{sp}/{lvl}/aug_*__{os.path.basename(f)}"):
                        cv2.imwrite(ad, out, [cv2.IMWRITE_JPEG_QUALITY, 92])
                    counts[f"{sp}/{lvl}/aug_{kind}"] = counts.get(f"{sp}/{lvl}/aug_{kind}", 0) + 1
    json.dump(dict(build="quality2-g2aug", src=a.src, seed=0, counts=counts), open(f"{a.dst}/manifest.json", "w"), indent=1)
    print(json.dumps(counts, indent=1))


if __name__ == "__main__":
    main()
