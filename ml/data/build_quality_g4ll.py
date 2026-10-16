"""quality2-g4ll (G4.4): stronger low-light training + a harder crop VAL for selection and temperature fitting.

TRAIN = quality2-g3crop train (unchanged) + ONE extra "night stall" copy of every ORIGINAL train image, as a
        detector-style jittered item crop (same jitter as g3crop) with the G4 strong low-light family:
        gain U(0.12,0.35), gamma U(1.3,2.0), luma noise sigma U(2,8) + chroma noise sigma U(3,10),
        p=0.5 warm bulb cast (R x U(1.05,1.25), B x U(0.7,0.9)), p=0.5 JPEG quality U(55,85).
        NOTE: the fixed eval corruptions low_light (gain .35, gamma 1.2) and low_light_hard (gain .25, gamma 1.6,
        sigma 7, JPEG70) lie INSIDE this family, so both become in-distribution in G4. corruptions.night_sodium_hard
        (new in G4) is held out: sodium cast + gain .18 + gamma 2.2 + motion blur, outside this family.
VAL   = quality2-g3crop val (unchanged, incl. its deterministic crop__ copies)
VAL_HARD (new, separate folder val_hard/) = for every val ORIGINAL, 3 deterministic hard copies (seed 11):
        jittered crop + strong low-light, jittered crop + tube_light_hard-like cast, jittered crop + blur/JPEG50.
        Used ONLY for model selection and temperature fitting (never for training, never TEST).
TEST  = unchanged (hard links).
  python ml/data/build_quality_g4ll.py --g3crop /workspace/work/cv/g3data/quality2_g3crop --dst /workspace/work/cv/g4data/quality2_g4ll
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from grading.eval_proxy import item_crop_box  # noqa: E402
from build_quality_g3crop import jitter_crop  # noqa: E402


def night(im, rng):
    f = im.astype(np.float32)
    if rng.random() < 0.5:
        f *= np.array([rng.uniform(0.7, 0.9), 1.0, rng.uniform(1.05, 1.25)], np.float32)  # BGR: warm bulb
    f = (np.clip(f, 0, 255) / 255.0) ** rng.uniform(1.3, 2.0) * rng.uniform(0.12, 0.35) * 255.0
    f += rng.normal(0, rng.uniform(2, 8), im.shape[:2])[..., None] + rng.normal(0, rng.uniform(3, 10), im.shape)
    out = np.clip(f, 0, 255).astype(np.uint8)
    if rng.random() < 0.5:
        ok, b = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, int(rng.uniform(55, 85))])
        out = cv2.imdecode(b, cv2.IMREAD_COLOR)
    return out


def cool_cast(im, rng):
    f = im.astype(np.float32) * np.array([rng.uniform(1.08, 1.2), rng.uniform(1.15, 1.3), rng.uniform(0.62, 0.75)], np.float32) * rng.uniform(0.65, 0.85)
    return np.clip(f, 0, 255).astype(np.uint8)


def blur_jpeg(im, rng):
    k = max(5, int(round(min(im.shape[:2]) * rng.uniform(0.015, 0.03))) | 1)
    kern = np.zeros((k, k), np.float32); kern[k // 2, :] = 1.0 / k
    out = cv2.filter2D(im, -1, kern)
    ok, b = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 50])
    return cv2.imdecode(b, cv2.IMREAD_COLOR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--g3crop", required=True)
    ap.add_argument("--dst", required=True)
    a = ap.parse_args()
    rng = np.random.default_rng(7)
    vrng = np.random.default_rng(11)
    counts = {}
    for sp in ["train", "val", "test"]:
        for lvl in ["fresh", "rotten"]:
            os.makedirs(f"{a.dst}/{sp}/{lvl}", exist_ok=True)
            if sp == "val":
                os.makedirs(f"{a.dst}/val_hard/{lvl}", exist_ok=True)
            for f in sorted(glob.glob(f"{a.g3crop}/{sp}/{lvl}/*.jpg")):
                b = os.path.basename(f)
                d = f"{a.dst}/{sp}/{lvl}/{b}"
                if not os.path.exists(d):
                    os.link(f, d)
                counts[f"{sp}/{lvl}"] = counts.get(f"{sp}/{lvl}", 0) + 1
                if sp == "test" or b.startswith(("aug_", "crop")):
                    continue
                im = cv2.imread(f)
                box = item_crop_box(im)
                if sp == "train":
                    cv2.imwrite(f"{a.dst}/{sp}/{lvl}/night__{b}", night(jitter_crop(im, box, rng), rng), [cv2.IMWRITE_JPEG_QUALITY, 92])
                    counts[f"{sp}/{lvl}/night"] = counts.get(f"{sp}/{lvl}/night", 0) + 1
                else:
                    for tag, fn in (("night", night), ("cool", cool_cast), ("blur", blur_jpeg)):
                        cv2.imwrite(f"{a.dst}/val_hard/{lvl}/{tag}__{b}", fn(jitter_crop(im, box, vrng), vrng), [cv2.IMWRITE_JPEG_QUALITY, 92])
                        counts[f"val_hard/{lvl}"] = counts.get(f"val_hard/{lvl}", 0) + 1
    json.dump(dict(build="quality2-g4ll", seeds=[7, 11], counts=counts, doc=__doc__), open(f"{a.dst}/manifest.json", "w"), indent=1)
    print(json.dumps(counts, indent=1))


if __name__ == "__main__":
    main()
