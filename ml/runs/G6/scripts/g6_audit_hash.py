#!/usr/bin/env python3
"""G6.1 audit step A: hash every image of every detector split (md5 + 64-bit dHash + 64-bit pHash, size,
label stats). Idempotent: writes g6data/audit/hashes.jsonl (resumes by skipping already-hashed paths).
Read-only on datasets."""
import os, sys, json, hashlib, glob
from multiprocessing import Pool
import cv2, numpy as np
OUT = "/workspace/work/cv/g6data/audit"; os.makedirs(OUT, exist_ok=True)
D3 = "/workspace/work/cv/g3data/det_v3"
LISTS = {s: f"{D3}/{s}.txt" for s in ["train", "val", "test", "test_rf", "test_oiv7", "neg_test"]}
LISTS["test_oiv7c"] = "/workspace/work/cv/g4data/test_oiv7c.txt"
GLOBS = {"oiv7c_train": "/workspace/work/cv/g4data/oiv7c/images/train/*.jpg",
         "oiv7c_val": "/workspace/work/cv/g4data/oiv7c/images/val/*.jpg",
         "g5hn_train": "/workspace/work/cv/g5data/g5hn/images/train/*"}


def items():
    for s, f in LISTS.items():
        for p in open(f).read().split():
            yield s, p
    for s, g in GLOBS.items():
        for p in sorted(glob.glob(g)):
            yield s, p


def lblpath(p):
    return p.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"


def phash(g):
    s = cv2.resize(g, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    d = cv2.dct(s)[:8, :8].flatten(); m = np.median(d[1:])
    return int("".join("1" if v > m else "0" for v in d), 2)


def dhash(g):
    s = cv2.resize(g, (9, 8), interpolation=cv2.INTER_AREA)
    return int("".join("1" if v else "0" for v in (s[:, 1:] > s[:, :-1]).flatten()), 2)


def work(a):
    s, p = a
    r = dict(split=s, path=p)
    try:
        b = open(p, "rb").read(); r["md5"] = hashlib.md5(b).hexdigest()
        im = cv2.imdecode(np.frombuffer(b, np.uint8), cv2.IMREAD_COLOR)
        h, w = im.shape[:2]; r["w"], r["h"] = w, h
        g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        r["ph"], r["dh"] = phash(g), dhash(g)
        r["mean"] = float(g.mean())
    except Exception as e:
        r["err"] = str(e)[:200]
    lp = lblpath(p); boxes = []
    if os.path.exists(lp):
        for l in open(lp).read().splitlines():
            t = l.split()
            if len(t) >= 5: boxes.append([int(t[0])] + [float(x) for x in t[1:5]])
    r["boxes"] = boxes; r["has_label_file"] = os.path.exists(lp)
    return r


if __name__ == "__main__":
    fo = f"{OUT}/hashes.jsonl"; done = set()
    if os.path.exists(fo):
        for l in open(fo):
            try: j = json.loads(l); done.add((j["split"], j["path"]))
            except Exception: pass
    todo = [a for a in items() if a not in done]
    print("todo", len(todo), "done", len(done), flush=True)
    with open(fo, "a") as f, Pool(2) as pool:
        for i, r in enumerate(pool.imap_unordered(work, todo, chunksize=16)):
            f.write(json.dumps(r) + "\n")
            if i % 500 == 0: f.flush(); print(i, flush=True)
    open(f"{OUT}/HASH_DONE", "w").write("ok")
