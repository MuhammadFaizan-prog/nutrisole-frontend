"""MT manifest (licensed sources) + source-level MT-train / MT-val split (~15% of source keys by md5 order) + F2 Kaggle kernel payload.
Usage: make_mt_payload.py"""
import json, csv, hashlib, base64, os, collections
R = "/workspace/work/nutrisole/ml/runs/G9/stageF"; D = "/workspace/work/cv/g9f"
S = {s["id"]: s for s in json.load(open(f"{D}/mt_sel.json"))}; L = json.load(open(f"{D}/mt_labels.json"))
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
keys = sorted({S[i]["source_key"] for i in L if L[i]["status"] == "ok"}, key=lambda k: hashlib.md5(k.encode()).hexdigest())
val_keys = set(keys[:max(1, round(0.15 * len(keys)))])
rows = []; items = []
for i in sorted(S):
    s = S[i]; l = L[i]; sp = "rejected" if l["status"] != "ok" else ("dev" if s["source_key"] in val_keys else "train")
    cls = collections.Counter(N[b[4]] for b in l["boxes"])
    rows.append([i, sp, s["title"], s["page"], s["licence"], s.get("uploader"), s.get("artist"), s["source_key"], s["intended"], len(l["boxes"]), len(l["grey"]),
                 "|".join(f"{k}:{v}" for k, v in sorted(cls.items())), l["note"], s["phash_min_dist_ref"],
                 "rejected in review" if sp == "rejected" else ("hand-boxed / verified negative" if (not l["boxes"] or "by hand" in l["note"]) else "OWLv2 proposals + agent region-level correction (class verified, non-target regions deleted, unverifiable regions greyed); item-level box tightness NOT verified"),
                 "agent-verified, NOT human-verified"])
    if sp != "rejected": items.append(dict(id=i, split=sp, url=s["url"], boxes=l["boxes"], grey=l["grey"]))
with open(f"{R}/mt_manifest.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["id", "split", "title", "page", "licence", "uploader", "artist", "source_key", "intended", "n_boxes", "n_grey", "classes", "note", "phash_min_dist_ref", "label_method", "verification"]); w.writerows(rows)
json.dump(dict(items=items), open(f"{R}/mt_labels.json", "w"))
st = dict(images={sp: sum(1 for r in rows if r[1] == sp) for sp in ("train", "dev", "rejected")}, sources_used=len(keys), val_sources=len(val_keys),
          boxes_by_class={sp: dict(collections.Counter(N[b[4]] for it in items if it["split"] == sp for b in it["boxes"])) for sp in ("train", "dev")},
          box_free_images={sp: sum(1 for it in items if it["split"] == sp and not it["boxes"]) for sp in ("train", "dev")},
          licences=dict(collections.Counter(r[4] for r in rows if r[1] != "rejected")), max_images_per_source=max(collections.Counter(r[7] for r in rows if r[1] != "rejected").values()))
json.dump(st, open(f"{R}/out/mt_stats.json", "w"), indent=1); print(json.dumps(st))
t = open(f"{R}/kaggle_train/run_template.py").read().replace("__MT_JSON_B64__", base64.b64encode(json.dumps(dict(items=items)).encode()).decode()).replace("__ARMS__", "F2s0,F2s1")
os.makedirs(f"{D}/kf2", exist_ok=True); open(f"{D}/kf2/run.py", "w").write(t)
json.dump({"id": "mfaizannnn/nutrisole-g9f-f2", "title": "nutrisole-g9f-f2", "code_file": "run.py", "language": "python", "kernel_type": "script", "is_private": True,
           "enable_gpu": True, "enable_internet": True, "dataset_sources": ["mfaizannnn/nutrisole-cv-g3", "mfaizannnn/nutrisole-cv-g6-w"], "competition_sources": [], "kernel_sources": []}, open(f"{D}/kf2/kernel-metadata.json", "w"))
