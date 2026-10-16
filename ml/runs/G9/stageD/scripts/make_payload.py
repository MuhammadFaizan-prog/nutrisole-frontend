"""Final S manifest (after leakage/uploader/dup drops), uploader-level S-train / S-dev split, and the D1/D2 Kaggle kernel.
Usage: make_payload.py"""
import json, base64, hashlib, csv, os
R = "/workspace/work/nutrisole/ml/runs/G9/stageD"; D = "/workspace/work/cv/g9d"
S = json.load(open(f"{D}/s_manifest_pre.json")); L = json.load(open(f"{R}/out/leakage_audit.json"))
drop = set(L["drop_leak"]) | set(L["drop_dup"]) | set(L["drop_uploader"])
items = [i for i in S["items"] if i["file"] not in drop]
ups = sorted({i["uploader"] for i in items}, key=lambda u: hashlib.md5(u.encode()).hexdigest()); devu = set(ups[:max(1, round(0.2 * len(ups)))])  # ~20% of uploaders
for i in items: i["split"] = "dev" if i["uploader"] in devu else "train"
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
with open(f"{R}/s_manifest.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["id", "split", "page", "licence", "uploader", "artist", "n_boxes", "classes", "grey_cells", "labels", "verification"])
    for i in items:
        cl = sorted({N[b[4]] for b in i["boxes"]})
        w.writerow([i["id"], i["split"], i["page"], i["licence"], i["uploader"], i["artist"], len(i["boxes"]), "|".join(cl), len(i["grey"]),
                    "G3-640 tiled teacher proposals + agent review edits", "agent-verified (not human): wrong boxes dropped/relabelled, unboxed produce greyed"])
json.dump(dict(items=items, dropped=sorted(drop), rejected_in_review=S["rejected"]), open(f"{R}/s_labels.json", "w"))
pay = dict(items=[dict(id=i["id"], split=i["split"], url=i["url"], boxes=[b[:5] for b in i["boxes"]], grey=i["grey"]) for i in items])
t = open(f"{R}/kaggle_train/run_template.py").read().replace("__S_JSON_B64__", base64.b64encode(json.dumps(pay).encode()).decode()).replace("__ARMS__", "D1,D2")
os.makedirs(f"{D}/kd12", exist_ok=True); open(f"{D}/kd12/run.py", "w").write(t)
json.dump({"id": "mfaizannnn/nutrisole-g9d-train", "title": "nutrisole-g9d-train", "code_file": "run.py", "language": "python", "kernel_type": "script", "is_private": True,
           "enable_gpu": True, "enable_internet": True, "dataset_sources": ["mfaizannnn/nutrisole-cv-g3", "mfaizannnn/nutrisole-cv-g6-w"], "competition_sources": [], "kernel_sources": []}, open(f"{D}/kd12/kernel-metadata.json", "w"))
import collections
print("kept", len(items), "dropped", sorted(drop), collections.Counter(i["split"] for i in items),
      {sp: sum(len(i["boxes"]) for i in items if i["split"] == sp) for sp in ("train", "dev")}, [i["id"] for i in items if i["split"] == "dev"])
