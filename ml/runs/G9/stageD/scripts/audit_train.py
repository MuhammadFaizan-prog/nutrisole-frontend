"""G9 Stage D Exp1: annotation/size audit of the G3 training data (det_v3 train) vs DEV val, at the deployed 480 letterbox.
Writes out/train_audit.json. Size = fraction of the SOURCE frame (as the guard measures) and side in 480-letterbox model pixels."""
import json, os, collections, sys
import numpy as np
from PIL import Image
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
SHOW = ["citrus", "apple", "banana", "tomato", "carrot"]
R = "/workspace/work/cv/g3data/det_v3"
def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i; return i / u if u > 0 else 0
def audit(lst):
    per = collections.defaultdict(lambda: collections.Counter()); side = collections.defaultdict(list); src = collections.Counter()
    imgs_with = collections.Counter(); carrot_imgs = collections.Counter(); objs_per_img = []; overl = collections.Counter(); W_ = []
    for p in [l.strip() for l in open(lst)]:
        part = p.split("/det_v3/")[1].split("/")[0]; src[part] += 1
        lp = p.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"; bs = []
        if os.path.exists(lp):
            for ln in open(lp):
                v = ln.split()
                if len(v) >= 5: c, cx, cy, w, h = int(v[0]), *map(float, v[1:5]); bs.append([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, c])
        if not bs: continue
        W, H = Image.open(p).size; s = 480 / max(W, H); W_.append(max(W, H)); objs_per_img.append(len(bs))
        for c in {b[4] for b in bs}: imgs_with[N[c]] += 1
        for i, b in enumerate(bs):
            a = (b[2] - b[0]) * (b[3] - b[1]); sd = ((b[2] - b[0]) * W * s * (b[3] - b[1]) * H * s) ** .5; n = N[b[4]]
            side[n].append(sd); per[n]["n"] += 1
            per[n]["lt1pct"] += a < 0.01; per[n]["lt0.25pct"] += a < 0.0025; per[n]["side_lt32"] += sd < 32; per[n]["side_lt16"] += sd < 16
            if any(j != i and o[4] == b[4] and iou(b, o) > 0.1 for j, o in enumerate(bs)): overl[n] += 1
        nc = sum(1 for b in bs if b[4] == 10)
        if nc: carrot_imgs["1" if nc == 1 else "2-4" if nc < 5 else "5-9" if nc < 10 else ">=10"] += 1
    out = {}
    for n in N:
        v = per[n]; sd = np.array(side[n]) if side[n] else np.array([0])
        out[n] = dict(boxes=v["n"], images=imgs_with[n], small_lt1pct=round(v["lt1pct"] / max(1, v["n"]), 3), tiny_lt0p25pct=round(v["lt0.25pct"] / max(1, v["n"]), 3),
                      side480_lt32=round(v["side_lt32"] / max(1, v["n"]), 3), side480_p10_p50_p90=[round(float(np.percentile(sd, q)), 1) for q in (10, 50, 90)],
                      overlapping_same_class_share=round(overl[n] / max(1, v["n"]), 3))
    return dict(sources=dict(src), labelled_images=len(objs_per_img), objs_per_img_p50_p90_max=[float(np.percentile(objs_per_img, 50)), float(np.percentile(objs_per_img, 90)), int(max(objs_per_img))],
                src_long_side_p50=float(np.median(W_)), carrot_images_by_count=dict(carrot_imgs), per_class=out)
res = dict(train=audit(f"{R}/train.txt"), val_DEV=audit(f"{R}/val.txt"))
json.dump(res, open(sys.argv[1], "w"), indent=1)
for k in res:
    print(k, res[k]["sources"], res[k]["labelled_images"], res[k]["objs_per_img_p50_p90_max"], res[k]["carrot_images_by_count"])
    for n in SHOW + ["carrot"][:0]: print("  ", n, res[k]["per_class"][n])
