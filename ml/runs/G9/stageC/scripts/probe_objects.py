"""SYNTHETIC probe, per class: GT objects (segment x object), objects with >=1 raw G3 hit (same class, IoU>=0.5, >=0.35), and objects with a hit
that survives each guard. Separates 'never detected' from 'detected but guarded out'."""
import json, sys, collections
sys.path.insert(0, "/workspace/work/nutrisole/ml/eval"); from tracker import iou; import video_gauntlet as vg
def area(b): return (b[2] - b[0]) * (b[3] - b[1])
G, D = json.load(open("/workspace/work/cv/g9c/probe/probe_clip.json")), json.load(open("/workspace/work/cv/g9c/probe/probe_dets.json"))
tot = collections.defaultdict(set); hit = collections.defaultdict(dict)
for fi, fr in enumerate(G["frames"]):
    for oi, o in enumerate(fr["objects"]):
        k = (fr["segment"], oi); c = vg.NAMES[o["cls"]]; tot[c].add(k)
        for d in D[fi]:
            if d[4] == o["cls"] and iou(d[:4], o["box_norm"]) >= .5: hit[c][k] = max(hit[c].get(k, 0), area(d[:4]))
res = {c: dict(objects=len(tot[c]), raw_hit=len(hit[c]), **{f"hit_kept_{g}": sum(1 for a in hit[c].values() if a >= g) for g in (0.01, 0.005, 0.0025, 0.0)}) for c in sorted(tot)}
json.dump(res, open("../out/probe_objects.json", "w"), indent=1)
for c, v in res.items(): print(c, v)
