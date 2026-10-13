# Interleaved ONNX CPU latency (letterbox 480 + session.run), same frames for every model. p50/p95 ms.
import sys, glob, json, time, numpy as np, cv2, onnxruntime as ort
models = dict(a.split("=", 1) for a in sys.argv[2:]); out = sys.argv[1]
fs = sorted(glob.glob("/workspace/work/cv/g3data/det_v3/det/images/val/*.jpg"))[:100]
S = {k: ort.InferenceSession(v, providers=["CPUExecutionProvider"]) for k, v in models.items()}
def prep(f):
    im = cv2.imread(f); h, w = im.shape[:2]; r = 480 / max(h, w); im = cv2.resize(im, (int(w * r), int(h * r)))
    c = np.full((480, 480, 3), 114, np.uint8); c[:im.shape[0], :im.shape[1]] = im
    return (c[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255.0).copy()
T = {k: [] for k in S}
for k, s in S.items():  # warmup
    for _ in range(5): s.run(None, {s.get_inputs()[0].name: prep(fs[0])})
for rep in range(2):
    for f in fs:
        x = prep(f)
        for k, s in (S.items() if rep == 0 else reversed(list(S.items()))):
            t = time.perf_counter(); s.run(None, {s.get_inputs()[0].name: x}); T[k].append((time.perf_counter() - t) * 1000)
res = {k: dict(n=len(v), p50=round(float(np.percentile(v, 50)), 2), p95=round(float(np.percentile(v, 95)), 2), mean=round(float(np.mean(v)), 2)) for k, v in T.items()}
res["note"] = "sandbox CPU (2 cores aarch64, shared), onnxruntime CPU EP, 100 val frames x 2 passes, model order alternated per pass, det session.run only (letterbox excluded)"
json.dump(res, open(out, "w"), indent=1); print(res)
