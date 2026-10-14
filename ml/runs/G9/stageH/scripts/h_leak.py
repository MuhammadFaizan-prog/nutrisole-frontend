"""Stage H leakage audit + split. References (imagehash 64-bit pHash): G3 train / DEV val / DEV clips / Stage D candidates
(cv/g9e/ref_hashes.json), M-DEV + M-TEST (cv/g9f/m_hashes.json, hashes only, never viewed), Stage D/E/F Commons pools (cv/g9[def] images),
CU Stage G candidates (191). Plus Commons title overlap with every earlier manifest. An H-set image is dropped at Hamming <= 10 or on a
title hit. Split by uploader (sha1 % 20): 0-9 H-train, 10-13 H-val, 14-19 H-eval. Writes out/h_leak_split.json and the hash list for the
Kaggle in-kernel audit (eval + all references; Kaggle training images near any of them are dropped there).  Usage: h_leak.py [SECONDS]"""
import json, glob, os, re, sys, time, hashlib, imagehash
from PIL import Image
B = "/workspace/work/nutrisole/ml/runs/G9/stageH"; HS = "/workspace/work/g9h/hset"; RC = "/workspace/work/g9h/refhash.json"
lim = float(sys.argv[1]) if len(sys.argv) > 1 else 100; t0 = time.time()
ref = json.load(open(RC)) if os.path.exists(RC) else {}
if "g9e" not in ref:
    ref["g9e"] = [[n, h] for n, h in json.load(open("/workspace/work/cv/g9e/ref_hashes.json"))]
    ref["m"] = [["m:" + k, h] for k, h in json.load(open("/workspace/work/cv/g9f/m_hashes.json")).items()]
    ref["pool"] = {}; ref["cu"] = {}
for p in sorted(glob.glob("/workspace/work/cv/g9[def]/**/*.jpg", recursive=True)) + sorted(glob.glob("/workspace/work/g9g/cu/img/*.jpg")):
    if "sheet" in p or "/dt_" in p or "/sl_" in p: continue
    d = ref["cu"] if "/g9g/" in p else ref["pool"]
    if p in d: continue
    if time.time() - t0 > lim: json.dump(ref, open(RC, "w")); raise SystemExit(f"partial pool={len(ref['pool'])} cu={len(ref['cu'])}")
    try: d[p] = str(imagehash.phash(Image.open(p).convert("RGB")))
    except Exception: pass
json.dump(ref, open(RC, "w"))
R = [(n, imagehash.hex_to_hash(h)) for n, h in ref["g9e"] + ref["m"]] + [("pool:" + p, imagehash.hex_to_hash(h)) for p, h in ref["pool"].items()] + \
    [("cu:" + os.path.basename(p), imagehash.hex_to_hash(h)) for p, h in ref["cu"].items()]
import numpy as np
RA = np.array([np.packbits(h.hash.flatten()) for _, h in R], np.uint8)
titles = set()
for p in glob.glob("/workspace/work/cv/g9*/**/*.json", recursive=True) + [f"/workspace/work/g9g/cu/cands.json"]:
    if os.path.getsize(p) > 30e6: continue
    try: titles |= set(re.findall(r"File:[^\"\n,|]+?\.(?:jpe?g|JPE?G|png|PNG)", open(p, errors="ignore").read()))
    except Exception: pass
C = json.load(open(f"{HS}/cands.json")); HC = f"{HS}/hhash.json"; hh = json.load(open(HC)) if os.path.exists(HC) else {}
for k in C:
    p = f"{HS}/img/{k}.jpg"
    if k not in hh and os.path.exists(p): hh[k] = str(imagehash.phash(Image.open(p).convert("RGB")))
json.dump(hh, open(HC, "w"))
res = {}; drop = []; split = {}
keys = sorted(hh)
HA = np.array([np.packbits(imagehash.hex_to_hash(hh[k]).hash.flatten()) for k in keys], np.uint8)
for i, k in enumerate(keys):
    d = np.unpackbits(RA ^ HA[i], axis=1).sum(1); j = int(d.argmin())
    # within-set near duplicates: keep the first, drop later ones (any split)
    dd = np.unpackbits(HA[:i] ^ HA[i], axis=1).sum(1) if i else np.array([99])
    t = C[k]["title"] in titles
    res[k] = dict(phash_min=int(d[j]), nearest=R[j][0][:80], title_overlap=t, intra_dup=int(dd.min()) <= 6)
    if t or d[j] <= 10 or res[k]["intra_dup"]: drop.append(k); continue
    u = C[k]["user"] or C[k]["artist"] or k; v = int(hashlib.sha1(u.encode()).hexdigest(), 16) % 20
    split[k] = "train" if v < 10 else "val" if v < 14 else "eval"
import collections
out = dict(n_refs=len(R), ref_counts=dict(collections.Counter(n.split(":")[0].split("(")[0] for n, _ in R)), n_titles=len(titles), n_hashed=len(keys),
           dropped=drop, drop_reasons=dict(collections.Counter("title" if res[k]["title_overlap"] else "intra_dup" if res[k]["intra_dup"] else "phash:" + res[k]["nearest"].split(":")[0].split("(")[0] for k in drop)),
           split=split, split_counts=dict(collections.Counter(split[k] + "|" + (C[k]["label"] if C[k]["group"] == "supported" else C[k]["group"]) for k in split)), per_image=res)
json.dump(out, open(f"{B}/out/h_leak_split.json", "w"), indent=0)
json.dump(sorted(set([h for _, h in ref["g9e"] + ref["m"]] + list(ref["pool"].values()) + list(ref["cu"].values()) + [hh[k] for k in split if split[k] == "eval"])),
          open("/workspace/work/g9h/eval_hashes.json", "w"))
print(out["n_refs"], out["ref_counts"], len(drop), out["drop_reasons"]); print(sorted(out["split_counts"].items()))
