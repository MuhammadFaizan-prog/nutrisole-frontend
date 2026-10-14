"""Stage F feasibility arm R (never selectable): resolution / crop strategies on M-DEV v2, with CPU and memory cost.
Modes: base480 (deployed letterbox 480), full640 (letterbox 640, needs a 640-input ONNX), tile480 (480 full frame + 2x2 overlapping
tiles at 480 = 5 passes, class-wise NMS 0.7 merge). Detections cached at floor 0.01 in eval_f format; latency per frame = preprocess +
all passes + decode/merge (ONNX Runtime CPU, 2 threads); peak RSS from getrusage. Usage: feas_r.py MODE ONNX OUT_DETS.json OUT_COST.json"""
import os, sys, json, time, resource, cv2, numpy as np, onnxruntime as ort
R = "/workspace/work/nutrisole"; sys.path.insert(0, f"{R}/ml/eval"); sys.path.insert(0, f"{R}/ml")
from geometry import letterbox, dst_to_src, decode
MODE, M, OUT, COST = sys.argv[1:5]
so = ort.SessionOptions(); so.intra_op_num_threads = 2; s = ort.InferenceSession(M, so, providers=["CPUExecutionProvider"]); di = s.get_inputs()[0].name
SZ = 640 if MODE == "full640" else 480
ids = json.load(open("/workspace/work/cv/g9f/mdev_ids.json")); res = {}; lat = []
def run(img, ox=0, oy=0):
    x, tf = letterbox(img, SZ); o = s.run(None, {di: x})[0]; out = []
    for d in decode(o, "raw", 0.01):
        b = dst_to_src(d["box"], tf); out.append([b[0] + ox, b[1] + oy, b[2] + ox, b[3] + oy, int(d["classId"]), float(d["score"])])
    return out
def nms(ds, thr=0.7):
    ds = sorted(ds, key=lambda d: -d[5]); keep = []
    for d in ds:
        ok = True
        for k in keep:
            if k[4] != d[4]: continue
            ix = max(0, min(d[2], k[2]) - max(d[0], k[0])); iy = max(0, min(d[3], k[3]) - max(d[1], k[1])); i = ix * iy
            if i / ((d[2] - d[0]) * (d[3] - d[1]) + (k[2] - k[0]) * (k[3] - k[1]) - i + 1e-9) > thr: ok = False; break
        if ok: keep.append(d)
    return keep
run(np.zeros((480, 640, 3), np.uint8))  # warm-up
for i in ids:
    fr = cv2.imread(f"/workspace/work/cv/g9e/commons/img/{i}.jpg"); H, W = fr.shape[:2]; t = time.perf_counter()
    if MODE == "tile480":
        ds = run(fr); tw, th = int(W * 0.55), int(H * 0.55)
        for ty in (0, H - th):
            for tx in (0, W - tw): ds += run(fr[ty:ty + th, tx:tx + tw], tx, ty)
        ds = nms(ds)
    else: ds = run(fr)
    lat.append((time.perf_counter() - t) * 1000)
    res[i] = dict(w=W, h=H, dets=[[round(d[0] / W, 5), round(d[1] / H, 5), round(d[2] / W, 5), round(d[3] / H, 5), d[4], round(d[5], 4)] for d in ds if d[2] - d[0] >= 2 and d[3] - d[1] >= 2])
json.dump(res, open(OUT, "w"))
c = dict(mode=MODE, onnx=os.path.basename(M), frames=len(lat), p50_ms=round(float(np.percentile(lat, 50)), 1), p95_ms=round(float(np.percentile(lat, 95)), 1),
         peak_rss_mb=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), threads=2, note="sandbox CPU (2 vCPU), ONNX Runtime; same session for all modes")
json.dump(c, open(COST, "w")); print(c)
