"""Cache G3 detections (raw 480 letterbox, class-wise NMS 0.7, floor 0.35, source-normalised; identical decode to
ml/runs/G9/stageB/scripts/cache_dets_any.py) for every frame of the SYNTHETIC probe clip. Resumable. Usage: cache_probe.py DIR [budget_s]"""
import os, sys, json, time, cv2, onnxruntime as ort
R = "/workspace/work/nutrisole"; sys.path.insert(0, f"{R}/ml/eval"); sys.path.insert(0, f"{R}/ml")
from geometry import letterbox, dst_to_src, decode
D = sys.argv[1]; B = float(sys.argv[2]) if len(sys.argv) > 2 else 100; t0 = time.time()
so = ort.SessionOptions(); so.intra_op_num_threads = 2
s = ort.InferenceSession("/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx", so, providers=["CPUExecutionProvider"]); di = s.get_inputs()[0].name
def det(frame):
    H, W = frame.shape[:2]; x, tf = letterbox(frame, 480); o = s.run(None, {di: x})[0]; ds = []
    for d in decode(o, "raw", 0.35):
        b = dst_to_src(d["box"], tf)
        if b[2] - b[0] < 2 or b[3] - b[1] < 2: continue
        ds.append([round(b[0] / W, 5), round(b[1] / H, 5), round(b[2] / W, 5), round(b[3] / H, 5), int(d["classId"]), round(float(d["score"]), 4)])
    return ds
fo = f"{D}/probe_dets.json"; part = fo.replace(".json", ".part.json")
if os.path.exists(fo): print("ALL DONE"); sys.exit(0)
rows = json.load(open(part)) if os.path.exists(part) else []
cap = cv2.VideoCapture(f"{D}/probe_clip.mp4")
for _ in range(len(rows)): cap.grab()
while True:
    ok, fr = cap.read()
    if not ok: break
    rows.append(det(fr))
    if time.time() - t0 > B: json.dump(rows, open(part, "w")); print("budget", len(rows)); sys.exit(0)
json.dump(rows, open(fo, "w")); os.path.exists(part) and os.remove(part); print("ALL DONE", len(rows))
