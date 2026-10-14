"""I2 pHash leakage audit + source-separated split for the Stage I candidates. References (64-bit pHash, Hamming <= 10 = leak):
Stage H in-kernel list (eval_hashes.json: all eval + references incl. M-DEV/M-TEST hashes, never viewed), H-set (hhash.json, incl. H-train),
refhash.json (G3 train / DEV / clips / Stage D-F pools / CU). Within the new set, near-duplicates (<= 6) are grouped and kept as ONE group
(same split, one representative for review). Split: Commons by uploader (sha1 % 10: 0-3 I-dev, 4-9 I-eval-A); each external dataset is
one source and goes whole to I-eval-B (FruitNet, carrot_m, tomato_m) so no source spans dev and eval. Writes out/i_leak_split.json."""
import json, hashlib, collections, numpy as np, imagehash
from PIL import Image
D = "/workspace/work/g9i/cands"; O = "/workspace/work/nutrisole/ml/runs/G9/stageI/out"
C = json.load(open(f"{D}/cands.json")); C = {k: v for k, v in C.items() if "size" in v}
ref = list(json.load(open("/workspace/work/g9h/eval_hashes.json"))) + list(json.load(open("/workspace/work/g9h/hset/hhash.json")).values())
rh = json.load(open("/workspace/work/g9h/refhash.json"))
ref += [h for _, h in rh["g9e"] + rh["m"]] + list(rh["pool"].values()) + list(rh["cu"].values())
ref = sorted(set(ref)); RA = np.array([np.packbits(imagehash.hex_to_hash(h).hash.flatten()) for h in ref], np.uint8)
H = {k: str(imagehash.phash(Image.open(f"{D}/img/{k}.jpg").convert("RGB"))) for k in C}
dmin = {k: int(np.unpackbits(RA ^ np.packbits(imagehash.hex_to_hash(h).hash.flatten()), axis=1).sum(1).min()) for k, h in H.items()}
leak = sorted(k for k, d in dmin.items() if d <= 10)
keys = [k for k in C if k not in leak]; A = np.array([np.packbits(imagehash.hex_to_hash(H[k]).hash.flatten()) for k in keys], np.uint8)
par = list(range(len(keys)))
def f(i):
    while par[i] != i: par[i] = par[par[i]]; i = par[i]
    return i
for i in range(len(keys)):
    d = np.unpackbits(A[i] ^ A, axis=1).sum(1)
    for j in np.where(d <= 6)[0]:
        if j > i: par[f(j)] = f(i)
grp = collections.defaultdict(list)
for i, k in enumerate(keys): grp[f(i)].append(k)
def split(v):
    if v["source"] != "commons": return "I-eval-B"
    return "I-dev" if int(hashlib.sha1((v.get("uploader") or v.get("artist") or "").encode()).hexdigest(), 16) % 10 < 4 else "I-eval-A"
S = {}; dup_conflict = 0
for g in grp.values():
    sp = {split(C[k]) for k in g}
    s = "I-eval-B" if "I-eval-B" in sp else ("I-eval-A" if "I-eval-A" in sp else "I-dev"); dup_conflict += len(sp) > 1
    for k in g: S[k] = dict(split=s, group_rep=g[0], dup_group_size=len(g))
PHONE = ("samsung", "realme", "xiaomi", "redmi", "apple iphone", "oneplus", "huawei", "oppo", "vivo", "motorola", "google pixel", "nokia", "sony xperia", "lg-", "lge")
out = dict(note="pHash leak audit vs every earlier reference (Hamming <= 10) + within-set near-dup groups (<= 6). Labels = source metadata (exploratory).",
           n_candidates=len(C), n_leak_dropped=len(leak), leak_keys=leak, n_groups=len(grp), cross_split_dup_groups_forced=dup_conflict,
           items={k: dict(**S[k], phash=H[k], ref_dmin=dmin[k], source=C[k]["source"], label=C[k]["label"], group=C[k]["group"],
                          phone_exif=any(p in (C[k].get("camera") or "").lower() for p in PHONE) or C[k]["source"] in ("fruitnet", "carrot_m", "tomato_m")) for k in keys})
out["counts"] = {s: dict(collections.Counter(f"{v['group']}|{v['label']}" for v in out["items"].values() if v["split"] == s and v["group_rep"] == k)) for s in ("I-dev", "I-eval-A", "I-eval-B") for k in [None]} if False else {}
for s in ("I-dev", "I-eval-A", "I-eval-B"):
    reps = [v for k, v in out["items"].items() if v["split"] == s and v["group_rep"] == k]
    out["counts"][s] = dict(sorted(collections.Counter(f"{v['group']}|{v['label']}" for v in reps).items()))
out["by_source"] = {s: dict(n=sum(1 for v in out["items"].values() if v["source"] == s), groups=sum(1 for k, v in out["items"].items() if v["source"] == s and v["group_rep"] == k)) for s in ("commons", "fruitnet", "carrot_m", "tomato_m")}
out["uploaders_commons"] = len({C[k].get("uploader") for k in keys if C[k]["source"] == "commons"})
json.dump(out, open(f"{O}/i_leak_split.json", "w"), indent=1)
print({k: out[k] for k in ("n_candidates", "n_leak_dropped", "n_groups", "cross_split_dup_groups_forced", "by_source", "uploaders_commons")}); print(json.dumps(out["counts"], indent=0))
