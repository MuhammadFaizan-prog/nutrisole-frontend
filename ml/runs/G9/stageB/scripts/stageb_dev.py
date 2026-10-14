"""G9 Stage B DEV evaluation of one arm (prereg section 4). Arm = detector cache dir (+ optional verifier ONNX and tau).
Val stills: per-class P/R at 0.35 (after verifier for verifier arms, each box verified on its own), false boxes on box-free images.
DEV det / neg clips: stock pipeline replay (floor 0.35, area guard, IouTracker defaults; VerifiedTracker for verifier arms, frames read from
the clip mp4), metrics from video_gauntlet.metrics() unchanged + TTFC from first GT visibility. Writes OUT json.
Usage: stageb_dev.py NAME DETCACHE_DIR OUT.json [VERIFIER.onnx TAU]"""
import json, os, sys, time, collections
import cv2, numpy as np
R = "/workspace/work/nutrisole"; sys.path.insert(0, f"{R}/ml/eval"); sys.path.insert(0, f"{R}/ml"); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tracker import IouTracker, iou
from scene_guard import scene_guard
import video_gauntlet as vg
from stageb_pipe import Verifier, VerifiedTracker, crop128
NAMES = vg.NAMES; SHOW = ["citrus", "apple", "banana", "tomato", "carrot"]
name, C, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
V = Verifier(sys.argv[4], threads=2) if len(sys.argv) > 4 else None; TAU = float(sys.argv[5]) if len(sys.argv) > 5 else None
res = dict(arm=name, det_cache=C, verifier=sys.argv[4] if V else None, tau=TAU)
# ---- val stills
val = json.load(open(f"{C}/val_dets.json")); vdir = "/workspace/work/cv/g3data/det_v3"
paths = {os.path.basename(l.strip()): l.strip() for l in open(f"{vdir}/val.txt")}
st = collections.defaultdict(lambda: dict(n=0, tp=0, fp=0)); boxfree_fp = boxfree_imgs = 0; vrej = 0
for r in val:
    ds = [d for d in r["dets"] if d[5] >= 0.35]
    if V and ds:
        im = cv2.imread(paths[r["img"]]); keep = []
        cr = [crop128(im, d[:4]) for d in ds]; ps = V([c for c in cr if c is not None]); k = 0
        for d, c in zip(ds, cr):
            p = None
            if c is not None: p = ps[k]; k += 1
            if p is None or p >= TAU: keep.append(d)
            else: vrej += 1
        ds = keep
    for c in range(12):
        g = [b for b in r["gt"] if b[4] == c]; st[c]["n"] += len(g); used = set()
        for d in sorted([d for d in ds if d[4] == c], key=lambda d: -d[5]):
            bi, bv = None, 0.5
            for j, b in enumerate(g):
                if j in used: continue
                v = iou(d[:4], b[:4])
                if v >= bv: bi, bv = j, v
            if bi is None: st[c]["fp"] += 1
            else: used.add(bi); st[c]["tp"] += 1
    if not r["gt"]: boxfree_imgs += 1; boxfree_fp += len(ds)
res["val"] = {NAMES[c]: dict(n=v["n"], tp=v["tp"], fp=v["fp"], P=round(v["tp"] / (v["tp"] + v["fp"]), 4) if v["tp"] + v["fp"] else None,
                             R=round(v["tp"] / v["n"], 4) if v["n"] else None) for c, v in st.items()}
res["val_boxfree"] = dict(images=boxfree_imgs, false_boxes=boxfree_fp); res["val_verifier_rejected_boxes"] = vrej
# ---- DEV clips
def replay(kind):
    gt = json.load(open(f"/workspace/work/cv/g3clips_dev/{kind}_clip.json")); D = json.load(open(f"{C}/devclip_{kind}_dets.json"))
    trk = VerifiedTracker(V, TAU) if V else IouTracker(); cap = cv2.VideoCapture(f"/workspace/work/cv/g3clips_dev/{kind}_clip.mp4") if V else None
    shown = []; calls = []
    for fi, fr in enumerate(gt["frames"][:len(D)]):
        frame = cap.read()[1] if cap is not None else None
        ds = scene_guard([dict(box=d[:4], classId=d[4], score=d[5]) for d in D[fi] if d[5] >= 0.35], maxSameClass=0, minAreaFrac=0.01)
        if fr.get("reset"): trk.reset()
        tr = trk.update(ds, fr["t_ms"], frame) if V else trk.update(ds, fr["t_ms"])
        if V: calls.append(trk.calls_this)
        shown.append([dict(id=x["id"], box=x["box"], label=x["label"], score=x["score"], grade=None, level=None, reasons=None) for x in tr])
    m = vg.metrics(gt, shown, kind)
    if kind == "det":  # TTFC from first GT visibility (G9 Stage A addendum A3 definition)
        tt = []  # scorer's per-segment TTFC re-based to the first frame the GT object is visible (identical to g9fp_dev_extra.py)
        for si, sg in enumerate(gt["segments"]):
            fv = next((fi for fi in range(sg["start"], sg["end"] + 1) if any(o["cls"] == sg["cls"] for o in gt["frames"][fi]["objects"])), None)
            r = m["segments_detail"][si]
            if fv is None or r["ttfc_ms"] is None: continue
            tt.append(gt["frames"][sg["start"]]["t_ms"] + r["ttfc_ms"] - gt["frames"][fv]["t_ms"])
        m["ttfc_from_visibility_ms"] = dict(p50=round(float(np.percentile(tt, 50))), p90=round(float(np.percentile(tt, 90))), n=len(tt)) if tt else None
    if V: m["verifier_calls_per_frame"] = round(sum(calls) / max(1, len(calls)), 4); m["verifier_calls_total"] = sum(calls)
    return m
for k in ("det", "neg"):
    t0 = time.time(); m = replay(k); res[f"dev_{k}"] = m; print(k, round(time.time() - t0, 1), "s", flush=True)
if V: res["verifier_ms_per_call_batch"] = dict(p50=round(float(np.percentile(V.ms, 50)), 3), p95=round(float(np.percentile(V.ms, 95)), 3), n=len(V.ms))
json.dump(res, open(OUT, "w"), indent=1)
d, n = res["dev_det"], res["dev_neg"]
print(name, "seg", d.get("segment_acc"), "frame", d.get("frame_acc"), "idsw", d.get("id_switches"), "FA/min neg", n.get("false_alarms_per_min"), "pcr", {k: v for k, v in (d.get("per_class_recall") or {}).items() if k in SHOW},
      "ttfc", d.get("ttfc_from_visibility_ms"), "boxfree", res["val_boxfree"])
