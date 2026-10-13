# NutriSole CV G8: VB8-holdout clip-level replay (Kaggle free CPU). Replays the 34 VB8-holdout recordings through the app
# pipeline (same code as ml/eval/video_gauntlet.py run_clip, fixed-frame mode, cls=None) for G3 (IouTracker), G3r5 (G3 with
# only the 5 showcase rows), showcase s0/s1 (IouTracker) and G3 + ByteTrack DEV pick. Writes per-processed-frame displayed
# tracks (id,label,score) per config; all scoring happens in the sandbox against the human clip-level truth.
# NO training, NO tuning: every parameter is fixed before this run (G8 prereg addendum 2026-10-14).
import glob, os, sys, json, subprocess, time, tarfile
from multiprocessing import Pool
W = os.environ.get("KW", "/kaggle/working"); I = os.environ.get("KI", "/kaggle/input"); t0 = time.time()
def log(*a): print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)
os.environ.get("KLOCAL") or subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics==8.4.175", "lap==0.5.13", "onnxruntime"], check=False)
base = os.path.dirname(glob.glob(f"{I}/**/hold_config.json", recursive=True)[0])
tars = glob.glob(f"{I}/**/hold_code.tar", recursive=True)
if tars: tarfile.open(tars[0]).extractall(f"{W}/code"); CODE = f"{W}/code/ml"
else: CODE = os.path.dirname(os.path.dirname([p for p in glob.glob(f"{I}/**/ml/eval/tracker.py", recursive=True)][0]))  # Kaggle auto-extracts tars
sys.path.insert(0, f"{CODE}/eval"); sys.path.insert(0, CODE); print("code", CODE, "base", base, flush=True)
CFG = json.load(open(f"{base}/hold_config.json")); log("config", CFG)
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
    from bytetrack_adapter import ByteTrackTracker
    from scene_guard import scene_guard
    from grading.rules import RUBRIC
    out_p = f"{W}/hold/{clip}.json"
    if os.path.exists(out_p): return clip, "cached"
    vp = vpath(clip)
    if vp is None: return clip, "NO VIDEO"
    so = ort.SessionOptions(); so.intra_op_num_threads = 1; so.inter_op_num_threads = 1
    dets_m = {k: ort.InferenceSession(f"{base}/{f}", so, providers=["CPUExecutionProvider"]) for k, f in CFG["models"].items()}
    trk = {}
    for name, c in CFG["configs"].items():
        trk[name] = ByteTrackTracker(**c["tracker_params"]) if c["tracker_kind"] == "bytetrack" else IouTracker(**c["tracker_params"])
    guard = CFG["guard"]; minsc = RUBRIC["detectorMinScore"]
    cap = cv2.VideoCapture(vp); fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    if not (1 <= fps <= 120): fps = 25.0
    stride = max(1, int(round(fps / CFG["target_fps"])))
    rec = {n: [] for n in CFG["configs"]}; lat = {k: [] for k in dets_m}; fi = 0; H = W_ = None
    low = min([minsc] + [trk[n].p["track_low_thresh"] for n, c in CFG["configs"].items() if c["tracker_kind"] == "bytetrack"])
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
            for n, c in CFG["configs"].items():
                ds = md[c["model"]]
                if c["tracker_kind"] == "iou": ds = [d for d in ds if d["score"] >= minsc]
                else: ds = [d for d in ds if d["score"] >= min(minsc, trk[n].p["track_low_thresh"])]
                ds = scene_guard(ds, **guard)
                tr = trk[n].update(ds, t)
                rec[n].append([round(t, 1), [[x_["id"], x_["label"], round(x_["score"], 3), int(bool(x_["stable"]))] for x_ in tr]])
        fi += 1
    json.dump(dict(clip=clip, video=os.path.basename(vp), fps=fps, n_frames=fi, stride=stride, w=W_, h=H, dur_s=fi / fps,
                   lat_det_ms={k: [float(np.percentile(v, q)) for q in (50, 90, 95)] if v else None for k, v in lat.items()},
                   rec=rec), open(out_p, "w"))
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
