"""G7 Phase 3, stage 1: adaptive keyframes + G3 detections + ByteTrack propagation for unlabelled web videos.

For each clip: decode at `--fps` (default 4), run the G3 control detector (ONNX raw, imgsz 480, class-wise NMS 0.7, score >= 0.1)
and ByteTrack b15 (ml/eval/bytetrack_adapter.py) over every sampled frame; keep a KEYFRAME when the scene changed enough
(mean abs grey diff on 64x36 thumbnails >= --diff, or the track set changed, or --max-gap s elapsed), capped per clip.
Outputs per clip (in --out/<clip_id>/): keyframes/*.jpg (max side 960), frames.json (all sampled frames: t, dets with track id),
keyframes.json. Everything produced here is a PROPOSAL (machine output), never ground truth.
  python ml/autolabel/extract.py --clips-dir DIR --out OUT [--ids c1 c2 ...]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "eval"))
from video_gauntlet import sess, letterbox, decode, dst_to_src  # noqa: E402
from bytetrack_adapter import ByteTrackTracker  # noqa: E402

DET = "/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx"
NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]


def run(path, out, det, fps=4.0, diff=18.0, max_gap=4.0, max_kf=40, max_s=180.0, imgsz=480):
    cap = cv2.VideoCapture(path)
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    step = max(1, int(round(src_fps / fps)))
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    dur = (cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) / src_fps
    min_gap = max(1.0, min(dur if dur > 0 else max_s, max_s) / max_kf)  # spread the keyframe budget over the clip
    trk = ByteTrackTracker(track_buffer=15)
    di = det.get_inputs()[0].name
    os.makedirs(f"{out}/keyframes", exist_ok=True)
    frames, kfs = [], []
    last_thumb, last_kf_t, last_ids = None, -1e9, set()
    fi = -1
    t0 = time.time()
    while True:
        ok = cap.grab()
        if not ok:
            break
        fi += 1
        if fi % step:
            continue
        ok, frame = cap.retrieve()
        if not ok:
            break
        t = fi / src_fps
        if t > max_s:
            break
        x, tf = letterbox(frame, imgsz)
        o = det.run(None, {di: x})[0]
        dets = []
        for d in decode(o, "raw", 0.1):
            b = dst_to_src(d["box"], tf)
            if b[2] - b[0] < 2 or b[3] - b[1] < 2:
                continue
            dets.append(dict(box=[b[0] / W, b[1] / H, b[2] / W, b[3] / H], classId=int(d["classId"]), score=round(float(d["score"]), 4)))
        tracks = trk.update(dets, t * 1000)
        shown = [dict(id=int(tr["id"]), box=[round(float(v), 5) for v in tr["box"]], label=int(tr["label"]), score=round(float(tr["score"]), 4)) for tr in tracks]
        frames.append(dict(fi=fi, t=round(t, 3), dets=dets, tracks=shown))
        g = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (64, 36)).astype(np.float32)
        ids = {s["id"] for s in shown}
        d_scene = float(np.abs(g - last_thumb).mean()) if last_thumb is not None else 1e9
        if len(kfs) < max_kf and ((d_scene >= diff and t - last_kf_t >= min_gap) or t - last_kf_t >= max(max_gap, 2 * min_gap) or (ids - last_ids and t - last_kf_t >= 1.5 * min_gap)):
            s = 960 / max(W, H) if max(W, H) > 960 else 1.0
            im = cv2.resize(frame, (int(W * s), int(H * s))) if s < 1 else frame
            name = f"kf_{fi:06d}.jpg"
            cv2.imwrite(f"{out}/keyframes/{name}", im, [cv2.IMWRITE_JPEG_QUALITY, 90])
            kfs.append(dict(file=name, fi=fi, t=round(t, 3), scene_diff=round(min(d_scene, 999.0), 2), n_g3=len(dets), track_ids=sorted(ids)))
            last_thumb, last_kf_t, last_ids = g, t, ids
    json.dump(dict(src=path, w=W, h=H, src_fps=src_fps, sample_fps=src_fps / step, det="G3 control ONNX raw 480 (score>=0.1)",
                   tracker="ByteTrack b15 (adapter)", frames=frames), open(f"{out}/frames.json", "w"))
    json.dump(dict(params=dict(fps=fps, diff=diff, max_gap=max_gap, max_kf=max_kf, max_s=max_s), keyframes=kfs), open(f"{out}/keyframes.json", "w"), indent=1)
    return len(frames), len(kfs), round(time.time() - t0, 1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips-dir", required=True); ap.add_argument("--out", required=True); ap.add_argument("--ids", nargs="*")
    ap.add_argument("--fps", type=float, default=4.0); ap.add_argument("--max-s", type=float, default=180.0)
    a = ap.parse_args()
    det = sess(DET)
    paths = sorted(glob.glob(f"{a.clips_dir}/*.webm") + glob.glob(f"{a.clips_dir}/*.ogv") + glob.glob(f"{a.clips_dir}/*.mp4"))
    for p in paths:
        cid = os.path.splitext(os.path.basename(p))[0]
        if a.ids and cid not in a.ids:
            continue
        o = f"{a.out}/{cid}"
        if os.path.exists(f"{o}/keyframes.json"):
            continue
        try:
            print(cid, *run(p, o, det, fps=a.fps, max_s=a.max_s), flush=True)
        except Exception as e:
            print("ERR", cid, repr(e), flush=True)
