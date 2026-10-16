"""G9 Stage D Exp1: missing-annotation sample. 36 random det_v3 TRAIN images (seed 0) that contain >= 1 showcase box; G3 at 640 on
2x2 overlapping tiles (upscaled) proposes boxes; proposals (score >= 0.5) with IoU < 0.3 to every GT box are drawn red, GT green.
The sheet is agent-reviewed. Writes out/missing_sample.json + /workspace/work/cv/g9d/missing_sheet_{1,2}.jpg"""
import os, sys, json, random, cv2, numpy as np, onnxruntime as ort
R = "/workspace/work/nutrisole"; sys.path.insert(0, f"{R}/ml/eval"); sys.path.insert(0, f"{R}/ml")
from geometry import letterbox, dst_to_src, decode
so = ort.SessionOptions(); so.intra_op_num_threads = 2
s = ort.InferenceSession("/workspace/work/cv/g9c/det_yolo11n_g3_at640_raw.onnx", so, providers=["CPUExecutionProvider"]); di = s.get_inputs()[0].name
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i; return i / u if u > 0 else 0
def lab(p):
    lp = p.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"; out = []
    for l in open(lp) if os.path.exists(lp) else []:
        v = l.split(); c, cx, cy, w, h = int(v[0]), *map(float, v[1:5]); out.append([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, c])
    return out
L = [l.strip() for l in open("/workspace/work/cv/g3data/det_v3/train.txt")]; random.seed(0); random.shuffle(L); pick = []
for p in L:
    g = lab(p)
    if any(b[4] in (0, 1, 3, 7, 10) for b in g): pick.append((p, g))
    if len(pick) == 36: break
rows = []; tiles = []
for i, (p, g) in enumerate(pick):
    im = cv2.imread(p); H, W = im.shape[:2]; im2 = cv2.resize(im, (W * 2, H * 2)); props = []
    for y0 in (0, H - H // 2 + 0) if False else (0, H // 1 - H // 1 + H * 2 - min(H * 2, int(H * 1.2))):
        pass
    T = [(0, 0), (W * 2 - int(W * 1.2), 0), (0, H * 2 - int(H * 1.2)), (W * 2 - int(W * 1.2), H * 2 - int(H * 1.2))]
    for x0, y0 in T:
        crop = im2[y0:y0 + int(H * 1.2), x0:x0 + int(W * 1.2)]; x, tf = letterbox(crop, 640)
        for d in decode(s.run(None, {di: x})[0], "raw", 0.5):
            b = dst_to_src(d["box"], tf); props.append([(b[0] + x0) / (2 * W), (b[1] + y0) / (2 * H), (b[2] + x0) / (2 * W), (b[3] + y0) / (2 * H), d["classId"], d["score"]])
    un = []
    for q in sorted(props, key=lambda q: -q[5]):
        if all(iou(q, b) < 0.3 for b in g) and all(iou(q, u) < 0.4 for u in un): un.append(q)
    rows.append(dict(img=os.path.basename(p), gt=len(g), unmatched_proposals=[[round(v, 3) for v in u[:4]] + [N[u[4]], round(u[5], 2)] for u in un]))
    vis = im.copy()
    for b in g: cv2.rectangle(vis, (int(b[0] * W), int(b[1] * H)), (int(b[2] * W), int(b[3] * H)), (0, 220, 0), 1)
    for u in un: cv2.rectangle(vis, (int(u[0] * W), int(u[1] * H)), (int(u[2] * W), int(u[3] * H)), (0, 0, 255), 2)
    sc = 400 / max(H, W); vis = cv2.resize(vis, (int(W * sc), int(H * sc))); c = np.full((400, 400, 3), 40, np.uint8); c[:vis.shape[0], :vis.shape[1]] = vis
    cv2.putText(c, f"{i} gt{len(g)} red{len(un)}", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1); tiles.append(c)
for k in range(2):
    t = tiles[k * 18:(k + 1) * 18]; t += [np.zeros_like(tiles[0])] * (18 - len(t))
    cv2.imwrite(f"/workspace/work/cv/g9d/missing_sheet_{k+1}.jpg", np.vstack([np.hstack(t[r * 6:(r + 1) * 6]) for r in range(3)]))
json.dump(rows, open(f"{R}/ml/runs/G9/stageD/out/missing_sample.json", "w"), indent=0); print("ok", sum(len(r["unmatched_proposals"]) for r in rows))
