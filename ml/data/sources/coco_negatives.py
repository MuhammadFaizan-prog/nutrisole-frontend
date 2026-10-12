"""COCO val2017 background (negative) images for the detector: scenes with NO produce.

Source: COCO 2017 val images (images.cocodataset.org, Flickr licences per image; COCO
annotations CC BY 4.0) + Ultralytics' YOLO-format COCO labels (coco2017labels.zip).
Selection rule (stated, not tuned on test):
  - image has >=1 COCO label (so it is a real scene, not blank) and NONE of the COCO
    food/tableware classes 39-55 (bottle, wine glass, cup, fork, knife, spoon, bowl,
    banana, apple, sandwich, orange, broccoli, carrot, hot dog, pizza, donut, cake)
    nor 60 (dining table) -> low chance of unlabelled produce;
  - image id NOT in LVIS Fruits & Vegetables (any split; those contain produce) and NOT
    in coco128 (used for the G1/G2 negative gauntlet clips);
  - deterministic: sorted by md5(id + 'nutrisole-neg'), first N taken.
Splits: train / val / neg_test (neg_test is LOCKED: image-level false-alarm metric).
Idempotent: existing non-empty files are skipped; writes sha256 log + selection json.

  python ml/data/sources/coco_negatives.py --out /workspace/work/cv/g2data/coco_neg --n-train 290 --n-val 50 --n-test 80
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import glob
import hashlib
import io
import json
import os
import subprocess
import urllib.request
import zipfile

LABELS_ZIP = "https://github.com/ultralytics/assets/releases/download/v0.0.0/coco2017labels.zip"
IMG = "http://images.cocodataset.org/val2017/{}.jpg"
BAD = set(range(39, 56)) | {60}
DATA = os.environ.get("NUTRISOLE_DATA", "/workspace/work/cv/g1data")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--labels-zip", default="/tmp/coco_labels.zip")
    ap.add_argument("--n-train", type=int, default=290)
    ap.add_argument("--n-val", type=int, default=50)
    ap.add_argument("--n-test", type=int, default=80)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if not os.path.exists(a.labels_zip):
        urllib.request.urlretrieve(LABELS_ZIP, a.labels_zip)
    excl = {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(f"{DATA}/lvis/labels/*/*.txt")}
    excl |= {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(f"{DATA}/neg/coco128/images/*/*.jpg")}
    cand = []
    with zipfile.ZipFile(a.labels_zip) as z:
        for n in z.namelist():
            if "/labels/val2017/" not in n or not n.endswith(".txt"):
                continue
            stem = os.path.splitext(os.path.basename(n))[0]
            if stem in excl:
                continue
            cls = {int(l.split()[0]) for l in z.read(n).decode().splitlines() if l.strip()}
            if cls and not (cls & BAD):
                cand.append(stem)
    cand.sort(key=lambda s: hashlib.md5((s + "nutrisole-neg").encode()).hexdigest())
    sel = {"train": cand[:a.n_train], "val": cand[a.n_train:a.n_train + a.n_val],
           "neg_test": cand[a.n_train + a.n_val:a.n_train + a.n_val + a.n_test]}
    jobs = []
    for sp, ids in sel.items():
        os.makedirs(f"{a.out}/images/{sp}", exist_ok=True)
        os.makedirs(f"{a.out}/labels/{sp}", exist_ok=True)
        for i in ids:
            open(f"{a.out}/labels/{sp}/{i}.txt", "w").close()  # empty label = background image
            jobs.append((i, f"{a.out}/images/{sp}/{i}.jpg"))

    def fetch(j):
        i, p = j
        if os.path.exists(p) and os.path.getsize(p) > 0:
            return p, hashlib.sha256(open(p, "rb").read()).hexdigest()
        b = None
        for _ in range(4):
            try:
                # curl, not urllib: the sandbox HTTP proxy returns 404 to urllib for this host
                b = subprocess.run(["curl", "-sf", "-m", "60", IMG.format(i)], capture_output=True, check=True).stdout
                break
            except Exception as e:  # transient CDN errors: retry, then drop the image
                err = repr(e)
        if b is None:
            for q in (p, p.replace("/images/", "/labels/")[:-4] + ".txt"):
                if os.path.exists(q):
                    os.remove(q)
            return p, "FAILED " + err
        open(p + ".part", "wb").write(b)
        os.replace(p + ".part", p)
        return p, hashlib.sha256(b).hexdigest()

    with cf.ThreadPoolExecutor(8) as ex:
        res = list(ex.map(fetch, jobs))
    with open(f"{a.out}/sha256.txt", "w") as fh:
        for p, h in sorted(res):
            fh.write(f"{h}  {os.path.relpath(p, a.out)}\n")
    failed = [p for p, h in res if h.startswith("FAILED")]
    json.dump(dict(rule="COCO val2017, no classes 39-55/60, not in LVIS F&V or coco128", candidates=len(cand),
                   counts={k: len(v) for k, v in sel.items()}, failed=failed, ids=sel), open(f"{a.out}/selection.json", "w"), indent=1)
    print({k: len(v) for k, v in sel.items()}, "candidates", len(cand))


if __name__ == "__main__":
    main()
