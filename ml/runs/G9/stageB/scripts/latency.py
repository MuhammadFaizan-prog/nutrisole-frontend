"""Sandbox CPU per-frame latency, interleaved per frame (same machine, same frames): full app step = detector (raw 480) + area guard +
tracker (+ selective verifier for B2). DEV det clip frames 0..N, then DEV neg clip frames (verifier rarely fires there). 2 threads."""
import sys, os, time, json, cv2, numpy as np, onnxruntime as ort
R = "/workspace/work/nutrisole"; sys.path.insert(0, f"{R}/ml/eval"); sys.path.insert(0, f"{R}/ml"); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geometry import letterbox, dst_to_src, decode
from scene_guard import scene_guard
from tracker import IouTracker
from stageb_pipe import Verifier, VerifiedTracker
N = int(sys.argv[1]) if len(sys.argv) > 1 else 250
so = ort.SessionOptions(); so.intra_op_num_threads = 2
S = {"G3": ort.InferenceSession("/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx", so, providers=["CPUExecutionProvider"]),
     "B1": ort.InferenceSession("/workspace/work/cv/g9b/kout/B1_raw480.onnx", so, providers=["CPUExecutionProvider"])}
V = Verifier("/workspace/work/cv/g9b/vout/verifier_mnv3s_128.onnx", 2)
arms = {"B0": ("G3", IouTracker()), "B1": ("B1", IouTracker()), "B2": ("G3", VerifiedTracker(V, 0.05))}
def step(arm, fr, t):
    m, trk = arms[arm]; s = S[m]; H, W = fr.shape[:2]; x, tf = letterbox(fr, 480); o = s.run(None, {s.get_inputs()[0].name: x})[0]; ds = []
    for d in decode(o, "raw", 0.35):
        b = dst_to_src(d["box"], tf)
        if b[2] - b[0] < 2 or b[3] - b[1] < 2: continue
        ds.append(dict(box=[b[0] / W, b[1] / H, b[2] / W, b[3] / H], classId=d["classId"], score=d["score"]))
    ds = scene_guard(ds, maxSameClass=0, minAreaFrac=0.01)
    return trk.update(ds, t, fr) if arm == "B2" else trk.update(ds, t)
lat = {a: [] for a in arms}; cap = cv2.VideoCapture("/workspace/work/cv/g3clips_dev/det_clip.mp4"); i = 0
for _ in range(5):
    ok, fr = cap.read(); [step(a, fr, 0) for a in arms]
while i < N:
    ok, fr = cap.read()
    if not ok: break
    for a in (list(arms) if i % 2 == 0 else list(arms)[::-1]):
        t0 = time.perf_counter(); step(a, fr, 1000 * i / 15); lat[a].append(1000 * (time.perf_counter() - t0))
    i += 1
out = {a: dict(p50=round(float(np.percentile(v, 50)), 1), p95=round(float(np.percentile(v, 95)), 1), n=len(v)) for a, v in lat.items()}
out["B2_verifier_calls"] = V.calls; out["frames"] = i
json.dump(out, open(f"{R}/ml/runs/G9/stageB/latency_sandbox.json", "w"), indent=1); print(out)
