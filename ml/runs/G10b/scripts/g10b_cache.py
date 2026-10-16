"""G10b: cache raw detector predictions ONCE per (model, image) so every guard / fusion analysis replays the same boxes (inference-only,
no training). Same predict settings as ml/eval/g10_ext_bench.py: Ultralytics predict, conf 0.001, NMS iou 0.7 (single-label), max_det 300.
Stores ALL native classes (incl. henningheyen's 49 unsupported LVIS classes) so mapping is applied later.
  python g10b_cache.py --model best.pt --imgsz 480 --lists val.txt negdev.txt --out cache.pkl
"""
import argparse, pickle, time, os
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--model", required=True); ap.add_argument("--imgsz", type=int, required=True)
ap.add_argument("--lists", nargs="+", required=True); ap.add_argument("--out", required=True)
a = ap.parse_args()
from ultralytics import YOLO
m = YOLO(a.model); out = dict(model=a.model, imgsz=a.imgsz, names=dict(m.names), preds={})
if os.path.exists(a.out): out = pickle.load(open(a.out, "rb"))
files = [l.strip() for L in a.lists for l in open(L) if l.strip()]
for i, f in enumerate(files):
    if f in out["preds"]: continue
    t0 = time.perf_counter(); r = m.predict(f, imgsz=a.imgsz, conf=0.001, iou=0.7, max_det=300, verbose=False, device="cpu")[0]
    ms = (time.perf_counter() - t0) * 1e3; H, W = r.orig_shape
    out["preds"][f] = dict(xyxy=r.boxes.xyxy.numpy().astype(np.float32), conf=r.boxes.conf.numpy().astype(np.float32), cls=r.boxes.cls.numpy().astype(np.int16), W=W, H=H, ms=ms)
    if i % 100 == 99: pickle.dump(out, open(a.out, "wb")); print(i + 1, flush=True)
pickle.dump(out, open(a.out, "wb")); print("done", len(out["preds"]))
