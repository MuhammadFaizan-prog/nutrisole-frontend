"""G2: tune IouTracker hysteresis on the DEV clips (built from VAL images; never test).

1. Runs the exported detector once over every frame of the dev clips (no frame dropping)
   and caches the decoded detections.
2. Replays the tracker for every parameter set in a small grid and scores it with the
   same metrics() as the video gauntlet.
Selection rule (stated up front): minimise static label flicker per 10 s over det+quality
dev clips, subject to (a) dev segment accuracy >= the current defaults' dev segment
accuracy, (b) dev time-to-first-correct p90 <= defaults' p90 + 200 ms (and <= 700 ms if the
defaults meet it), (c) dev false alarms/min <= defaults'. Ties -> fewer frames of delay
(smaller switchFrames, then minHits).

  python ml/eval/tune_tracker.py --det <onnx> --det-kind e2e --imgsz 320 --clips /workspace/work/cv/g2clips_dev --out ml/runs/G2/tracker_tune
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import pickle
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from geometry import letterbox, dst_to_src, decode  # noqa: E402
from tracker import IouTracker, DEFAULT  # noqa: E402
from video_gauntlet import sess, metrics, RUBRIC  # noqa: E402
from scene_guard import scene_guard  # noqa: E402


def cache_dets(det, kind, imgsz, video, gt):
    cap = cv2.VideoCapture(video)
    di = det.get_inputs()[0].name
    W, H = gt["w"], gt["h"]
    out = []
    for fr in gt["frames"]:
        ok, frame = cap.read()
        if not ok:
            break
        x, tf = letterbox(frame, imgsz)
        o = det.run(None, {di: x})[0]
        ds = []
        for d in decode(o, kind, RUBRIC["detectorMinScore"]):
            b = dst_to_src(d["box"], tf)
            if b[2] - b[0] < 2 or b[3] - b[1] < 2:
                continue
            ds.append(dict(box=[b[0] / W, b[1] / H, b[2] / W, b[3] / H], classId=d["classId"], score=d["score"]))
        out.append(ds)
    return out


def replay(gt, dets, params, guard=None):
    trk = IouTracker(**params)
    shown = []
    for fr, ds in zip(gt["frames"], dets):
        if guard is not None:
            ds = scene_guard(ds, **guard)
        if fr.get("reset"):
            trk.reset()
        tr = trk.update(ds, fr["t_ms"])
        shown.append([dict(id=t["id"], box=t["box"], label=t["label"], score=t["score"], grade=None, level=None) for t in tr])
    return shown


def score(gts, dets, params, guard=None):
    r = {}
    for k in ["det", "quality", "neg"]:
        r[k] = metrics(gts[k], replay(gts[k], dets[k], params, guard), k)
    st = sum(x["static_s"] for k in ["det", "quality"] for x in r[k]["segments_detail"])
    ch = sum(x["label_changes_static"] for k in ["det", "quality"] for x in r[k]["segments_detail"])
    segs = [x for k in ["det", "quality"] for x in r[k]["segments_detail"]]
    tt = [x["ttfc_ms"] for x in segs if x["ttfc_ms"] is not None]
    return dict(flicker_static_10s=round(10 * ch / st, 3), det_flicker=r["det"]["label_flicker_per_10s_static"],
                quality_flicker=r["quality"]["label_flicker_per_10s_static"], seg_acc=round(np.mean([x["seg_correct"] for x in segs]), 4),
                det_seg_acc=r["det"]["segment_acc"], quality_seg_acc=r["quality"]["segment_acc"],
                ttfc_p90=float(np.percentile(tt, 90)) if tt else None, never_correct=sum(x["ttfc_ms"] is None for x in segs),
                fa_per_min=r["neg"]["false_alarms_per_min"], fa_episodes_per_min=r["neg"]["fa_episodes_per_min"], no_box_static=round(np.mean([x["no_box_frac_static"] for x in segs]), 3))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--det", required=True)
    ap.add_argument("--det-kind", choices=["e2e", "raw"], required=True)
    ap.add_argument("--imgsz", type=int, default=320)
    ap.add_argument("--clips", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--guard-grid", action="store_true", help="G3: tune the scene guard (default tracker params)")
    ap.add_argument("--guard", default=None, help="G3: fixed scene guard 'maxSameClass,minAreaFrac' applied during the tracker grid")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    det = sess(a.det)
    gts, dets = {}, {}
    cp = f"{a.out}/dets_cache_{os.path.basename(a.det)}.pkl"
    cache = pickle.load(open(cp, "rb")) if os.path.exists(cp) else {}
    for k in ["det", "quality", "neg"]:
        gts[k] = json.load(open(f"{a.clips}/{k}_clip.json"))
        if k not in cache:
            cache[k] = cache_dets(det, a.det_kind, a.imgsz, f"{a.clips}/{k}_clip.mp4", gts[k])
            pickle.dump(cache, open(cp, "wb"))
        dets[k] = cache[k]
    if a.guard_grid:
        return guard_grid(a, gts, dets)
    G = None
    if a.guard:
        msc, maf = a.guard.split(",")
        G = dict(maxSameClass=int(msc), minAreaFrac=float(maf))
    base = score(gts, dets, {}, G)
    rows = []
    for sm, sf, sa, mh, mm in itertools.product([0.1, 0.15, 0.25, 0.35], [3, 5, 8], [0.2, 0.35, 0.5], [2, 3], [4, 8]):
        p = dict(switchMargin=sm, switchFrames=sf, scoreAlpha=sa, minHits=mh, maxMissed=mm)
        rows.append(dict(params=p, **score(gts, dets, p, G)))
    ttfc_cap = base["ttfc_p90"] + 200 if base["ttfc_p90"] is not None else 1e9
    if base["ttfc_p90"] is not None and base["ttfc_p90"] <= 700:
        ttfc_cap = min(ttfc_cap, 700)
    ok = [r for r in rows if r["seg_acc"] >= base["seg_acc"] and r["ttfc_p90"] is not None and r["ttfc_p90"] <= ttfc_cap and r["fa_per_min"] <= base["fa_per_min"]]
    best = min(ok, key=lambda r: (r["flicker_static_10s"], r["params"]["switchFrames"], r["params"]["minHits"])) if ok else None
    res = dict(det=a.det, clips=a.clips, scene_guard=G, defaults=DEFAULT, defaults_score=base, ttfc_cap_ms=ttfc_cap, n_grid=len(rows), n_feasible=len(ok),
               best=best, top10=sorted(ok, key=lambda r: r["flicker_static_10s"])[:10],
               note="DEV clips from VAL images, detector run on every frame (no drops); final numbers come from the realtime gauntlet on TEST clips.")
    json.dump(res, open(f"{a.out}/tracker_tune.json", "w"), indent=1)
    print(json.dumps(dict(defaults=base, best=best, n_feasible=len(ok)), indent=1))


def guard_grid(a, gts, dets):
    """G3 scene-guard tuning on DEV clips. Rule (stated up front): minimise dev FA episodes/min, then FA
    tracks/min, subject to dev segment accuracy >= no-guard segment accuracy - 0.02 and ttfc p90 <= no-guard + 200 ms.
    Ties -> the weaker guard (larger maxSameClass, smaller minAreaFrac)."""
    base = score(gts, dets, {}, None)
    rows = []
    for msc in [0, 3, 4, 6, 8]:
        for maf in [0.0, 0.002, 0.005, 0.01, 0.02]:
            g = dict(maxSameClass=msc, minAreaFrac=maf)
            rows.append(dict(guard=g, **score(gts, dets, {}, g)))
    cap = (base["ttfc_p90"] or 1e9) + 200
    ok = [r for r in rows if r["seg_acc"] >= base["seg_acc"] - 0.02 and r["ttfc_p90"] is not None and r["ttfc_p90"] <= cap]
    key = lambda r: (r["fa_episodes_per_min"], r["fa_per_min"], -(r["guard"]["maxSameClass"] or 99), r["guard"]["minAreaFrac"])
    best = min(ok, key=key) if ok else None
    res = dict(det=a.det, clips=a.clips, no_guard=base, rule=guard_grid.__doc__, n_feasible=len(ok), best=best, rows=rows)
    json.dump(res, open(f"{a.out}/guard_tune.json", "w"), indent=1)
    print(json.dumps(dict(no_guard=base, best=best, n_feasible=len(ok)), indent=1))


if __name__ == "__main__":
    main()
