"""G9 Stage D Exp1: box PROPOSALS for collected high-res images by the G3 weights at their training size (640) on overlapping tiles
(objects appear large in a tile) + one whole-image pass. Proposals are only a starting point: every image is agent-verified on a sheet
before use. Resumable. Usage: teacher_tiles.py IMGDIR OUT.json [budget_s]"""
import os, sys, json, time, glob, cv2, numpy as np, onnxruntime as ort
R = "/workspace/work/nutrisole"; sys.path.insert(0, f"{R}/ml/eval"); sys.path.insert(0, f"{R}/ml")
from geometry import letterbox, dst_to_src, decode
D, OUT = sys.argv[1], sys.argv[2]; B = float(sys.argv[3]) if len(sys.argv) > 3 else 100; t0 = time.time()
so = ort.SessionOptions(); so.intra_op_num_threads = 2
s = ort.InferenceSession("/workspace/work/cv/g9c/det_yolo11n_g3_at640_raw.onnx", so, providers=["CPUExecutionProvider"]); di = s.get_inputs()[0].name
def run(im, conf=0.30):
    x, tf = letterbox(im, 640); return [(dst_to_src(d["box"], tf), d["classId"], d["score"]) for d in decode(s.run(None, {di: x})[0], "raw", conf)]
def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i; return i / u if u > 0 else 0
res = json.load(open(OUT)) if os.path.exists(OUT) else {}
for p in sorted(glob.glob(f"{D}/*.jpg")):
    k = os.path.basename(p)
    if k in res: continue
    im = cv2.imread(p)
    if im is None: res[k] = dict(err="read"); continue
    H, W = im.shape[:2]; T, O = 640, 200; cand = [(b, c, sc, "whole") for b, c, sc in run(im)]
    xs = list(range(0, max(1, W - T), T - O)) + [max(0, W - T)]; ys = list(range(0, max(1, H - T), T - O)) + [max(0, H - T)]
    for y0 in sorted(set(ys)):
        for x0 in sorted(set(xs)):
            for b, c, sc in run(im[y0:y0 + T, x0:x0 + T]):
                gb = [b[0] + x0, b[1] + y0, b[2] + x0, b[3] + y0]
                edge = (b[0] < 3 and x0 > 0) or (b[1] < 3 and y0 > 0) or (b[2] > T - 3 and x0 + T < W) or (b[3] > T - 3 and y0 + T < H)
                if not edge: cand.append((gb, c, sc, "tile"))
    cand.sort(key=lambda r: -r[2]); keep = []
    for r in cand:
        if all(not (q[1] == r[1] and iou(q[0], r[0]) > 0.45) for q in keep): keep.append(r)
    res[k] = dict(W=W, H=H, boxes=[[round(b[0] / W, 5), round(b[1] / H, 5), round(b[2] / W, 5), round(b[3] / H, 5), int(c), round(float(sc), 3), src] for b, c, sc, src in keep])
    if time.time() - t0 > B: break
json.dump(res, open(OUT, "w")); print("done", len(res), "of", len(glob.glob(f"{D}/*.jpg")))
