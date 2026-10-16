"""Build detection dataset v1 (CPU scale) from LVIS Fruits & Vegetables (HF mirror).

Source: huggingface.co/datasets/henningheyen/LVIS_Fruits_And_Vegetables (Apache-2.0 card;
images are COCO/LVIS photos with their own Flickr licences, plus a 180-image manually
labelled Roboflow test split). Images come from the dataset's parquet shards (which keep
the original file name); boxes from labels/{train,val,test}/*.txt (YOLO format, 63 classes).

Remap through ml/data/class_map.csv to the 12 NutriSole v1 ids (mango, guava,
pomegranate have no boxes here). Other LVIS produce annotations are dropped; images that
only contain dropped produce are kept as hard negatives (unsupported produce -> no box).

Splits (no image crosses):
  train  <- HF train (subsampled to --max-train positives for the CPU budget)
  val    <- HF validation, first half by md5 order (subsampled to --max-val)
  test   <- HF validation, second half (LVIS domain, locked)
  test_rf<- HF test (180 manually labelled photos; grouped by session uuid; locked)
Dedupe: MD5 exact + pHash<=4 across splits (later split loses the duplicate).
LVIS is a federated dataset: not every instance of a class is guaranteed annotated in
every image (missing-label noise); recorded in the manifest.
"""
from __future__ import annotations

import argparse
import collections
import csv
import glob
import hashlib
import io
import json
import os
import random
import re
import shutil

import cv2
import imagehash
import numpy as np
import pyarrow.parquet as pq
from PIL import Image

DATA = os.environ.get("NUTRISOLE_DATA", "/workspace/work/cv/g1data")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LV = f"{DATA}/lvis"
NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]


def load_map():
    m = {}
    with open(f"{REPO}/ml/data/class_map.csv") as fh:
        for row in csv.DictReader(fh):
            if row["source"] == "lvis_fv" and row["source_id"] not in ("", "*"):
                m[int(row["source_id"])] = int(row["nutrisole_id"])
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-train", type=int, default=2400)
    ap.add_argument("--max-val", type=int, default=400)
    ap.add_argument("--max-test", type=int, default=600)
    ap.add_argument("--neg-frac", type=float, default=0.10)
    ap.add_argument("--side", type=int, default=640)
    a = ap.parse_args()
    rnd = random.Random(0)
    cmap = load_map()
    out = f"{DATA}/builds/v1/det"
    shutil.rmtree(out, ignore_errors=True)
    shards = {"train": sorted(glob.glob(f"{LV}/data/train-*.parquet")), "val": glob.glob(f"{LV}/data/validation-*.parquet"),
              "test": glob.glob(f"{LV}/data/test-*.parquet")}
    items = []
    missing_lbl = collections.Counter()
    for hf_split, files in shards.items():
        for f in files:
            t = pq.read_table(f, columns=["image"])
            for row in t.column("image").to_pylist():
                name = row["path"]
                stem = os.path.splitext(name)[0]
                lp = f"{LV}/labels/{hf_split}/{stem}.txt"
                if not os.path.exists(lp):
                    missing_lbl[hf_split] += 1
                    continue
                objs, other = [], 0
                for line in open(lp).read().strip().splitlines():
                    p = line.split()
                    if len(p) != 5:
                        continue
                    c = int(p[0])
                    x, y, w, h = map(float, p[1:])
                    if w <= 0 or h <= 0 or not (0 <= x <= 1 and 0 <= y <= 1):
                        continue
                    if c in cmap:
                        objs.append((cmap[c], x, y, min(w, 1.0), min(h, 1.0)))
                    else:
                        other += 1
                items.append(dict(hf_split=hf_split, name=name, bytes=row["bytes"], objs=objs, other=other))
    print("items", len(items), "missing labels", dict(missing_lbl), flush=True)
    for it in items:
        it["md5"] = hashlib.md5(it["bytes"]).hexdigest()
    # assign splits
    val_items = sorted([i for i in items if i["hf_split"] == "val"], key=lambda i: i["md5"])
    half = len(val_items) // 2
    for i, it in enumerate(val_items):
        it["split"] = "val" if i < half else "test"
    for it in items:
        if it["hf_split"] == "train":
            it["split"] = "train"
        elif it["hf_split"] == "test":
            it["split"] = "test_rf"
            m = re.match(r"\d+_([0-9a-f-]{36})_", it["name"])
            it["group"] = m.group(1) if m else it["name"]
    caps = {"train": a.max_train, "val": a.max_val, "test": a.max_test, "test_rf": 10 ** 9}
    chosen = []
    for s in ["test_rf", "test", "val", "train"]:  # locked sets first so dedupe removes from train
        pos = [i for i in items if i["split"] == s and i["objs"]]
        neg = [i for i in items if i["split"] == s and not i["objs"] and i["other"] > 0]
        rnd.shuffle(pos)
        rnd.shuffle(neg)
        pos = pos[:caps[s]]
        neg = neg[:int(len(pos) * a.neg_frac)] if s != "test_rf" else neg
        chosen += pos + neg
    seen_md5, seen_ph, kept, dropped = set(), [], [], collections.Counter()
    for it in chosen:
        if it["md5"] in seen_md5:
            dropped[("md5", it["split"])] += 1
            continue
        img = Image.open(io.BytesIO(it["bytes"])).convert("RGB")
        ph = imagehash.phash(img)
        if any(ph - q <= 4 for q in seen_ph):
            dropped[("phash", it["split"])] += 1
            continue
        seen_md5.add(it["md5"])
        seen_ph.append(ph)
        it["phash"] = str(ph)
        im = np.array(img)[:, :, ::-1]
        h, w = im.shape[:2]
        s = a.side / max(h, w)
        if s < 1:
            im = cv2.resize(im, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
        stem = os.path.splitext(it["name"])[0][:80]
        os.makedirs(f"{out}/images/{it['split']}", exist_ok=True)
        os.makedirs(f"{out}/labels/{it['split']}", exist_ok=True)
        cv2.imwrite(f"{out}/images/{it['split']}/{stem}.jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 92])
        with open(f"{out}/labels/{it['split']}/{stem}.txt", "w") as fh:
            for c, x, y, w_, h_ in it["objs"]:
                fh.write(f"{c} {x:.6f} {y:.6f} {w_:.6f} {h_:.6f}\n")
        it["stem"] = stem
        kept.append(it)
    cnt_img = collections.Counter(i["split"] for i in kept)
    cnt_neg = collections.Counter(i["split"] for i in kept if not i["objs"])
    cnt_obj = collections.Counter((i["split"], NAMES[o[0]]) for i in kept for o in i["objs"])
    cnt_imgcls = collections.Counter((i["split"], NAMES[c]) for i in kept for c in {o[0] for o in i["objs"]})
    listing = "\n".join(sorted(f"{i['split']}/{i['stem']},{i['md5']}" for i in kept)).encode()
    manifest = dict(build="det-v1", source="henningheyen/LVIS_Fruits_And_Vegetables@51362ad3532292d29e63f9e46c2cd33945ffe6b5",
                    names=NAMES, params=vars(a), missing_label_files=dict(missing_lbl),
                    images=dict(cnt_img), negatives=dict(cnt_neg),
                    instances={f"{s}/{c}": n for (s, c), n in sorted(cnt_obj.items())},
                    images_with_class={f"{s}/{c}": n for (s, c), n in sorted(cnt_imgcls.items())},
                    dedupe_dropped={f"{k[0]}:{k[1]}": v for k, v in dropped.items()},
                    classes_without_data=[n for n in NAMES if not any(c == n for (_, c) in cnt_obj)],
                    test_rf_groups=len({i.get('group') for i in kept if i['split'] == 'test_rf'}),
                    listing_sha256=hashlib.sha256(listing).hexdigest(),
                    caveats=["LVIS is federated: unannotated instances of a class can exist (missing-label noise)",
                             "COCO-derived photos: cluttered everyday scenes, few close-up market shots",
                             "test_rf (180 imgs) has session uuids; several photos per session, all inside test_rf"])
    os.makedirs(f"{REPO}/ml/data/builds/v1", exist_ok=True)
    json.dump(manifest, open(f"{REPO}/ml/data/builds/v1/det_manifest.json", "w"), indent=1)
    print(json.dumps({k: manifest[k] for k in ["images", "negatives", "dedupe_dropped", "classes_without_data", "missing_label_files"]}))


if __name__ == "__main__":
    main()
