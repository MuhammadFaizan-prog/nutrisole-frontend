"""Interleaved CPU latency for feasibility arm R (same frames, same process, round-robin per frame): base480 / full640 / tile480 (5 passes).
Detector floor 0.35 (deployed), class-wise NMS, no guard. 2 threads. Usage: lat_feas.py N OUT.json ONNX480 ONNX640"""
import sys, time, json, cv2, numpy as np, onnxruntime as ort
R = "/workspace/work/nutrisole"; sys.path.insert(0, f"{R}/ml/eval"); sys.path.insert(0, f"{R}/ml")
from geometry import letterbox, dst_to_src, decode
N, OUT, M4, M6 = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]; so = ort.SessionOptions(); so.intra_op_num_threads = 2
s4 = ort.InferenceSession(M4, so, providers=["CPUExecutionProvider"]); s6 = ort.InferenceSession(M6, so, providers=["CPUExecutionProvider"])
def run(s, sz, img):
    x, tf = letterbox(img, sz); o = s.run(None, {s.get_inputs()[0].name: x})[0]; return [dst_to_src(d["box"], tf) for d in decode(o, "raw", 0.35)]
ids = json.load(open("/workspace/work/cv/g9f/mdev_ids.json"))[:N]; T = {"base480": [], "full640": [], "tile480": []}
for k in range(2):
    for i in ids:
        fr = cv2.imread(f"/workspace/work/cv/g9e/commons/img/{i}.jpg"); H, W = fr.shape[:2]
        t = time.perf_counter(); run(s4, 480, fr); T["base480"].append(1000 * (time.perf_counter() - t))
        t = time.perf_counter(); run(s6, 640, fr); T["full640"].append(1000 * (time.perf_counter() - t))
        t = time.perf_counter(); run(s4, 480, fr); tw, th = int(W * .55), int(H * .55)
        for ty in (0, H - th):
            for tx in (0, W - tw): run(s4, 480, fr[ty:ty + th, tx:tx + tw])
        T["tile480"].append(1000 * (time.perf_counter() - t))
res = {m: dict(p50=round(float(np.percentile(v[N:], 50)), 1), p95=round(float(np.percentile(v[N:], 95)), 1), n=len(v) - N) for m, v in T.items()}
res["note"] = "second pass over the frames only (first pass = warm-up); sandbox 2 vCPU ONNX Runtime"; json.dump(res, open(OUT, "w"), indent=1); print(res)
