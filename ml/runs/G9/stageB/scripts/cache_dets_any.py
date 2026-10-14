"""Cache detections (raw 480, class-wise NMS 0.7, floor 0.35; same decode as ml/runs/G9/fp/scripts/cache_dets.py) of any detector ONNX for:
val stills (val_dets.json), DEV det / neg clips (devclip_{det,neg}_dets.json, every frame). Resumable within a time budget.
Usage: cache_dets_any.py DET.onnx OUTDIR [budget_s]"""
import os, sys, json, time
import cv2, onnxruntime as ort
R = "/workspace/work/nutrisole"; sys.path.insert(0, f"{R}/ml/eval"); sys.path.insert(0, f"{R}/ml")
from geometry import letterbox, dst_to_src, decode
DET, OUT = sys.argv[1], sys.argv[2]; B = float(sys.argv[3]) if len(sys.argv) > 3 else 100; os.makedirs(OUT, exist_ok=True); t0 = time.time()
so = ort.SessionOptions(); so.intra_op_num_threads = 2
s = ort.InferenceSession(DET, so, providers=["CPUExecutionProvider"]); di = s.get_inputs()[0].name
def det(frame):
    H, W = frame.shape[:2]; x, tf = letterbox(frame, 480); o = s.run(None, {di: x})[0]; ds = []
    for d in decode(o, "raw", 0.35):
        b = dst_to_src(d["box"], tf)
        if b[2] - b[0] < 2 or b[3] - b[1] < 2: continue
        ds.append([round(b[0] / W, 5), round(b[1] / H, 5), round(b[2] / W, 5), round(b[3] / H, 5), int(d["classId"]), round(float(d["score"]), 4)])
    return ds
def over(): return time.time() - t0 > B
if not os.path.exists(f"{OUT}/val_dets.json"):
    part = f"{OUT}/val_dets.part.json"; rows = json.load(open(part)) if os.path.exists(part) else []
    lines = [l.strip() for l in open("/workspace/work/cv/g3data/det_v3/val.txt")]
    for p in lines[len(rows):]:
        lp = p.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"; gt = []
        if os.path.exists(lp):
            for ln in open(lp):
                v = ln.split()
                if len(v) >= 5: c, cx, cy, w, h = int(v[0]), *map(float, v[1:5]); gt.append([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, c])
        rows.append(dict(img=os.path.basename(p), gt=gt, dets=det(cv2.imread(p))))
        if over(): json.dump(rows, open(part, "w")); print("budget val", len(rows)); sys.exit(0)
    json.dump(rows, open(f"{OUT}/val_dets.json", "w")); os.path.exists(part) and os.remove(part); print("val done")
for kind in ("det", "neg"):
    fo = f"{OUT}/devclip_{kind}_dets.json"
    if os.path.exists(fo): continue
    part = fo.replace(".json", ".part.json"); rows = json.load(open(part)) if os.path.exists(part) else []
    cap = cv2.VideoCapture(f"/workspace/work/cv/g3clips_dev/{kind}_clip.mp4"); n = len(rows)
    for _ in range(n): cap.grab()
    while True:
        ok, fr = cap.read()
        if not ok: break
        rows.append(det(fr))
        if over(): json.dump(rows, open(part, "w")); print("budget", kind, len(rows)); sys.exit(0)
    json.dump(rows, open(fo, "w")); os.path.exists(part) and os.remove(part); print(kind, "done", len(rows))
print("ALL DONE")
