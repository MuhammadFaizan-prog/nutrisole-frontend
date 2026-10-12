"""quality2-g5ll (G5.4): physics / Retinex-style low-light synthesis + leave-one-lighting-out (LOLO) selection.

TRAIN = quality2-g3crop train (unchanged) + ONE "retinex night" copy of every ORIGINAL train image (detector-style
        jittered crop as in g3crop), synthesised in LINEAR light:
          lin = (img/255)^2.2; illumination L = Gaussian blur of max-channel (Retinex estimate); reflectance R = lin/L;
          new illumination L' = L^a * gain * point-light falloff 1/(1+(d/r)^2), a U(0.6,1.0), gain U(0.04,0.3);
          illuminant colour = blackbody-like RGB for T U(2700,6500) K (warm LED/incandescent -> daylight LED);
          sensor = Poisson shot noise (full well U(150,900) e-) + Gaussian read noise U(0.002,0.01), then
          auto-exposure digital gain to mean U(0.10,0.30), gamma 1/2.2, JPEG q U(55,90).
        HELD OUT (never synthesised, never used for selection): corruptions.night_sodium_hard (low-pressure sodium,
        orange cast + motion blur) and corruptions.tube_light_hard (fluorescent cool/green cast).
VAL      = quality2-g3crop val (unchanged)
VAL_LOLO = for every val ORIGINAL, 2 deterministic copies (seed 11): retinex night, and blur/JPEG50.
           The G4 "cool" (tube-like) copy is deliberately NOT built, so selection never sees a held-out family.
TEST  = unchanged (hard links); never shipped to Kaggle.
  python ml/data/build_quality_g5ll.py --g3crop /workspace/work/cv/g3data/quality2_g3crop --dst /workspace/work/cv/g5data/quality2_g5ll
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
from build_quality_g4ll import blur_jpeg  # noqa: E402


def kelvin_bgr(t):
    """Approximate blackbody RGB (Tanner Helland fit), normalised to G=1; returned in BGR order."""
    t = t / 100.0
    r = 255.0 if t <= 66 else 329.698727446 * (t - 60) ** -0.1332047592
    g = 99.4708025861 * np.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * (t - 60) ** -0.0755148492
    b = 255.0 if t >= 66 else (0.0 if t <= 19 else 138.5177312231 * np.log(t - 10) - 305.0447927307)
    rgb = np.clip(np.array([r, g, b], np.float64), 1, 255) / max(1.0, g)
    return np.array([rgb[2], rgb[1], rgb[0]], np.float32)


def retinex_night(im, rng):
    h, w = im.shape[:2]
    lin = (im.astype(np.float32) / 255.0) ** 2.2
    L = cv2.GaussianBlur(lin.max(2), (0, 0), max(2.0, 0.06 * max(h, w)))
    L = np.clip(L, 0.02, 1.0)
    R = lin / L[..., None]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = rng.uniform(-0.2, 1.2) * w, rng.uniform(-0.2, 1.2) * h
    r = rng.uniform(0.4, 1.5) * max(h, w)
    fall = 1.0 / (1.0 + ((xx - cx) ** 2 + (yy - cy) ** 2) / r ** 2)
    Ln = (L ** rng.uniform(0.6, 1.0)) * rng.uniform(0.04, 0.3) * fall
    out = np.clip(R * Ln[..., None] * kelvin_bgr(rng.uniform(2700, 6500)), 0, 1)
    fw = rng.uniform(150, 900)
    out = rng.poisson(out * fw).astype(np.float32) / fw + rng.normal(0, rng.uniform(0.002, 0.01), out.shape).astype(np.float32)
    out = np.clip(out, 0, None)
    out *= rng.uniform(0.10, 0.30) / max(1e-4, float(out.mean()))
    out = (np.clip(out, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)
    ok, b = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, int(rng.uniform(55, 90))])
    return cv2.imdecode(b, cv2.IMREAD_COLOR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--g3crop", required=True)
    ap.add_argument("--dst", required=True)
    a = ap.parse_args()
    rng, vrng = np.random.default_rng(7), np.random.default_rng(11)
    counts = {}
    for sp in ["train", "val", "test"]:
        for lvl in ["fresh", "rotten"]:
            os.makedirs(f"{a.dst}/{sp}/{lvl}", exist_ok=True)
            if sp == "val":
                os.makedirs(f"{a.dst}/val_lolo/{lvl}", exist_ok=True)
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
                    cv2.imwrite(f"{a.dst}/{sp}/{lvl}/rnight__{b}", retinex_night(jitter_crop(im, box, rng), rng), [cv2.IMWRITE_JPEG_QUALITY, 92])
                    counts[f"{sp}/{lvl}/rnight"] = counts.get(f"{sp}/{lvl}/rnight", 0) + 1
                else:
                    for tag, fn in (("rnight", retinex_night), ("blur", blur_jpeg)):
                        cv2.imwrite(f"{a.dst}/val_lolo/{lvl}/{tag}__{b}", fn(jitter_crop(im, box, vrng), vrng), [cv2.IMWRITE_JPEG_QUALITY, 92])
                        counts[f"val_lolo/{lvl}"] = counts.get(f"val_lolo/{lvl}", 0) + 1
    json.dump(dict(build="quality2-g5ll", seeds=[7, 11], counts=counts, doc=__doc__), open(f"{a.dst}/manifest.json", "w"), indent=1)
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
