"""Visible-condition measurements on a produce crop (NutriSole G1).

All functions take an RGB uint8 crop (H, W, 3) of ONE detected item and return
plain numbers. They measure VISIBLE surface properties only; they make no claim
about food safety, disease or shelf-life.

Pipeline:
  object_mask()      -> boolean mask of the item inside the crop (GrabCut seeded
                        by an inset rectangle, Otsu-on-saturation fallback)
  colour_bands()     -> % of item pixels in each produce-specific hue/value band
  dark_defect_area() -> % of item pixels that are dark blemishes (Lab L-channel
                        threshold relative to the item's own median + morphology)
  shape_metrics()    -> contour solidity and ellipse-fit ratio
  measure()          -> all of the above in one dict (used by rules.grade)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict

import cv2
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "colour_bands.json"), "r", encoding="utf-8") as fh:
    COLOUR_BANDS: dict = json.load(fh)

MIN_MASK_FRACTION = 0.08  # below this the segmentation is not trusted -> ungradable
with open(os.path.join(_HERE, "measure_params.json"), "r", encoding="utf-8") as fh:
    MEASURE_PARAMS: dict = json.load(fh)


@dataclass
class Measurements:
    mask_fraction: float          # item pixels / crop pixels
    colour_bands: dict            # band name -> percent of item pixels
    colour_band: str              # dominant band name ("unknown" if no table for class)
    defect_area_pct: float        # dark-blemish percent of item pixels
    solidity: float               # contour area / convex hull area (1.0 = convex)
    ellipse_ratio: float          # contour area / fitted ellipse area
    shape_score: float            # min(solidity, ellipse-based regularity) in [0,1]
    blur_var: float               # variance of Laplacian on the crop (lower = blurrier)
    mean_v: float                 # mean HSV value of item pixels in [0,255]
    segmentation: str             # "grabcut" | "otsu" | "full"

    def to_dict(self) -> dict:
        return asdict(self)


def object_mask(rgb: np.ndarray, inset: float = 0.06, use_grabcut: bool = True) -> tuple[np.ndarray, str]:
    """Return (mask bool HxW, method). The crop is assumed to be a detector box,
    so the item fills most of it; the border strip is treated as probable background."""
    h, w = rgb.shape[:2]
    if h < 8 or w < 8:
        return np.ones((h, w), bool), "full"
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    if use_grabcut:
        try:
            mask = np.zeros((h, w), np.uint8)
            dx, dy = max(1, int(w * inset)), max(1, int(h * inset))
            rect = (dx, dy, max(2, w - 2 * dx), max(2, h - 2 * dy))
            bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
            cv2.grabCut(bgr, mask, rect, bgd, fgd, 3, cv2.GC_INIT_WITH_RECT)
            m = (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)
            m = _largest_component(m)
            if m.mean() >= MIN_MASK_FRACTION:
                return m, "grabcut"
        except cv2.error:
            pass
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    s = cv2.GaussianBlur(hsv[..., 1], (5, 5), 0)
    _, th = cv2.threshold(s, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    m = _largest_component(th > 0)
    if m.mean() < MIN_MASK_FRACTION:
        return np.ones((h, w), bool), "full"
    return m, "otsu"


def _largest_component(m: np.ndarray) -> np.ndarray:
    m8 = m.astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m8, 8)
    if n <= 1:
        return m.astype(bool)
    idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    out = lab == idx
    # fill holes so dark blemishes inside the fruit stay part of the item
    out8 = out.astype(np.uint8) * 255
    cnts, _ = cv2.findContours(out8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(out8)
    cv2.drawContours(filled, cnts, -1, 255, -1)
    return filled > 0


def colour_bands(rgb: np.ndarray, mask: np.ndarray, produce: str) -> tuple[dict, str]:
    """Percent of item pixels inside each band defined in colour_bands.json for this
    produce. Hue is OpenCV scale 0-179. Bands may overlap; the dominant band is the
    one with the most pixels. Returns ({}, 'unknown') for produce without a table."""
    table = COLOUR_BANDS.get(produce)
    if not table or mask.sum() == 0:
        return {}, "unknown"
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    hh, ss, vv = hsv[..., 0][mask], hsv[..., 1][mask], hsv[..., 2][mask]
    out = {}
    for name, b in table["bands"].items():
        sel = np.ones_like(hh, bool)
        h_lo, h_hi = b.get("h", [0, 179])
        if h_lo <= h_hi:
            sel &= (hh >= h_lo) & (hh <= h_hi)
        else:  # wraps around red
            sel &= (hh >= h_lo) | (hh <= h_hi)
        s_lo, s_hi = b.get("s", [0, 255])
        v_lo, v_hi = b.get("v", [0, 255])
        sel &= (ss >= s_lo) & (ss <= s_hi) & (vv >= v_lo) & (vv <= v_hi)
        out[name] = round(100.0 * float(sel.mean()), 2)
    dominant = max(out, key=out.get) if out and max(out.values()) > 0 else "unknown"
    return out, dominant


def surface_mask(rgb: np.ndarray, mask: np.ndarray, ring_frac: float | None = None, shadow_chroma: float | None = None,
                 spec_v: float | None = None, spec_s: float | None = None) -> np.ndarray:
    """G2: the part of the item mask whose darkness/brightness is meaningful.

    Removes (a) SPECULAR highlights (HSV V >= spec_v and S <= spec_s) and (b) SHADOW pixels:
    low-chroma (Lab chroma < shadow_chroma) pixels inside the outer ring of the silhouette
    (distance to the mask edge < ring_frac * max distance). GrabCut often swallows the cast
    shadow on the table/paper, and the item's own terminator shadow lives on the rim; real
    rot is either chromatic (brown) or sits away from the rim. Defaults from
    measure_params.json ("surface"); ring_frac 0 disables the shadow rule."""
    P = MEASURE_PARAMS.get("surface", {})
    ring_frac = P.get("ring_frac", 0.0) if ring_frac is None else ring_frac
    shadow_chroma = P.get("shadow_chroma", 12.0) if shadow_chroma is None else shadow_chroma
    spec_v = P.get("spec_v", 256) if spec_v is None else spec_v
    spec_s = P.get("spec_s", 30) if spec_s is None else spec_s
    m = mask.astype(bool).copy()
    if m.sum() == 0:
        return m
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    m &= ~((hsv[..., 2] >= spec_v) & (hsv[..., 1] <= spec_s))
    if ring_frac > 0:
        dist = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 3)
        ring = dist < ring_frac * max(1.0, float(dist.max()))
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
        chroma = np.sqrt((lab[..., 1] - 128.0) ** 2 + (lab[..., 2] - 128.0) ** 2)
        m &= ~(ring & (chroma < shadow_chroma))
    if m.sum() < 0.3 * mask.sum():  # rule removed most of the item: do not trust it
        return mask.astype(bool)
    return m


def dark_defect_area(rgb: np.ndarray, mask: np.ndarray, rel_drop: float | None = None,
                     abs_floor: float | None = None, erode_px: int = 2, chroma_max: float | None = -1,
                     produce: str | None = None, baseline_weight: float | None = None) -> float:
    """Percent of item pixels that are dark blemishes.

    A pixel is a blemish if its Lab L* (0-100) is below
    max(abs_floor, median_L - rel_drop) -- i.e. clearly darker than the item's own
    typical surface, so dark-skinned produce is not flagged wholesale. The mask is
    eroded first so the shadowed silhouette edge is not counted, and blobs are
    cleaned with a 3x3 opening. If chroma_max is set, a dark pixel only counts when its
    Lab chroma is below chroma_max (rot/bruise is brown-black; deep red or dark green skin
    is saturated). Defaults come from measure_params.json (tuned on VAL only)."""
    P = MEASURE_PARAMS["dark_defect"]
    rel_drop = P["rel_drop"] if rel_drop is None else rel_drop
    abs_floor = P["abs_floor"] if abs_floor is None else abs_floor
    chroma_max = P.get("chroma_max") if chroma_max == -1 else chroma_max
    if mask.sum() == 0:
        return 0.0
    m = mask.astype(np.uint8)
    if erode_px > 0:
        m = cv2.erode(m, np.ones((2 * erode_px + 1, 2 * erode_px + 1), np.uint8))
    if m.sum() < 20:
        m = mask.astype(np.uint8)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    L = lab[..., 0].astype(np.float32) * (100.0 / 255.0)
    vals = L[m > 0]
    ref = float(np.median(vals))
    # G2 per-class baseline: blend the item's own median L* with the median L* of FRESH
    # train items of this class (measure_params.json "class_baseline_L"), so a heavily
    # rotten item cannot drag its own reference down and hide its rot, and dark-skinned
    # classes keep a low reference.
    bw = P.get("baseline_weight", 0.0) if baseline_weight is None else baseline_weight
    base = MEASURE_PARAMS.get("class_baseline_L", {}).get(produce or "", None)
    if bw > 0 and base is not None:
        ref = (1 - bw) * ref + bw * float(base)
    thr = max(abs_floor, ref - rel_drop)
    dark = (L < thr) & (m > 0)
    if chroma_max is not None:
        a = lab[..., 1].astype(np.float32) - 128.0
        b = lab[..., 2].astype(np.float32) - 128.0
        dark &= np.sqrt(a * a + b * b) < chroma_max
    dark = dark.astype(np.uint8)
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return round(100.0 * float(dark.sum()) / float(m.sum()), 2)


def shape_metrics(mask: np.ndarray) -> tuple[float, float]:
    m8 = mask.astype(np.uint8) * 255
    cnts, _ = cv2.findContours(m8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cnts:
        return 0.0, 0.0
    c = max(cnts, key=cv2.contourArea)
    area = float(cv2.contourArea(c))
    hull = float(cv2.contourArea(cv2.convexHull(c)))
    solidity = area / hull if hull > 0 else 0.0
    if len(c) >= 5:
        (_, _), (ma, mi), _ = cv2.fitEllipse(c)
        ell = np.pi * ma * mi / 4.0
        ratio = area / ell if ell > 0 else 0.0
    else:
        ratio = 0.0
    return round(solidity, 4), round(ratio, 4)


def measure(rgb: np.ndarray, produce: str, use_grabcut: bool = True) -> Measurements:
    mask, method = object_mask(rgb, use_grabcut=use_grabcut)
    bands, dom = colour_bands(rgb, mask, produce)
    surf = surface_mask(rgb, mask)
    defect = dark_defect_area(rgb, surf, produce=produce)
    sol, ell = shape_metrics(mask)
    # elongated produce (banana, carrot, cucumber) is not elliptical in silhouette;
    # only solidity is used for them.
    elongated = COLOUR_BANDS.get(produce, {}).get("elongated", False)
    ell_reg = 1.0 - min(1.0, abs(1.0 - ell)) if ell > 0 else 0.0
    shape = sol if elongated else min(sol, ell_reg)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    v = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)[..., 2][mask]
    return Measurements(
        mask_fraction=round(float(mask.mean()), 4), colour_bands=bands, colour_band=dom,
        defect_area_pct=defect, solidity=sol, ellipse_ratio=ell, shape_score=round(float(shape), 4),
        blur_var=round(blur, 2), mean_v=round(float(v.mean()) if v.size else 0.0, 2), segmentation=method)
