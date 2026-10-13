"""G9 existing-models arm: minimal 2 fps replay of the VB8 DEV web clips (splits_v7.csv rows with split dev / dev_v7 ONLY;
never holdout / holdout_v7_pending / negatives_v7). These clips have NO human box labels ("machine proposals only"), so the
output is descriptive: per-class detections, frames with any box, out-of-taxonomy (unmapped) source classes, latency, and a
WEAK title-level check (expected class taken from the Wikimedia file title, only where the title names one produce type).
Same threshold (RUBRIC detectorMinScore 0.35), class-wise NMS 0.7 and scene guard (minAreaFrac 0.01, rule 2 off) for every model.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from g9common import Detector, NAMES, REPO  # noqa: E402
sys.path.insert(0, os.path.join(REPO, "ml/eval"))
from scene_guard import scene_guard  # noqa: E402

SPLITS = os.path.join(REPO, "ml/runs/G7/video_v7/splits_v7.csv")
RAW = ["/workspace/work/cv/g6src/raw", "/workspace/work/cv/g7src/raw"]
CONF = 0.35       # reporting threshold for the summary (RUBRIC detectorMinScore); raw boxes are dumped from DUMP_CONF
DUMP_CONF = 0.1   # G9 addendum: raw per-frame boxes kept at >=0.1 so DEV-tuned thresholds can be applied offline
# WEAK title-level expectations (file title names produce; written before scoring). Chilli-emoji "Pepper" clips: no expectation.
TITLE_EXPECT = {
    "c42c27498": ["carrot"], "ca3a8411d": ["carrot", "cucumber"], "ca4d0f9cf": ["carrot", "cucumber"], "c20606e36": ["carrot", "cucumber"],
    "cfda01e90": ["carrot"], "ca5207d1f": ["carrot", "cucumber"], "cbc4ee137": ["carrot", "cucumber"], "cf11cd00b": ["cucumber"],
    "c86f74c3a": ["citrus"], "c18be0288": ["tomato"], "c6c0d485a": ["tomato"], "cb045e06b": ["mango"],
}
CHILLI_TITLE = ["ccd5949e0", "cb09ab182", "c9048d7da", "c1ee7d682", "c5e5004e3", "c69f0e13b"]


def dev_clips():
    rows = [r for r in csv.DictReader(open(SPLITS)) if r["split"] in ("dev", "dev_v7")]
    out = []
    for r in rows:
        p = next((os.path.join(d, f) for d in RAW for f in sorted(os.listdir(d)) if f.startswith(r["clip_id"] + ".")), None)
        out.append((r["clip_id"], r["split"], r["page"], p))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=["g3", "snapml", "calories"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=float, default=2.0)
    a = ap.parse_args()
    det = Detector(a.model)
    res = dict(model=a.model, sample_fps=a.fps, conf=CONF, guard=dict(maxSameClass=0, minAreaFrac=0.01), clips={})
    lat = []
    for cid, split, page, path in dev_clips():
        if path is None:
            res["clips"][cid] = dict(error="file missing"); continue
        cap = cv2.VideoCapture(path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        nxt, fi, n = 0.0, 0, 0
        frames_any, cls_frames, cls_dets, unm = 0, collections.Counter(), collections.Counter(), collections.Counter()
        per_frame, raw_frames, bright = [], [], []
        while True:
            ok, fr = cap.read()
            if not ok:
                break
            t = fi / fps; fi += 1
            if t + 1e-6 < nxt:
                continue
            nxt += 1.0 / a.fps
            H, W = fr.shape[:2]
            r = det(fr, DUMP_CONF)
            raw_all = [[c, round(s_, 4), round(b[0] / W, 4), round(b[1] / H, 4), round(b[2] / W, 4), round(b[3] / H, 4)] for b, c, s_ in r["mapped"]]
            bright.append(float(cv2.cvtColor(cv2.resize(fr, (64, 36)), cv2.COLOR_BGR2GRAY).mean()))
            r["mapped"] = [m_ for m_ in r["mapped"] if m_[2] >= CONF]
            lat.append(r["ms"]); n += 1
            dets = [dict(box=[b[0] / W, b[1] / H, b[2] / W, b[3] / H], classId=c, score=s) for b, c, s in r["mapped"]]
            dets = scene_guard(dets, maxSameClass=0, minAreaFrac=0.01)
            unm.update(r["unmapped"])
            if dets:
                frames_any += 1
            for c in {d["classId"] for d in dets}:
                cls_frames[NAMES[c]] += 1
            for d in dets:
                cls_dets[NAMES[d["classId"]]] += 1
            per_frame.append([round(t, 2), [[NAMES[d["classId"]], round(d["score"], 3)] for d in dets]])
            raw_frames.append([round(t, 2), raw_all])
        exp = TITLE_EXPECT.get(cid)
        row = dict(split=split, page=page, sampled_frames=n, frames_any=frames_any, frac_any=round(frames_any / max(1, n), 3),
                   class_frames=dict(cls_frames), class_dets=dict(cls_dets), unmapped_src_dets=dict(unm), title_expect=exp,
                   chilli_title=cid in CHILLI_TITLE, mean_luma=round(float(np.mean(bright)), 1) if bright else None,
                   wh=[W, H] if n else None, per_frame=per_frame, raw_frames_conf01=raw_frames)
        if exp:
            row["title_hit_frac"] = round(sum(1 for _, ds in per_frame if any(d[0] in exp for d in ds)) / max(1, n), 3)
            row["off_title_frames"] = sum(1 for _, ds in per_frame if any(d[0] not in exp for d in ds))
        res["clips"][cid] = row
        print(cid, n, frames_any, dict(cls_frames), flush=True)
    res["latency_ms"] = dict(p50=float(np.percentile(lat, 50)), p90=float(np.percentile(lat, 90)), p95=float(np.percentile(lat, 95)), n=len(lat))
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=1)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
