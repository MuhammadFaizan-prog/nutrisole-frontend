"""G9 Stage D DEV replay of one config = (detector cache dir, guard) with stock IouTracker (iouMatch 0.3). DEV only.
Guards: g1 / g05 / g025 (minAreaFrac 1% / 0.5% / 0.25% of the source frame), none (raw, pre-guard), ssf50 / ssf60 (size-dependent
score floor: >=1% normal 0.35 floor; [0.25%,1%) needs score >= 0.50 / 0.60; <0.25% dropped). Derived from stageC/stagec_eval.py.
Usage: stageD_eval.py CACHE_DIR GUARD OUT.json [PROBE_CACHE_DIR]
Tracker variants: 'iou0.3' (stock IouTracker defaults), 'iou0.2' (iouMatch 0.2), 'ctr' (stock + centre-distance fallback for small boxes,
analysis only: after IoU matching, unmatched track/detection pairs whose boxes are both < 2% of the frame are associated greedily by centre
distance if distance <= 1.0 x mean side of the two boxes).
Usage: stagec_eval.py MAF TRACKER OUT.json"""
import json, sys, time, collections
import numpy as np
R = "/workspace/work/nutrisole"; sys.path.insert(0, f"{R}/ml/eval")
from tracker import IouTracker, Track, iou
from scene_guard import scene_guard
import video_gauntlet as vg
N = vg.NAMES; SHOW = ["citrus", "apple", "banana", "tomato", "carrot"]
BINS = [(0, .0025, "<0.25%"), (.0025, .005, "0.25-0.5%"), (.005, .01, "0.5-1%"), (.01, .025, "1-2.5%"), (.025, 9, ">=2.5%")]
def area(b): return (b[2] - b[0]) * (b[3] - b[1])
def binof(a): return next(n for lo, hi, n in BINS if lo <= a < hi)
C, GUARD, OUT = sys.argv[1], sys.argv[2], sys.argv[3]; TRK = "iou0.3"; PC = sys.argv[4] if len(sys.argv) > 4 else None
P = "/workspace/work/cv/g9c/probe"
MAF = {"g1": 0.01, "g05": 0.005, "g025": 0.0025, "none": 0.0, "ssf50": 0.0025, "ssf60": 0.0025}[GUARD]
SSF = {"ssf50": 0.5, "ssf60": 0.6}.get(GUARD)
def gfilter(ds):  # ds: list of dict(box, classId, score), already >= 0.35
    out = scene_guard(ds, maxSameClass=0, minAreaFrac=MAF)
    if SSF is not None: out = [d for d in out if area(d["box"]) >= 0.01 or d["score"] >= SSF]
    return out

class CentreTracker(IouTracker):
    """IouTracker + small-box centre-distance fallback (analysis only). Same update as tracker.py, one extra association pass."""
    def update(self, dets, t_ms):
        P_ = self.p; pairs = []
        for ti, t in enumerate(self.tracks):
            for di, d in enumerate(dets):
                v = iou(t.box, d["box"])
                if v >= P_["iouMatch"]: pairs.append((v, ti, di))
        pairs.sort(key=lambda x: (-x[0], self.tracks[x[1]].id, x[2])); usedT, usedD, M = set(), set(), []
        for _, ti, di in pairs:
            if ti in usedT or di in usedD: continue
            usedT.add(ti); usedD.add(di); M.append((ti, di))
        cand = []
        for ti, t in enumerate(self.tracks):
            if ti in usedT or area(t.box) >= 0.02: continue
            for di, d in enumerate(dets):
                if di in usedD or area(d["box"]) >= 0.02: continue
                ct = ((t.box[0] + t.box[2]) / 2, (t.box[1] + t.box[3]) / 2); cd = ((d["box"][0] + d["box"][2]) / 2, (d["box"][1] + d["box"][3]) / 2)
                dist = ((ct[0] - cd[0]) ** 2 + (ct[1] - cd[1]) ** 2) ** .5; side = (area(t.box) ** .5 + area(d["box"]) ** .5) / 2
                if dist <= 1.0 * side: cand.append((dist, ti, di))
        for _, ti, di in sorted(cand):
            if ti in usedT or di in usedD: continue
            usedT.add(ti); usedD.add(di); M.append((ti, di)); self.n_fallback = getattr(self, "n_fallback", 0) + 1
        for ti, di in M:
            t, d = self.tracks[ti], dets[di]
            if iou(t.rawBox, d["box"]) < P_["stableIou"]: t.stableSinceMs = t_ms
            t.rawBox = list(d["box"]); t.box = [(1 - P_["boxAlpha"]) * t.box[k] + P_["boxAlpha"] * d["box"][k] for k in range(4)]
            for c in set(t.scores) | {d["classId"]}:
                prev = t.scores.get(c, 0.0); t.scores[c] = (1 - P_["scoreAlpha"]) * prev + P_["scoreAlpha"] * (d["score"] if c == d["classId"] else 0.0)
            self._hyst(t); t.hits += 1; t.missed = 0
        surv = []
        for ti, t in enumerate(self.tracks):
            if ti not in usedT: t.missed += 1
            if t.missed <= P_["maxMissed"]: surv.append(t)
        self.tracks = surv
        for di, d in enumerate(dets):
            if di in usedD: continue
            self.tracks.append(Track(id=self.nextId, box=list(d["box"]), rawBox=list(d["box"]), label=d["classId"], scores={d["classId"]: d["score"]}, stableSinceMs=t_ms, firstSeenMs=t_ms)); self.nextId += 1
        return [dict(id=t.id, box=t.box, label=t.label, score=t.scores.get(t.label, 0.0), stable=(t_ms - t.stableSinceMs) >= P_["stableMs"], ageMs=t_ms - t.firstSeenMs)
                for t in self.tracks if t.hits >= P_["minHits"] and t.missed == 0]

def mk(): return CentreTracker() if TRK == "ctr" else IouTracker(iouMatch=float(TRK[3:]))
res = dict(cache=C, guard=GUARD, minAreaFrac=MAF, small_score_floor=SSF, tracker=TRK)
# ---------- val stills: per-class P/R, recall by GT size bin, false boxes
val = json.load(open(f"{C}/val_dets.json")); st = collections.defaultdict(collections.Counter); sb = collections.defaultdict(collections.Counter); bf = 0; fpb = collections.Counter()
for r in val:
    ds = [[*d["box"], d["classId"], d["score"]] for d in gfilter([dict(box=d[:4], classId=d[4], score=d[5]) for d in r["dets"] if d[5] >= 0.35])]
    for c in range(12):
        g = [b for b in r["gt"] if b[4] == c]; used = set(); st[c]["n"] += len(g)
        for d in sorted([d for d in ds if d[4] == c], key=lambda d: -d[5]):
            bi, bv = None, 0.5
            for j, b in enumerate(g):
                if j not in used and iou(d[:4], b[:4]) >= bv: bi, bv = j, iou(d[:4], b[:4])
            if bi is None: st[c]["fp"] += 1; fpb[binof(area(d[:4]))] += 1
            else: used.add(bi); st[c]["tp"] += 1
        for j, b in enumerate(g):
            k = (N[c], binof(area(b[:4]))); sb[k]["n"] += 1; sb[k]["tp"] += j in used
    if not r["gt"]: bf += len(ds)
res["val"] = {N[c]: dict(n=v["n"], tp=v["tp"], fp=v["fp"], R=round(v["tp"] / v["n"], 4) if v["n"] else None) for c, v in sorted(st.items()) if v["n"] or v["fp"]}
res["val_recall_by_bin"] = {f"{c}|{b}": dict(n=v["n"], tp=v["tp"]) for (c, b), v in sorted(sb.items())}
res["val_false_boxes"] = dict(total=sum(v["fp"] for v in st.values()), by_bin=dict(fpb), boxfree_images=bf)

def replay(gt, D, kind):
    trk = mk(); shown = []; ms = []
    for fi, fr in enumerate(gt["frames"][:len(D)]):
        a = time.perf_counter()
        ds = gfilter([dict(box=d[:4], classId=d[4], score=d[5]) for d in D[fi] if d[5] >= 0.35])
        if fr.get("reset"): trk.reset()
        tr = trk.update(ds, fr["t_ms"]); ms.append(1000 * (time.perf_counter() - a))
        shown.append([dict(id=x["id"], box=x["box"], label=x["label"], score=x["score"], grade=None, level=None, reasons=None) for x in tr])
    m = vg.metrics(gt, shown, kind); m["post_ms"] = dict(p50=round(float(np.percentile(ms, 50)), 4), p95=round(float(np.percentile(ms, 95)), 4))
    if getattr(trk, "n_fallback", None) is not None: m["centre_fallback_matches"] = trk.n_fallback
    if kind == "neg": return m
    tt = []
    for si, sg in enumerate(gt["segments"]):
        fv = next((fi for fi in range(sg["start"], sg["end"] + 1) if any(o["cls"] == sg["cls"] for o in gt["frames"][fi]["objects"])), None)
        r = m["segments_detail"][si]
        if fv is None or r["ttfc_ms"] is None: continue
        tt.append(gt["frames"][sg["start"]]["t_ms"] + r["ttfc_ms"] - gt["frames"][fv]["t_ms"])
    m["ttfc_from_visibility_ms"] = dict(p50=round(float(np.percentile(tt, 50))), p90=round(float(np.percentile(tt, 90))), n=len(tt)) if tt else None
    # all-object frame recall by size bin, IDs per GT object, mixed-scene false tracks
    ob = collections.defaultdict(collections.Counter); ids = collections.defaultdict(list); good = set(); allid = set(); gapids = set()
    for fi, fr in enumerate(gt["frames"][:len(D)]):
        for s in shown[fi]: allid.add(s["id"])
        if fr["segment"] < 0: gapids |= {s["id"] for s in shown[fi]}
        for oi, o in enumerate(fr["objects"]):
            hit = None
            for s in shown[fi]:
                if s["label"] == o["cls"] and iou(s["box"], o["box_norm"]) >= 0.5 and (hit is None or iou(s["box"], o["box_norm"]) > iou(hit["box"], o["box_norm"])): hit = s
            k = (N[o["cls"]], binof(area(o["box_norm"]))); ob[k]["n"] += 1
            if hit: ob[k]["tp"] += 1; ids[(fr["segment"], oi)].append(hit["id"]); good.add(hit["id"])
        for s in shown[fi]:
            if any(iou(s["box"], o["box_norm"]) >= 0.3 for o in fr["objects"]): good.add(s["id"])
    m["object_frame_recall_by_bin"] = {f"{c}|{b}": dict(n=v["n"], tp=v["tp"]) for (c, b), v in sorted(ob.items())}
    seq = [v for v in ids.values()]
    m["ids_per_gt_object"] = dict(objects_matched=len(seq), mean_distinct_ids=round(float(np.mean([len(set(v)) for v in seq])), 3) if seq else None,
                                  objects_with_gt1_id=sum(1 for v in seq if len(set(v)) > 1), id_switches_all_objects=sum(sum(1 for a_, b_ in zip(v, v[1:]) if a_ != b_) for v in seq))
    mins = len(D) / gt["fps"] / 60
    m["mixed_false_tracks"] = dict(n=len(allid - good), per_min=round(len(allid - good) / mins, 3), gap_frame_tracks=len(gapids), minutes=round(mins, 3))
    m.pop("segments_detail"); return m
for k in ("det", "neg"):
    res[f"dev_{k}"] = replay(json.load(open(f"/workspace/work/cv/g3clips_dev/{k}_clip.json")), json.load(open(f"{C}/devclip_{k}_dets.json")), k)
import os
if PC and os.path.exists(f"{PC}/probe_dets.json"):
    res["probe_SYNTHETIC"] = replay(json.load(open(f"{P}/probe_clip.json")), json.load(open(f"{PC}/probe_dets.json")), "det")
json.dump(res, open(OUT, "w"), indent=1)
d, n = res["dev_det"], res["dev_neg"]
print(C, GUARD, "pcr", {k: v["recall"] for k, v in d["per_class_recall"].items() if k in SHOW}, "FA", n["false_alarms_per_min"], n["fa_episodes_per_min"], "idsw", d["id_switches"], "ttfc", d["ttfc_from_visibility_ms"])
