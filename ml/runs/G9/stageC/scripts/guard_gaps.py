"""Does the area guard interrupt association? For every GT object in the DEV det clip and the SYNTHETIC probe: frames where a raw G3 box
(>=0.35, same class, IoU>=0.5) exists, and how many of those the guard removes (the object then misses a tracker update). Objects whose raw
detections straddle the threshold (some kept, some removed) are the ones a guard can fragment."""
import json, sys, collections
sys.path.insert(0, "/workspace/work/nutrisole/ml/eval"); from tracker import iou
def area(b): return (b[2] - b[0]) * (b[3] - b[1])
out = {}
for name, gp, dp in [("dev_det", "/workspace/work/cv/g3clips_dev/det_clip.json", "/workspace/work/cv/g9fp/devclip_det_dets.json"),
                     ("probe_SYNTHETIC", "/workspace/work/cv/g9c/probe/probe_clip.json", "/workspace/work/cv/g9c/probe/probe_dets.json")]:
    G, D = json.load(open(gp)), json.load(open(dp)); obj = collections.defaultdict(list)
    for fi, fr in enumerate(G["frames"][:len(D)]):
        for oi, o in enumerate(fr["objects"]):
            m = [d for d in D[fi] if d[4] == o["cls"] and d[5] >= .35 and iou(d[:4], o["box_norm"]) >= .5]
            if m: obj[(fr["segment"], oi)].append(max(area(d[:4]) for d in m))
    r = {}
    for g in (0.01, 0.005, 0.0025):
        straddle = sum(1 for v in obj.values() if any(a < g for a in v) and any(a >= g for a in v))
        allrm = sum(1 for v in obj.values() if all(a < g for a in v)); fr_rm = sum(sum(1 for a in v if a < g) for v in obj.values())
        r[str(g)] = dict(objects_with_raw_hits=len(obj), objects_all_removed=allrm, objects_straddling=straddle, raw_hit_frames=sum(map(len, obj.values())), raw_hit_frames_removed=fr_rm)
    out[name] = r
json.dump(out, open("../out/guard_gaps.json", "w"), indent=1); print(json.dumps(out, indent=1))
