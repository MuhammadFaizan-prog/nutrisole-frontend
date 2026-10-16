"""G9 Stage H occlusion / visibility cues on a close-up analysis crop. Mirrors the decision rule in native/src/cv/pipeline/verify.ts
(occlusionReasons). Cues are computed from the object mask (GrabCut, ml/grading/measure.object_mask) and an independent second
segmentation (saturation Otsu), never from area, confidence or colour alone:
  solidity      mask area / convex-hull area (bites taken out of the outline by an occluder)
  ellipseIoU    IoU of the mask with its fitted ellipse (produce outlines are near-convex, smooth)
  straightFrac  fraction of the outline (away from the crop border) lying on locally straight runs (occluder / cut edges are straight)
  borderFrac    fraction of the outline on the crop border (partial object cut by the box or frame)
  segAgree      IoU of the GrabCut mask with an independent saturation-Otsu foreground (something foreign inside the 'item')
  flatFrac      fraction of mask 8x8 cells that are flat (local std < 2.5) - flat foreign blobs, plastic glare
  colourSplit   Lab 2-means split inside the mask: minor-cluster fraction x separation (two materials in one 'item')
  partAgree     (optional) close-up classifier on 4 half-crops: fraction of halves that agree with the verified class
"""
from __future__ import annotations
import numpy as np, cv2

DEFAULT_OCC = dict(minSolidity=0.0, minEllipseIoU=0.0, maxStraightFrac=1.0, maxBorderFrac=1.0, minSegAgree=0.0, maxFlatFrac=1.0,
                   maxColourSplit=1e9, minPartAgree=0.0)


def _contour(mask):
    m8 = mask.astype(np.uint8)
    cs, _ = cv2.findContours(m8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return max(cs, key=cv2.contourArea) if cs else None


def straight_frac(cnt, shape, win_frac=0.12, tol=1.0, border=None):
    """Fraction of non-border outline points that sit in a window (win_frac of the perimeter) whose points all lie within tol px of a line."""
    h, w = shape; P = cnt[:, 0, :].astype(np.float32); n = len(P)
    if n < 20: return 0.0, 0.0
    # GrabCut is initialised with a rect inset 6% (measure.object_mask): the mask can only reach that rect, so 'on the border' means
    # within 6% + 2 px of the crop edge (an item cut by the box / frame runs along it)
    bx, by = (int(0.06 * w) + 2, int(0.06 * h) + 2) if border is None else (border, border)
    onb = (P[:, 0] <= bx) | (P[:, 1] <= by) | (P[:, 0] >= w - 1 - bx) | (P[:, 1] >= h - 1 - by)
    k = max(6, int(win_frac * n)); straight = np.zeros(n, bool)
    for i in range(0, n, max(1, k // 6)):
        idx = np.arange(i, i + k) % n
        if onb[idx].mean() > 0.3: continue
        Q = P[idx]; c = Q.mean(0); u, s, vt = np.linalg.svd(Q - c, full_matrices=False)
        d = np.abs((Q - c) @ vt[1]);
        if d.max() <= tol * max(1.0, (h * w) ** 0.5 / 96): straight[idx] = True
    nb = ~onb
    return float(straight[nb].mean()) if nb.any() else 0.0, float(onb.mean())


def cues(bgr, mask) -> dict:
    h, w = mask.shape; m = mask.astype(bool); area = m.sum()
    cnt = _contour(m)
    if cnt is None or area < 30: return dict(solidity=0.0, ellipseIoU=0.0, straightFrac=1.0, borderFrac=1.0, segAgree=0.0, flatFrac=1.0, colourSplit=99.0)
    hull = cv2.convexHull(cnt); sol = float(cv2.contourArea(cnt) / max(cv2.contourArea(hull), 1e-6))
    eiou = 0.0
    if len(cnt) >= 5:
        e = cv2.fitEllipse(cnt); em = np.zeros((h, w), np.uint8); cv2.ellipse(em, e, 1, -1); em = em.astype(bool)
        eiou = float((em & m).sum() / max((em | m).sum(), 1))
    sf, bf = straight_frac(cnt, (h, w))
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV); s = cv2.GaussianBlur(hsv[..., 1], (5, 5), 0)
    _, th = cv2.threshold(s, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU); o = th > 0
    seg = float((o & m).sum() / max((o | m).sum(), 1))
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32); cs = 8 if min(h, w) >= 96 else 4; flat = tot = 0
    for y in range(0, h - cs + 1, cs):
        for x in range(0, w - cs + 1, cs):
            if m[y:y + cs, x:x + cs].mean() < 0.9: continue
            tot += 1; flat += g[y:y + cs, x:x + cs].std() < 2.5
    ff = float(flat / tot) if tot else 0.0
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).reshape(-1, 3)[m.reshape(-1)].astype(np.float32)
    if len(lab) > 2000: lab = lab[np.random.default_rng(0).choice(len(lab), 2000, replace=False)]
    _, lb, ctr = cv2.kmeans(lab, 2, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5), 2, cv2.KMEANS_PP_CENTERS)
    minor = float(min((lb == 0).mean(), (lb == 1).mean())); sep = float(np.linalg.norm(ctr[0] - ctr[1]))
    return dict(solidity=round(sol, 4), ellipseIoU=round(eiou, 4), straightFrac=round(sf, 4), borderFrac=round(bf, 4), segAgree=round(seg, 4),
                flatFrac=round(ff, 4), colourSplit=round(minor * sep, 3))


def occlusion_reasons(c: dict, p: dict | None = None) -> list[str]:
    """c: cue dict (optionally partAgree). Returns occlusion 'Not graded' reasons (empty = OK). Mirror of verify.ts occlusionReasons."""
    P = {**DEFAULT_OCC, **(p or {})}; r = []
    if c["solidity"] < P["minSolidity"] or c["ellipseIoU"] < P["minEllipseIoU"]: r.append("outline_incomplete")
    if c["straightFrac"] > P["maxStraightFrac"]: r.append("straight_occluder_edge")
    if c["borderFrac"] > P["maxBorderFrac"]: r.append("partial_object")
    if c["segAgree"] < P["minSegAgree"]: r.append("foreground_inconsistent")
    if c["flatFrac"] > P["maxFlatFrac"]: r.append("flat_foreign_region")
    if c["colourSplit"] > P["maxColourSplit"]: r.append("mixed_materials")
    if c.get("partAgree") is not None and c["partAgree"] < P["minPartAgree"]: r.append("parts_disagree")
    return r

FROZEN_OCC = dict(DEFAULT_OCC, minSolidity=0.8, minEllipseIoU=0.7, maxStraightFrac=0.4, maxBorderFrac=0.7)  # Stage H frozen pick on CU-tune only (see G9_stageH.md); mirror native/src/cv/pipeline/verify.ts FROZEN_OCC


# ---- G9 Stage I targeted cues (I3). Additive only: occlusion_reasons() and FROZEN_OCC above are unchanged. Mirror: verify.ts targetedOcclusionReasons.
def targeted_cues(bgr, mask) -> dict:
    """sideTouch: max over the 4 crop sides of the fraction of that side's length where the mask reaches the GrabCut inset band
    (6% + 2 px) - an item cut by the tap box (inner truncation) runs along one whole side. skinFrac: YCrCb skin pixels (Cr 135-180,
    Cb 85-135) in a 3-7% ring just outside the mask - a hand next to / over the outline. specFrac: low-saturation, bright pixels
    (S < 40, V > 215) inside the mask - plastic film / bag glare. hullGap: deepest convexity defect / sqrt(mask area) - a bite taken out
    of the outline by overlapping produce."""
    h, w = mask.shape; m = mask.astype(bool); area = int(m.sum())
    if area < 30: return dict(sideTouch=1.0, skinFrac=0.0, specFrac=0.0, hullGap=1.0)
    bx, by = int(0.06 * w) + 2, int(0.06 * h) + 2
    st = max(m[:by + 1].any(0).mean(), m[h - by - 1:].any(0).mean(), m[:, :bx + 1].any(1).mean(), m[:, w - bx - 1:].any(1).mean())
    k = max(3, int(0.05 * min(h, w)))
    ring = cv2.dilate(m.astype(np.uint8), np.ones((k, k), np.uint8)).astype(bool) & ~m
    ycc = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb); skin = (ycc[..., 1] >= 135) & (ycc[..., 1] <= 180) & (ycc[..., 2] >= 85) & (ycc[..., 2] <= 135)
    sk = float((skin & ring).sum() / max(ring.sum(), 1))
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV); sp = float(((hsv[..., 1] < 40) & (hsv[..., 2] > 215) & m).sum() / area)
    cnt = _contour(m); hg = 0.0
    if cnt is not None and len(cnt) >= 5:
        hull = cv2.convexHull(cnt, returnPoints=False)
        try:
            d = cv2.convexityDefects(cnt, hull)
            if d is not None and len(d): hg = float(d.reshape(-1, 4)[:, 3].max() / 256.0 / max(area ** 0.5, 1e-6))
        except cv2.error: pass
    return dict(sideTouch=round(float(st), 4), skinFrac=round(sk, 4), specFrac=round(sp, 4), hullGap=round(hg, 4))


DEFAULT_TARGETED = dict(maxSideTouch=1.01, maxSkinFrac=1.01, maxSpecFrac=1.01, maxHullGap=1e9)


def targeted_reasons(t: dict, p: dict | None = None) -> list[str]:
    """Extra 'Not graded' reasons from targeted_cues (only ever ADDS rejections on top of occlusion_reasons)."""
    P = {**DEFAULT_TARGETED, **(p or {})}; r = []
    if t["sideTouch"] > P["maxSideTouch"]: r.append("cut_by_box")
    if t["skinFrac"] > P["maxSkinFrac"]: r.append("hand_near_item")
    if t["specFrac"] > P["maxSpecFrac"]: r.append("packaging_glare")
    if t["hullGap"] > P["maxHullGap"]: r.append("outline_bite")
    return r
