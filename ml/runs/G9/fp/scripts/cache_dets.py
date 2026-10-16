"""G9 Stage A: cache G3 (raw 480, class-wise NMS 0.7) detections >= 0.35 for DEV data:
val stills (n=402) and the synthetic DEV det / neg clips (every frame). Threshold / tracker arms are then replayed
offline from this cache (detector output is deterministic; post-processing is the only thing that changes)."""
import os, sys, json, time
import cv2, numpy as np, onnxruntime as ort
R = "/workspace/work/nutrisole"; sys.path.insert(0, f"{R}/ml/eval"); sys.path.insert(0, f"{R}/ml")
from geometry import letterbox, dst_to_src, decode
DET = "/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx"; OUT = "/workspace/work/cv/g9fp"; FLOOR = 0.35
so = ort.SessionOptions(); so.intra_op_num_threads = 2
s = ort.InferenceSession(DET, so, providers=["CPUExecutionProvider"]); di = s.get_inputs()[0].name
def det(frame):
    H, W = frame.shape[:2]; x, tf = letterbox(frame, 480); o = s.run(None, {di: x})[0]; ds = []
    for d in decode(o, "raw", FLOOR):
        b = dst_to_src(d["box"], tf)
        if b[2] - b[0] < 2 or b[3] - b[1] < 2: continue
        ds.append([round(b[0] / W, 5), round(b[1] / H, 5), round(b[2] / W, 5), round(b[3] / H, 5), int(d["classId"]), round(float(d["score"]), 4)])
    return ds
t0 = time.time()
if not os.path.exists(f"{OUT}/val_dets.json"):
    rows = []
    for l in open("/workspace/work/cv/g3data/det_v3/val.txt"):
        p = l.strip(); lp = p.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"
        gt = []
        if os.path.exists(lp):
            for ln in open(lp):
                v = ln.split()
                if len(v) >= 5:
                    c, cx, cy, w, h = int(v[0]), *map(float, v[1:5]); gt.append([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, c])
        rows.append(dict(img=os.path.basename(p), gt=gt, dets=det(cv2.imread(p))))
    json.dump(rows, open(f"{OUT}/val_dets.json", "w")); print("val done", time.time() - t0, flush=True)
for kind in ("det", "neg"):
    op = f"{OUT}/devclip_{kind}_dets.json"
    if os.path.exists(op): continue
    cap = cv2.VideoCapture(f"/workspace/work/cv/g3clips_dev/{kind}_clip.mp4"); fr = []
    while True:
        ok, f = cap.read()
        if not ok: break
        fr.append(det(f))
    json.dump(fr, open(op, "w")); print(kind, len(fr), time.time() - t0, flush=True)
print("DONE", flush=True)
