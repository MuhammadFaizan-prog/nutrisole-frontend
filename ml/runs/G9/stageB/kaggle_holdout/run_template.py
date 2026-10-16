# NutriSole CV G9 Stage B: VB8-holdout clip-level replay of the frozen arms (Kaggle free CPU), run ONCE after the DEV freeze.
# Derived from the G9 Stage A / A3 holdout kernels (same decode, guard, IouTracker, 10 fps fixed-frame, 1 thread per clip).
# Arms (docs/cv/gauntlet/G9_stageB_prereg.md): B0 = G3; B1 = G3 + HN fine-tune; B2 = G3 + crop verifier (VerifiedTracker, tau frozen on DEV);
# B3 = B1 + verifier only if listed in CFG. No training, no tuning here. Scoring happens in the sandbox with the unchanged G8/G9 scorer.
import glob, os, sys, json, subprocess, time, tarfile
EMBEDDED_CFG = r"""__CFG__"""
PIPE_SRC = r'''__PIPE__'''
from multiprocessing import Pool
W = os.environ.get("KW", "/kaggle/working"); I = os.environ.get("KI", "/kaggle/input"); t0 = time.time()
def log(*a): print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)
os.environ.get("KLOCAL") or subprocess.run([sys.executable, "-m", "pip", "install", "-q", "onnxruntime"], check=False)
CFG = json.loads(EMBEDDED_CFG); log("config", {k: v for k, v in CFG.items() if k != "clips"})
def find(name): return glob.glob(f"{I}/**/{name}", recursive=True)[0]
MODELS = {k: find(f) for k, f in CFG["models"].items()}; VER = find(CFG["verifier"]) if CFG.get("verifier") else None
tars = glob.glob(f"{I}/**/hold_code.tar", recursive=True)
if tars: tarfile.open(tars[0]).extractall(f"{W}/code"); CODE = f"{W}/code/ml"
else: CODE = os.path.dirname(os.path.dirname([p for p in glob.glob(f"{I}/**/ml/eval/tracker.py", recursive=True)][0]))
sys.path.insert(0, f"{CODE}/eval"); sys.path.insert(0, CODE); open(f"{W}/stageb_pipe.py", "w").write(PIPE_SRC); sys.path.insert(0, W)
log("models", MODELS, "verifier", VER, "code", CODE)
vids = glob.glob(f"{I}/**/*.webm", recursive=True) + glob.glob(f"{I}/**/*.mp4", recursive=True)
def vpath(c):
    h = [v for v in vids if os.path.basename(v) == f"{c}.h264.mp4"]
    if h: return h[0]
    w = [v for v in vids if os.path.basename(v) == f"{c}.webm"]
    return w[0] if w else None

def run(clip):
    os.environ["OMP_NUM_THREADS"] = "1"
    import cv2, numpy as np, onnxruntime as ort
    from geometry import letterbox, dst_to_src, decode
    from tracker import IouTracker
    from scene_guard import scene_guard
    from stageb_pipe import Verifier, VerifiedTracker
    out_p = f"{W}/hold/{clip}.json"
    if os.path.exists(out_p): return clip, "cached"
    vp = vpath(clip)
    if vp is None: return clip, "NO VIDEO"
    so = ort.SessionOptions(); so.intra_op_num_threads = 1; so.inter_op_num_threads = 1
    dets_m = {k: ort.InferenceSession(p, so, providers=["CPUExecutionProvider"]) for k, p in MODELS.items()}
    trk = {}; vers = {}
    for n, c in CFG["arms"].items():
        if c.get("tau") is not None: vers[n] = Verifier(VER, 1); trk[n] = VerifiedTracker(vers[n], c["tau"], K=CFG["K"])
        else: trk[n] = IouTracker()
    cap = cv2.VideoCapture(vp); fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    if not (1 <= fps <= 120): fps = 25.0
    stride = max(1, int(round(fps / CFG["target_fps"])))
    raw = {k: [] for k in dets_m}; rec = {n: [] for n in CFG["arms"]}; lat = {k: [] for k in dets_m}; plat = {n: [] for n in CFG["arms"]}; calls = {n: 0 for n in CFG["arms"]}
    fi = 0; H = W_ = None; nproc = 0
    while True:
        ok, frame = cap.read()
        if not ok: break
        if fi % stride == 0:
            H, W_ = frame.shape[:2]; t = 1000.0 * fi / fps; x, tf = letterbox(frame, CFG["imgsz"]); md = {}; nproc += 1
            for k, s in dets_m.items():
                a = time.perf_counter(); o = s.run(None, {s.get_inputs()[0].name: x})[0]; ds = []
                for d in decode(o, "raw", 0.35):
                    b = dst_to_src(d["box"], tf)
                    if b[2] - b[0] < 2 or b[3] - b[1] < 2: continue
                    ds.append(dict(box=[b[0] / W_, b[1] / H, b[2] / W_, b[3] / H], classId=d["classId"], score=d["score"]))
                md[k] = scene_guard(ds, **CFG["guard"]); lat[k].append(1000 * (time.perf_counter() - a))
                raw[k].append([round(t, 1), [[d_["classId"], round(d_["score"], 3)] for d_ in md[k]]])
            for n, c in CFG["arms"].items():
                a = time.perf_counter()
                tr = trk[n].update(md[c["model"]], t, frame) if n in vers else trk[n].update(md[c["model"]], t)
                post = 1000 * (time.perf_counter() - a); plat[n].append(lat[c["model"]][-1] + post)
                if n in vers: calls[n] += trk[n].calls_this
                rec[n].append([round(t, 1), [[x_["id"], x_["label"], round(x_["score"], 3), int(bool(x_["stable"]))] for x_ in tr]])
        fi += 1
    pc = lambda v: [float(np.percentile(v, q)) for q in (50, 90, 95)] if v else None
    json.dump(dict(clip=clip, video=os.path.basename(vp), fps=fps, n_frames=fi, stride=stride, w=W_, h=H, dur_s=fi / fps, n_processed=nproc,
                   lat_det_ms={k: pc(v) for k, v in lat.items()}, lat_arm_ms={n: pc(v) for n, v in plat.items()}, lat_arm_all={n: [round(x_, 2) for x_ in v] for n, v in plat.items()},
                   verifier_calls=calls, rec=rec, raw=raw), open(out_p, "w"))
    return clip, f"ok {fi} frames stride {stride} {time.time()-t0:.0f}s"

os.makedirs(f"{W}/hold", exist_ok=True)
clips = CFG["clips"] if not os.environ.get("KCLIPS") else os.environ["KCLIPS"].split(",")
def dur(c):
    import cv2; cap = cv2.VideoCapture(vpath(c) or ""); n = cap.get(cv2.CAP_PROP_FRAME_COUNT); return n or 0
clips = sorted(clips, key=lambda c: -dur(c)); log("clips", len(clips))
with Pool(int(os.environ.get("KWORK", CFG["workers"]))) as p:
    for c, s in p.imap_unordered(run, clips): log(c, s)
json.dump(dict(cfg=CFG, cpu=os.cpu_count(), wall_s=time.time() - t0), open(f"{W}/hold_meta.json", "w"))
log("DONE")
