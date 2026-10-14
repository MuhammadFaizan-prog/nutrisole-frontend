"""M-DEV v2 results per source (Commons uploader/author key) and per evaluated image group, for every arm (g1 and raw035). Usage: per_source_f.py OUT.json"""
import json, csv, collections, sys, os
R = "/workspace/work/nutrisole/ml/runs/G9/stageF"
key = {r["id"]: r["source_key"] for r in csv.DictReader(open("/workspace/work/nutrisole/ml/runs/G9/stageE/m_manifest.csv"))}
L = json.load(open(f"{R}/m_labels_v2.json")); out = {}
for a in ("F0", "F1s0", "F1s1", "F2s0", "F2s1"):
    p = f"{R}/out/mdev_{a}.json"
    if not os.path.exists(p): continue
    e = json.load(open(p)); out[a] = {}
    for g in ("g1", "raw035"):
        agg = collections.defaultdict(lambda: dict(images=0, gt=0, tp=0, fp=0))
        for i, v in e[g]["per_image"].items():
            k = key.get(i, "?"); agg[k]["images"] += 1; agg[k]["gt"] += len(L[i]["boxes"]); agg[k]["tp"] += v["tp"]; agg[k]["fp"] += v["fp"]
        out[a][g] = dict(agg)
src = sorted(out["F0"]["raw035"], key=lambda k: -out["F0"]["raw035"][k]["gt"])
json.dump(out, open(sys.argv[1], "w"), indent=0)
print("| Source (boxed GT) | " + " | ".join(f"{a} raw035 TP/FP" for a in out) + " |"); print("|---" * (len(out) + 1) + "|")
for k in [k for k in src if out["F0"]["raw035"][k]["gt"] > 0][:12]:
    print(f"| {k.split(':', 1)[1][:28]} ({out['F0']['raw035'][k]['gt']}) | " + " | ".join(f"{out[a]['raw035'][k]['tp']}/{out[a]['raw035'][k]['fp']}" for a in out) + " |")
neg = [k for k in src if out["F0"]["raw035"][k]["gt"] == 0]
print(f"| all {len(neg)} sources with no boxed GT | " + " | ".join(f"0/{sum(out[a]['raw035'][k]['fp'] for k in neg)}" for a in out) + " |")
