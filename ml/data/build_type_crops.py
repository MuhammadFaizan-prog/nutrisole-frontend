"""G4 two-stage experiment, stage-2 data: produce TYPE crops (11 classes with GT + 'other') from det-v3 train/val GT boxes.
Crops: GT box + 10% pad, min side 24 px, max 2500 per class per split-ratio (seed 0). 'other' = random boxes from the
det-v3 background images (COCO negatives + mined hard negatives), same size distribution. Locked test splits are never read.
  python ml/data/build_type_crops.py --root /workspace/work/cv/g3data/det_v3 --dst /workspace/work/cv/g4data/typecrops"""
import argparse, glob, json, os, random, collections
import cv2
NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); ap.add_argument("--dst", required=True); ap.add_argument("--cap", type=int, default=2500)
a = ap.parse_args(); rng = random.Random(0); stats = {}
for sp in ["train", "val"]:
    files = [l.strip() for l in open(f"{a.root}/{sp}.txt") if l.strip()]
    boxes = collections.defaultdict(list); bgs = []; sizes = []
    for f in files:
        lp = f.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"
        rows = [l.split() for l in open(lp)] if os.path.exists(lp) else []
        rows = [r for r in rows if len(r) == 5]
        if not rows: bgs.append(f); continue
        for r in rows: boxes[int(r[0])].append((f, *map(float, r[1:]))); sizes.append((float(r[3]), float(r[4])))
    cap = a.cap if sp == "train" else a.cap // 8
    cnt = {}
    for c, bl in boxes.items():
        rng.shuffle(bl); os.makedirs(f"{a.dst}/{sp}/{NAMES[c]}", exist_ok=True); n = 0
        for f, x, y, w, h in bl:
            if n >= cap: break
            im = cv2.imread(f); H, W = im.shape[:2]
            x1, y1, x2, y2 = (x - w * 0.6) * W, (y - h * 0.6) * H, (x + w * 0.6) * W, (y + h * 0.6) * H
            if min(x2 - x1, y2 - y1) < 24: continue
            cr = im[int(max(0, y1)):int(min(H, y2)), int(max(0, x1)):int(min(W, x2))]
            if cr.size == 0: continue
            cv2.imwrite(f"{a.dst}/{sp}/{NAMES[c]}/{n:05d}.jpg", cr); n += 1
        cnt[NAMES[c]] = n
    os.makedirs(f"{a.dst}/{sp}/other", exist_ok=True); n = 0; tries = 0
    while n < cap and bgs and tries < cap * 5:
        tries += 1; f = rng.choice(bgs); w, h = rng.choice(sizes); im = cv2.imread(f); H, W = im.shape[:2]
        if w * W < 24 or h * H < 24: continue
        x1, y1 = rng.uniform(0, 1 - w), rng.uniform(0, 1 - h)
        cv2.imwrite(f"{a.dst}/{sp}/other/{n:05d}.jpg", im[int(y1 * H):int((y1 + h) * H), int(x1 * W):int((x1 + w) * W)]); n += 1
    cnt["other"] = n; stats[sp] = cnt; print(sp, cnt, flush=True)
json.dump(dict(build="typecrops-g4", stats=stats, doc=__doc__), open(f"{a.dst}/manifest.json", "w"), indent=1)
