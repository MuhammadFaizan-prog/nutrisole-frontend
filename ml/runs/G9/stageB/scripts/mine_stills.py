"""G9 Stage B: G3 as deployed (raw 480, floor 0.35, area guard) on the Commons hard-negative stills; writes boxes + pHash."""
import os, sys, json, glob
import cv2, onnxruntime as ort, imagehash
from PIL import Image
R = "/workspace/work/nutrisole"; sys.path.insert(0, f"{R}/ml/eval"); sys.path.insert(0, f"{R}/ml")
from geometry import letterbox, dst_to_src, decode
from scene_guard import scene_guard
DET = sys.argv[2] if len(sys.argv) > 2 else "/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx"
D = "/workspace/work/cv/g9b/commons"; OUT = sys.argv[1]
so = ort.SessionOptions(); so.intra_op_num_threads = 2
s = ort.InferenceSession(DET, so, providers=["CPUExecutionProvider"]); di = s.get_inputs()[0].name
res = json.load(open(OUT)) if os.path.exists(OUT) else {}
for p in sorted(glob.glob(f"{D}/img/*.jpg")):
    f = os.path.basename(p)
    if f in res: continue
    fr = cv2.imread(p)
    if fr is None: res[f] = dict(error="unreadable"); continue
    H, W = fr.shape[:2]; x, tf = letterbox(fr, 480); o = s.run(None, {di: x})[0]; ds = []
    for d in decode(o, "raw", 0.35):
        b = dst_to_src(d["box"], tf)
        if b[2] - b[0] < 2 or b[3] - b[1] < 2: continue
        ds.append(dict(box=[b[0] / W, b[1] / H, b[2] / W, b[3] / H], classId=int(d["classId"]), score=float(d["score"])))
    g = scene_guard(ds, maxSameClass=0, minAreaFrac=0.01)
    res[f] = dict(w=W, h=H, phash=str(imagehash.phash(Image.open(p))), boxes=[[round(v, 4) for v in d["box"]] + [d["classId"], round(d["score"], 4)] for d in g])
json.dump(res, open(OUT, "w")); print(len(res), "imgs;", sum(1 for v in res.values() if v.get("boxes")), "with a box")
