"""G9 Stage B P1: run G3 as deployed (raw 480, floor 0.35, area guard 0.01) on mining-pool clips (M-train / M-dev only,
see ml/runs/G9/stageB/mining_split.csv) at 2 fps; store every frame's boxes. Resumable per clip. Never touches holdout clips."""
import os, sys, json, csv, time
import cv2, onnxruntime as ort
R = "/workspace/work/nutrisole"; sys.path.insert(0, f"{R}/ml/eval"); sys.path.insert(0, f"{R}/ml")
from geometry import letterbox, dst_to_src, decode
from scene_guard import scene_guard
DET = "/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx"; OUT = "/workspace/work/cv/g9b/mine"; FPS = 2.0
split = {r["clip_id"]: r for r in csv.DictReader(open(f"{R}/ml/runs/G9/stageB/mining_split.csv"))}
so = ort.SessionOptions(); so.intra_op_num_threads = 2
s = ort.InferenceSession(DET, so, providers=["CPUExecutionProvider"]); di = s.get_inputs()[0].name
budget = float(sys.argv[1]) if len(sys.argv) > 1 else 100; t0 = time.time()
def vpath(c):
    for d in ("g6src", "g7src"):
        for e in ("webm", "ogv"):
            p = f"/workspace/work/cv/{d}/raw/{c}.{e}"
            if os.path.exists(p): return p
for c, r in split.items():
    if r["stageB_role"] not in ("M-train", "M-dev"): continue
    op = f"{OUT}/{c}.json"
    if os.path.exists(op): continue
    part = f"{OUT}/{c}.part.json"; st = json.load(open(part)) if os.path.exists(part) else dict(clip=c, role=r["stageB_role"], frames=[])
    cap = cv2.VideoCapture(vpath(c)); fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    if not (1 <= fps <= 120): fps = 25.0
    stride = max(1, int(round(fps / FPS))); st.update(fps=fps, stride=stride)
    done = {f["fi"] for f in st["frames"]}; fi = 0
    while True:
        ok = cap.grab()
        if not ok: break
        if fi % stride == 0 and fi not in done:
            ok, fr = cap.retrieve()
            if not ok: break
            H, W = fr.shape[:2]; x, tf = letterbox(fr, 480); o = s.run(None, {di: x})[0]; ds = []
            for d in decode(o, "raw", 0.35):
                b = dst_to_src(d["box"], tf)
                if b[2] - b[0] < 2 or b[3] - b[1] < 2: continue
                ds.append(dict(box=[b[0] / W, b[1] / H, b[2] / W, b[3] / H], classId=int(d["classId"]), score=float(d["score"])))
            g = scene_guard(ds, maxSameClass=0, minAreaFrac=0.01)
            st["frames"].append(dict(fi=fi, t=round(fi / fps, 3), w=W, h=H, boxes=[[round(v, 5) for v in d["box"]] + [d["classId"], round(d["score"], 4)] for d in g]))
            if time.time() - t0 > budget:
                json.dump(st, open(part, "w")); print("budget stop", c, len(st["frames"])); sys.exit(0)
        fi += 1
    st["n_frames"] = fi; json.dump(st, open(op, "w"))
    if os.path.exists(part): os.remove(part)
    print("done", c, len(st["frames"]), round(time.time() - t0), flush=True)
print("ALL DONE")
