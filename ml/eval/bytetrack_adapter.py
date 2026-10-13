"""G6.4 ByteTrack adapter with the SAME interface as tracker.IouTracker (update(dets, t_ms) -> list of dicts, reset(),
.tracks with .id, .p). Association is Ultralytics BYTETracker (Kalman motion + two-stage high/low-score matching);
label hysteresis, score EMA and the 'stable' flag reuse IouTracker's rules so only the association step differs.
Python-only research path (NOT ported to native/); behind the gauntlet --tracker-kind flag, default 'iou'.
Low-score detections (>= track_low_thresh) must be passed in for ByteTrack's second association; only tracks
confirmed by a detection >= track_high_thresh are ever shown."""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
from ultralytics.trackers.byte_tracker import BYTETracker
from ultralytics.trackers.bot_sort import BOTSORT

from tracker import DEFAULT as IOU_DEFAULT
from tracker import iou

DEFAULT = dict(track_high_thresh=0.35, track_low_thresh=0.1, new_track_thresh=0.35, track_buffer=15, match_thresh=0.8,
               fuse_score=True, scoreAlpha=IOU_DEFAULT["scoreAlpha"], switchMargin=IOU_DEFAULT["switchMargin"],
               switchFrames=IOU_DEFAULT["switchFrames"], minHits=IOU_DEFAULT["minHits"], stableIou=IOU_DEFAULT["stableIou"],
               stableMs=IOU_DEFAULT["stableMs"], boxAlpha=IOU_DEFAULT["boxAlpha"])


class _Res:
    """Minimal Results-like container accepted by BYTETracker (boolean indexing, conf/xywh/cls)."""

    def __init__(self, xywh, conf, cls):
        self.xywh, self.conf, self.cls = xywh, conf, cls

    def __len__(self):
        return len(self.conf)

    def __getitem__(self, m):
        return _Res(self.xywh[m], self.conf[m], self.cls[m])


class _T:  # per-track label state (mirrors tracker.Track fields used by the gauntlet)
    def __init__(self, id_, box, label, score, t_ms):
        self.id, self.box, self.rawBox, self.label = id_, list(box), list(box), label
        self.scores = {label: score}; self.hits = 1; self.pendingLabel, self.pendingCount = -1, 0
        self.stableSinceMs = t_ms; self.firstSeenMs = t_ms; self.seen_frame = 0


class ByteTrackTracker:
    def __init__(self, **params):
        self.p = {**DEFAULT, **params}
        self._new()

    kind = "bytetrack"

    def _new(self):
        a = SimpleNamespace(**{k: self.p[k] for k in ["track_high_thresh", "track_low_thresh", "new_track_thresh",
                                                        "track_buffer", "match_thresh", "fuse_score"]})
        if self.kind == "botsort":  # G7 (GPT review): BoT-SORT without ReID and without camera-motion compensation
            a.gmc_method, a.proximity_thresh, a.appearance_thresh, a.with_reid, a.model = "none", 0.5, 0.8, False, "auto"
            self.bt = BOTSORT(a)
        else:
            self.bt = BYTETracker(a)
        self.state: dict[int, _T] = {}
        self.tracks: list[_T] = []
        self.frame = 0

    def reset(self):
        self._new()

    def update(self, dets: list[dict], t_ms: float) -> list[dict]:
        P = self.p; self.frame += 1
        if dets:
            b = np.array([d["box"] for d in dets], np.float32)
            xywh = np.stack([(b[:, 0] + b[:, 2]) / 2, (b[:, 1] + b[:, 3]) / 2, b[:, 2] - b[:, 0], b[:, 3] - b[:, 1]], 1)
            res = _Res(xywh, np.array([d["score"] for d in dets], np.float32), np.array([d["classId"] for d in dets], np.float32))
        else:
            res = _Res(np.zeros((0, 4), np.float32), np.zeros(0, np.float32), np.zeros(0, np.float32))
        out = self.bt.update(res)
        live = {}
        for r in out:  # [x1,y1,x2,y2,id,score,cls,idx]; only tracks updated by a detection THIS frame are returned
            tid, idx = int(r[4]), int(r[7]); d = dets[idx]; box = [float(v) for v in r[:4]]
            t = self.state.get(tid)
            if t is None:
                t = _T(tid, d["box"], d["classId"], d["score"], t_ms); self.state[tid] = t
            else:
                if iou(t.rawBox, d["box"]) < P["stableIou"]:
                    t.stableSinceMs = t_ms
                t.rawBox = list(d["box"])
                t.box = [(1 - P["boxAlpha"]) * t.box[k] + P["boxAlpha"] * d["box"][k] for k in range(4)]
                for c in set(t.scores) | {d["classId"]}:
                    prev = t.scores.get(c, 0.0)
                    t.scores[c] = (1 - P["scoreAlpha"]) * prev + P["scoreAlpha"] * (d["score"] if c == d["classId"] else 0.0)
                self._hyst(t); t.hits += 1
            t.seen_frame = self.frame; live[tid] = t
        # forget label state of tracks ByteTrack removed (lost beyond buffer); keep lost-but-buffered ones
        keep = {s.track_id for s in self.bt.tracked_stracks + self.bt.lost_stracks}
        self.state = {k: v for k, v in self.state.items() if k in keep or k in live}
        self.tracks = list(live.values())
        return [dict(id=t.id, box=t.box, label=t.label, score=t.scores.get(t.label, 0.0),
                     stable=(t_ms - t.stableSinceMs) >= P["stableMs"], ageMs=t_ms - t.firstSeenMs)
                for t in self.tracks if t.hits >= P["minHits"]]

    def _hyst(self, t):
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


class BotSortTracker(ByteTrackTracker):
    """G7 DEV-only research option: Ultralytics BOTSORT association (KalmanFilterXYWH), with_reid=False, gmc_method='none';
    same label layer as ByteTrackTracker. Not ported to native/."""
    kind = "botsort"


def make_parity_fixture(path: str, n_frames: int = 160, seed: int = 0):
    """G7.3: detection stream for the TS port parity test (native/tests/cvByteTrack.test.ts): three objects, one moving
    across another, low-score frames (second association), multi-frame dropouts (lost -> refind within the buffer and
    removal beyond it), class noise, a duplicate box, spurious single-frame boxes, and a reset."""
    import json
    import random
    rnd = random.Random(seed)
    frames = []
    for f in range(n_frames):
        dets = []
        if (f < 50 or 58 <= f < 120) and rnd.random() > 0.08:  # A: static, 8-frame gap (lost then refound)
            cls = 1 if rnd.random() > 0.2 else rnd.choice([0, 3, 6])
            j = [rnd.uniform(-0.008, 0.008) for _ in range(4)]
            s = round(rnd.uniform(0.15, 0.34), 4) if 30 <= f < 36 else round(rnd.uniform(0.4, 0.95), 4)
            dets.append(dict(box=[0.30 + j[0], 0.30 + j[1], 0.60 + j[2], 0.65 + j[3]], classId=cls, score=s))
            if f % 17 == 3:  # near-duplicate box
                dets.append(dict(box=[0.31 + j[0], 0.31 + j[1], 0.61 + j[2], 0.66 + j[3]], classId=cls, score=round(rnd.uniform(0.36, 0.6), 4)))
        if 10 <= f < 130:  # B: moves right, crosses A
            x = 0.02 + 0.006 * (f - 10)
            if rnd.random() > 0.1:
                dets.append(dict(box=[x, 0.40, x + 0.18, 0.62], classId=10 if rnd.random() > 0.15 else 9, score=round(rnd.uniform(0.2, 0.9), 4)))
        if 70 <= f < 150 and not (90 <= f < 110):  # C: appears, 20-frame gap (> buffer 15 -> new id)
            dets.append(dict(box=[0.70, 0.70, 0.90, 0.95], classId=7, score=round(rnd.uniform(0.35, 0.9), 4)))
        if rnd.random() < 0.05:  # spurious
            x, y = rnd.uniform(0, 0.8), rnd.uniform(0, 0.8)
            dets.append(dict(box=[x, y, x + 0.1, y + 0.1], classId=rnd.randrange(12), score=round(rnd.uniform(0.1, 0.6), 4)))
        rnd.shuffle(dets)
        frames.append(dict(tMs=round(f * 33.333, 3), dets=dets, reset=(f == 140)))
    trk = ByteTrackTracker()
    outs = []
    for fr in frames:
        if fr["reset"]:
            trk.reset()
        outs.append([dict(id=o["id"], box=[float(v) for v in o["box"]], label=int(o["label"]), score=float(o["score"]), stable=bool(o["stable"]), ageMs=float(o["ageMs"]))
                     for o in trk.update(fr["dets"], fr["tMs"])])
    p = {k: (bool(v) if isinstance(v, bool) else v) for k, v in trk.p.items()}
    json.dump(dict(params=p, frames=frames, expected=outs), open(path, "w"))


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    make_parity_fixture(os.path.join(here, "fixtures", "bytetrack_parity.json"))
    print("wrote fixture")
