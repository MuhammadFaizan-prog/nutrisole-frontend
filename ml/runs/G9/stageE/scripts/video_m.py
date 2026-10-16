"""G9 Stage E real-market video (licensed Commons clips, unlabelled): G3 detections at 10 fps (every 3rd frame), then each guard config ->
IouTracker (defaults) -> displayed tracks. Without box labels, false tracks are measured as a LOWER BOUND: tracks whose class was verified
absent from the clip (agent keyframe review, ABSENT list per clip). Also reports all displayed tracks/min per config.
Usage: video_m.py cache CLIP.webm OUT_dets.json | video_m.py eval DETS.json ABSENT(comma class names) OUT.json | video_m.py sheet CLIP.webm OUT.jpg"""
import sys, json, os, collections
R = "/workspace/work/nutrisole"; sys.path.insert(0, f"{R}/ml/eval"); sys.path.insert(0, f"{R}/ml")
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
G = {"g1": (0.01, None), "ssf50": (0.0025, .5), "ssf525": (0.0025, .525), "ssf55": (0.0025, .55), "ssf575": (0.0025, .575), "ssf60": (0.0025, .6), "none": (0.0, None)}
def area(b): return (b[2] - b[0]) * (b[3] - b[1])
if sys.argv[1] in ("cache", "sheet"):
    import cv2
    cap = cv2.VideoCapture(sys.argv[2]); fps = cap.get(cv2.CAP_PROP_FPS); frames = []; i = 0
    while True:
        ok, fr = cap.read()
        if not ok: break
        if i % 3 == 0: frames.append(fr)
        i += 1
    if sys.argv[1] == "sheet":
        import numpy as np
        idx = np.linspace(0, len(frames) - 1, 8).astype(int); t = [cv2.resize(frames[k], (700, int(700 * frames[k].shape[0] / frames[k].shape[1]))) for k in idx]
        cv2.imwrite(sys.argv[3], np.vstack([np.hstack(t[j:j + 2]) for j in range(0, 8, 2)])); print("sheet", len(frames)); sys.exit()
    import onnxruntime as ort
    from geometry import letterbox, dst_to_src, decode
    so = ort.SessionOptions(); so.intra_op_num_threads = 2
    s = ort.InferenceSession("/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx", so, providers=["CPUExecutionProvider"]); di = s.get_inputs()[0].name; D = []
    for fr in frames:
        H, W = fr.shape[:2]; x, tf = letterbox(fr, 480); o = s.run(None, {di: x})[0]; ds = []
        for d in decode(o, "raw", 0.35):
            b = dst_to_src(d["box"], tf)
            if b[2] - b[0] < 2 or b[3] - b[1] < 2: continue
            ds.append([round(b[0] / W, 5), round(b[1] / H, 5), round(b[2] / W, 5), round(b[3] / H, 5), int(d["classId"]), round(float(d["score"]), 4)])
        D.append(ds)
    json.dump(dict(fps=fps / 3, n=len(D), dets=D), open(sys.argv[3], "w")); print("cached", len(D))
else:
    from tracker import IouTracker
    C = json.load(open(sys.argv[2])); absent = set(sys.argv[3].split(",")) if sys.argv[3] else set(); out = {}
    mins = C["n"] / C["fps"] / 60
    for g, (maf, ssf) in G.items():
        trk = IouTracker(); seen = {}; t = 0.0
        for ds in C["dets"]:
            f = [dict(box=d[:4], classId=d[4], score=d[5]) for d in ds if area(d) >= maf and (ssf is None or area(d) >= 0.01 or d[5] >= ssf)]
            for x in trk.update(f, t): seen.setdefault(x["id"], collections.Counter())[x["label"]] += 1
            t += 1000 / C["fps"]
        lab = {k: v.most_common(1)[0][0] for k, v in seen.items()}; byc = collections.Counter(N[c] for c in lab.values())
        fa = sum(1 for c in lab.values() if N[c] in absent)
        out[g] = dict(tracks=len(lab), tracks_per_min=round(len(lab) / mins, 2), absent_class_tracks=fa, absent_class_tracks_per_min=round(fa / mins, 2), by_class=dict(byc))
    json.dump(dict(minutes=round(mins, 3), absent_classes=sorted(absent), configs=out), open(sys.argv[4], "w"), indent=0)
    for g, v in out.items(): print(g, v)
