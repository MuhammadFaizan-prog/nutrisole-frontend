"""G9 Stage F: M-DEV v2 evaluation (copy of Stage E eval_m.py; configs restricted to g1 = deployed guard, raw035 = all boxes >= 0.35 no guard, raw001 = floor 0.01 for raw AP50). Usage: eval_f.py DETS.json LABELS.json OUT.json
Matching per image and class: detections sorted by score, greedy to unmatched non-crowd GT of the same class at IoU >= 0.5. An unmatched
detection whose centre lies in a crowd region of the SAME class is ignored; otherwise it is a false box (tagged 'class_error:<gt class>' when
it overlaps a GT of another class at IoU >= 0.5 or sits in a crowd region of another class, 'background' otherwise).
AP50 per class (VOC all-point) on (a) the displayed set (>= 0.35, after the guard) and (b) raw (floor 0.01, no guard), crowd-ignore applied."""
import json, sys, collections
import numpy as np
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
SHOW = ["citrus", "apple", "banana", "tomato", "carrot"]
BINS = [(0, .0025, "<0.25%"), (.0025, .005, "0.25-0.5%"), (.005, .01, "0.5-1%"), (.01, .025, "1-2.5%"), (.025, 9, ">=2.5%")]
SMALL = ["<0.25%", "0.25-0.5%", "0.5-1%"]
G = {"g1": (0.01, None), "raw035": (0.0, None), "raw001": (0.0, None)}  # Stage F: fixed g1 guard (displayed) + raw; the Stage E ssf grid stays closed
def area(b): return (b[2] - b[0]) * (b[3] - b[1])
def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    return i / (area(a) + area(b) - i + 1e-12)
def binof(a): return next(n for lo, hi, n in BINS if lo <= a < hi)
def inside(d, c): cx, cy = (d[0] + d[2]) / 2, (d[1] + d[3]) / 2; return c[0] <= cx <= c[2] and c[1] <= cy <= c[3]
def filt(ds, g):
    maf, ssf = G[g]; floor = 0.01 if g == "raw001" else 0.35
    return [d for d in ds if d[5] >= floor and area(d) >= maf and (ssf is None or area(d) >= 0.01 or d[5] >= ssf)]
def ap(rec):  # rec: list of (score, is_tp), npos
    sc, npos = rec
    if npos == 0: return None
    sc = sorted(sc, key=lambda x: -x[0]); tp = np.cumsum([t for _, t in sc]); fp = np.cumsum([1 - t for _, t in sc])
    if not len(sc): return 0.0
    r = tp / npos; p = tp / np.maximum(tp + fp, 1e-9); mr = np.concatenate([[0], r, [1]]); mp = np.concatenate([[0], p, [0]])
    for i in range(len(mp) - 2, -1, -1): mp[i] = max(mp[i], mp[i + 1])
    idx = np.where(mr[1:] != mr[:-1])[0]; return float(np.sum((mr[idx + 1] - mr[idx]) * mp[idx + 1]))
D = json.load(open(sys.argv[1])); L = json.load(open(sys.argv[2])); out = {}
ids = [i for i in L if L[i]["status"] == "ok" and i in D]
for g in G:
    rb = collections.defaultdict(collections.Counter); fp_tag = collections.Counter(); fp_bin = collections.Counter(); conf = collections.Counter()
    tp = fp = ign = 0; bf = 0; bf_imgs = 0; per_img = {}; apr = {c: [[], 0] for c in range(12)}
    for i in ids:
        gt = [b for b in L[i]["boxes"]]; cr = L[i].get("crowd", []); ds = filt(D[i]["dets"], g); neg = not gt and not cr
        bf_imgs += neg; itp = ifp = 0
        for c in range(12):
            gc = [b for b in gt if b[4] == c]; used = set(); apr[c][1] += len(gc)
            for d in sorted([d for d in ds if d[4] == c], key=lambda d: -d[5]):
                bi, bv = None, 0.5
                for j, b in enumerate(gc):
                    v = iou(d, b)
                    if j not in used and v >= bv: bi, bv = j, v
                if bi is not None: used.add(bi); tp += 1; itp += 1; apr[c][0].append((d[5], 1)); continue
                if any(inside(d, x) for x in cr if x[4] in (c, -1)): ign += 1; continue
                fp += 1; ifp += 1; apr[c][0].append((d[5], 0)); fp_bin[binof(area(d))] += 1
                other = [b for b in gt if b[4] != c and iou(d, b) >= 0.5] + [x for x in cr if x[4] not in (c, -1) and inside(d, x)]
                if other: fp_tag["class_error"] += 1; conf[f"{N[c]}<-{N[other[0][4]]}"] += 1
                else: fp_tag["background"] += 1
                if neg: bf += 1
            for j, b in enumerate(gc): k = (N[c], binof(area(b))); rb[k]["n"] += 1; rb[k]["tp"] += j in used
        per_img[i] = dict(tp=itp, fp=ifp)
    def rec(cls, bins):
        n = sum(v["n"] for (c, b), v in rb.items() if c in cls and b in bins); t = sum(v["tp"] for (c, b), v in rb.items() if c in cls and b in bins)
        return dict(n=n, tp=t, R=round(t / n, 4) if n else None)
    out[g] = dict(images=len(ids), negative_images=bf_imgs, tp=tp, fp=fp, ignored_in_crowd=ign, boxfree_fp=bf, fp_by_bin=dict(fp_bin), fp_tags=dict(fp_tag), class_confusions=dict(conf.most_common()),
                  small_show=rec(SHOW, SMALL), small_all=rec(N, SMALL), small_carrot=rec(["carrot"], SMALL), normal_show=rec(SHOW, ["1-2.5%", ">=2.5%"]),
                  small_by_class={c: rec([c], SMALL) for c in N}, normal_by_class={c: rec([c], ["1-2.5%", ">=2.5%"]) for c in N},
                  recall_by_bin={f"{c}|{b}": dict(v) for (c, b), v in sorted(rb.items())},
                  ap50={N[c]: (round(ap(apr[c]), 4) if apr[c][1] else None) for c in range(12)}, per_image=per_img)
    v = [x for x in out[g]["ap50"].values() if x is not None]; out[g]["map50"] = round(float(np.mean(v)), 4) if v else None
json.dump(out, open(sys.argv[3], "w"), indent=0)
for g, v in out.items(): print(g, "smallShow", v["small_show"], "carrot", v["small_carrot"], "tp/fp", v["tp"], v["fp"], "bf", v["boxfree_fp"], "mAP", v["map50"], v["fp_tags"])
