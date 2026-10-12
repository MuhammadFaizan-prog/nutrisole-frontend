"""Per-object IoU tracker with label hysteresis. EXACT mirror of
native/src/cv/pipeline/tracker.ts (parity enforced by native/tests/cvTracker.test.ts,
which replays ml/eval/fixtures/tracker_parity.json produced by this module)."""
from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT = dict(iouMatch=0.3, boxAlpha=0.6, scoreAlpha=0.2, switchMargin=0.15, switchFrames=3,
               minHits=2, maxMissed=4, stableIou=0.8, stableMs=500)


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


@dataclass
class Track:
    id: int
    box: list
    rawBox: list
    label: int
    scores: dict
    hits: int = 1
    missed: int = 0
    pendingLabel: int = -1
    pendingCount: int = 0
    stableSinceMs: float = 0.0
    firstSeenMs: float = 0.0


class IouTracker:
    def __init__(self, **params):
        self.p = {**DEFAULT, **params}
        self.tracks: list[Track] = []
        self.nextId = 1

    def reset(self):
        self.tracks = []

    def update(self, dets: list[dict], t_ms: float) -> list[dict]:
        P = self.p
        pairs = []
        for ti, t in enumerate(self.tracks):
            for di, d in enumerate(dets):
                v = iou(t.box, d["box"])
                if v >= P["iouMatch"]:
                    pairs.append((v, ti, di))
        pairs.sort(key=lambda x: (-x[0], self.tracks[x[1]].id, x[2]))
        usedT, usedD = set(), set()
        for _, ti, di in pairs:
            if ti in usedT or di in usedD:
                continue
            usedT.add(ti)
            usedD.add(di)
            t, d = self.tracks[ti], dets[di]
            if iou(t.rawBox, d["box"]) < P["stableIou"]:
                t.stableSinceMs = t_ms
            t.rawBox = list(d["box"])
            t.box = [(1 - P["boxAlpha"]) * t.box[k] + P["boxAlpha"] * d["box"][k] for k in range(4)]
            for c in set(t.scores) | {d["classId"]}:
                prev = t.scores.get(c, 0.0)
                t.scores[c] = (1 - P["scoreAlpha"]) * prev + P["scoreAlpha"] * (d["score"] if c == d["classId"] else 0.0)
            self._hyst(t)
            t.hits += 1
            t.missed = 0
        surv = []
        for ti, t in enumerate(self.tracks):
            if ti not in usedT:
                t.missed += 1
            if t.missed <= P["maxMissed"]:
                surv.append(t)
        self.tracks = surv
        for di, d in enumerate(dets):
            if di in usedD:
                continue
            self.tracks.append(Track(id=self.nextId, box=list(d["box"]), rawBox=list(d["box"]), label=d["classId"],
                                     scores={d["classId"]: d["score"]}, stableSinceMs=t_ms, firstSeenMs=t_ms))
            self.nextId += 1
        return [dict(id=t.id, box=t.box, label=t.label, score=t.scores.get(t.label, 0.0),
                     stable=(t_ms - t.stableSinceMs) >= P["stableMs"], ageMs=t_ms - t.firstSeenMs)
                for t in self.tracks if t.hits >= P["minHits"] and t.missed == 0]

    def _hyst(self, t: Track):
        P = self.p
        best, best_s = t.label, t.scores.get(t.label, 0.0)
        for k in sorted(t.scores):
            if t.scores[k] > best_s:
                best, best_s = k, t.scores[k]
        if best != t.label and best_s - t.scores.get(t.label, 0.0) >= P["switchMargin"]:
            if t.pendingLabel == best:
                t.pendingCount += 1
            else:
                t.pendingLabel, t.pendingCount = best, 1
            if t.pendingCount >= P["switchFrames"]:
                t.label, t.pendingLabel, t.pendingCount = best, -1, 0
        else:
            t.pendingLabel, t.pendingCount = -1, 0


def make_parity_fixture(path: str, n_frames: int = 120, seed: int = 0):
    """Random but structured detection stream: two objects, jitter, dropouts, class noise,
    an object leaving and a new one entering at the same spot."""
    import json
    import random
    rnd = random.Random(seed)
    frames = []
    for f in range(n_frames):
        dets = []
        if f < 60 or f >= 70:  # object A until 60; gap; object C at same place from 70
            cls = 1 if f < 60 else 7
            if rnd.random() < 0.2:
                cls = rnd.choice([0, 3, 6])
            if rnd.random() > 0.1:
                j = [rnd.uniform(-0.01, 0.01) for _ in range(4)]
                dets.append(dict(box=[0.30 + j[0], 0.30 + j[1], 0.60 + j[2], 0.65 + j[3]], classId=cls, score=round(rnd.uniform(0.4, 0.95), 4)))
        if 20 <= f < 100:
            x = 0.05 + 0.002 * (f - 20)
            dets.append(dict(box=[x, 0.7, x + 0.2, 0.95], classId=10, score=round(rnd.uniform(0.3, 0.9), 4)))
        frames.append(dict(tMs=round(f * 33.333, 3), dets=dets, reset=(f == 110)))
    trk = IouTracker()
    outs = []
    for fr in frames:
        if fr["reset"]:
            trk.reset()
        outs.append(trk.update(fr["dets"], fr["tMs"]))
    json.dump(dict(params=trk.p, frames=frames, expected=outs), open(path, "w"))


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(here, "fixtures"), exist_ok=True)
    make_parity_fixture(os.path.join(here, "fixtures", "tracker_parity.json"))
    print("wrote fixture")
