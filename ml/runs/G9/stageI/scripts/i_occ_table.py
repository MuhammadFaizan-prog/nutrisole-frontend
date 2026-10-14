"""I3 occlusion table (DEV; selection on CU-tune ONLY, CU-check reported once). Baseline = Stage H FROZEN_OCC on GrabCut cues (unchanged).
(a) Fast masks: FROZEN_OCC applied to cues from gc64 / sat / lab masks - kept only if tune occluder leakage <= GrabCut's.
(b) Targeted cues: thresholds for sideTouch / skinFrac / specFrac / hullGap (OR-added to FROZEN_OCC; can only add rejections) picked on
    tune: min occluder leakage s.t. clean false rejection (clean crops passing Stage G that are rejected) <= 0.20 (Stage H limit).
Leakage is reported (i) rule-only (occlusion rule + Stage G, no identity) and (ii) full pipeline (identity re-verified with H2, as Stage H).
Writes out/occ_stageI.json. Usage: i_occ_table.py"""
import json, sys, itertools, collections, numpy as np
sys.path.insert(0, "/workspace/work/nutrisole")
from ml.eval.closeup import quality_reasons, FROZEN_GATE
from ml.eval.occlusion import occlusion_reasons, targeted_reasons, FROZEN_OCC
from ml.eval.verify import verify_identity, FROZEN_VERIFY
S = "/workspace/work/nutrisole/ml/runs/G9/stageH/out"; O = "/workspace/work/nutrisole/ml/runs/G9/stageI/out"
R = [json.loads(l) for l in open(f"{S}/occ_items.jsonl")]; BEN = {json.loads(l)["k"]: json.loads(l) for l in open(f"{O}/occ_bench.jsonl")}
ST = {}; [ST.update(json.loads(l)) for l in open(f"{S}/occ_cues.jsonl")]; H2 = json.load(open(f"{S}/occ_h2.json"))
NC = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
OCC = ["g_skin50", "block_red", "block_green", "block_blue", "block_white", "block_black", "block_grey", "skin30", "hand_0", "hand_1", "hand_2", "bag_side50", "bag_full", "neigh30", "neigh50", "trunc40_edge", "trunc40_inner", "trunc25_inner"]
GR = {"A", "B", "C", "Reject"}
def q(r): return dict(sidePx=r["side"], blurVar=r["blur"], meanV=r["meanV"], touchesEdge=r["edge"], visibleFrac=r["vis"], maxProb=r["maxP"], margin=r["margin"], blockiness=r["block"])
rows = []
for it in R:
    for s, d in it["sizes"].items():
        for c, r in d.items():
            k = f"{it['id']}_{s}_{c}"
            if k not in BEN: continue
            ver = verify_identity(dict(status="identified", classId=NC.index(it["cls"])), None, H2[k]["probs"], FROZEN_VERIFY)["status"] == "verified"
            rows.append(dict(k=k, split=it["split"], cond=c, size=int(s), g_ok=r["grade"] in GR and not quality_reasons(q(r), FROZEN_GATE), ver=ver, b=BEN[k]))
# GrabCut recompute vs stored Stage H cues (GrabCut is deterministic per input; differences = none expected)
agree = sum(all(abs(rw["b"]["gc"][x] - ST[rw["k"]][x]) < 1e-3 for x in ("solidity", "ellipseIoU", "straightFrac", "borderFrac")) for rw in rows)
def rej(rw, mask, tp):
    c = rw["b"][mask]; return bool(occlusion_reasons(c, FROZEN_OCC) or (tp and targeted_reasons(c, tp)))
def metrics(rs, mask="gc", tp=None, identity=False):
    ok = lambda rw: rw["g_ok"] and (rw["ver"] or not identity) and not rej(rw, mask, tp)
    occ = [rw for rw in rs if rw["cond"] in OCC]; cl = [rw for rw in rs if rw["cond"] == "clean"]
    per = {c: round(sum(ok(rw) for rw in rs if rw["cond"] == c) / max(1, sum(rw["cond"] == c for rw in rs)), 4) for c in OCC}
    clg = [rw for rw in cl if rw["g_ok"]]
    return dict(occ_leak=sum(ok(rw) for rw in occ), n_occ=len(occ), occ_leak_rate=round(sum(ok(rw) for rw in occ) / len(occ), 4),
                max_type=max(per, key=per.get), max_type_rate=per[max(per, key=per.get)], per_type=per,
                clean_graded=sum(ok(rw) for rw in cl), n_clean=len(cl), clean_false_reject=round(sum(rej(rw, mask, tp) for rw in clg) / max(1, len(clg)), 4))
tu = [r for r in rows if r["split"] == "tune"]; ch = [r for r in rows if r["split"] == "check"]
out = dict(n=len(rows), gc_recompute_matches_stageH=agree, note="DEV only. CU-tune selection, CU-check reported once. FROZEN_OCC unchanged; new cues only add rejections.")
lat = {m: dict(p50=round(float(np.percentile([r["b"][m]["ms"] for r in rows if r["size"] == s], 50)), 2), p95=round(float(np.percentile([r["b"][m]["ms"] for r in rows if r["size"] == s], 95)), 2)) for m in ("gc", "gc64", "sat", "lab") for s in (192,)}
out["mask_latency_ms_192px_sandbox"] = lat
out["masks"] = {m: dict(tune=metrics(tu, m), check=metrics(ch, m), check_full=metrics(ch, m, identity=True)) for m in ("gc", "gc64", "sat", "lab")}
for m in out["masks"]:
    out["masks"][m]["kept"] = out["masks"][m]["tune"]["occ_leak"] <= out["masks"]["gc"]["tune"]["occ_leak"] and out["masks"][m]["tune"]["clean_false_reject"] <= 0.20
GRID = dict(maxSideTouch=[1.01, 0.5, 0.6, 0.7, 0.8, 0.9], maxSkinFrac=[1.01, 0.1, 0.2, 0.3, 0.5], maxSpecFrac=[1.01, 0.05, 0.1, 0.2], maxHullGap=[1e9, 0.15, 0.2, 0.3, 0.4])
def select(mask):
    best = None
    for vals in itertools.product(*GRID.values()):
        tp = dict(zip(GRID, vals)); d = metrics(tu, mask, tp)
        if d["clean_false_reject"] > 0.20: continue
        key = (d["occ_leak"], d["clean_false_reject"], sum(v != GRID[k][0] for k, v in tp.items()))
        if best is None or key < best[0]: best = (key, tp, d)
    return best
for m in ("gc", "gc64"):
    b = select(m)
    if b: out[f"targeted_{m}"] = dict(pick=b[1], tune=b[2], check=metrics(ch, m, b[1]), check_full=metrics(ch, m, b[1], identity=True), tune_full=metrics(tu, m, b[1], identity=True))
    else: out[f"targeted_{m}"] = dict(pick=None, note="infeasible: no setting keeps clean false reject <= 0.20 on tune")
# per-cue ablation on check at the picked thresholds (gc)
if out["targeted_gc"].get("pick"):
    P = out["targeted_gc"]["pick"]
    out["targeted_gc"]["check_single_cue"] = {k: metrics(ch, "gc", {**{kk: GRID[kk][0] for kk in GRID}, k: P[k]}) | {} for k in GRID if P[k] != GRID[k][0]}
json.dump(out, open(f"{O}/occ_stageI.json", "w"), indent=1)
print("gc recompute matches:", agree, "/", len(rows)); print("latency", lat)
for m, d in out["masks"].items(): print(m, "kept" if d["kept"] else "drop", {s: {k: d[s][k] for k in ("occ_leak_rate", "max_type", "max_type_rate", "clean_false_reject", "clean_graded")} for s in ("tune", "check", "check_full")})
for m in ("gc", "gc64"):
    t = out[f"targeted_{m}"]; print("targeted", m, t.get("pick"))
    if t.get("pick"): print({s: {k: t[s][k] for k in ("occ_leak_rate", "max_type", "max_type_rate", "clean_false_reject", "clean_graded")} for s in ("tune", "check", "check_full", "tune_full")}); print(" trunc25_inner check_full", t["check_full"]["per_type"]["trunc25_inner"], "rule-only", t["check"]["per_type"]["trunc25_inner"])
print("baseline gc check_full trunc25_inner", out["masks"]["gc"]["check_full"]["per_type"]["trunc25_inner"])
