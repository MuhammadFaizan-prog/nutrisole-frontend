"""Stage G feasibility suite (CU close-ups, DEV only). Per item: G3 ID on the still, tap ROI, native crop reference, then crops at
native side S in {32,64,96,128,192,256} (INTER_AREA from the native crop = the pixels a camera frame would carry at that size) under
conditions clean / blur / lowlight / jpeg / occlusion / truncation, plus 5 jittered consecutive frames per (S, clean|jpeg) for
stability. Writes one JSON line per item to out/feas_items.jsonl (resumable). Usage: feas_g.py MAX_SECONDS"""
import json, os, sys, time, random, cv2, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from g_models import detect, assess, N
from ml.eval.closeup import roi_from_tap, crop_rect, id_policy
from ml.grading.measure import object_mask
B = "/workspace/work/nutrisole/ml/runs/G9/stageG"; T = json.load(open(f"{B}/cu_triage.json")); L = json.load(open(f"{B}/out/cu_leak_split.json"))
FEAT = os.environ.get("FEAT") == "1"
OUT = f"{B}/out/feas_block.jsonl" if FEAT else f"{B}/out/feas_items.jsonl"; done = {json.loads(l)["id"] for l in open(OUT)} if os.path.exists(OUT) else set()
SIZES = [32, 64, 96, 128, 192, 256]; CONDS = ["clean", "blur", "lowlight", "jpeg", "occlusion", "truncation"]

def degrade(c, cond, rng):
    h, w = c.shape[:2]
    if cond == "blur": return cv2.GaussianBlur(c, (0, 0), 2.0), False
    if cond == "lowlight":
        x = (c.astype(np.float32) / 255) ** 1.8 * 0.35 * 255 + rng.normal(0, 5, c.shape); return np.clip(x, 0, 255).astype(np.uint8), False
    if cond == "jpeg": return cv2.imdecode(cv2.imencode(".jpg", c, [cv2.IMWRITE_JPEG_QUALITY, 15])[1], 1), False
    if cond == "occlusion":
        o = c.copy(); o[:, : int(0.5 * w)] = (60, 90, 140); return o, False  # skin-tone block over half the item (hand / other produce)
    if cond == "truncation": return c[:, : max(4, int(0.6 * w))].copy(), True  # 40% cut by the frame border
    return c, False

def at_size(native, s):
    h, w = native.shape[:2]; sc = s / (h * w) ** 0.5
    return cv2.resize(native, (max(2, round(w * sc)), max(2, round(h * sc))), interpolation=cv2.INTER_AREA)

def blockiness(bgr):
    """Phase-invariant 8x8 blocking measure: max / median of the mean |horizontal + vertical gradient| per position mod 8 (1.0 = none)."""
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    if min(g.shape) < 24: return 1.0
    dx = np.abs(np.diff(g, axis=1)).mean(0); dy = np.abs(np.diff(g, axis=0)).mean(1)
    px = np.array([dx[i::8].mean() for i in range(8)]); py = np.array([dy[i::8].mean() for i in range(8)])
    return round(float(max(px.max() / max(np.median(px), 1e-6), py.max() / max(np.median(py), 1e-6))), 4)

if FEAT:
    def assess(crop, cls): return dict(block=blockiness(crop))
    def rec(a, s, edge): return a["block"]
    _rec = None
if not FEAT:
  def rec(a, s, edge):
    return dict(cond=a["cond"], pF=round(a["probs"]["fresh"], 4), grade=a["grade"], status=a["status"], blur=a["blurVar"], meanV=a["meanV"], vis=a["visibleFrac"],
                maxP=round(a["maxProb"], 4), margin=round(a["margin"], 4), side=s, edge=edge, ripe=a["ripeness"].get("stage", a["ripeness"]["status"]))

t0 = time.time(); lim = float(sys.argv[1]) if len(sys.argv) > 1 else 100
for k, (cls, lab, tap) in T["item"].items():
    if k in done or ("cu" + k) in L["dropped"]: continue
    if time.time() - t0 > lim: break
    im = cv2.imread(f"/workspace/work/g9g/cu/img/cu{k}.jpg"); H, W = im.shape[:2]; rng = np.random.default_rng(int(k))
    dets = detect(im); r = roi_from_tap(tap, W, H, [d[0] for d in dets])
    hit = [d for d in dets if d[0] == r["box"]] if r["source"] == "track" else []
    idr = id_policy(hit[0][1], hit[0][2], 3) if hit else dict(status="unable", reason="no detection at tap")
    box = r["box"]
    if r["source"] == "tap_roi":  # user ROI fallback: segment the item inside the tapped square
        x1, y1, x2, y2 = map(int, box); sub = im[y1:y2, x1:x2]; m, _ = object_mask(sub[:, :, ::-1].copy())
        ys, xs = np.where(m)
        if len(xs) > 50: box = [x1 + xs.min(), y1 + ys.min(), x1 + xs.max() + 1, y1 + ys.max() + 1]
    cr = crop_rect(box, W, H, pad=0.08); native = im[cr["y"]:cr["y"] + cr["h"], cr["x"]:cr["x"] + cr["w"]]
    ref = assess(native, cls); row = dict(id=k, cls=cls, label={"f": "fresh", "r": "rotten"}[lab], split=L["split"][k], roi=r["source"], native_side=cr["sidePx"],
                                         g3=[[N[d[1]], round(d[2], 3)] for d in dets], id_policy=idr, ref=rec(ref, cr["sidePx"], False), sizes={}, stab={})
    row["id"] = k; row["id_status"] = idr["status"]; row["id_class"] = N[idr["classId"]] if idr["status"] == "identified" else None
    for s in SIZES:
        if s > cr["sidePx"] * 1.05: continue
        base = at_size(native, s); row["sizes"][s] = {}
        for c in CONDS:
            d, edge = degrade(base, c, rng); row["sizes"][s][c] = rec(assess(d, cls), s, edge)
        for c in ("clean", "jpeg"):
            seq = []
            for f in range(5):  # consecutive frames: box jitter +-4% shift, +-5% scale on the native crop, sensor noise
                hh, ww = native.shape[:2]; dx, dy = rng.uniform(-.04, .04) * ww, rng.uniform(-.04, .04) * hh; z = rng.uniform(.95, 1.05)
                M = np.float32([[z, 0, dx + (1 - z) * ww / 2], [0, z, dy + (1 - z) * hh / 2]]); j = cv2.warpAffine(native, M, (ww, hh), borderMode=cv2.BORDER_REFLECT)
                j = at_size(j, s); j = np.clip(j.astype(np.float32) + rng.normal(0, 2, j.shape), 0, 255).astype(np.uint8)
                j, edge = degrade(j, c, rng); seq.append(rec(assess(j, cls), s, edge))
            row["stab"].setdefault(s, {})[c] = seq
    with open(OUT, "a") as f: f.write(json.dumps(row) + "\n")
    print(k, cls, lab, r["source"], cr["sidePx"], idr["status"], ref.get("cond"), ref.get("grade"), round(time.time() - t0), flush=True)
