"""Detection dataset v3 (G3) = det-v2 + audited Open Images V7 produce + mined hard negatives,
with LVIS federated-label hygiene on train/val.

  det/      det-v1 LVIS F&V + Roboflow: train/val MINUS images whose labelled class is
            LVIS not_exhaustive (ml/data/sources/lvis_hygiene.py); test + test_rf UNCHANGED (locked)
  neg/      COCO val2017 backgrounds from det-v2: train/val/neg_test UNCHANGED
  oiv7/     ml/data/sources/oiv7_audit.py output: train/val + NEW split test_oiv7 (OIV7's own test)
  hardneg/  ml/data/sources/hard_negatives.py output: train/val backgrounds (empty labels)
Writes <root>/{train,val,test,test_rf,test_oiv7,neg_test}.txt (absolute paths), det_v3.yaml, and
ml/data/builds/v3/det_manifest.json + per-split list sha256 (test/test_rf must equal v2's).
  python ml/data/build_det_v3.py --root /workspace/work/cv/g3data/det_v3 --out ml/data/builds/v3
"""
from __future__ import annotations

import argparse
import collections
import glob
import hashlib
import json
import os

NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
SRC = dict(det="/workspace/work/cv/g1data/builds/v1/det", neg="/workspace/work/cv/g2data/coco_neg",
           oiv7="/workspace/work/cv/g3data/det_v3_oiv7", hardneg="/workspace/work/cv/g3data/hardneg")


def link_tree(src, dst, splits, skip=frozenset()):
    for sp in splits:
        for kind in ("images", "labels"):
            os.makedirs(f"{dst}/{kind}/{sp}", exist_ok=True)
        for p in glob.glob(f"{src}/images/{sp}/*.jpg"):
            stem = os.path.basename(p)[:-4]
            if stem in skip:
                continue
            d = f"{dst}/images/{sp}/{stem}.jpg"
            if not os.path.exists(d):
                os.link(p, d)
            lp = f"{src}/labels/{sp}/{stem}.txt"
            ld = f"{dst}/labels/{sp}/{stem}.txt"
            if not os.path.exists(ld):
                if os.path.exists(lp):
                    os.link(lp, ld)
                else:
                    open(ld, "w").close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-hygiene", action="store_true")
    a = ap.parse_args()
    hyg = json.load(open(f"{a.out}/lvis_hygiene.json"))
    drop = set() if a.no_hygiene else set(hyg["drop"].get("train", [])) | set(hyg["drop"].get("val", []))
    link_tree(SRC["det"], f"{a.root}/det", ["train", "val"], skip=drop)
    link_tree(SRC["det"], f"{a.root}/det", ["test", "test_rf"])
    link_tree(SRC["neg"], f"{a.root}/neg", ["train", "val", "neg_test"])
    link_tree(SRC["oiv7"], f"{a.root}/oiv7", ["train", "val", "test_oiv7"])
    link_tree(SRC["hardneg"], f"{a.root}/hardneg", ["train", "val"])
    lists = {
        "train": [f"{a.root}/{s}/images/train" for s in ("det", "neg", "oiv7", "hardneg")],
        "val": [f"{a.root}/{s}/images/val" for s in ("det", "neg", "oiv7", "hardneg")],
        "test": [f"{a.root}/det/images/test"], "test_rf": [f"{a.root}/det/images/test_rf"],
        "test_oiv7": [f"{a.root}/oiv7/images/test_oiv7"], "neg_test": [f"{a.root}/neg/images/neg_test"],
    }
    counts = {}
    os.makedirs(a.out, exist_ok=True)
    for sp, dirs in lists.items():
        files = sorted(f for d in dirs for f in glob.glob(f"{d}/*.jpg"))
        open(f"{a.root}/{sp}.txt", "w").write("\n".join(files) + "\n")
        inst, empty, src = collections.Counter(), 0, collections.Counter()
        for f in files:
            src[f.split(a.root + "/")[1].split("/")[0]] += 1
            rows = [l for l in open(f.replace("/images/", "/labels/")[:-4] + ".txt").read().splitlines() if l.strip()]
            empty += not rows
            for r in rows:
                inst[NAMES[int(r.split()[0])]] += 1
        counts[sp] = dict(images=len(files), background_images=empty, by_source=dict(src), instances=dict(sorted(inst.items())))
        open(f"{a.out}/det_{sp}_list_sha256.txt", "w").write(
            hashlib.sha256("\n".join(os.path.basename(f) for f in files).encode()).hexdigest() + "\n")
    yaml = (f"# det-v3 (ml/data/build_det_v3.py); absolute split paths (custom splits resolve vs cwd otherwise)\npath: {a.root}\n"
            + "".join(f"{sp}: {a.root}/{sp}.txt\n" for sp in lists) + "names:\n" + "".join(f"  {i}: {n}\n" for i, n in enumerate(NAMES)))
    open(f"{a.root}/det_v3.yaml", "w").write(yaml)
    open(f"{a.out}/det_v3_template.yaml", "w").write(yaml.replace(a.root, "<root>"))
    v2 = {sp: open(f"{os.path.dirname(a.out)}/v2/det_{sp}_list_sha256.txt").read().strip() for sp in ("test", "test_rf", "neg_test")}
    same = {sp: v2[sp] == open(f"{a.out}/det_{sp}_list_sha256.txt").read().strip() for sp in v2}
    oa = json.load(open(f"{SRC['oiv7']}/audit.json")); hn = json.load(open(f"{SRC['hardneg']}/hardneg.json"))
    man = dict(build="det-v3", base="det-v2", hygiene=("off" if a.no_hygiene else f"dropped {len(drop)} LVIS train/val images with not-exhaustive labelled classes"),
               locked_lists_identical_to_v2=same, oiv7_audit=dict(counters=oa["counters"], drops=oa["drops"], licences=oa["licences"]),
               hardneg=dict(pool=hn["pool"], selected=hn["selected"], selected_textures=hn["selected_textures"], rule=hn["score_rule"]),
               missing_classes=["guava (not an OIV7 boxable class; needs Lahore photos or a licensed set)"],
               counts=counts)
    json.dump(man, open(f"{a.out}/det_manifest.json", "w"), indent=1)
    print(json.dumps(dict(same=same, counts=counts), indent=1))


if __name__ == "__main__":
    main()
