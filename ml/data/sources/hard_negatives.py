"""G3: hard-negative mining for the detector (texture / clutter false alarms).

Pool (no produce expected, nothing locked):
  * COCO val2017 + a train2017 sample, same filter as coco_negatives.py (>=1 COCO label, none of
    classes 39-55/60 food+tableware+dining table), NOT in LVIS F&V, NOT in coco128 (G1 neg clip),
    NOT already used by det-v2 negatives (train/val/neg_test). train2017 sample is biased to
    crowd/texture scenes: >=6 persons, or chair/bench/couch/umbrella/sports ball/kite/clock present.
  * synthetic textures (own generator, NOT make_videos.make_bg): stripes, checker, bricks, fabric
    weave, dot grids (incl. red/orange dots = stadium seats), bokeh lights, wood grain, solid colour.
Mining: run the G2 detectors (yolo11n 640-trained @480, yolo26n @384) and the G1 detector @320 on the
pool (Ultralytics, CPU, conf 0.25); score = max over models of (max box conf) + 0.02*(#boxes>=0.25).
Selection: top-N by score (ties broken by md5) -> train; next N_val -> val. Images written with EMPTY
label files (background). neg_test and the negtest/G1 clips are never touched.
  python ml/data/sources/hard_negatives.py --out /workspace/work/cv/g3data/hardneg --stage all
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import glob
import hashlib
import json
import os
import random
import subprocess
import urllib.request
import zipfile

import cv2
import numpy as np

LABELS_ZIP = "https://github.com/ultralytics/assets/releases/download/v0.0.0/coco2017labels.zip"
IMG = "http://images.cocodataset.org/{}/{}.jpg"
BAD = set(range(39, 56)) | {60}
TEXTURE_COCO = {56, 57, 13, 25, 32, 33, 74}  # chair, couch, bench, umbrella, sports ball, kite, clock
DATA = "/workspace/work/cv/g1data"
NEG = "/workspace/work/cv/g2data/coco_neg"


def h(s):
    return hashlib.md5((s + "nutrisole-hardneg").encode()).hexdigest()


def pool(a):
    zp = f"{a.out}/coco2017labels.zip"
    if not os.path.exists(zp):
        urllib.request.urlretrieve(LABELS_ZIP, zp + ".part"); os.rename(zp + ".part", zp)
    excl = {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(f"{DATA}/lvis/labels/*/*.txt")}
    excl |= {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(f"{DATA}/neg/coco128/images/*/*.jpg")}
    sel = json.load(open(f"{NEG}/selection.json"))
    for v in sel["ids"].values():
        excl |= set(v)
    val, tr = [], []
    with zipfile.ZipFile(zp) as z:
        for n in z.namelist():
            if not n.endswith(".txt") or "/labels/" not in n:
                continue
            sp = "val2017" if "/val2017/" in n else "train2017" if "/train2017/" in n else None
            if not sp:
                continue
            stem = os.path.splitext(os.path.basename(n))[0]
            if stem in excl:
                continue
            rows = [l.split() for l in z.read(n).decode().splitlines() if l.strip()]
            cls = [int(r[0]) for r in rows]
            if not cls or set(cls) & BAD:
                continue
            if sp == "val2017":
                val.append(stem)
            elif cls.count(0) >= 6 or set(cls) & TEXTURE_COCO:
                tr.append(stem)
    val = sorted(val, key=h)[: a.n_val_pool]
    tr = sorted(tr, key=h)[: a.n_train_pool]
    return [("val2017", s) for s in val] + [("train2017", s) for s in tr]


def download(a, items):
    d = f"{a.out}/pool"; os.makedirs(d, exist_ok=True)

    def one(it):
        sp, s = it
        p = f"{d}/{s}.jpg"
        if os.path.exists(p) and os.path.getsize(p) > 0:
            return p
        for _ in range(3):
            # urllib gets HTTP 404 from images.cocodataset.org in this sandbox; curl works
            r = subprocess.run(["curl", "-sfL", "-o", p + ".part", IMG.format(sp, s)])
            if r.returncode == 0 and os.path.getsize(p + ".part") > 1000:
                os.rename(p + ".part", p); return p
        return None
    with cf.ThreadPoolExecutor(16) as ex:
        return [p for p in ex.map(one, items) if p]


def textures(a, n):
    d = f"{a.out}/pool"; os.makedirs(d, exist_ok=True)
    rnd = random.Random(2026)
    out = []
    for k in range(n):
        p = f"{d}/tex_{k:03d}.jpg"
        out.append(p)
        if os.path.exists(p):
            continue
        W, H = 640, 480
        kind = ["stripes", "checker", "bricks", "weave", "dots", "reddots", "bokeh", "wood", "solid"][k % 9]
        col = np.array([rnd.randint(0, 255) for _ in range(3)], np.float32)
        col2 = np.array([rnd.randint(0, 255) for _ in range(3)], np.float32)
        img = np.zeros((H, W, 3), np.float32) + col
        yy, xx = np.mgrid[0:H, 0:W]
        if kind == "stripes":
            per = rnd.randint(8, 60); ang = rnd.uniform(0, np.pi)
            m = (np.sin((xx * np.cos(ang) + yy * np.sin(ang)) * 2 * np.pi / per) > 0)
            img[m] = col2
        elif kind == "checker":
            s = rnd.randint(10, 80); img[((xx // s + yy // s) % 2) == 1] = col2
        elif kind == "bricks":
            bh, bw = rnd.randint(15, 40), rnd.randint(40, 100)
            img[:] = (rnd.randint(120, 180), rnd.randint(60, 90), rnd.randint(150, 210))[::-1] if rnd.random() < .5 else col
            m = (yy % bh < 3) | (((xx + (yy // bh % 2) * bw // 2) % bw) < 3)
            img[m] = (200, 200, 200)
        elif kind == "weave":
            per = rnd.randint(4, 12)
            img += 25 * np.sin(xx * 2 * np.pi / per)[..., None] * np.sin(yy * 2 * np.pi / per)[..., None]
        elif kind in ("dots", "reddots"):
            r = rnd.randint(6, 22); sp = r * 2 + rnd.randint(4, 20)
            c2 = (rnd.randint(0, 60), rnd.randint(20, 90), rnd.randint(170, 255)) if kind == "reddots" else tuple(col2.tolist())
            for y in range(sp // 2, H, sp):
                off = (y // sp % 2) * sp // 2
                for x in range(sp // 2 + off, W, sp):
                    cv2.ellipse(img, (x, y), (r, int(r * rnd.uniform(.7, 1.0))), 0, 0, 360, c2, -1)
        elif kind == "bokeh":
            img[:] = col * 0.25
            for _ in range(rnd.randint(15, 60)):
                c3 = tuple(float(v) for v in np.clip(np.array([rnd.randint(80, 255) for _ in range(3)]), 0, 255))
                cv2.circle(img, (rnd.randint(0, W), rnd.randint(0, H)), rnd.randint(8, 50), c3, -1)
            img = cv2.GaussianBlur(img, (0, 0), 6)
        elif kind == "wood":
            img[:] = (rnd.randint(30, 70), rnd.randint(70, 110), rnd.randint(120, 170))
            img += 20 * np.sin((yy + 15 * np.sin(xx / 40.0)) / rnd.uniform(3, 8))[..., None]
        img += np.random.default_rng(k).normal(0, 6, img.shape)
        cv2.imwrite(p, np.clip(img, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 90])
    return out


def mine(a, paths):
    cache = f"{a.out}/scores.json"
    sc = json.load(open(cache)) if os.path.exists(cache) else {}
    from ultralytics import YOLO
    for mp, sz in a.models:
        tag = f"{os.path.basename(os.path.dirname(os.path.dirname(mp)))}@{sz}"
        todo = [p for p in paths if tag not in sc.get(os.path.basename(p), {})]
        if not todo:
            continue
        m = YOLO(mp)
        for i in range(0, len(todo), 16):
            for p, r in zip(todo[i:i + 16], m.predict(todo[i:i + 16], imgsz=sz, conf=0.25, verbose=False, device="cpu")):
                cf_ = r.boxes.conf.tolist()
                sc.setdefault(os.path.basename(p), {})[tag] = dict(max=round(max(cf_), 4) if cf_ else 0.0, n=len(cf_),
                                                                   cls=[int(c) for c in r.boxes.cls.tolist()][:20])
            if i % 160 == 0:
                json.dump(sc, open(cache, "w")); print(tag, i, len(todo), flush=True)
        json.dump(sc, open(cache, "w"))
    return sc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--stage", default="all")
    ap.add_argument("--n-val-pool", type=int, default=1300)
    ap.add_argument("--n-train-pool", type=int, default=900)
    ap.add_argument("--n-tex", type=int, default=180)
    ap.add_argument("--n-sel-train", type=int, default=520)
    ap.add_argument("--n-sel-val", type=int, default=60)
    a = ap.parse_args()
    R = "/workspace/work/nutrisole/ml/runs"
    a.models = [(f"{R}/G2/kaggle_det_yolo11n_640/runs/det_yolo11n_640/weights/best.pt", 480),
                (f"{R}/G2/kaggle_det_yolo26n_640/runs/det_yolo26n_640/weights/best.pt", 384),
                (f"{R}/G1/det_yolo26n_320/weights/best.pt", 320)]
    os.makedirs(a.out, exist_ok=True)
    items = pool(a)
    print("pool", len(items), flush=True)
    paths = download(a, items) + textures(a, a.n_tex)
    print("downloaded", len(paths), flush=True)
    if a.stage == "download":
        return
    sc = mine(a, paths)

    def score(k):
        v = sc[k].values()
        return max(x["max"] + 0.02 * x["n"] for x in v)
    keys = sorted([os.path.basename(p) for p in paths], key=lambda k: (-score(k), h(k)))
    hits = [k for k in keys if score(k) > 0]
    sel = dict(train=hits[: a.n_sel_train], val=hits[a.n_sel_train: a.n_sel_train + a.n_sel_val])
    for sp, ks in sel.items():
        os.makedirs(f"{a.out}/images/{sp}", exist_ok=True); os.makedirs(f"{a.out}/labels/{sp}", exist_ok=True)
        for k in ks:
            dst = f"{a.out}/images/{sp}/hn_{k}"
            if not os.path.exists(dst):
                os.link(f"{a.out}/pool/{k}", dst)
            open(f"{a.out}/labels/{sp}/hn_{k[:-4]}.txt", "w").close()
    rep = dict(pool=len(paths), with_fp_any_model=len(hits), selected={k: len(v) for k, v in sel.items()},
               selected_textures={k: sum(x.startswith("tex_") for x in v) for k, v in sel.items()},
               score_rule="max over models of (max conf + 0.02*#boxes>=0.25)", models=[f"{m}@{s}" for m, s in a.models],
               top20=[(k, round(score(k), 3)) for k in keys[:20]], selection=sel)
    json.dump(rep, open(f"{a.out}/hardneg.json", "w"), indent=1)
    print(json.dumps({k: rep[k] for k in ["pool", "with_fp_any_model", "selected", "selected_textures", "top20"]}, indent=1))


if __name__ == "__main__":
    main()
