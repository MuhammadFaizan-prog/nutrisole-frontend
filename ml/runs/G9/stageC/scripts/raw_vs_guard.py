"""G9 Stage C step 2: G3 boxes >= 0.35 (raw decode + class-wise NMS 0.7, source-normalised) before vs after each area guard,
by class and size bin, split into GT-matched (same class, IoU >= 0.5 to a GT box of that frame) and unmatched. DEV only.
Usage: raw_vs_guard.py CACHE_DIR OUT.json [probe_dir]"""
import json, sys, os, collections
R = "/workspace/work/nutrisole"; sys.path.insert(0, f"{R}/ml/eval")
from tracker import iou
import video_gauntlet as vg
N = vg.NAMES; BINS = [(0, .0025, "<0.25%"), (.0025, .005, "0.25-0.5%"), (.005, .01, "0.5-1%"), (.01, .025, "1-2.5%"), (.025, 9, ">=2.5%")]
GUARDS = [0.01, 0.005, 0.0025, 0.0]
def area(b): return (b[2] - b[0]) * (b[3] - b[1])
def bin_of(a): return next(n for lo, hi, n in BINS if lo <= a < hi)
def tally(frames):  # frames: list of (dets [x0,y0,x1,y1,c,s], gt [[box,c],...])
    T = collections.defaultdict(lambda: collections.Counter())
    for ds, gt in frames:
        for d in ds:
            if d[5] < 0.35: continue
            a = area(d[:4]); m = any(c == d[4] and iou(d[:4], b) >= 0.5 for b, c in gt)
            key = (N[d[4]], bin_of(a), "tp" if m else "fp")
            T[key]["raw"] += 1
            for g in GUARDS:
                if a >= g: T[key][f"kept_{g}"] += 1
    return T
C, OUT = sys.argv[1], sys.argv[2]; res = {}
val = json.load(open(f"{C}/val_dets.json"))
res["val"] = tally([(r["dets"], [(b[:4], b[4]) for b in r["gt"]]) for r in val])
for k in ("det", "neg"):
    D = json.load(open(f"{C}/devclip_{k}_dets.json")); G = json.load(open(f"{R}/../cv/g3clips_dev/{k}_clip.json".replace(f"{R}/../", "/workspace/work/")))
    res[f"dev_{k}"] = tally([(D[i], [(o["box_norm"], o["cls"]) for o in G["frames"][i]["objects"]]) for i in range(len(D))])
if len(sys.argv) > 3:
    P = sys.argv[3]; D = json.load(open(f"{P}/probe_dets.json")); G = json.load(open(f"{P}/probe_clip.json"))
    res["probe_SYNTHETIC"] = tally([(D[i], [(o["box_norm"], o["cls"]) for o in G["frames"][i]["objects"]]) for i in range(len(D))])
out = {}
for src, T in res.items():
    rows = []
    for (c, b, t), v in sorted(T.items()):
        rows.append(dict(cls=c, bin=b, match=t, raw=v["raw"], **{f"kept_{g}": v[f"kept_{g}"] for g in GUARDS}))
    out[src] = rows
json.dump(out, open(OUT, "w"), indent=1)
for src, rows in out.items():
    print("==", src)
    tot = collections.Counter()
    for r in rows:
        for k in ("raw", *[f"kept_{g}" for g in GUARDS]): tot[(r["match"], k)] += r[k]
    for m in ("tp", "fp"): print(m, {k: tot[(m, k)] for k in ("raw", *[f"kept_{g}" for g in GUARDS])})
    sm = collections.Counter()
    for r in rows:
        if r["bin"] in ("<0.25%", "0.25-0.5%", "0.5-1%"):
            for k in ("raw", *[f"kept_{g}" for g in GUARDS]): sm[(r["match"], r["cls"], k)] += r[k]
    for (m, c, k), v in sorted(sm.items()):
        if k == "raw": print("  small<1%", m, c, "raw", v, "kept@0.5%", sm[(m, c, 'kept_0.005')], "kept@0.25%", sm[(m, c, 'kept_0.0025')], "kept@1%", sm[(m, c, 'kept_0.01')])
