#!/usr/bin/env python3
"""G6.1 audit step B: duplicate/leakage, class distribution, tiny boxes, label sanity, corrected TRAIN manifest.
Input g6data/audit/hashes.jsonl. Outputs (all new files; locked splits untouched):
  g6data/audit/audit.json, dup_pairs.csv, class_dist.csv, tiny_boxes.csv
  g6data/det_g6/train_corrected.txt (+ removed.csv)  -- TRAIN-side leakage removal only
"""
import json, collections, csv, os, re
import numpy as np
A = "/workspace/work/cv/g6data/audit"; G = "/workspace/work/cv/g6data/det_g6"; os.makedirs(G, exist_ok=True)
NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
R = [json.loads(l) for l in open(f"{A}/hashes.jsonl")]
seen = {}
for r in R: seen[(r["split"], r["path"])] = r
R = list(seen.values())
EVAL = ["test", "test_rf", "test_oiv7", "test_oiv7c", "neg_test"]
TRAINLIKE = ["train", "val", "oiv7c_train", "oiv7c_val", "g5hn_train"]
out = dict(n_images={}, errors=[r["path"] for r in R if "err" in r])
for s in sorted({r["split"] for r in R}): out["n_images"][s] = sum(r["split"] == s for r in R)


def src(r):
    p = r["path"]
    m = re.search(r"/(det|neg|oiv7|hardneg|oiv7c|g5hn)/images/", p)
    return m.group(1) if m else "?"


# ---- exact duplicates (md5)
by_md5 = collections.defaultdict(list)
for r in R:
    if "md5" in r: by_md5[r["md5"]].append(r)
exact = [v for v in by_md5.values() if len(v) > 1]
exact_cross = collections.Counter()
for v in exact:
    sp = sorted({x["split"] for x in v})
    exact_cross["+".join(sp)] += 1
out["exact_dup_groups"] = len(exact); out["exact_dup_groups_by_splits"] = dict(exact_cross)

# ---- near duplicates: pHash<=PH and dHash<=DH, eval vs train-like and eval vs eval (different split)
PH, DH = 6, 8
ok = [r for r in R if "ph" in r]
ph = np.array([r["ph"] for r in ok], dtype=np.uint64); dh = np.array([r["dh"] for r in ok], dtype=np.uint64)
sp = np.array([r["split"] for r in ok])


def popcnt(x):
    x = x.copy(); c = np.zeros(x.shape, np.int64)
    for _ in range(64):
        c += (x & np.uint64(1)).astype(np.int64); x >>= np.uint64(1)
    return c


pairs = []
idx_eval = [i for i, r in enumerate(ok) if r["split"] in EVAL]
for i in idx_eval:
    a = popcnt(ph ^ ph[i]); b = popcnt(dh ^ dh[i])
    for j in np.where((a <= PH) & (b <= DH))[0]:
        if j == i: continue
        if ok[j]["split"] == ok[i]["split"] and j < i: continue
        pairs.append((ok[i]["split"], ok[i]["path"], ok[j]["split"], ok[j]["path"], int(a[j]), int(b[j]),
                      ok[i].get("md5") == ok[j].get("md5")))
with open(f"{A}/dup_pairs.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["eval_split", "eval_path", "other_split", "other_path", "phash_ham", "dhash_ham", "exact_md5"])
    w.writerows(pairs)
pc = collections.Counter(f"{a}<->{c}" for a, _, c, _, _, _, _ in pairs)
out["near_dup_rule"] = f"pHash Hamming <= {PH} AND dHash Hamming <= {DH} (64-bit each)"
out["near_dup_pairs_by_splits"] = dict(pc)
leak_train = {(c, d) for a, b, c, d, *_ in pairs if c in TRAINLIKE}
out["eval_images_with_trainlike_near_dup"] = {e: len({b for a, b, c, d, *_ in pairs if a == e and c in TRAINLIKE}) for e in EVAL}

# ---- Roboflow capture groups inside test_rf (correlated frames -> effective n)
grp = collections.Counter()
for r in R:
    if r["split"] == "test_rf":
        b = os.path.basename(r["path"]); m = re.match(r"(.*?)_(\d+)_(png|jpg|jpeg)\.rf\.", b)
        grp[m.group(1) if m else b] += 1
out["test_rf_capture_groups"] = dict(n_groups=len(grp), n_images=sum(grp.values()), largest=grp.most_common(5))

# ---- class distribution, tiny / degenerate boxes
dist = collections.defaultdict(lambda: collections.Counter()); imgs = collections.defaultdict(lambda: collections.Counter())
tiny = []; bad = []; empty = collections.Counter(); boxsrc = collections.defaultdict(lambda: collections.Counter())
for r in R:
    s = r["split"]
    if not r["boxes"]: empty[s] += 1
    for c in {b[0] for b in r["boxes"]}: imgs[s][c] += 1
    sc = 480 / max(r.get("w", 480), r.get("h", 480))
    for c, x, y, w, h in r["boxes"]:
        dist[s][c] += 1; boxsrc[f"{s}/{src(r)}"][c] += 1
        if w <= 0 or h <= 0 or not (0 <= x <= 1 and 0 <= y <= 1) or w > 1.001 or h > 1.001: bad.append((s, r["path"], c, x, y, w, h))
        pw, phh = w * r.get("w", 0) * sc, h * r.get("h", 0) * sc
        if min(pw, phh) < 6: tiny.append((s, r["path"], NAMES[c] if c < 12 else c, round(pw, 1), round(phh, 1)))
with open(f"{A}/class_dist.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["split", "class", "instances", "images"])
    for s in sorted(dist):
        for c in range(12): w.writerow([s, NAMES[c], dist[s][c], imgs[s][c]])
with open(f"{A}/tiny_boxes.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["split", "path", "class", "w_px@480", "h_px@480"]); w.writerows(tiny)
out["class_instances"] = {s: {NAMES[c]: dist[s][c] for c in range(12)} for s in sorted(dist)}
out["empty_label_images"] = dict(empty)
out["degenerate_boxes"] = len(bad); out["degenerate_examples"] = bad[:10]
out["tiny_boxes_lt6px_at480"] = dict(collections.Counter(t[0] for t in tiny))
out["tiny_boxes_by_class"] = {s: dict(collections.Counter(t[2] for t in tiny if t[0] == s)) for s in {t[0] for t in tiny}}
out["instances_by_split_source"] = {k: {NAMES[c]: v[c] for c in range(12) if v[c]} for k, v in sorted(boxsrc.items())}
out["low_light_share_mean_lt60"] = {s: round(float(np.mean([r["mean"] < 60 for r in R if r["split"] == s and "mean" in r])), 3) for s in out["n_images"]}

# ---- corrected TRAIN manifest: G3 train.txt minus images that are exact/near dups of any eval image
train = open("/workspace/work/cv/g3data/det_v3/train.txt").read().split()
drop = {d for c, d in leak_train if c == "train"}
# also exact md5 dups of eval images
evmd5 = {r["md5"] for r in R if r["split"] in EVAL and "md5" in r}
drop |= {r["path"] for r in R if r["split"] == "train" and r.get("md5") in evmd5}
# within-train exact duplicates: keep first
first = {}; wdup = set()
for p in train:
    r = seen.get(("train", p)); m = r.get("md5") if r else None
    if m in first: wdup.add(p)
    else: first[m] = p
corr = [p for p in train if p not in drop and p not in wdup]
open(f"{G}/train_corrected.txt", "w").write("\n".join(corr) + "\n")
with open(f"{G}/removed.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["path", "reason"])
    for p in sorted(drop): w.writerow([p, "near/exact duplicate of a locked eval image"])
    for p in sorted(wdup - drop): w.writerow([p, "exact duplicate within train"])
out["corrected_train"] = dict(n_in=len(train), n_out=len(corr), removed_eval_leak=len(drop), removed_within_train_dup=len(wdup - drop))
json.dump(out, open(f"{A}/audit.json", "w"), indent=1, default=str)
print(json.dumps({k: out[k] for k in ["n_images", "exact_dup_groups_by_splits", "near_dup_pairs_by_splits", "eval_images_with_trainlike_near_dup", "corrected_train", "test_rf_capture_groups", "empty_label_images", "degenerate_boxes", "tiny_boxes_lt6px_at480"]}, indent=1, default=str))

# ---- Kaggle removal list (relative paths), TRAIN-side only: G3 train + OIV7c train (used by rpx)
rel = lambda p: p.split("/det_v3/", 1)[1] if "/det_v3/" in p else p.split("/g4data/", 1)[1]
oc_drop = {d for c, d in leak_train if c == "oiv7c_train"} | {r["path"] for r in R if r["split"] == "oiv7c_train" and r.get("md5") in evmd5}
rem = sorted(rel(p) for p in (drop | wdup | oc_drop))
open(f"{G}/g6_removed_basenames.txt", "w").write("\n".join(rem) + "\n")
out["oiv7c_train_removed_eval_leak"] = len(oc_drop)
json.dump(out, open(f"{A}/audit.json", "w"), indent=1, default=str)
print("kaggle removal list", len(rem), "oiv7c_train leak", len(oc_drop))
