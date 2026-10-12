"""G3: LVIS federated-label hygiene for det-v1/v2 positives (train/val only; locked test untouched).

LVIS is federated: per image, a category is (a) positive (annotated; exhaustive unless it is in
not_exhaustive_category_ids), (b) verified negative (neg_category_ids), or (c) unknown (neither:
may be present but unlabelled). For each det image (COCO id) and each NutriSole class C we map the
LVIS categories of C (ml/data/class_map.csv) and record status:
  pos_exhaustive | pos_not_exhaustive | neg | unknown
Rule for det-v3 (stated before training):
  * train/val image is DROPPED if any NutriSole class present in its labels is pos_not_exhaustive
    (known missing instances of a labelled class -> correct detections are penalised).
  * images with 'unknown' classes are kept (most images; dropping all would remove most data) but
    counted, so G4 can try ignore-masking.
  * test / test_rf are never modified (comparability).
Streams lvis_v1_{train,val}.json.zip with ijson (the train json is ~1 GB).
  python ml/data/sources/lvis_hygiene.py --meta /workspace/work/cv/g3data/lvis_meta --det /workspace/work/cv/g1data/builds/v1/det --out ml/data/builds/v3/lvis_hygiene.json
"""
from __future__ import annotations

import argparse
import collections
import csv
import glob
import json
import os
import zipfile

import ijson

NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
# LVIS v1 category ids for the mapped categories (class_map.csv lvis_fv rows; ids from lvis_v1 categories)
CAT2CLS = {45: "banana", 12: "apple", 735: "citrus", 666: "citrus", 266: "citrus", 639: "lemon_lime", 647: "lemon_lime",
           1099: "tomato", 838: "potato", 342: "cucumber", 217: "carrot", 87: "capsicum"}
LVIS_NAME = sorted(set(CAT2CLS.values()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", required=True)
    ap.add_argument("--det", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    want = {}
    for sp in ["train", "val", "test"]:
        for p in glob.glob(f"{a.det}/images/{sp}/*.jpg"):
            s = os.path.basename(p)[:-4]
            if s.isdigit():
                want[int(s)] = (sp, s)
    cat2cls, info = dict(CAT2CLS), {}
    for fn in ["lvis_v1_val.json.zip", "lvis_v1_train.json.zip"]:
        with zipfile.ZipFile(f"{a.meta}/{fn}") as z:
            with z.open(z.namelist()[0]) as f:
                for im in ijson.items(f, "images.item"):
                    if im["id"] in want:
                        info[im["id"]] = dict(neg=im.get("neg_category_ids", []), nex=im.get("not_exhaustive_category_ids", []))
            # positives per image from annotations
            with z.open(z.namelist()[0]) as f:
                for an in ijson.items(f, "annotations.item"):
                    if an["image_id"] in info and an["category_id"] in cat2cls:
                        info[an["image_id"]].setdefault("pos", set()).add(an["category_id"])
    rep = dict(cat_map={str(k): v for k, v in cat2cls.items()}, per_split={}, drop={})
    for iid, (sp, stem) in want.items():
        d = info.get(iid)
        if d is None:
            rep["per_split"].setdefault(sp, collections.Counter())["no_lvis_meta"] += 1
            continue
        lab = f"{a.det}/labels/{sp}/{stem}.txt"
        present = {NAMES[int(l.split()[0])] for l in open(lab).read().splitlines() if l.strip()} if os.path.exists(lab) else set()
        st = {}
        for k in LVIS_NAME:
            cats = [c for c, v in cat2cls.items() if v == k]
            if any(c in d["nex"] for c in cats) and (k in present or any(c in d.get("pos", ()) for c in cats)):
                st[k] = "pos_not_exhaustive"
            elif k in present or any(c in d.get("pos", ()) for c in cats):
                st[k] = "pos_exhaustive"
            elif any(c in d["neg"] for c in cats):
                st[k] = "neg"
            else:
                st[k] = "unknown"
        c = rep["per_split"].setdefault(sp, collections.Counter())
        c["images"] += 1
        for k, v in st.items():
            c[f"{v}"] += 1
        if any(v == "pos_not_exhaustive" for v in st.values()):
            c["img_with_pos_not_exhaustive"] += 1
            if sp in ("train", "val"):
                rep["drop"].setdefault(sp, []).append(stem)
        if any(v == "unknown" for v in st.values()):
            c["img_with_unknown"] += 1
    rep["per_split"] = {k: dict(v) for k, v in rep["per_split"].items()}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(rep, open(a.out, "w"), indent=1)
    print(json.dumps(rep["per_split"], indent=1), {k: len(v) for k, v in rep["drop"].items()})


if __name__ == "__main__":
    main()
