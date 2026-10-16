"""I3 per-cue separability (AUC, GrabCut mask, CU-tune and CU-check separately): targeted cue on the occluder type it targets vs clean crops."""
import json, numpy as np
O = "/workspace/work/nutrisole/ml/runs/G9/stageI/out"; S = "/workspace/work/nutrisole/ml/runs/G9/stageH/out"
B = {json.loads(l)["k"]: json.loads(l) for l in open(f"{O}/occ_bench.jsonl")}; SP = {json.loads(l)["id"]: json.loads(l)["split"] for l in open(f"{S}/occ_items.jsonl")}
T = dict(sideTouch=["trunc25_inner", "trunc40_inner", "trunc40_edge"], skinFrac=["hand_0", "hand_1", "hand_2", "skin30", "g_skin50"], specFrac=["bag_side50", "bag_full"], hullGap=["neigh30", "neigh50"])
def auc(pos, neg):
    pos, neg = np.array(pos), np.array(neg); return float(((pos[:, None] > neg[None]).mean() + 0.5 * (pos[:, None] == neg[None]).mean())) if len(pos) and len(neg) else None
out = {}
for cue, types in T.items():
    for sp in ("tune", "check"):
        for m in ("gc", "gc64"):
            neg = [v[m][cue] for k, v in B.items() if k.endswith("_clean") and SP[k[:4]] == sp]
            for t in types:
                pos = [v[m][cue] for k, v in B.items() if k.endswith("_" + t) and SP[k[:4]] == sp]
                out[f"{cue}|{t}|{sp}|{m}"] = round(auc(pos, neg), 3)
json.dump(out, open(f"{O}/occ_cue_auc.json", "w"), indent=1)
for k, v in out.items():
    if k.endswith("|gc"): print(k, v)
