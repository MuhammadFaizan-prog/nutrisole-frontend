"""G9 Stage B P3, analysis only: why the carrot track(s) in holdout #16 (ca1cbf110) fragment. Re-runs the deployed G3 pipeline
(A0: raw 480, floor 0.35, area guard, IouTracker defaults, ~10 fps fixed-frame stride as in the holdout kernel) on this single clip to get
the per-frame boxes that the stored replay JSON does not keep, then logs every matcher decision. Nothing is tuned; no gate variant is tried."""
import sys, json, cv2, onnxruntime as ort
R = "/workspace/work/nutrisole"; sys.path.insert(0, f"{R}/ml/eval"); sys.path.insert(0, f"{R}/ml")
from geometry import letterbox, dst_to_src, decode
from scene_guard import scene_guard
from tracker import IouTracker, iou
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
so = ort.SessionOptions(); so.intra_op_num_threads = 2
s = ort.InferenceSession("/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx", so, providers=["CPUExecutionProvider"])
cap = cv2.VideoCapture("/workspace/work/cv/g6src/raw/ca1cbf110.webm"); fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
stride = max(1, int(round(fps / 10))); trk = IouTracker(); fi = 0; log = []; prev = []
while True:
    ok, fr = cap.read()
    if not ok: break
    if fi % stride == 0:
        H, W = fr.shape[:2]; x, tf = letterbox(fr, 480); o = s.run(None, {s.get_inputs()[0].name: x})[0]; ds = []
        for d in decode(o, "raw", 0.35):
            b = dst_to_src(d["box"], tf)
            if b[2] - b[0] < 2 or b[3] - b[1] < 2: continue
            ds.append(dict(box=[b[0] / W, b[1] / H, b[2] / W, b[3] / H], classId=int(d["classId"]), score=float(d["score"])))
        ds_all = ds; ds = scene_guard(ds, maxSameClass=0, minAreaFrac=0.01); t = 1000 * fi / fps
        before = {tr.id: list(tr.box) for tr in trk.tracks}
        shown = trk.update(ds, t)
        dl = []
        for d in ds:
            best = max([(iou(b, d["box"]), i) for i, b in before.items()], default=(0, None))
            dl.append(dict(cls=N[d["classId"]], score=round(d["score"], 3), box=[round(v, 3) for v in d["box"]],
                           area=round((d["box"][2] - d["box"][0]) * (d["box"][3] - d["box"][1]), 4), best_iou_prev_track=round(best[0], 3), prev_track=best[1]))
        log.append(dict(t_s=round(t / 1000, 2), n_raw_ge035=len(ds_all), n_raw_removed_by_area_guard=len(ds_all) - len(ds), dets=dl,
                        live_tracks=[dict(id=tr.id, label=N[tr.label], hits=tr.hits, missed=tr.missed) for tr in trk.tracks],
                        shown=[dict(id=x_["id"], label=N[x_["label"]], score=round(x_["score"], 3)) for x_ in shown]))
    fi += 1
json.dump(dict(fps=fps, stride=stride, frames=log), open(f"{R}/ml/runs/G9/stageB/carrot16_trace.json", "w"), indent=1)
for f in log:
    print(f["t_s"], "raw", f["n_raw_ge035"], "guard-", f["n_raw_removed_by_area_guard"], [(d["cls"], d["score"], d["area"], d["best_iou_prev_track"], d["prev_track"]) for d in f["dets"]], "shown", [(x["id"], x["label"]) for x in f["shown"]])
