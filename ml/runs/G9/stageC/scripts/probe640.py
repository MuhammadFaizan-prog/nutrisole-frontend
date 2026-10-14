"""DIAGNOSTIC ONLY (not an arm, not a candidate): same G3 weights run at 640 letterbox (its training size) instead of the deployed 480,
on the SYNTHETIC probe's showcase-class segment frames, to tell input resolution apart from training coverage. Counts per class:
GT objects with >=1 raw hit (same class, IoU>=0.5, >=0.35) at 480 (from the cache) vs at 640, and object-frame hits."""
import json, sys, collections, cv2, onnxruntime as ort
R = "/workspace/work/nutrisole"; sys.path.insert(0, f"{R}/ml/eval"); sys.path.insert(0, f"{R}/ml")
from geometry import letterbox, dst_to_src, decode
from tracker import iou; import video_gauntlet as vg
SHOW = {0, 1, 3, 7, 10}  # model: the same G3 best.pt (sha256 29cc5212...) exported raw at imgsz 640 -> /workspace/work/cv/g9c/det_yolo11n_g3_at640_raw.onnx
so = ort.SessionOptions(); so.intra_op_num_threads = 2
s = ort.InferenceSession(sys.argv[1] if len(sys.argv) > 1 else "/workspace/work/cv/g9c/det_yolo11n_g3_at640_raw.onnx", so, providers=["CPUExecutionProvider"]); di = s.get_inputs()[0].name
def det(frame, sz):
    H, W = frame.shape[:2]; x, tf = letterbox(frame, sz); o = s.run(None, {di: x})[0]; ds = []
    for d in decode(o, "raw", 0.35):
        b = dst_to_src(d["box"], tf); ds.append([b[0] / W, b[1] / H, b[2] / W, b[3] / H, int(d["classId"]), float(d["score"])])
    return ds
G = json.load(open("/workspace/work/cv/g9c/probe/probe_clip.json")); D = json.load(open("/workspace/work/cv/g9c/probe/probe_dets.json"))
segs = {i for i, sg in enumerate(G["segments"]) if sg["cls"] in SHOW}
cap = cv2.VideoCapture("/workspace/work/cv/g9c/probe/probe_clip.mp4"); fi = -1
H = {480: collections.defaultdict(set), 640: collections.defaultdict(set)}; F = {480: collections.Counter(), 640: collections.Counter()}; T = collections.defaultdict(set); NF = collections.Counter()
while True:
    ok, fr = cap.read(); fi += 1
    if not ok: break
    g = G["frames"][fi]
    if g["segment"] not in segs: continue
    d640 = det(fr, 640)
    for oi, o in enumerate(g["objects"]):
        c = vg.NAMES[o["cls"]]; k = (g["segment"], oi); T[c].add(k); NF[c] += 1
        for sz, ds in ((480, D[fi]), (640, d640)):
            if any(d[4] == o["cls"] and d[5] >= .35 and iou(d[:4], o["box_norm"]) >= .5 for d in ds): H[sz][c].add(k); F[sz][c] += 1
res = {c: dict(objects=len(T[c]), obj_hit_480=len(H[480][c]), obj_hit_640=len(H[640][c]), objframes=NF[c], objframe_hit_480=F[480][c], objframe_hit_640=F[640][c]) for c in sorted(T)}
json.dump(res, open("/workspace/work/nutrisole/ml/runs/G9/stageC/out/probe_640_diagnostic.json", "w"), indent=1); print(json.dumps(res))
