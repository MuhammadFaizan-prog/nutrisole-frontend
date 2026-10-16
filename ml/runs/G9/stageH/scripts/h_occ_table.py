"""Stage H P2 occlusion table. Stage G frozen checks = baseline (single-frame 'graded' = rubric grade + no quality reason, as the Stage G
878-crop metric). Stage H candidates add occlusion cues (ml/eval/occlusion.py) and, when present, H2 part agreement (out/occ_h2.json).
Selection on CU-tune (prereg rule): minimise leakage over all non-clean conditions subject to clean false rejection (clean crops that pass
Stage G but are rejected by the occlusion rule) <= 0.20, using >= 2 distinct cues; ties -> lower clean false rejection, then fewer cues.
Reports CU-check per condition. Writes out/occlusion.json. Usage: h_occ_table.py"""
import json, sys, itertools, collections, os, numpy as np
sys.path.insert(0, "/workspace/work/nutrisole")
from ml.eval.closeup import quality_reasons, FROZEN_GATE as P
from ml.eval.occlusion import occlusion_reasons
B = "/workspace/work/nutrisole/ml/runs/G9/stageH/out"
R = [json.loads(l) for l in open(f"{B}/occ_items.jsonl")]; CU = {}
for l in open(f"{B}/occ_cues.jsonl"): CU.update(json.loads(l))
H2 = json.load(open(f"{B}/occ_h2.json")) if os.path.exists(f"{B}/occ_h2.json") else {}
GR = {"A", "B", "C", "Reject"}; OCC = ["g_skin50", "block_red", "block_green", "block_blue", "block_white", "block_black", "block_grey", "skin30", "hand_0", "hand_1", "hand_2",
                                      "bag_side50", "bag_full", "neigh30", "neigh50", "trunc40_edge", "trunc40_inner", "trunc25_inner"]
OTHER = ["blur", "lowlight", "jpeg"]
def q(r): return dict(sidePx=r["side"], blurVar=r["blur"], meanV=r["meanV"], touchesEdge=r["edge"], visibleFrac=r["vis"], maxProb=r["maxP"], margin=r["margin"], blockiness=r["block"])
rows = []
for it in R:
    for s, d in it["sizes"].items():
        for c, r in d.items():
            k = f"{it['id']}_{s}_{c}"; cu = dict(CU[k])
            if k in H2: cu["partAgree"] = H2[k]["partAgree"]
            rows.append(dict(id=it["id"], split=it["split"], cls=it["cls"], size=int(s), cond=c, g_ok=r["grade"] in GR and not quality_reasons(q(r), P), cues=cu))
GRID = dict(minSolidity=[0, 0.6, 0.7, 0.8, 0.9], minEllipseIoU=[0, 0.6, 0.7, 0.8], maxStraightFrac=[1, 0.2, 0.3, 0.4, 0.5, 0.6], maxBorderFrac=[1, 0.3, 0.5, 0.7],
            minSegAgree=[0, 0.1, 0.2, 0.3], maxFlatFrac=[1, 0.2, 0.3, 0.4], maxColourSplit=[1e9, 30, 40, 50], minPartAgree=[0, 0.25, 0.5, 0.75, 1.0] if H2 else [0])
ACTIVE = lambda p: sum(p[k] != v for k, v in dict(minSolidity=0, minEllipseIoU=0, maxStraightFrac=1, maxBorderFrac=1, minSegAgree=0, maxFlatFrac=1, maxColourSplit=1e9, minPartAgree=0).items())
def stats(rs, p):
    deg = [r for r in rs if r["cond"] != "clean"]; cl = [r for r in rs if r["cond"] == "clean" and r["g_ok"]]
    leak = sum(r["g_ok"] and not occlusion_reasons(r["cues"], p) for r in deg)
    fr = sum(bool(occlusion_reasons(r["cues"], p)) for r in cl)
    return leak, len(deg), fr, len(cl)
def per_cond(rs, p):
    out = {}
    for c in ["clean"] + OCC + OTHER:
        x = [r for r in rs if r["cond"] == c]
        if not x: continue
        g = sum(r["g_ok"] for r in x); h = sum(r["g_ok"] and not occlusion_reasons(r["cues"], p) for r in x)
        out[c] = dict(n=len(x), stageG_graded=g, stageG_rate=round(g / len(x), 3), stageH_graded=h, stageH_rate=round(h / len(x), 3))
    return out
tune = [r for r in rows if r["split"] == "tune"]; check = [r for r in rows if r["split"] == "check"]
# vectorised-ish grid: precompute per-row cue arrays
keys = list(GRID); best = None; n_ok = 0
cand = []
for vals in itertools.product(*GRID.values()):
    p = dict(zip(keys, vals))
    if ACTIVE(p) < 2 or ACTIVE(p) > 4: continue
    cand.append(p)
def arr(rs):
    A = {k: np.array([r["cues"].get(k, 1.0 if k == "partAgree" else 0) for r in rs], float) for k in ["solidity", "ellipseIoU", "straightFrac", "borderFrac", "segAgree", "flatFrac", "colourSplit", "partAgree"]}
    return A, np.array([r["g_ok"] for r in rs]), np.array([r["cond"] == "clean" for r in rs])
def rej(A, p):
    return (A["solidity"] < p["minSolidity"]) | (A["ellipseIoU"] < p["minEllipseIoU"]) | (A["straightFrac"] > p["maxStraightFrac"]) | (A["borderFrac"] > p["maxBorderFrac"]) | \
           (A["segAgree"] < p["minSegAgree"]) | (A["flatFrac"] > p["maxFlatFrac"]) | (A["colourSplit"] > p["maxColourSplit"]) | (A["partAgree"] < p["minPartAgree"])
A, gok, clean = arr(tune); scored = []
for p in cand:
    rj = rej(A, p); leak = int((gok & ~rj & ~clean).sum()); fr = (rj & gok & clean).sum() / max(1, (gok & clean).sum())
    if fr <= 0.20: scored.append((leak, round(float(fr), 4), ACTIVE(p), p))
scored.sort(key=lambda x: (x[0], x[1], x[2])); pick = scored[0][3] if scored else None
base = dict(minSolidity=0, minEllipseIoU=0, maxStraightFrac=1, maxBorderFrac=1, minSegAgree=0, maxFlatFrac=1, maxColourSplit=1e9, minPartAgree=0)
def summary(rs, p):
    l, n, f, nc = stats(rs, p); occ = [r for r in rs if r["cond"] in OCC]
    lo = sum(r["g_ok"] and not occlusion_reasons(r["cues"], p) for r in occ)
    return dict(leak_all_degraded=l, n_degraded=n, leak_rate=round(l / n, 4), occluder_leak=lo, n_occluder=len(occ), occluder_leak_rate=round(lo / len(occ), 4),
                clean_pass_stageG=nc, clean_false_reject=f, clean_false_reject_rate=round(f / max(nc, 1), 4))
out = dict(selection="CU-tune; min leakage s.t. clean false rejection <= 0.20; 2-4 cues", n_candidates=len(cand), n_feasible=len(scored), pick=pick,
           top5=[dict(leak=s[0], fr=s[1], cues=s[2], p=s[3]) for s in scored[:5]], uses_part_agreement=bool(H2),
           tune=dict(stageG=summary(tune, base), stageH=summary(tune, pick)), check=dict(stageG=summary(check, base), stageH=summary(check, pick)),
           check_per_condition=per_cond(check, pick), tune_per_condition=per_cond(tune, pick))
# single-cue ablation on check (does any one cue alone do it?)
abl = {}
for k in keys:
    if not pick or pick[k] == base[k]: continue
    p1 = dict(base); p1[k] = pick[k]; abl[k] = summary(check, p1)
out["check_single_cue_ablation"] = abl
# full pipeline on the occluded crops: identity re-verified on the occluded crop (wide = the item's class, frozen identity pick), then the
# occlusion rule, then the Stage G checks. This is the leakage a user would see.
if H2 and os.path.exists(f"{B}/identity.json"):
    from ml.eval.verify import verify_identity
    PV = json.load(open(f"{B}/identity.json"))["pick"]; NC = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
    def full(rs, p):
        res = {}
        for c in ["clean"] + OCC + OTHER:
            x = [r for r in rs if r["cond"] == c]
            if not x: continue
            ver = [verify_identity(dict(status="identified", classId=NC.index(r["cls"])), None, H2[f"{r['id']}_{r['size']}_{r['cond']}"]["probs"], PV)["status"] == "verified" for r in x]
            g = sum(v and r["g_ok"] and not occlusion_reasons(r["cues"], p) for v, r in zip(ver, x))
            res[c] = dict(n=len(x), identity_verified=sum(ver), graded=g, rate=round(g / len(x), 3))
        occ_n = sum(res[c]["n"] for c in OCC if c in res); occ_g = sum(res[c]["graded"] for c in OCC if c in res)
        oth_n = sum(res[c]["n"] for c in OTHER if c in res); oth_g = sum(res[c]["graded"] for c in OTHER if c in res)
        return dict(per_condition=res, occluder_leak=occ_g, n_occluder=occ_n, occluder_leak_rate=round(occ_g / occ_n, 4), other_degraded_leak=oth_g, n_other=oth_n,
                    max_per_type=max(res[c]["rate"] for c in OCC if c in res), clean_graded=res["clean"]["graded"], clean_rate=res["clean"]["rate"])
    out["full_pipeline_check"] = full(check, pick); out["full_pipeline_tune"] = full(tune, pick)
    out["full_pipeline_check_identity_only"] = full(check, base)
    print("FULL check", {k: v for k, v in out["full_pipeline_check"].items() if k != "per_condition"})
    print("FULL check identity only (no occlusion rule)", {k: v for k, v in out["full_pipeline_check_identity_only"].items() if k != "per_condition"})
json.dump(out, open(f"{B}/occlusion.json" if H2 else f"{B}/occlusion_noh2.json", "w"), indent=1)
print(json.dumps({k: out[k] for k in ("pick", "tune", "check")}, indent=0)); print(json.dumps(out["check_per_condition"]))
