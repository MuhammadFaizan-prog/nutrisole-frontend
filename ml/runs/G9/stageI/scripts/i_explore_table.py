"""Summarise out/i_explore.jsonl per source / split (EXPLORATORY: source-metadata labels). -> out/i_explore.json"""
import json, sys, collections, numpy as np
sys.path.insert(0, "/workspace/work/nutrisole")
from ml.eval.verify import verify_identity, h2_decision, FROZEN_VERIFY, H2_CLASSES
O = "/workspace/work/nutrisole/ml/runs/G9/stageI/out"; N = H2_CLASSES[:12]
R = [json.loads(l) for l in open(f"{O}/i_explore.jsonl")]
def sc(rows):
    c = collections.Counter()
    for r in rows:
        w = dict(status="identified", classId=r["wide"]["classId"]) if r["wide"]["status"] == "identified" else dict(status="unable")
        sup = r["group"] == "supported" and r["truth"] in N; v = verify_identity(w, None, r["h2_crop"], FROZEN_VERIFY)
        dc, df = h2_decision(r["h2_crop"], FROZEN_VERIFY), h2_decision(r["h2_full"], FROZEN_VERIFY)
        if sup:
            t = N.index(r["truth"]); c["sup"] += 1
            c["wide_correct"] += w.get("classId") == t; c["wide_wrong"] += w["status"] == "identified" and w["classId"] != t
            c["h2crop_top1"] += int(np.argmax(r["h2_crop"][:12])) == t; c["h2full_top1"] += int(np.argmax(r["h2_full"][:12])) == t
            c["h2crop_unknown_top"] += int(np.argmax(r["h2_crop"])) == 12; c["h2full_unknown_top"] += int(np.argmax(r["h2_full"])) == 12
            c["h2crop_acc_correct"] += dc["accept"] and dc["classId"] == t; c["h2crop_acc_wrong"] += dc["accept"] and dc["classId"] != t
            c["h2full_acc_correct"] += df["accept"] and df["classId"] == t; c["h2full_acc_wrong"] += df["accept"] and df["classId"] != t
            c["Hfinal_correct"] += v["status"] == "verified" and v["classId"] == t; c["Hfinal_wrong"] += v["status"] == "verified" and v["classId"] != t
        else:
            c["neg"] += 1; c["neg_wide_identified"] += w["status"] == "identified"; c["neg_Hfinal_accept"] += v["status"] == "verified"; c["neg_h2crop_accept"] += dc["accept"]
            c[f"neg_{r['group']}"] += 1; c[f"neg_{r['group']}_Hfinal_accept"] += v["status"] == "verified"
    return dict(c)
out = dict(note="EXPLORATORY. Labels are source metadata (dataset folder / Commons query intent), not human labels. Commons 'packaging/printed/occluded' "
                "queries are treated as negatives here although some show supported produce; the human protocol re-labels them.",
           by_source={s: sc([r for r in R if r["source"] == s]) for s in ("commons", "fruitnet", "carrot_m", "tomato_m")},
           by_split={s: sc([r for r in R if r["split"] == s]) for s in ("I-dev", "I-eval-A", "I-eval-B")},
           by_class_supported={c: sc([r for r in R if r["truth"] == c and r["group"] == "supported"]) for c in ("apple", "banana", "citrus", "tomato", "carrot")},
           confusion_h2crop={c: dict(collections.Counter(H2_CLASSES[int(np.argmax(r["h2_crop"]))] for r in R if r["truth"] == c and r["group"] == "supported").most_common()) for c in ("apple", "banana", "citrus", "tomato", "carrot")},
           confusion_h2full={c: dict(collections.Counter(H2_CLASSES[int(np.argmax(r["h2_full"]))] for r in R if r["truth"] == c and r["group"] == "supported").most_common()) for c in ("apple", "banana", "citrus", "tomato", "carrot")})
json.dump(out, open(f"{O}/i_explore.json", "w"), indent=1)
for k in ("by_source", "by_split", "by_class_supported"): print(k); [print("  ", a, b) for a, b in out[k].items()]
print("conf crop", out["confusion_h2crop"]); print("conf full", out["confusion_h2full"])
