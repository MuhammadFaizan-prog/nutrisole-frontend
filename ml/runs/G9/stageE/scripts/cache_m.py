"""Cache G3 detections (raw 480 letterbox, class-wise NMS 0.7, floor 0.01 so raw AP50 can be computed; display uses >= 0.35) on M-DEV
images. The source frame is the downloaded Commons rendition (1280 px wide). Usage: cache_m.py IDS_JSON OUT.json [onnx]"""
import os, sys, json, cv2, onnxruntime as ort
R = "/workspace/work/nutrisole"; sys.path.insert(0, f"{R}/ml/eval"); sys.path.insert(0, f"{R}/ml")
from geometry import letterbox, dst_to_src, decode
ids = json.load(open(sys.argv[1])); OUT = sys.argv[2]
DET = sys.argv[3] if len(sys.argv) > 3 else "/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx"
so = ort.SessionOptions(); so.intra_op_num_threads = 2; s = ort.InferenceSession(DET, so, providers=["CPUExecutionProvider"]); di = s.get_inputs()[0].name
res = json.load(open(OUT)) if os.path.exists(OUT) else {}
for i in ids:
    if i in res: continue
    fr = cv2.imread(f"/workspace/work/cv/g9e/commons/img/{i}.jpg"); H, W = fr.shape[:2]; x, tf = letterbox(fr, 480); o = s.run(None, {di: x})[0]; ds = []
    for d in decode(o, "raw", 0.01):
        b = dst_to_src(d["box"], tf)
        if b[2] - b[0] < 2 or b[3] - b[1] < 2: continue
        ds.append([round(b[0] / W, 5), round(b[1] / H, 5), round(b[2] / W, 5), round(b[3] / H, 5), int(d["classId"]), round(float(d["score"]), 4)])
    res[i] = dict(w=W, h=H, dets=ds)
json.dump(res, open(OUT, "w")); print("cached", len(res))
