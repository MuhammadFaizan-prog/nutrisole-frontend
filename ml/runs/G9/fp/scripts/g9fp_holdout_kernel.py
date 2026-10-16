# NutriSole CV G9 Stage A (FP): VB8-holdout clip-level replay of frozen arms A0/A1/A2 (Kaggle free CPU). Derived from the G8 kernel;
# only change: per-class detector thresholds + PolicyTracker (minHits, birth margin) per config, G3 weights only.
# ORIGINAL G8 HEADER: Replays the 34 VB8-holdout recordings through the app
# pipeline (same code as ml/eval/video_gauntlet.py run_clip, fixed-frame mode, cls=None) for G3 (IouTracker), G3r5 (G3 with
# only the 5 showcase rows), showcase s0/s1 (IouTracker) and G3 + ByteTrack DEV pick. Writes per-processed-frame displayed
# tracks (id,label,score) per config; all scoring happens in the sandbox against the human clip-level truth.
# NO training, NO tuning: every parameter is fixed before this run (G8 prereg addendum 2026-10-14).
import glob, os, sys, json, subprocess, time, tarfile
EMBEDDED_CFG = r"""{"imgsz": 480, "target_fps": 10, "workers": 4, "guard": {"maxSameClass": 0, "minAreaFrac": 0.01}, "models": {"G3": "G3_raw480.onnx"}, "configs": {"A0": {"model": "G3", "thr": [0.35, 0.35, 0.35, 0.35, 0.35, 0.35, 0.35, 0.35, 0.35, 0.35, 0.35, 0.35], "minHits": 2, "delta": 0.0}, "A1": {"model": "G3", "thr": [0.4, 0.4, 0.5, 0.45, 0.35, 0.35, 0.75, 0.45, 0.9, 0.6, 0.45, 0.8], "minHits": 2, "delta": 0.0}, "A2": {"model": "G3", "thr": [0.4, 0.4, 0.5, 0.45, 0.35, 0.35, 0.75, 0.45, 0.9, 0.6, 0.45, 0.8], "minHits": 3, "delta": 0.0}}, "clips": ["c6e08132a", "c61cbc2a6", "c9030be18", "c97bdc431", "c19ae062b", "c8b2d2f36", "c0a13587f", "c20a12a9c", "c32085ee7", "c3cc14a1f", "c59f957c2", "c87e3900a", "c94ab39f5", "c973b3f44", "c97e354bf", "ca1cbf110", "cb05e346c", "cd1a3f857", "cf0b25e3b", "cfe0b39f1", "c31b80875", "c4880a292", "c6473db48", "c90447971", "cd4211720", "c0a08d565", "c3d854faf", "c4a35a451", "c4e9a7195", "c6f5ac9b4", "c82e63d5a", "cc5585ebc", "cd17ce723", "ce9f2fe34"], "frozen": "thresholds_A1.json + policy_A2.json, G9_fp_prereg.md"}"""  # = ml/runs/G9/fp/g9fp_config.json (frozen)
from multiprocessing import Pool
W = os.environ.get("KW", "/kaggle/working"); I = os.environ.get("KI", "/kaggle/input"); t0 = time.time()
def log(*a): print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)
os.environ.get("KLOCAL") or subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics==8.4.175", "lap==0.5.13", "onnxruntime"], check=False)
base = os.path.dirname(glob.glob(f"{I}/**/G3_raw480.onnx", recursive=True)[0])  # G8 holdrun dataset (same G3 sha256); Kaggle blob upload failed 2026-10-14, so the frozen config is embedded below
tars = glob.glob(f"{I}/**/hold_code.tar", recursive=True)
if tars: tarfile.open(tars[0]).extractall(f"{W}/code"); CODE = f"{W}/code/ml"
else: CODE = os.path.dirname(os.path.dirname([p for p in glob.glob(f"{I}/**/ml/eval/tracker.py", recursive=True)][0]))  # Kaggle auto-extracts tars
sys.path.insert(0, f"{CODE}/eval"); sys.path.insert(0, CODE); print("code", CODE, "base", base, flush=True)
CFG = json.loads(EMBEDDED_CFG); log("config", CFG)
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
    from grading.rules import RUBRIC
    out_p = f"{W}/hold/{clip}.json"
    if os.path.exists(out_p): return clip, "cached"
    vp = vpath(clip)
    if vp is None: return clip, "NO VIDEO"
    so = ort.SessionOptions(); so.intra_op_num_threads = 1; so.inter_op_num_threads = 1
    dets_m = {k: ort.InferenceSession(f"{base}/{f}", so, providers=["CPUExecutionProvider"]) for k, f in CFG["models"].items()}
    from tracker import iou as _iou
    class PolicyTracker(IouTracker):  # identical to ml/runs/G9/fp/scripts/g9fp_replay.py PolicyTracker
        def __init__(self, thr, delta=0.0, **p):
            super().__init__(**p); self.thr, self.delta = thr, delta
        def update(self, dets, t_ms):
            if self.delta > 0:
                dets = [d for d in dets if d["score"] >= self.thr[d["classId"]] + self.delta
                        or any(_iou(tr.box, d["box"]) >= self.p["iouMatch"] for tr in self.tracks)]
            return super().update(dets, t_ms)
    trk = {name: PolicyTracker(c["thr"], c["delta"], minHits=c["minHits"]) for name, c in CFG["configs"].items()}
    guard = CFG["guard"]; minsc = RUBRIC["detectorMinScore"]
    cap = cv2.VideoCapture(vp); fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    if not (1 <= fps <= 120): fps = 25.0
    stride = max(1, int(round(fps / CFG["target_fps"])))
    raw = []; rec = {n: [] for n in CFG["configs"]}; lat = {k: [] for k in dets_m}; fi = 0; H = W_ = None
    low = minsc
    while True:
        ok, frame = cap.read()
        if not ok: break
        if fi % stride == 0:
            H, W_ = frame.shape[:2]; t = 1000.0 * fi / fps
            x, tf = letterbox(frame, CFG["imgsz"]); md = {}
            for k, s in dets_m.items():
                a = time.perf_counter(); o = s.run(None, {s.get_inputs()[0].name: x})[0]; lat[k].append(1000 * (time.perf_counter() - a))
                ds = []
                for d in decode(o, "raw", low):
                    b = dst_to_src(d["box"], tf)
                    if b[2] - b[0] < 2 or b[3] - b[1] < 2: continue
                    ds.append(dict(box=[b[0] / W_, b[1] / H, b[2] / W_, b[3] / H], classId=d["classId"], score=d["score"]))
                md[k] = ds
            _g = scene_guard(md["G3"], **guard); raw.append([round(t, 1), len(md["G3"]), [[d_["classId"], round(d_["score"], 3)] for d_ in _g]])  # raw detector (floor 0.35, post area guard), G9 user addition 3
            for n, c in CFG["configs"].items():
                ds = md[c["model"]]
                ds = [d for d in ds if d["score"] >= c["thr"][d["classId"]]]
                ds = scene_guard(ds, **guard)
                tr = trk[n].update(ds, t)
                rec[n].append([round(t, 1), [[x_["id"], x_["label"], round(x_["score"], 3), int(bool(x_["stable"]))] for x_ in tr]])
        fi += 1
    json.dump(dict(clip=clip, video=os.path.basename(vp), fps=fps, n_frames=fi, stride=stride, w=W_, h=H, dur_s=fi / fps,
                   lat_det_ms={k: [float(np.percentile(v, q)) for q in (50, 90, 95)] if v else None for k, v in lat.items()},
                   rec=rec, raw=raw), open(out_p, "w"))
    return clip, f"ok {fi} frames stride {stride} {time.time()-t0:.0f}s"

os.makedirs(f"{W}/hold", exist_ok=True)
clips = CFG["clips"] if not os.environ.get("KCLIPS") else os.environ["KCLIPS"].split(",")
# longest first for load balance
def dur(c):
    import cv2; cap = cv2.VideoCapture(vpath(c) or ""); n = cap.get(cv2.CAP_PROP_FRAME_COUNT); return n or 0
clips = sorted(clips, key=lambda c: -dur(c)); log("clips", len(clips), [(c, vpath(c)) for c in clips][:3])
with Pool(int(os.environ.get("KWORK", CFG["workers"]))) as p:
    for c, s in p.imap_unordered(run, clips): log(c, s)
json.dump(dict(cfg=CFG, cpu=os.cpu_count(), wall_s=time.time() - t0), open(f"{W}/hold_meta.json", "w"))
log("DONE")
