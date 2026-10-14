"""Stage H P2: diagnose the 35 / 878 Stage G CU-check degraded crops that passed the frozen gate (single frame). Re-derives the list
from Stage G out/feas_items.jsonl + out/feas_block.jsonl with the same rule as feas_table.degraded_emission, then summarises which
checks they passed and by what margin. Output out/leak35.json."""
import json, collections, sys
sys.path.insert(0, "/workspace/work/nutrisole")
from ml.eval.closeup import quality_reasons, FROZEN_GATE as P
G = "/workspace/work/nutrisole/ml/runs/G9/stageG/out"; B = "/workspace/work/nutrisole/ml/runs/G9/stageH/out"
R = [json.loads(l) for l in open(f"{G}/feas_items.jsonl")]; BL = {json.loads(l)["id"]: json.loads(l) for l in open(f"{G}/feas_block.jsonl")}
GRADED = {"A", "B", "C", "Reject"}; DEG = ["blur", "lowlight", "jpeg", "occlusion", "truncation"]
def q(r): return dict(sidePx=r["side"], blurVar=r["blur"], meanV=r["meanV"], touchesEdge=r["edge"], visibleFrac=r["vis"], maxProb=r["maxP"], margin=r["margin"], blockiness=r.get("block"))
def ok(r): return r["grade"] in GRADED and not quality_reasons(q(r), P)
leaks = []; n = 0
for it in R:
    if it["split"] != "check": continue
    b = BL.get(it["id"])
    for s_, d in it["sizes"].items():
        for c, r in d.items():
            if b: r["block"] = b["sizes"][s_][c]
        if int(s_) < P["minSidePx"]:
            for c, r in d.items():
                n += 1
                if ok(r): leaks.append(dict(id=it["id"], cls=it["cls"], label=it["label"], id_class=it["id_class"], size=int(s_), cond=c, **{k: r[k] for k in ("grade", "vis", "maxP", "margin", "blur", "meanV")}))
            continue
        for c in DEG:
            n += 1; r = d[c]
            if ok(r): leaks.append(dict(id=it["id"], cls=it["cls"], label=it["label"], id_class=it["id_class"], size=int(s_), cond=c, ref_grade=it["ref"]["grade"], **{k: r[k] for k in ("grade", "vis", "maxP", "margin", "blur", "meanV")}))
occ = [l for l in leaks if l["cond"] == "occlusion"]
summ = dict(n_degraded_or_small=n, n_leaks=len(leaks), by_cond=dict(collections.Counter(l["cond"] for l in leaks)),
            by_item=dict(collections.Counter(f'{l["id"]}:{l["cls"]}' for l in leaks)), by_size=dict(collections.Counter(l["size"] for l in leaks)),
            occlusion_vis_min_med_max=[min(l["vis"] for l in occ), sorted(l["vis"] for l in occ)[len(occ) // 2], max(l["vis"] for l in occ)] if occ else None,
            occlusion_maxP_min=min(l["maxP"] for l in occ) if occ else None,
            occlusion_grade_vs_ref=dict(collections.Counter(f'{l["ref_grade"]}->{l["grade"]}' for l in occ)),
            occlusion_on_wrong_or_no_id=sum(1 for l in occ if l["id_class"] != l["cls"]), leaks=leaks)
json.dump(summ, open(f"{B}/leak35.json", "w"), indent=1)
print({k: v for k, v in summ.items() if k != "leaks"})
