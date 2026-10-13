"""G7 Phase 5 / Addendum B: build train_pool_v7 manifest from the ACCEPTED external sources, group-split.

Nothing here touches a locked split. Every row: source, file (relative to the extracted source root), task, fruit, label,
group, split, sha256 (first 16), dhash. Groups = union of (a) near-duplicate dHash (64-bit, Hamming <= 6) within a source and
(b) for camera-named files (IMG<yyyymmdd><hhmmss>), shots taken <= 30 s apart (same fruit photographed in a burst).
Splits by GROUP, seed 0, 80/10/10 (train/val/test). Exceptions (fixed before looking at any model result):
  * 56c75hvm7r banana: the dataset's own train/val/test kept; its test was the G4 external ripeness test -> never train.
  * w3fg8jjmzr Pakistan guava: whole source = 'eval_only' (independent guava detector eval + guava maturity eval).
  * x4s2jz55dx Egyptian tomato: only 'Three Classes' used (the 'Two Classes' folders re-sort the same photos; verified by sha).
Output: ml/data/builds/v7/train_pool_v7.csv + summary json.
  python ml/data/build_pool_v7.py --ext /workspace/work/cv/g7data/ext --out ml/data/builds/v7
"""
from __future__ import annotations

import argparse
import collections
import csv
import glob
import hashlib
import json
import os
import random
import re
from datetime import datetime

import cv2
import numpy as np


def dhash(path):
    im = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if im is None:
        return None
    s = cv2.resize(im, (9, 8), interpolation=cv2.INTER_AREA).astype(np.int16)
    return int("".join("1" if v else "0" for v in (s[:, 1:] > s[:, :-1]).flatten()), 2)


class UF:
    def __init__(self, n):
        self.p = list(range(n))

    def f(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]; x = self.p[x]
        return x

    def u(self, a, b):
        self.p[self.f(a)] = self.f(b)


def sources(ext):
    R = []  # (source, root, relpath, task, fruit, label, fixed_split)
    z = f"{ext}/zenodo17609211/dataset"
    for f in sorted(glob.glob(f"{z}/*/*")):
        fr, q = os.path.basename(os.path.dirname(f)).split("_")
        R.append(("zenodo17609211", z, os.path.relpath(f, z), "quality_goodbad", fr.lower(), q.lower(), None))
    m = f"{ext}/mangodhds"
    for f in sorted(glob.glob(f"{m}/*/*.jpg")):
        R.append(("mangodhds_b4nrw5hyyc", m, os.path.relpath(f, m), "visible_defect", "mango",
                  os.path.basename(os.path.dirname(f)).lower().replace(" ", "_"), None))
    t = f"{ext}/tomato_eg/Dataset/Three Classes"
    for f in sorted(glob.glob(f"{t}/*/*")):
        R.append(("tomato_eg_x4s2jz55dx", t, os.path.relpath(f, t), "ripeness_or_reject", "tomato", os.path.basename(os.path.dirname(f)).lower(), None))
    b = f"{ext}/banana_56c75hvm7r/BANANA_DATASET"
    for f in sorted(glob.glob(f"{b}/images/*/*/*") + glob.glob(f"{b}/images/*/*.jpg")):
        rel = os.path.relpath(f, b); sp = rel.split("/")[1]
        lab = os.path.basename(f).split("_")[0].lower() if "/" not in rel.split("/", 2)[2] else rel.split("/")[2].lower()
        R.append(("banana_56c75hvm7r", b, rel, "ripeness+det_box", "banana", lab, {"train": "train", "val": "val", "test": "test_reserved"}[sp]))
    g = f"{ext}/guava_pk/Guava Dataset"
    for f in sorted(glob.glob(f"{g}/*/*/*.jpg")):
        v, mat = f.split("/")[-3:-1]
        R.append(("guava_pk_w3fg8jjmzr", g, os.path.relpath(f, g), "guava_eval(variety:" + v + ")", "guava", mat.lower().replace(" ", "_"), "eval_only"))
    return R


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--ext", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    R = [r for r in sources(a.ext) if r[2].lower().endswith((".jpg", ".jpeg", ".png"))]
    rows = []
    for src, root, rel, task, fr, lab, fx in R:
        p = f"{root}/{rel}"; h = dhash(p)
        if h is None:
            continue
        rows.append(dict(source=src, file=rel, task=task, fruit=fr, label=lab, fixed=fx,
                         sha=hashlib.sha256(open(p, "rb").read()).hexdigest()[:16], dhash=h))
    out, summ = [], {}
    rnd = random.Random(0)
    for src in sorted({r["source"] for r in rows}):
        S = [r for r in rows if r["source"] == src]; uf = UF(len(S))
        H = np.array([r["dhash"] for r in S], dtype=np.uint64)
        for i in range(len(S)):  # exact sha dups + dHash <= 6 (O(n^2) popcount, n <= 7k per source)
            x = np.bitwise_xor(H[i + 1:], H[i])
            d = np.array([bin(int(v)).count("1") for v in x]) if len(x) else np.array([])
            for j in np.nonzero(d <= 6)[0]:
                uf.u(i, i + 1 + int(j))
        ts = []
        for i, r in enumerate(S):
            m = re.search(r"IMG_?(\d{8})_?(\d{6})", os.path.basename(r["file"]))
            if m:
                ts.append((datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").timestamp(), i))
        ts.sort()
        for (t1, i1), (t2, i2) in zip(ts, ts[1:]):
            if t2 - t1 <= 30 and S[i1]["label"] == S[i2]["label"] and S[i1]["fruit"] == S[i2]["fruit"]:
                uf.u(i1, i2)
        groups = collections.defaultdict(list)
        for i in range(len(S)):
            groups[uf.f(i)].append(i)
        gids = sorted(groups); rnd.shuffle(gids)
        for k, gid in enumerate(gids):
            sp = "train" if k < 0.8 * len(gids) else "val" if k < 0.9 * len(gids) else "test"
            for i in groups[gid]:
                r = S[i]; r2 = {kk: vv for kk, vv in r.items() if kk not in ("fixed", "dhash")}
                r2.update(group=f"{src}:{gid}", split=r["fixed"] or sp, dhash=f"{r['dhash']:016x}"); out.append(r2)
        cnt = collections.Counter((r["split"], r["label"]) for r in out if r["source"] == src)
        summ[src] = dict(images=len(S), groups=len(groups), largest_group=max(len(v) for v in groups.values()),
                         by_split_label={f"{s}/{l}": n for (s, l), n in sorted(cnt.items())})
    with open(f"{a.out}/train_pool_v7.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
    json.dump(dict(rule=__doc__.split("Output:")[0].strip(), sources=summ), open(f"{a.out}/train_pool_v7_summary.json", "w"), indent=1)
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
