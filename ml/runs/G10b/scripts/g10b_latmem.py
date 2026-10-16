"""G10b: ONNX Runtime CPU latency + peak memory per configuration, each in a FRESH process (peak RSS = ru_maxrss of that process).
Sandbox CPU (2 vCPU aarch64, shared; not a phone). intra_op 2 threads, batch 1, 5 warm-up + N timed runs on real det_v3 val images
(letterbox + normalisation included in 'total'; 'model' = session.run only). Config 'G3+v8m' runs both sessions sequentially per frame.
  python g10b_latmem.py CONFIG N OUT.json      CONFIG in {G3, v8m, G3+v8m}
"""
import json, resource, sys, time
import cv2, numpy as np, onnxruntime as ort
M = {"G3": ("/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx", 480), "v8m": ("/workspace/work/cv/g10/models/henning_v8m_640.onnx", 640)}
cfg, n, outp = sys.argv[1], int(sys.argv[2]), sys.argv[3]
rss0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
so = ort.SessionOptions(); so.intra_op_num_threads = 2; so.inter_op_num_threads = 1
S = {k: (ort.InferenceSession(M[k][0], so, providers=["CPUExecutionProvider"]), M[k][1]) for k in cfg.split("+")}
imgs = [cv2.imread(l.strip()) for l in open("/workspace/work/cv/g10/val.txt").readlines()[:20]]
def prep(im, s):
    h, w = im.shape[:2]; r = s / max(h, w); nw, nh = round(w * r), round(h * r); c = np.full((s, s, 3), 114, np.uint8)
    c[(s - nh) // 2:(s - nh) // 2 + nh, (s - nw) // 2:(s - nw) // 2 + nw] = cv2.resize(im, (nw, nh)); return (c[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255)
tot, mod = [], []
for i in range(n + 5):
    im = imgs[i % len(imgs)]; t0 = time.perf_counter(); tm = 0
    for k, (s, sz) in S.items():
        x = prep(im, sz); t1 = time.perf_counter(); s.run(None, {s.get_inputs()[0].name: x}); tm += time.perf_counter() - t1
    if i >= 5: tot.append((time.perf_counter() - t0) * 1e3); mod.append(tm * 1e3)
pc = lambda v, q: round(float(np.percentile(v, q)), 1)
r = dict(config=cfg, n=n, device="sandbox CPU 2 vCPU aarch64 (shared), ORT CPU EP, 2 threads", model_ms_p50=pc(mod, 50), model_ms_p95=pc(mod, 95),
         total_ms_p50=pc(tot, 50), total_ms_p95=pc(tot, 95), peak_rss_mb=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), rss_before_sessions_mb=round(rss0 / 1024, 1),
         onnx_mb={k: round(__import__("os").path.getsize(M[k][0]) / 1e6, 1) for k in S})
json.dump(r, open(outp, "w"), indent=1); print(r)
