"""Sandbox CPU per-frame latency, interleaved per frame (same frames, same session): detector (raw 480) + guard + IouTracker.
Usage: latency_d.py N OUT.json NAME:ONNX:GUARD [...]   GUARD in g1|g05|g025|ssf50|ssf60. 2 threads, DEV det clip frames 0..N-1."""
import sys, time, json, cv2, numpy as np, onnxruntime as ort
R = "/workspace/work/nutrisole"; sys.path.insert(0, f"{R}/ml/eval"); sys.path.insert(0, f"{R}/ml")
from geometry import letterbox, dst_to_src, decode
from scene_guard import scene_guard
from tracker import IouTracker
N, OUT = int(sys.argv[1]), sys.argv[2]; so = ort.SessionOptions(); so.intra_op_num_threads = 2
MAF = {"g1": 0.01, "g05": 0.005, "g025": 0.0025, "ssf50": 0.0025, "ssf60": 0.0025}; SSF = {"ssf50": 0.5, "ssf60": 0.6}
A = []
for spec in sys.argv[3:]:
    n, m, g = spec.split(":"); A.append((n, ort.InferenceSession(m, so, providers=["CPUExecutionProvider"]), g, IouTracker(), []))
cap = cv2.VideoCapture("/workspace/work/cv/g3clips_dev/det_clip.mp4"); fi = 0
while fi < N:
    ok, fr = cap.read()
    if not ok: break
    H, W = fr.shape[:2]
    for n, s, g, trk, ms in A:
        t = time.perf_counter(); x, tf = letterbox(fr, 480); o = s.run(None, {s.get_inputs()[0].name: x})[0]; ds = []
        for d in decode(o, "raw", 0.35):
            b = dst_to_src(d["box"], tf); ds.append(dict(box=[b[0] / W, b[1] / H, b[2] / W, b[3] / H], classId=d["classId"], score=d["score"]))
        ds = scene_guard(ds, maxSameClass=0, minAreaFrac=MAF[g])
        if g in SSF: ds = [d for d in ds if (d["box"][2] - d["box"][0]) * (d["box"][3] - d["box"][1]) >= 0.01 or d["score"] >= SSF[g]]
        trk.update(ds, fi * 66.7); ms.append(1000 * (time.perf_counter() - t))
    fi += 1
res = {n: dict(guard=g, p50=round(float(np.percentile(ms[10:], 50)), 1), p95=round(float(np.percentile(ms[10:], 95)), 1), n=len(ms) - 10) for n, s, g, trk, ms in A}
res["frames"] = fi; json.dump(res, open(OUT, "w"), indent=1); print(res)
