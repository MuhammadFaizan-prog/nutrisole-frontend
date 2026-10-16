"""G9 Stage B P3 (DEV only, analysis): association of short-lived objects on the synthetic DEV det clip, using cached G3 detections
(g9fp/devclip_det_dets.json) and the stock IouTracker (no new gate). (1) For each GT segment, truncate the visible part to its first
k frames (k = 3, 6, 9, 15 at 15 fps = 0.2-1.0 s; detections outside are dropped) and record whether the class is displayed at all and
for >= 0.5 s, and how many track ids carry it. (2) Consecutive-frame IoU of the box matched to the same GT object, small vs large objects.
(3) Share of GT-matching raw boxes removed by the 1% area guard, by object size."""
import json, sys, collections, statistics as st
R = "/workspace/work/nutrisole"; sys.path.insert(0, f"{R}/ml/eval"); sys.path.insert(0, f"{R}/ml")
from tracker import IouTracker, iou
from scene_guard import scene_guard
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
g = json.load(open("/workspace/work/cv/g3clips_dev/det_clip.json")); D = json.load(open("/workspace/work/cv/g9fp/devclip_det_dets.json"))
F = g["frames"]; fps = g["fps"]; out = dict(truncation={}, consecutive_iou={}, area_guard={})
for k in (3, 6, 9, 15, 60):
    res = []
    for si, sg in enumerate(g["segments"]):
        vis = [i for i in range(sg["start"], sg["end"] + 1) if i < len(F) and F[i]["objects"]]
        if not vis: continue
        keep = set(vis[:k]); trk = IouTracker(); shown_t = 0; ids = set(); disp = False
        for i in range(max(0, sg["start"] - 2), min(len(F), sg["end"] + 10)):
            ds = [dict(box=d[:4], classId=d[4], score=d[5]) for d in D[i]] if i in keep else []
            ds = scene_guard(ds, maxSameClass=0, minAreaFrac=0.01)
            sh = trk.update(ds, F[i]["t_ms"])
            c = [x for x in sh if x["label"] == sg["cls"]]
            if c: shown_t += 1; disp = True; ids |= {x["id"] for x in c}
        res.append(dict(seg=si, cls=N[sg["cls"]], shown_s=round(shown_t / fps, 3), displayed=disp, ok05=shown_t / fps >= 0.5 - 1e-9, n_ids=len(ids)))
    out["truncation"][f"{k}f_{round(k / fps, 2)}s"] = dict(segments=len(res), displayed=sum(r["displayed"] for r in res), shown_ge_0_5s=sum(r["ok05"] for r in res),
        mean_ids_when_displayed=round(st.mean([r["n_ids"] for r in res if r["displayed"]]), 2) if any(r["displayed"] for r in res) else None,
        carrot=[r for r in res if r["cls"] == "carrot"])
# consecutive IoU and area guard
ci = collections.defaultdict(list); ag = collections.Counter()
prev = None
for i, f in enumerate(F):
    if not f["objects"]: prev = None; continue
    o = f["objects"][0]; gb = o["box_norm"]; area = (gb[2] - gb[0]) * (gb[3] - gb[1]); size = "small(<3%)" if area < 0.03 else "large"
    m = [d for d in D[i] if d[4] == o["cls"] and iou(d[:4], gb) >= 0.3]
    kept = scene_guard([dict(box=d[:4], classId=d[4], score=d[5]) for d in m], maxSameClass=0, minAreaFrac=0.01)
    ag[(size, "raw")] += len(m); ag[(size, "kept")] += len(kept)
    best = max(m, key=lambda d: iou(d[:4], gb)) if m else None
    if best and prev: ci[size].append(iou(best[:4], prev[:4]))
    prev = best
out["consecutive_iou"] = {k: dict(n=len(v), median=round(st.median(v), 3), p10=round(sorted(v)[len(v) // 10], 3), share_below_0_3=round(sum(x < 0.3 for x in v) / len(v), 3)) for k, v in ci.items() if v}
out["area_guard"] = {s: dict(raw=ag[(s, "raw")], kept=ag[(s, "kept")]) for s in ("small(<3%)", "large")}
json.dump(out, open(f"{R}/ml/runs/G9/stageB/dev_shortlived.json", "w"), indent=1)
for k, v in out["truncation"].items(): print(k, {a: b for a, b in v.items() if a != "carrot"}, [(c["shown_s"], c["n_ids"]) for c in v["carrot"]])
print(out["consecutive_iou"]); print(out["area_guard"])
