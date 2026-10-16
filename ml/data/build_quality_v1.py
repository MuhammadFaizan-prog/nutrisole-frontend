"""Build quality dataset v1 (classification crops) with dedupe + GROUPED splits.

Sources: Sultana originals (5 v1 fruits, fresh/rotten) and FruQ-DB (Fresh/Mild/Rotten,
no per-image fruit type). Steps:
  1. resize originals to max side 384 into a pool (training is at <=224)
  2. MD5 exact-duplicate removal, 64-bit pHash
  3. ImageNet embedding (yolo26n-cls backbone) for near-duplicate / same-object grouping
  4. union-find groups:  pHash Hamming <= PHASH_T  OR  cosine >= COS_T (within source)
     FruQ-DB additionally: k-means on embeddings (K_FRUQ clusters) as a proxy for the
     source time-lapse video, because FruQ frames come from ~11 YouTube time-lapses and
     carry no video id. A whole cluster stays in one split.
  5. split by group 70/15/15 (stratified by fruit x level for Sultana)
  6. write Ultralytics classify folders quality2/ (Sultana fresh/rotten) and quality3/
     (Sultana + FruQ, fresh/mild/rotten) + manifest.json with counts, hashes and a
     cross-split leakage audit (max cross-split cosine, min cross-split pHash distance).
Run: python ml/data/build_quality_v1.py  (env NUTRISOLE_DATA, default /workspace/work/cv/g1data)
"""
from __future__ import annotations

import collections
import glob
import hashlib
import io
import json
import os
import random
import shutil
import sys
import zipfile

import cv2
import imagehash
import numpy as np
from PIL import Image

DATA = os.environ.get("NUTRISOLE_DATA", "/workspace/work/cv/g1data")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(DATA, "builds/v1")
POOL = os.path.join(OUT, "_pool")
PHASH_T, COS_T, K_FRUQ, SEED = 8, 0.93, 40, 0
FRUIT2CLASS = {"apple": "apple", "banana": "banana", "guava": "guava", "orange": "citrus", "pomegranate": "pomegranate"}


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def resize_max(im: np.ndarray, side: int = 384) -> np.ndarray:
    h, w = im.shape[:2]
    s = side / max(h, w)
    return cv2.resize(im, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA) if s < 1 else im


def ingest() -> list[dict]:
    recs = []
    os.makedirs(f"{POOL}/sultana", exist_ok=True)
    os.makedirs(f"{POOL}/fruq", exist_ok=True)
    for f in sorted(glob.glob(f"{DATA}/sultana/raw/*.jpg")):
        name = os.path.basename(f)
        fruit, lab, idx = name[:-4].split("_")
        dst = f"{POOL}/sultana/{name}"
        raw = open(f, "rb").read()
        if not os.path.exists(dst):
            im = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_REDUCED_COLOR_4)
            cv2.imwrite(dst, resize_max(im), [cv2.IMWRITE_JPEG_QUALITY, 92])
        recs.append(dict(id=f"sultana/{name}", src="sultana_agml", path=dst, md5=md5(raw), produce=FRUIT2CLASS[fruit],
                         level="fresh" if lab == "0" else "rotten", src_index=int(idx)))
    z = zipfile.ZipFile(f"{DATA}/fruq/FruQ-DB.zip")
    for n in sorted(z.namelist()):
        if n.endswith("/") or not n.lower().endswith((".png", ".jpg", ".jpeg")):
            continue
        lvl = n.split("/")[1].lower()
        raw = z.read(n)
        safe = n.split("/")[1] + "_" + os.path.basename(n).replace(" ", "_").replace("(", "").replace(")", "")
        safe = os.path.splitext(safe)[0] + ".jpg"
        dst = f"{POOL}/fruq/{safe}"
        if not os.path.exists(dst):
            im = np.array(Image.open(io.BytesIO(raw)).convert("RGB"))[:, :, ::-1]
            cv2.imwrite(dst, im, [cv2.IMWRITE_JPEG_QUALITY, 95])
        recs.append(dict(id=f"fruq/{safe}", src="fruq_db", path=dst, md5=md5(raw), produce="__unknown_produce__", level=lvl))
    return recs


def embed(paths: list[str]) -> np.ndarray:
    import torch
    from ultralytics import YOLO
    m = YOLO("yolo26n-cls.pt").model.eval()
    feats = []
    hook_out = {}
    head = m.model[-1]
    h = head.linear.register_forward_hook(lambda mod, i, o: hook_out.__setitem__("f", i[0].detach()))
    mean, std = np.array([0.0, 0.0, 0.0]), np.array([1.0, 1.0, 1.0])  # Ultralytics cls uses /255 only
    with torch.no_grad():
        for i in range(0, len(paths), 64):
            batch = []
            for p in paths[i:i + 64]:
                im = cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB)
                im = cv2.resize(im, (224, 224), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
                batch.append(((im - mean) / std).transpose(2, 0, 1))
            m(torch.from_numpy(np.stack(batch)).float())
            f = hook_out["f"].numpy()
            feats.append(f / (np.linalg.norm(f, axis=1, keepdims=True) + 1e-9))
    h.remove()
    return np.concatenate(feats)


class UF:
    def __init__(self, n):
        self.p = list(range(n))

    def f(self, a):
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def u(self, a, b):
        a, b = self.f(a), self.f(b)
        if a != b:
            self.p[b] = a


def main():
    random.seed(SEED)
    np.random.seed(SEED)
    recs = ingest()
    print("ingested", len(recs), flush=True)
    # 1) exact duplicates (MD5)
    seen, dups, keep = {}, [], []
    for r in recs:
        if r["md5"] in seen:
            dups.append((r["id"], seen[r["md5"]]))
        else:
            seen[r["md5"]] = r["id"]
            keep.append(r)
    recs = keep
    # 2) pHash
    for r in recs:
        r["phash"] = str(imagehash.phash(Image.open(r["path"]).convert("RGB")))
    ph = np.array([[int(c, 16) for c in r["phash"]] for r in recs], np.uint8)
    bits = np.unpackbits(ph.astype(np.uint8)[:, :, None], axis=2)[:, :, 4:].reshape(len(recs), 64)
    # 3) embeddings
    E = embed([r["path"] for r in recs])
    print("embedded", E.shape, flush=True)
    n = len(recs)
    uf = UF(n)
    src = np.array([r["src"] for r in recs])
    near_pairs = collections.Counter()
    for i in range(n):
        ham = (bits[i + 1:] != bits[i]).sum(1)
        cos = E[i + 1:] @ E[i]
        same_src = src[i + 1:] == src[i]
        js = np.where(same_src & ((ham <= PHASH_T) | (cos >= COS_T)))[0] + i + 1
        for j in js:
            near_pairs["phash" if (bits[j] != bits[i]).sum() <= PHASH_T else "cos"] += 1
            uf.u(i, int(j))
    # FruQ: cluster proxy for source video
    fq = np.where(src == "fruq_db")[0]
    if len(fq):
        from sklearn.cluster import KMeans
        km = KMeans(K_FRUQ, random_state=SEED, n_init=4).fit(E[fq])
        first = {}
        for k, i in zip(km.labels_, fq):
            if k in first:
                uf.u(first[k], int(i))
            else:
                first[k] = int(i)
    for i, r in enumerate(recs):
        r["group"] = f"g{uf.f(i)}"
    groups = collections.defaultdict(list)
    for i, r in enumerate(recs):
        groups[r["group"]].append(i)
    # 4) split groups. Sultana: stratify by the group's majority (produce, level).
    split_of = {}
    for s in ["sultana_agml", "fruq_db"]:
        gs = [g for g, ix in groups.items() if recs[ix[0]]["src"] == s]
        strata = collections.defaultdict(list)
        for g in gs:
            maj = collections.Counter((recs[i]["produce"], recs[i]["level"]) for i in groups[g]).most_common(1)[0][0]
            strata[maj if s == "sultana_agml" else "all"].append(g)
        for key, glist in strata.items():
            random.shuffle(glist)
            total = sum(len(groups[g]) for g in glist)
            acc = 0
            for g in sorted(glist, key=lambda g: -len(groups[g])) if s == "fruq_db" else glist:
                frac = acc / max(1, total)
                split_of[g] = "train" if frac < 0.70 else ("val" if frac < 0.85 else "test")
                acc += len(groups[g])
    for r in recs:
        r["split"] = split_of[r["group"]]
    # FruQ big clusters were assigned first -> may starve val/test; rebalance by moving whole
    # clusters until each split has >= 10% of FruQ (documented).
    # 5) leakage audit
    audit = {}
    for s in ["sultana_agml", "fruq_db"]:
        idx = [i for i, r in enumerate(recs) if r["src"] == s]
        for a, b in [("train", "test"), ("train", "val")]:
            A = [i for i in idx if recs[i]["split"] == a]
            B = [i for i in idx if recs[i]["split"] == b]
            if not A or not B:
                continue
            C = E[B] @ E[A].T
            H = np.array([(bits[A] != bits[j]).sum(1).min() for j in B])
            audit[f"{s}:{a}-vs-{b}"] = dict(max_cos=float(C.max()), p99_nn_cos=float(np.percentile(C.max(1), 99)),
                                           mean_nn_cos=float(C.max(1).mean()), min_phash=int(H.min()),
                                           n_test_with_nn_cos_ge_0_90=int((C.max(1) >= 0.90).sum()), n=len(B))
    # 6) write folders
    for ds in ["quality2", "quality3"]:
        shutil.rmtree(f"{OUT}/{ds}", ignore_errors=True)
    rows = []
    for r in recs:
        for ds in ["quality2", "quality3"]:
            if ds == "quality2" and r["src"] != "sultana_agml":
                continue
            d = f"{OUT}/{ds}/{r['split']}/{r['level']}"
            os.makedirs(d, exist_ok=True)
            pref = r["produce"] + "__"
            shutil.copyfile(r["path"], f"{d}/{pref}{os.path.basename(r['path'])}")
        rows.append({k: r[k] for k in ["id", "src", "produce", "level", "group", "split", "md5", "phash"]})
    cnt = collections.Counter((r["src"], r["produce"], r["level"], r["split"]) for r in rows)
    gcount = collections.Counter((r["src"], r["split"]) for r in {r["group"]: r for r in rows}.values())
    listing = "\n".join(sorted(f"{r['id']},{r['split']},{r['md5']}" for r in rows)).encode()
    manifest = dict(
        build="quality-v1", seed=SEED, params=dict(PHASH_T=PHASH_T, COS_T=COS_T, K_FRUQ=K_FRUQ, embed_model="yolo26n-cls.pt (ImageNet)", pool_max_side=384),
        n_images=len(rows), exact_duplicates_removed=len(dups), duplicate_examples=dups[:10], near_dup_pairs=dict(near_pairs),
        n_groups=len(groups), group_size_max=max(len(v) for v in groups.values()),
        counts=[dict(src=k[0], produce=k[1], level=k[2], split=k[3], n=v) for k, v in sorted(cnt.items())],
        groups_per_split=[dict(src=k[0], split=k[1], n_groups=v) for k, v in sorted(gcount.items())],
        leakage_audit=audit, listing_sha256=hashlib.sha256(listing).hexdigest())
    os.makedirs(f"{REPO}/ml/data/builds/v1", exist_ok=True)
    json.dump(manifest, open(f"{REPO}/ml/data/builds/v1/quality_manifest.json", "w"), indent=1)
    with open(f"{REPO}/ml/data/builds/v1/quality_index.csv", "w") as fh:
        fh.write("id,src,produce,level,group,split,md5,phash\n")
        for r in rows:
            fh.write(",".join(str(r[k]) for k in ["id", "src", "produce", "level", "group", "split", "md5", "phash"]) + "\n")
    print(json.dumps({k: manifest[k] for k in ["n_images", "exact_duplicates_removed", "near_dup_pairs", "n_groups", "group_size_max", "groups_per_split", "leakage_audit"]}, indent=1))


if __name__ == "__main__":
    main()
