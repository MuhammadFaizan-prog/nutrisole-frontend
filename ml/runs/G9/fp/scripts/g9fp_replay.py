"""G9 Stage A DEV replay: per-class thresholds (A1) and provisional-display / birth-margin policy (A2) on cached G3 detections.
Equivalent to `ml/eval/video_gauntlet.py --no-realtime --stride 1 --max-same-class 0` for det/neg metrics (the quality classifier
only adds grades and never changes tracks or labels); metrics come from video_gauntlet.metrics() unchanged. A0 parity vs the G8
DEV G3 run is checked in g9fp_dev.py. Default behaviour of the shared scorer is untouched."""
import json, os, sys
R = "/workspace/work/nutrisole"; sys.path.insert(0, f"{R}/ml/eval"); sys.path.insert(0, f"{R}/ml")
from tracker import IouTracker, iou
from scene_guard import scene_guard, fa_episodes
import video_gauntlet as vg
NAMES = vg.NAMES
C = "/workspace/work/cv/g9fp"; CL = "/workspace/work/cv/g3clips_dev"


class PolicyTracker(IouTracker):
    """IouTracker + birth margin: an unmatched detection (IoU < iouMatch with every live track box) may start a new track
    only if score >= thr[c] + delta. minHits is the stock IouTracker display gate."""
    def __init__(self, thr, delta=0.0, **p):
        super().__init__(**p); self.thr, self.delta = thr, delta

    def update(self, dets, t_ms):
        if self.delta > 0:
            dets = [d for d in dets if d["score"] >= self.thr[d["classId"]] + self.delta
                    or any(iou(tr.box, d["box"]) >= self.p["iouMatch"] for tr in self.tracks)]
        return super().update(dets, t_ms)


def replay(kind, thr, minHits=2, delta=0.0, guard=dict(maxSameClass=0, minAreaFrac=0.01), cache=None, return_shown=False):
    gt = json.load(open(f"{CL}/{kind}_clip.json")); fr_d = cache or json.load(open(f"{C}/devclip_{kind}_dets.json"))
    trk = PolicyTracker(thr, delta, minHits=minHits); shown = []; rawf = []
    for fi, fr in enumerate(gt["frames"][:len(fr_d)]):
        ds = [dict(box=d[:4], classId=d[4], score=d[5]) for d in fr_d[fi] if d[5] >= thr[d[4]]]
        ds = scene_guard(ds, **guard); rawf.append(ds)
        if fr.get("reset"): trk.reset()
        tr = trk.update(ds, fr["t_ms"])
        shown.append([dict(id=x["id"], box=x["box"], label=x["label"], score=x["score"], grade=None, level=None, reasons=None) for x in tr])
    m = vg.metrics(gt, shown, kind)
    if kind == "neg":
        life = {}
        for st in shown:
            for s in st: life[s["id"]] = life.get(s["id"], 0) + 1
        L = [v / gt["fps"] for v in life.values()]
        m.update(false_track_births_per_min=m["false_alarms_per_min"], false_track_lifetime_mean_s=round(sum(L) / len(L), 3) if L else 0.0,
                 false_track_lifetime_max_s=round(max(L), 3) if L else 0.0)
        cls_of = {}
        for st in shown:
            for s in st: cls_of.setdefault(s["id"], NAMES[s["label"]])
        import collections
        m["false_tracks_by_class"] = dict(collections.Counter(cls_of.values()))
    return (m, shown, rawf, gt) if return_shown else m
