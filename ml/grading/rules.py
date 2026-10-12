"""Rule table: calibrated quality probabilities + measurements -> visual grade.

Grade semantics (rubric v0.1-g1, PROPOSAL, not calibrated with human graders):
  A / B / C / Reject = VISIBLE condition only; 'ungradable' when the view cannot
  be assessed. Never a food-safety, disease or shelf-life claim (rule 8.4).
Thresholds live in rubric_v0.json and are shared with the TypeScript port.
"""
from __future__ import annotations

import json
import os
from typing import Optional
import math


def _r(x: float) -> int:
    """Round half up (matches JS Math.round in the TS port)."""
    return int(math.floor(x + 0.5))

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "rubric_v0.json"), "r", encoding="utf-8") as fh:
    RUBRIC = json.load(fh)
with open(os.path.join(_HERE, "colour_bands.json"), "r", encoding="utf-8") as fh:
    _BANDS = json.load(fh)


def band_roles(produce: str, bands: dict) -> dict:
    """Sum band percentages by role (target/unripe/overripe)."""
    table = _BANDS.get(produce, {}).get("bands", {})
    out = {"target": 0.0, "unripe": 0.0, "overripe": 0.0}
    for name, pct in (bands or {}).items():
        role = table.get(name, {}).get("role")
        if role in out:
            out[role] += float(pct)
    return out


def grade(produce: str, det_score: float, probs: Optional[dict], m: Optional[dict]) -> dict:
    """probs: calibrated {'fresh':..,'rotten':.., optional 'mild':..} or None.
    m: Measurements.to_dict() or None. Returns
    {'grade', 'reasons', 'numbers', 'status'} where status mirrors CvAssessment.status."""
    R = RUBRIC
    if det_score < R["detectorMinScore"]:
        return {"grade": "ungradable", "status": "unsupported",
                "reasons": ["Point the camera at one fruit or vegetable"], "numbers": {"detScore": det_score}}
    if m is not None:
        if m.get("mean_v", 128) < R["minMeanV"]:
            return {"grade": "ungradable", "status": "poor_capture", "reasons": ["Too dark: try better light"], "numbers": {"meanV": m["mean_v"]}}
        if m.get("mean_v", 128) > R["maxMeanV"]:
            return {"grade": "ungradable", "status": "poor_capture", "reasons": ["Overexposed: avoid direct glare"], "numbers": {"meanV": m["mean_v"]}}
        if m.get("blur_var", 999) < R["minBlurVar"]:
            return {"grade": "ungradable", "status": "poor_capture", "reasons": ["Image is blurry: hold the phone steady"], "numbers": {"blurVar": m["blur_var"]}}
        if m.get("mask_fraction", 1) < R["minMaskFraction"]:
            return {"grade": "ungradable", "status": "poor_capture", "reasons": ["Cannot assess this view: item too small or obstructed"], "numbers": {"maskFraction": m["mask_fraction"]}}
    if not probs or max(probs.values()) < R["qualityMinMaxProb"]:
        return {"grade": "ungradable", "status": "uncertain", "reasons": ["Not sure, try better light"],
                "numbers": {"maxProb": max(probs.values()) if probs else None}}

    p_f, p_r, p_m = probs.get("fresh", 0.0), probs.get("rotten", 0.0), probs.get("mild")
    defect = float(m["defect_area_pct"]) if m else None
    shape = float(m["shape_score"]) if m else None
    roles = band_roles(produce, m.get("colour_bands", {})) if m else None
    has_table = bool(_BANDS.get(produce))
    nums = {"pFresh": round(p_f, 3), "pRotten": round(p_r, 3), "pMild": None if p_m is None else round(p_m, 3),
            "defectPct": defect, "shapeScore": shape, "bandRoles": roles}

    def out(g, reasons):
        return {"grade": g, "status": "supported", "reasons": reasons[:2], "numbers": nums}

    # --- Reject
    rs = []
    if p_r >= R["reject"]["pRotten"]:
        rs.append(f"Visible rot likely ({_r(100 * p_r)}%)")
    if defect is not None and defect >= R["reject"]["defectPct"]:
        rs.append(f"Dark marks ~{_r(defect)}% of visible surface")
    if rs:
        return out("Reject", rs)
    # --- C
    rs = []
    if p_m is not None and p_m >= R["c"]["pMild"]:
        rs.append(f"Mild visible deterioration ({_r(100 * p_m)}%)")
    if defect is not None and defect >= R["c"]["defectPct"]:
        rs.append(f"Dark marks ~{_r(defect)}% of visible surface")
    if roles and has_table and roles["overripe"] >= R["c"]["overripeBandPct"]:
        rs.append(f"Overripe colour on ~{_r(roles['overripe'])}% of surface")
    if rs:
        return out("C", rs)
    # --- B
    rs = []
    if defect is not None and defect >= R["b"]["defectPct"]:
        rs.append(f"Small dark marks ~{_r(defect)}% of visible surface")
    if roles and has_table and roles["unripe"] >= R["b"]["unripeBandPct"]:
        rs.append(f"Not yet ripe colour on ~{_r(roles['unripe'])}% of surface")
    if shape is not None and shape < R["b"]["shapeScore"]:
        rs.append(f"Irregular shape (score {shape:.2f})")
    if rs:
        return out("B", rs)
    # --- A (all conditions must hold)
    colour_ok = (not has_table) or (roles is not None and roles["target"] >= R["a"]["targetBandPct"])
    if p_f >= R["a"]["pFresh"] and defect is not None and colour_ok:
        reasons = [f"Looks fresh ({_r(100 * p_f)}%), dark marks ~{_r(defect)}%"]
        if not has_table:
            reasons.append("Colour not assessed for this produce yet")
        return out("A", reasons)
    reasons = []
    if p_f < R["a"]["pFresh"]:
        reasons.append(f"Freshness confidence only {_r(100 * p_f)}%")
    if not colour_ok:
        reasons.append("Colour outside the usual ripe range")
    if defect is None:
        reasons.append("Surface marks not measured")
    return out("B", reasons or ["Minor visible issues"])
