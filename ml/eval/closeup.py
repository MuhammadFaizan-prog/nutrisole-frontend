"""G9 Stage G close-up path: coordinate mapping, ROI, identification policy, quality checks and the move-closer grade gate.
EXACT mirror: native/src/cv/pipeline/closeup.ts (parity: native/tests/cvCloseup.test.ts replays ml/eval/fixtures/closeup_parity.json).

Flow (demo story): wide scan (G3 480, unchanged) -> identification policy (else "Unable to identify") -> user taps an item
(ROI) -> move-closer gate on FULL-RESOLUTION frame pixels -> quality checks -> condition / ripeness / rules on the full-res crop
-> N consistent assessments -> grade, else "Not graded" with reasons. Confidence alone never produces a grade."""
from __future__ import annotations

import math

INPUT = 480
DEFAULT_ID = dict(idMinScore=0.5, idMinHits=3)
# Candidate values from the Stage F proposal; Stage G picks the frozen values on CU-tune (see G9_stageG.md).
DEFAULT_GATE = dict(minSidePx=96, minFrames=3, mode="count", scoreTol=0.15, minBlurVar=15.0, minMeanV=40.0, maxMeanV=245.0,
                    edgeMarginFrac=0.01, minVisibleFrac=0.25, minMaxProb=0.7, minMargin=0.3, maxBlockiness=1.5)


def letterbox_transform(src_w: int, src_h: int, dst: int = INPUT) -> dict:
    s = min(dst / src_w, dst / src_h); nw, nh = round(src_w * s), round(src_h * s)
    return dict(sx=nw / src_w, sy=nh / src_h, px=round((dst - nw) / 2 - 0.1), py=round((dst - nh) / 2 - 0.1), w=src_w, h=src_h)


def detector_to_frame(box, frame_w: int, frame_h: int, dst: int = INPUT):
    """480-letterbox detector box -> full-resolution frame pixels (clipped). Same convention as preprocess.ts dstToSrc."""
    t = letterbox_transform(frame_w, frame_h, dst)
    x1, y1, x2, y2 = (box[0] - t["px"]) / t["sx"], (box[1] - t["py"]) / t["sy"], (box[2] - t["px"]) / t["sx"], (box[3] - t["py"]) / t["sy"]
    c = lambda v, hi: min(hi, max(0.0, v))
    return [c(x1, frame_w), c(y1, frame_h), c(x2, frame_w), c(y2, frame_h)]


def crop_rect(box, frame_w: int, frame_h: int, pad: float = 0.08):
    """Integer crop rectangle on the full-res frame (box padded by pad*side), clamped. side = sqrt(area) of the UNPADDED box."""
    w, h = box[2] - box[0], box[3] - box[1]; px, py = pad * w, pad * h
    x1, y1 = max(0, math.floor(box[0] - px)), max(0, math.floor(box[1] - py))
    x2, y2 = min(frame_w, math.ceil(box[2] + px)), min(frame_h, math.ceil(box[3] + py))
    return dict(x=x1, y=y1, w=max(0, x2 - x1), h=max(0, y2 - y1), sidePx=round(math.sqrt(max(0.0, w) * max(0.0, h)), 2))


def touches_edge(box, frame_w: int, frame_h: int, margin_frac: float) -> bool:
    mx, my = margin_frac * frame_w, margin_frac * frame_h
    return box[0] <= mx or box[1] <= my or box[2] >= frame_w - mx or box[3] >= frame_h - my


def roi_from_tap(tap, frame_w: int, frame_h: int, frame_boxes: list, roi_frac: float = 0.35):
    """User tap (normalised) -> ROI. A tracked box containing the tap wins (smallest such box); otherwise a square user ROI of
    roi_frac*min(W,H) centred on the tap (tracking-fragmentation fallback), clamped inside the frame."""
    x, y = tap[0] * frame_w, tap[1] * frame_h
    hits = [b for b in frame_boxes if b[0] <= x <= b[2] and b[1] <= y <= b[3]]
    if hits:
        b = min(hits, key=lambda b: (b[2] - b[0]) * (b[3] - b[1])); return dict(source="track", box=list(b))
    s = roi_frac * min(frame_w, frame_h); x1 = min(max(0.0, x - s / 2), frame_w - s); y1 = min(max(0.0, y - s / 2), frame_h - s)
    return dict(source="tap_roi", box=[x1, y1, x1 + s, y1 + s])


def id_policy(label: int, score: float, hits: int, citrus_ambiguous: bool = False, p: dict | None = None) -> dict:
    P = {**DEFAULT_ID, **(p or {})}
    if citrus_ambiguous: return dict(status="unable", reason="citrus family ambiguous")
    if hits < P["idMinHits"]: return dict(status="pending", reason="confirming")
    if score < P["idMinScore"]: return dict(status="unable", reason="low confidence")
    return dict(status="identified", classId=int(label))


def quality_reasons(q: dict, p: dict | None = None) -> list[str]:
    """q: sidePx, blurVar, meanV, touchesEdge, visibleFrac, maxProb, margin, optional blockiness (8x8 JPEG blocking, 1.0 = none). Returns the 'Not graded' reasons (empty = OK)."""
    P = {**DEFAULT_GATE, **(p or {})}; r = []
    if q["sidePx"] < P["minSidePx"]: r.append("too_small: move closer")
    if q["touchesEdge"]: r.append("truncated: keep the whole item in view")
    if q["meanV"] < P["minMeanV"]: r.append("too_dark")
    if q["meanV"] > P["maxMeanV"]: r.append("overexposed")
    if q["blurVar"] < P["minBlurVar"]: r.append("blurry")
    if q["visibleFrac"] < P["minVisibleFrac"]: r.append("occluded_or_little_surface")
    if q.get("blockiness") is not None and q["blockiness"] > P["maxBlockiness"]: r.append("compression_artifacts")
    if q["maxProb"] < P["minMaxProb"] or q["margin"] < P["minMargin"]: r.append("model_uncertain")
    return r


class GradeGate:
    """Consecutive-assessment gate. push(a) with a = {ok, grade, pFresh, reasons}. count mode: the last minFrames assessments
    are all ok AND agree on the grade. score mode: the last minFrames are ok, agree on the grade, and pFresh spans <= scoreTol.
    Any failed assessment or disagreement resets the run. Returns {status: graded|pending|not_graded, ...}."""

    def __init__(self, p: dict | None = None):
        self.P = {**DEFAULT_GATE, **(p or {})}; self.hist: list[dict] = []

    def reset(self):
        self.hist = []

    def push(self, a: dict) -> dict:
        P = self.P
        if not a["ok"]:
            self.hist = []; return dict(status="not_graded", reasons=list(a["reasons"]))
        if self.hist and self.hist[-1]["grade"] != a["grade"]:
            self.hist = [a]; return dict(status="pending", reasons=["assessments_disagree"], have=1, need=P["minFrames"])
        self.hist.append(a); self.hist = self.hist[-P["minFrames"]:]
        if len(self.hist) < P["minFrames"]: return dict(status="pending", reasons=["confirming"], have=len(self.hist), need=P["minFrames"])
        if P["mode"] == "score":
            fs = [h["pFresh"] for h in self.hist]
            if max(fs) - min(fs) > P["scoreTol"]: return dict(status="pending", reasons=["quality_score_unstable"], have=len(self.hist), need=P["minFrames"])
        return dict(status="graded", grade=a["grade"])


def blockiness(gray) -> float:
    """Phase-invariant 8x8 blocking measure on a grayscale crop (numpy 2-D): max / median of the mean |gradient| per position mod 8,
    horizontal and vertical (1.0 = no blocking). Crops < 24 px return 1.0."""
    import numpy as np
    g = np.asarray(gray, dtype=np.float32)
    if min(g.shape) < 24: return 1.0
    dx = np.abs(np.diff(g, axis=1)).mean(0); dy = np.abs(np.diff(g, axis=0)).mean(1)
    px = np.array([dx[i::8].mean() for i in range(8)]); py = np.array([dy[i::8].mean() for i in range(8)])
    return round(float(max(px.max() / max(float(np.median(px)), 1e-6), py.max() / max(float(np.median(py)), 1e-6))), 4)
