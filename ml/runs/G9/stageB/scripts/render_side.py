"""Side-by-side comparison video: G3 (left) vs a Stage B arm (right) on independent M-dev real clips (never trained on, not holdout),
app pipeline at 10 fps fixed-frame (floor 0.35, area guard, IouTracker defaults; VerifiedTracker when a verifier is given).
Usage: render_side.py OUT.mp4 LEFT_LABEL LEFT_DET RIGHT_LABEL RIGHT_DET [RIGHT_VERIFIER TAU] -- clip1,clip2,..."""
import os, sys, subprocess, cv2, numpy as np
R = "/workspace/work/nutrisole"; sys.path.insert(0, f"{R}/ml/eval"); sys.path.insert(0, f"{R}/ml"); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import onnxruntime as ort
from geometry import letterbox, dst_to_src, decode
from scene_guard import scene_guard
from tracker import IouTracker
from stageb_pipe import Verifier, VerifiedTracker
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
a = sys.argv[1:]; k = a.index("--"); clips = a[k + 1].split(","); a = a[:k]
OUT, LL, LD, RL, RD = a[:5]; RV, TAU = (a[5], float(a[6])) if len(a) > 6 else (None, None)
so = ort.SessionOptions(); so.intra_op_num_threads = 2
def sess(p): return ort.InferenceSession(p, so, providers=["CPUExecutionProvider"])
SL, SR = sess(LD), sess(RD); V = Verifier(RV, 2) if RV else None
GUARDS = {"g1": (0.01, None), "g05": (0.005, None), "g025": (0.0025, None), "ssf50": (0.0025, 0.5), "ssf60": (0.0025, 0.6)}  # Stage D: optional env LGUARD / RGUARD (default g1)
def det(s, fr, guard="g1"):
    H, W = fr.shape[:2]; x, tf = letterbox(fr, 480); o = s.run(None, {s.get_inputs()[0].name: x})[0]; ds = []
    for d in decode(o, "raw", 0.35):
        b = dst_to_src(d["box"], tf)
        if b[2] - b[0] < 2 or b[3] - b[1] < 2: continue
        ds.append(dict(box=[b[0] / W, b[1] / H, b[2] / W, b[3] / H], classId=d["classId"], score=d["score"]))
    maf, ssf = GUARDS[guard]; ds = scene_guard(ds, maxSameClass=0, minAreaFrac=maf)
    return [d for d in ds if ssf is None or (d["box"][2] - d["box"][0]) * (d["box"][3] - d["box"][1]) >= 0.01 or d["score"] >= ssf]
def draw(fr, tr, label):
    im = fr.copy(); H, W = im.shape[:2]
    for t in tr:
        b = t["box"]; p1, p2 = (int(b[0] * W), int(b[1] * H)), (int(b[2] * W), int(b[3] * H))
        cv2.rectangle(im, p1, p2, (0, 255, 0), 2); cv2.putText(im, f"{N[t['label']]} {t['score']:.2f}", (p1[0] + 2, max(14, p1[1] + 14)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
    cv2.rectangle(im, (0, 0), (W, 26), (0, 0, 0), -1); cv2.putText(im, f"{label}  tracks shown: {len(tr)}", (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    return im
tmp = OUT + ".raw.avi"; vw = None
for c in clips:
    p = next(q for d in ("g6src", "g7src") for e in ("webm", "ogv") for q in [f"/workspace/work/cv/{d}/raw/{c}.{e}"] if os.path.exists(q))
    cap = cv2.VideoCapture(p); fps = cap.get(cv2.CAP_PROP_FPS) or 25; st = max(1, int(round(fps / 10))); fi = 0
    tl, tr_ = IouTracker(), (VerifiedTracker(V, TAU) if V else IouTracker())
    while True:
        ok, fr = cap.read()
        if not ok: break
        if fi % st == 0:
            s = 360 / fr.shape[0]; fr = cv2.resize(fr, (int(fr.shape[1] * s) // 2 * 2, 360)); t = 1000 * fi / fps
            LG, RG = os.environ.get("LGUARD", "g1"), os.environ.get("RGUARD", "g1")
            L = tl.update(det(SL, fr, LG), t); Rr = tr_.update(det(SR, fr, RG), t, fr) if V else tr_.update(det(SR, fr, RG), t)
            im = np.hstack([draw(fr, L, LL), draw(fr, Rr, RL)]); cv2.putText(im, f"M-dev clip {c} (independent, not trained on)  t={t/1000:.1f}s", (4, 352), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
            if vw is None: sz = (im.shape[1], im.shape[0]); vw = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*"MJPG"), 10, sz)
            if (im.shape[1], im.shape[0]) != sz: im = cv2.resize(im, sz)
            vw.write(im)
        fi += 1
vw.release()
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-c:v", "libx264", "-crf", "28", "-preset", "veryfast", "-pix_fmt", "yuv420p", OUT], check=True); os.remove(tmp); print("wrote", OUT)
