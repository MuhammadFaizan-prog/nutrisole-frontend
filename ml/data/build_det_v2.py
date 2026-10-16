"""Detection dataset v2 = det-v1 (all splits unchanged) + COCO val2017 background images.

v2 adds only NON-produce negatives (ml/data/sources/coco_negatives.py): train +290, val +50,
plus a LOCKED neg_test (80) for an image-level false-alarm metric. Train/val/test/test_rf
positives are byte-identical to v1, so G1 and G2 test numbers are directly comparable.
Open Images V7 mango/pomegranate: BLOCKED in G2 (storage.googleapis.com/openimages returns
403 AccessDenied from this sandbox for every annotation CSV; guava is not an OIV7 boxable
class at all) -> v2 still covers 9/12 classes.

Writes list files (absolute paths under --root) + a YAML + manifest.json:
  python ml/data/build_det_v2.py --root /tmp/nsdata2 --out ml/data/builds/v2
--root must contain det/ (copy of g1data/builds/v1/det) and neg/ (copy of g2data/coco_neg).
"""
from __future__ import annotations

import argparse
import collections
import glob
import hashlib
import json
import os

NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    lists = {}
    for sp in ["train", "val", "test", "test_rf"]:
        lists[sp] = sorted(glob.glob(f"{a.root}/det/images/{sp}/*.jpg"))
    for sp in ["train", "val", "neg_test"]:
        neg = sorted(glob.glob(f"{a.root}/neg/images/{sp}/*.jpg"))
        lists[sp] = lists.get(sp, []) + neg
    counts = {}
    for sp, files in lists.items():
        with open(f"{a.root}/{sp}.txt", "w") as fh:
            fh.write("\n".join(files) + "\n")
        inst = collections.Counter()
        empty = 0
        for f in files:
            lp = f.replace("/images/", "/labels/")[:-4] + ".txt"
            rows = [l for l in open(lp).read().splitlines() if l.strip()] if os.path.exists(lp) else []
            empty += not rows
            for r in rows:
                inst[NAMES[int(r.split()[0])]] += 1
        counts[sp] = dict(images=len(files), background_images=empty,
                          coco_negatives=sum("/neg/" in f for f in files), instances=dict(sorted(inst.items())))
        with open(f"{a.out}/det_{sp}_list_sha256.txt", "w") as fh:
            fh.write(hashlib.sha256("\n".join(os.path.basename(f) for f in files).encode()).hexdigest() + "\n")
    yaml = (f"# det-v2 (built by ml/data/build_det_v2.py); machine-specific root\npath: {a.root}\n"
            "train: train.txt\nval: val.txt\ntest: test.txt\nnames:\n" + "".join(f"  {i}: {n}\n" for i, n in enumerate(NAMES)))
    open(f"{a.root}/det_v2.yaml", "w").write(yaml)
    open(f"{a.out}/det_v2_template.yaml", "w").write(yaml.replace(a.root, "<root>"))
    neg_sel = json.load(open(f"{a.root}/neg/selection.json"))
    man = dict(build="det-v2", base="det-v1 (ml/data/builds/v1/det_manifest.json), positives unchanged",
               added="COCO val2017 backgrounds: " + neg_sel["rule"], neg_candidates=neg_sel["candidates"],
               blocked=["Open Images V7 mango/pomegranate: annotation CSVs 403 AccessDenied (2026-10-12)", "guava: not an OIV7 boxable class"],
               counts=counts)
    json.dump(man, open(f"{a.out}/det_manifest.json", "w"), indent=1)
    print(json.dumps(counts, indent=1))


if __name__ == "__main__":
    main()
