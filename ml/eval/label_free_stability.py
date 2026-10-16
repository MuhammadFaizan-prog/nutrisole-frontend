"""G6.4 label-free stability proxy on real (unlabelled) web clips: IouTracker vs ByteTrack with the same detector.
No ground truth -> these are STABILITY numbers only (track births/min, shown-track lifetime, label flips per shown
track-minute, fraction of frames with any box). Fewer births / longer lives can also mean hidden misses, so this never
decides adoption alone. Detector + scene guard + decode exactly as video_gauntlet.py; frames read every --stride and capped
at --max-s seconds per clip; tracker reset per clip.
usage: python ml/eval/label_free_stability.py --det X.onnx --clips a.webm b.webm ... --out out.json [--stride 2 --max-s 40]"""
import argparse, json, os, sys, time, collections
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from video_gauntlet import sess, letterbox, decode, dst_to_src, scene_guard, RUBRIC, DEFAULT_GUARD  # noqa: E402
from tracker import IouTracker  # noqa: E402
from bytetrack_adapter import ByteTrackTracker  # noqa: E402


def run(det, path, kind, params, imgsz, stride, max_s):
    cap = cv2.VideoCapture(path); trk = ByteTrackTracker(**params) if kind == "bytetrack" else IouTracker(**params)
    thr = min(RUBRIC["detectorMinScore"], trk.p["track_low_thresh"]) if kind == "bytetrack" else RUBRIC["detectorMinScore"]
    di = det.get_inputs()[0].name; fi = 0; shown_frames = 0; n = 0; first = {}; last = {}; labels = collections.defaultdict(list); lat = []; t_end = 0.0
    while True:
        ok, fr = cap.read()
        if not ok: break
        t = cap.get(cv2.CAP_PROP_POS_MSEC)
        if t > max_s * 1000: break
        fi += 1; t_end = t
        if (fi - 1) % stride: continue
        H, W = fr.shape[:2]; t0 = time.perf_counter()
        x, tf = letterbox(fr, imgsz); out = det.run(None, {di: x})[0]; dets = []
        for d in decode(out, "raw", thr):
            b = dst_to_src(d["box"], tf)
            if b[2] - b[0] < 2 or b[3] - b[1] < 2: continue
            dets.append(dict(box=[b[0] / W, b[1] / H, b[2] / W, b[3] / H], classId=d["classId"], score=d["score"]))
        dets = scene_guard(dets, **DEFAULT_GUARD)  # same guard as the G3 control gauntlet (rule 2 off, minAreaFrac 0.01)
        tr = trk.update(dets, t); lat.append(1000 * (time.perf_counter() - t0)); n += 1
        if tr: shown_frames += 1
        for o in tr:
            first.setdefault(o["id"], t); last[o["id"]] = t; labels[o["id"]].append(o["label"])
    minutes = max(1e-9, t_end / 60000)  # clip time actually covered
    dur = sum(max(0, last[k] - first[k]) for k in first) / 1000
    flips = sum(sum(1 for a, b in zip(v, v[1:]) if a != b) for v in labels.values())
    return dict(frames=n, covered_s=round(t_end / 1000, 1), shown_tracks=len(first), births_per_min=round(len(first) / minutes, 2),
                mean_track_life_s=round(dur / max(1, len(first)), 2), label_flips_per_track_min=round(flips / max(1e-9, dur / 60), 3),
                frac_frames_with_box=round(shown_frames / max(1, n), 3), lat_p50_ms=round(float(np.median(lat)), 1) if lat else None)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--det", required=True); ap.add_argument("--clips", nargs="+", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--imgsz", type=int, default=480); ap.add_argument("--stride", type=int, default=2)
    ap.add_argument("--max-s", type=float, default=40); ap.add_argument("--bt", default='{"track_buffer": 8}')
    a = ap.parse_args(); det = sess(a.det); res = dict(det=a.det, imgsz=a.imgsz, stride=a.stride, max_s=a.max_s, device="sandbox CPU onnxruntime", clips={})
    for c in a.clips:
        res["clips"][os.path.basename(c)] = {k: run(det, c, k, (json.loads(a.bt) if k == "bytetrack" else {}), a.imgsz, a.stride, a.max_s) for k in ["iou", "bytetrack"]}
        print(c, json.dumps(res["clips"][os.path.basename(c)]), flush=True)
    agg = {}
    for k in ["iou", "bytetrack"]:
        rows = [v[k] for v in res["clips"].values()]
        agg[k] = {m: round(float(np.mean([r[m] for r in rows if r[m] is not None])), 3) for m in ["births_per_min", "mean_track_life_s", "label_flips_per_track_min", "frac_frames_with_box", "lat_p50_ms"]}
        agg[k]["n_clips"] = len(rows)
    res["mean_over_clips"] = agg; json.dump(res, open(a.out, "w"), indent=1); print(json.dumps(agg))
