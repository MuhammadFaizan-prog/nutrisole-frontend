"""G9 Stage J: source-separated train / dev / untouched-eval partitions + near-duplicate audit + diversity proxies + training gap.
Rules (frozen here):
  J-eval  = Stage I I-eval-A (Commons uploaders sha1%10 in 4-9) U I-eval-B (FruitNet, carrot_m, tomato_m whole sources). Membership unchanged.
  J-dev   = Stage I I-dev items whose uploader has sha1%10 in 2-3 (threshold tuning only).
  J-train = Stage I I-dev items with sha1%10 in 0-1  +  Stage J extra licensed sources (citrus_tw, veg_in, veg_bd, commons_t).
  Grouping key: Commons uploader, and also the artist/author string (union-find: an uploader or artist in two splits is a leak); a dataset is
  one group as a whole. Near-duplicates: 64-bit pHash, Hamming <= 10 across splits or against every earlier reference (Stage H in-kernel list
  incl. M-DEV/M-TEST hashes, H-set, G3 train/DEV/clips, Stage D-F pools, CU) -> the NON-eval item is quarantined (eval never changes).
  Licence-excluded files (j_licence.json) and Stage I leak drops are removed. M-TEST content is never opened: only its stored hashes are used.
Labels here are SOURCE metadata (exploratory) until the human labels arrive.
Output: ml/runs/G9/stageJ/out/j_partitions.json (+ j_manifest_candidates.csv)."""
import json, hashlib, csv, collections, re, os, sys
import numpy as np, imagehash
from PIL import Image, ImageStat
ROOT = "/workspace/work/nutrisole/ml/runs/G9"; OUT = f"{ROOT}/stageJ/out"
C = json.load(open("/workspace/work/g9i/cands/cands.json")); L = json.load(open(f"{ROOT}/stageI/out/i_leak_split.json"))
LIC = json.load(open(f"{OUT}/j_licence.json")); lic_bad = set(LIC["excluded_keys"])
TJ = "/workspace/work/g9j/train/train_cands.json"; T = json.load(open(TJ)) if os.path.exists(TJ) else {}
TL = json.load(open(f"{OUT}/j_licence_train.json")) if os.path.exists(f"{OUT}/j_licence_train.json") else {"excluded_keys": []}
lic_bad |= set(TL["excluded_keys"])
RID = json.load(open(f"{ROOT}/stageI/out/review_ids.json"))
def bucket(s): return int(hashlib.sha1((s or "").encode()).hexdigest(), 16) % 10
def img_path(k): return f"/workspace/work/g9i/cands/img/{k}.jpg" if k in C else f"/workspace/work/g9j/train/img/{k}.jpg"
items = {}
for k, it in L["items"].items():                      # Stage I kept items (leaks already removed)
    if k in lic_bad: continue
    v = C[k]; s = it["split"]
    if s == "I-dev": js = "J-dev" if bucket(v.get("uploader") or v.get("artist") or "") in (2, 3) else "J-train"
    else: js = "J-eval"
    items[k] = dict(split=js, stageI_split=s, group=it["group_rep"], phash=it["phash"], source=v["source"], label=v["label"], kind=v["group"],
                    uploader=v.get("uploader", ""), artist=(v.get("artist") or "").strip(), item_id=RID.get(it["group_rep"]))
ref = list(json.load(open("/workspace/work/g9h/eval_hashes.json"))) + list(json.load(open("/workspace/work/g9h/hset/hhash.json")).values())
rh = json.load(open("/workspace/work/g9h/refhash.json")); ref += [h for _, h in rh["g9e"] + rh["m"]] + list(rh["pool"].values()) + list(rh["cu"].values())
ref = sorted(set(ref)); BLANK = {"0000000000000000", "8000000000000000"}
def bits(h): return np.unpackbits(np.frombuffer(bytes.fromhex(h), np.uint8))
RA = np.array([bits(h) for h in ref], np.uint8)
quar = {}
for k, v in T.items():                                  # Stage J extra training candidates
    if "size" not in v or k in lic_bad: continue
    try: h = str(imagehash.phash(Image.open(img_path(k)).convert("RGB")))
    except Exception: continue
    dmin = int((RA ^ bits(h)).sum(1).min())
    if dmin <= 10: quar[k] = f"near-dup of an earlier reference set (Hamming {dmin})"; continue
    items[k] = dict(split="J-train", stageI_split=None, group=k, phash=h, source=v["source"], label=v["label"], kind="supported",
                    uploader=v.get("uploader", ""), artist=(v.get("author") or "").strip(), item_id=None, ref_dmin=dmin)
# source separation: uploader / artist union across splits (eval wins, then dev)
def person_keys(v):
    ks = []
    if v["source"] in ("commons", "commons_t"):
        if v["uploader"]: ks.append("u:" + v["uploader"].lower())
        a = re.sub(r"\s+", " ", v["artist"].lower()).strip()
        if a and not re.search(r"^(unknown|anonymous|unbekannt|author unknown)|unknown author", a) and len(a) > 2: ks.append("a:" + a[:80])
    else: ks.append("d:" + v["source"])
    return ks
owner = {}
for rank in ("J-eval", "J-dev", "J-train"):
    for k, v in items.items():
        if v["split"] != rank: continue
        for pk in person_keys(v): owner.setdefault(pk, rank)
moved = []
for k, v in list(items.items()):
    for pk in person_keys(v):
        if owner[pk] != v["split"]:
            quar[k] = f"{pk} also in {owner[pk]} (source separation)"; moved.append((k, v["split"], pk, owner[pk])); items.pop(k); break
# near-duplicate audit across splits (<= 10); quarantine the lower-priority side
order = {"J-eval": 0, "J-dev": 1, "J-train": 2}
keys = sorted(items, key=lambda k: order[items[k]["split"]]); A = np.array([bits(items[k]["phash"]) for k in keys], np.uint8)
cross = []
for i, k in enumerate(keys):
    if k in quar or items[k]["phash"] in BLANK: continue
    d = (A[:i] ^ A[i]).sum(1) if i else np.array([])
    for j in np.where(d <= 10)[0]:
        kj = keys[j]
        if kj in quar or items[kj]["split"] == items[k]["split"]: continue
        cross.append((kj, items[kj]["split"], k, items[k]["split"], int(d[j]))); quar[k] = f"near-dup (Hamming {int(d[j])}) of {kj} in {items[kj]['split']}"; break
for k in list(items):
    if k in quar: items.pop(k)
# within-split near-dup groups for new train items (<= 6), so a reviewer sees each once
tr = [k for k, v in items.items() if v["stageI_split"] is None]; At = np.array([bits(items[k]["phash"]) for k in tr], np.uint8) if tr else None
for i, k in enumerate(tr):
    if i and ((At[:i] ^ At[i]).sum(1) <= 6).any():
        j = int(np.where((At[:i] ^ At[i]).sum(1) <= 6)[0][0]); items[k]["group"] = items[tr[j]]["group"]
# diversity proxies on each image
def proxies(k):
    im = Image.open(img_path(k)).convert("L"); w, h = im.size; a = np.asarray(im, np.float32); m = a.mean()
    bw = max(2, int(0.1 * min(w, h))); ring = np.concatenate([a[:bw].ravel(), a[-bw:].ravel(), a[:, :bw].ravel(), a[:, -bw:].ravel()])
    light = "dark" if m < 75 else "bright" if m > 175 else "normal"
    bm, bs = ring.mean(), ring.std()
    bg = ("plain_dark" if bm < 60 else "plain_light" if bm > 190 else "plain_mid") if bs < 22 else "textured"
    return light, bg
for k, v in items.items(): v["light"], v["bg"] = proxies(k)
# summaries (group representatives only = what reviewers see)
reps = {v["group"] for v in items.values()}
def summ(split):
    g = [v for k, v in items.items() if v["split"] == split and k == v["group"]]
    c = collections.Counter
    return dict(groups=len(g), images=sum(1 for v in items.values() if v["split"] == split),
                supported_by_class=dict(c(v["label"] for v in g if v["kind"] == "supported")), negatives_by_kind=dict(c(v["kind"] for v in g if v["kind"] != "supported")),
                by_source=dict(c(v["source"] for v in g)), commons_uploaders=len({v["uploader"] for v in g if v["source"].startswith("commons")}),
                light=dict(c(v["light"] for v in g)), background=dict(c(v["bg"] for v in g)),
                class_x_source={cl: dict(c(v["source"] for v in g if v["label"] == cl and v["kind"] == "supported")) for cl in ("apple", "banana", "citrus", "tomato", "carrot")})
S = {s: summ(s) for s in ("J-train", "J-dev", "J-eval")}
# training gap (frozen target, see G9_stageJ_readiness.md T-gates): >= 150 human-verified training images per priority class
YIELD = {"commons": 0.55, "commons_t": 0.55, "citrus_tw": 0.9, "veg_in": 0.9, "veg_bd": 0.9}   # assumed review yield (inferred from Stage I sheet triage)
TARGET = 150; gap = {}
for cl in ("apple", "banana", "citrus", "tomato", "carrot"):
    g = [v for k, v in items.items() if v["split"] == "J-train" and k == v["group"] and v["label"] == cl]
    exp = sum(YIELD.get(v["source"], 0.7) for v in g); gap[cl] = dict(candidates=len(g), expected_verified=round(exp), target=TARGET, shortfall=max(0, TARGET - round(exp)),
                                                                        sources=sorted({v["source"] for v in g}))
negs_tr = sum(1 for k, v in items.items() if v["split"] == "J-train" and k == v["group"] and v["kind"] != "supported")
out = dict(note=__doc__.split("\n")[0], rules=__doc__, n_items=len(items), n_quarantined=len(quar), quarantined=quar, cross_split_neardups=cross, person_moves=moved,
           licence_excluded=sorted(lic_bad), splits=S, training_gap=gap, train_negative_groups=negs_tr, yield_assumption=YIELD,
           uploaders_dev_eval=sorted({v["uploader"] for v in items.values() if v["split"] != "J-train" and v["uploader"]}),
           items=items)
json.dump(out, open(f"{OUT}/j_partitions.json", "w"), indent=0, ensure_ascii=False)
with open(f"{OUT}/j_manifest_candidates.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["key", "split", "stageI_split", "group", "is_group_rep", "source", "uploader", "source_label_exploratory", "source_kind", "phash", "light_proxy", "bg_proxy"])
    for k, v in sorted(items.items(), key=lambda x: (x[1]["split"], x[0])):
        w.writerow([k, v["split"], v["stageI_split"] or "", v["group"], int(k == v["group"]), v["source"], v["uploader"], v["label"], v["kind"], v["phash"], v["light"], v["bg"]])
print(json.dumps(dict(n=len(items), quarantined=len(quar), cross=len(cross), moves=len(moved), splits=S, gap=gap, negs_tr=negs_tr), indent=1, ensure_ascii=False))
