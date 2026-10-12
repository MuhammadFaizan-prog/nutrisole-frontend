"""G3: audit the Open Images V7 produce subset and write the det-v3 OIV7 part (YOLO format).

Input  (--src): extracted oiv7_produce.tgz from Kaggle kernel mfaizannnn/nutrisole-oiv7-produce
        images/<id>.jpg (<=1024 px), labels/<id>.txt (12-class v1 index), boxes_index.csv
        (ImageID,split,cls,IsGroupOf in label-line order), image_licences.csv, stats.json.
        Depictions (IsDepiction=1) were already excluded by the kernel.
Output (--out): images/{train,val,test_oiv7}/, labels/..., audit.json, licences.csv

Audit rules (stated before training; none of them look at the locked test / test_rf):
  1. licence: every image must have a CC licence row (all CC BY 2.0 in this subset) -> else drop.
  2. label sanity: class id in 0..11, box inside [0,1], w,h >= 0.004 -> else drop the box.
  3. IsGroupOf boxes (one box around a pile) are dropped and their region is filled with
     YOLO letterbox grey (114) so the pile is not an unlabelled positive; the remaining
     single-item boxes are pasted back from the original. Image dropped if groups cover >50%.
  4. missing labels: OIV7 boxes are exhaustive only for the image-level labels that were
     verified; lemon/orange MIDs did not resolve in the kernel, so citrus/lemon instances may
     be unlabelled. Screen with the G2 yolo11n detector (480, conf>=0.5): a detection of a
     class not labelled in that image and IoU<0.3 with every GT box is a suspected missing
     label. train/val: grey-fill it. test_oiv7: drop the image (no model-driven edits in test).
  5. dedupe: 64-bit dHash vs every det-v1 image (train/val/test/test_rf) and COCO negatives;
     Hamming <= 6 -> drop from OIV7.
OIV7's own split is kept: train->train, validation->val, test->test_oiv7 (new, separate split).
"""
from __future__ import annotations

import argparse
import collections
import csv
import glob
import json
import os

import cv2
import numpy as np

NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
SPLIT = {"train": "train", "validation": "val", "test": "test_oiv7"}


def dhash(path):
    im = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if im is None:
        return None
    s = cv2.resize(im, (9, 8), interpolation=cv2.INTER_AREA)
    bits = (s[:, 1:] > s[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    i = max(0, x2 - x1) * max(0, y2 - y1)
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0


def xyxy(r, W, H):
    c, x, y, w, h = r
    return [(x - w / 2) * W, (y - h / 2) * H, (x + w / 2) * W, (y + h / 2) * H]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--existing", nargs="+", required=True, help="globs of existing images for dedupe")
    ap.add_argument("--screen-model", required=True)
    ap.add_argument("--screen-imgsz", type=int, default=480)
    ap.add_argument("--screen-conf", type=float, default=0.5)
    a = ap.parse_args()
    lic = {r["ImageID"]: r for r in csv.DictReader(open(f"{a.src}/image_licences.csv"))}
    bidx = collections.defaultdict(list)
    for r in csv.DictReader(open(f"{a.src}/boxes_index.csv")):
        bidx[r["ImageID"]].append(r)
    audit = collections.Counter()
    drops = collections.defaultdict(list)
    # dedupe hashes
    cache = f"{a.out}/_existing_dhash.json"
    os.makedirs(a.out, exist_ok=True)
    if os.path.exists(cache):
        ex = json.load(open(cache))
    else:
        ex = {}
        for g in a.existing:
            for p in glob.glob(g):
                h = dhash(p)
                if h is not None:
                    ex[p] = h
        json.dump(ex, open(cache, "w"))
    exh = np.array(list(ex.values()), dtype=np.uint64)
    exn = list(ex.keys())
    from ultralytics import YOLO
    det = YOLO(a.screen_model)
    lic_rows = []
    per_split = collections.defaultdict(collections.Counter)
    for ip in sorted(glob.glob(f"{a.src}/images/*.jpg")):
        iid = os.path.basename(ip)[:-4]
        rows_meta = bidx.get(iid, [])
        if not rows_meta:
            drops["no_index"].append(iid); continue
        sp = SPLIT[rows_meta[0]["split"]]
        if iid not in lic or "creativecommons" not in lic[iid]["License"]:
            drops["licence"].append(iid); continue
        h = dhash(ip)
        dist = np.array([bin(int(x) ^ h).count("1") for x in exh]) if len(exh) else np.array([99])
        if dist.min() <= 6:
            drops["duplicate"].append(dict(id=iid, match=exn[int(dist.argmin())], hamming=int(dist.min()))); continue
        lab = [l.split() for l in open(f"{a.src}/labels/{iid}.txt").read().splitlines() if l.strip()]
        if len(lab) != len(rows_meta):
            drops["index_mismatch"].append(iid); continue
        im = cv2.imread(ip)
        H, W = im.shape[:2]
        keep, groups = [], []
        for l, m in zip(lab, rows_meta):
            c = int(l[0]); x, y, w, hh = map(float, l[1:])
            if not (0 <= c < 12) or w < 0.004 or hh < 0.004 or x - w / 2 < -0.01 or x + w / 2 > 1.01 or y - hh / 2 < -0.01 or y + hh / 2 > 1.01:
                audit["box_invalid"] += 1; continue
            x1, x2 = max(0, x - w / 2), min(1, x + w / 2); y1, y2 = max(0, y - hh / 2), min(1, y + hh / 2)
            r = (c, (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1)
            if m["IsGroupOf"] == "1":
                groups.append(r); audit["group_boxes_removed"] += 1
            else:
                keep.append(r)
        gmask = np.zeros((H, W), np.uint8)
        for r in groups:
            b = [int(round(v)) for v in xyxy(r, W, H)]
            gmask[max(0, b[1]):b[3], max(0, b[0]):b[2]] = 1
        if gmask.mean() > 0.5:
            drops["group_cover_gt50"].append(iid); continue
        # model screen for missing labels
        res = det.predict(ip, imgsz=a.screen_imgsz, conf=a.screen_conf, verbose=False, device="cpu")[0]
        gtb = [xyxy(r, W, H) for r in keep + groups]
        labelled = {r[0] for r in keep + groups}
        sus = []
        for bb, cc, cf in zip(res.boxes.xyxy.tolist(), res.boxes.cls.tolist(), res.boxes.conf.tolist()):
            if int(cc) in labelled:
                continue
            if all(iou(bb, g) < 0.3 for g in gtb):
                sus.append((int(cc), bb, round(float(cf), 3)))
        if sus and sp == "test_oiv7":
            drops["test_suspected_missing_label"].append(dict(id=iid, sus=[(NAMES[c], cf) for c, _, cf in sus])); continue
        fill = gmask.copy()
        for c, bb, cf in sus:
            b = [int(round(v)) for v in bb]
            fill[max(0, b[1]):b[3], max(0, b[0]):b[2]] = 1
            audit[f"suspected_missing_{NAMES[c]}_filled"] += 1
        if not keep:
            drops["no_single_boxes_left"].append(iid); continue
        if fill.any():
            orig = im.copy()
            im[fill.astype(bool)] = 114
            for r in keep:  # paste labelled single items back
                b = [int(round(v)) for v in xyxy(r, W, H)]
                im[max(0, b[1]):b[3], max(0, b[0]):b[2]] = orig[max(0, b[1]):b[3], max(0, b[0]):b[2]]
            audit["images_greyfilled"] += 1
        os.makedirs(f"{a.out}/images/{sp}", exist_ok=True); os.makedirs(f"{a.out}/labels/{sp}", exist_ok=True)
        cv2.imwrite(f"{a.out}/images/{sp}/oiv7_{iid}.jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 92])
        with open(f"{a.out}/labels/{sp}/oiv7_{iid}.txt", "w") as f:
            for r in keep:
                f.write(f"{r[0]} {r[1]:.6f} {r[2]:.6f} {r[3]:.6f} {r[4]:.6f}\n")
                per_split[sp][NAMES[r[0]]] += 1
        per_split[sp]["_images"] += 1
        lic_rows.append(dict(file=f"oiv7_{iid}.jpg", split=sp, **{k: lic[iid][k] for k in ["License", "Author", "OriginalURL"]}))
    with open(f"{a.out}/licences.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "split", "License", "Author", "OriginalURL"]); w.writeheader(); w.writerows(lic_rows)
    out = dict(rules=__doc__.split("Audit rules")[1].split("OIV7's own")[0].strip(), counters=dict(audit),
               drops={k: len(v) for k, v in drops.items()}, drop_detail=drops,
               kept=dict((k, dict(v)) for k, v in per_split.items()), licences=dict(collections.Counter(r["License"] for r in lic_rows)),
               screen_model=a.screen_model, screen_imgsz=a.screen_imgsz, screen_conf=a.screen_conf)
    json.dump(out, open(f"{a.out}/audit.json", "w"), indent=1)
    print(json.dumps({k: out[k] for k in ["counters", "drops", "kept", "licences"]}, indent=1))


if __name__ == "__main__":
    main()
