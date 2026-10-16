"""G5 causal temporal rescoring (Seq-NMS / tubelet score smoothing, online variant).

EXACT mirror of TemporalRescorer in native/src/cv/pipeline/temporal.ts
(parity: native/tests/cvTemporal.test.ts replays ml/eval/fixtures/temporal_parity.json made here).

Applied per processed frame AFTER decode (at a lower pre-threshold) + mapping to normalised frame
coords + scene guard, BEFORE the tracker:
  * keep a buffer of the last (window - 1) frames of detections (class + score + box);
  * for each current detection, in every buffered frame take the detection with the highest IoU
    to the current box (class-agnostic link, IoU >= iouLink) and add its score to that class;
  * rescored score = summed score of the winning class / frames in the tube window (current frame
    + buffered frames; a frame with no linked box contributes 0), so an isolated one-frame box is
    divided down and dropped by `minScore`, while a box seen in most frames keeps its score;
  * the displayed class is the class with the highest summed score (ties -> lowest class id).
Online/causal: only past frames are used (the app cannot see the future). reset() clears the buffer.
Order of output: by rescored score desc, then input order.
"""
from __future__ import annotations

DEFAULT_TEMPORAL = dict(window=5, iouLink=0.5, preScore=0.2, minScore=0.35)


def _iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / u if u > 0 else 0.0


class TemporalRescorer:
    def __init__(self, window=DEFAULT_TEMPORAL["window"], iouLink=DEFAULT_TEMPORAL["iouLink"],
                 preScore=DEFAULT_TEMPORAL["preScore"], minScore=DEFAULT_TEMPORAL["minScore"]):
        self.p = dict(window=int(window), iouLink=float(iouLink), preScore=float(preScore), minScore=float(minScore))
        self.buf: list[list[dict]] = []

    def reset(self):
        self.buf = []

    def update(self, dets: list[dict]) -> list[dict]:
        P = self.p
        cur = [d for d in dets if d["score"] >= P["preScore"]]
        frames = len(self.buf) + 1
        out = []
        for idx, d in enumerate(cur):
            acc = {d["classId"]: d["score"]}
            for past in self.buf:
                best, bi = None, P["iouLink"]
                for q in past:
                    v = _iou(d["box"], q["box"])
                    if v >= bi and (best is None or v > bi):
                        best, bi = q, v
                if best is not None:
                    acc[best["classId"]] = acc.get(best["classId"], 0.0) + best["score"]
            c = min(acc, key=lambda k: (-acc[k], k))
            s = acc[c] / frames
            if s >= P["minScore"]:
                out.append(dict(box=list(d["box"]), classId=int(c), score=float(s), _i=idx))
        self.buf.append([dict(box=list(d["box"]), classId=d["classId"], score=d["score"]) for d in cur])
        if len(self.buf) > P["window"] - 1:
            self.buf = self.buf[len(self.buf) - (P["window"] - 1):] if P["window"] > 1 else []
        out.sort(key=lambda r: (-r["score"], r["_i"]))
        for r in out:
            del r["_i"]
        return out


def make_fixture(path):
    """Deterministic random sequences -> expected outputs (consumed by the TS parity test)."""
    import json
    import random
    rng = random.Random(5)
    cases = []
    for params in [dict(window=3, iouLink=0.5, preScore=0.2, minScore=0.35), dict(window=5, iouLink=0.5, preScore=0.2, minScore=0.35),
                   dict(window=7, iouLink=0.4, preScore=0.15, minScore=0.3), dict(window=1, iouLink=0.5, preScore=0.35, minScore=0.35)]:
        tr = TemporalRescorer(**params)
        frames = []
        base = [[rng.uniform(0.05, 0.5), rng.uniform(0.05, 0.5)] for _ in range(3)]
        for t in range(40):
            dets = []
            for k, (x, y) in enumerate(base):
                if rng.random() < 0.75:
                    w = 0.3 + 0.02 * rng.random()
                    dx, dy = rng.uniform(-0.02, 0.02), rng.uniform(-0.02, 0.02)
                    dets.append(dict(box=[round(x + dx, 4), round(y + dy, 4), round(x + dx + w, 4), round(y + dy + w, 4)],
                                     classId=rng.choice([k, k, k, 7]), score=round(rng.uniform(0.15, 0.95), 4)))
            if rng.random() < 0.3:  # isolated false alarm
                x, y = rng.uniform(0, 0.8), rng.uniform(0, 0.8)
                dets.append(dict(box=[round(x, 4), round(y, 4), round(x + 0.1, 4), round(y + 0.1, 4)], classId=rng.randrange(12), score=round(rng.uniform(0.3, 0.9), 4)))
            reset = t == 25
            if reset:
                tr.reset()
            frames.append(dict(dets=dets, reset=reset, expected=tr.update(dets)))
        cases.append(dict(params=params, frames=frames))
    json.dump(dict(cases=cases), open(path, "w"), indent=0)


if __name__ == "__main__":
    import os
    make_fixture(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "temporal_parity.json"))
    print("fixture written")
