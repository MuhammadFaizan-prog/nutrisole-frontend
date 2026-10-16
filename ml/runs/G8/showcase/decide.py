# G8 showcase S3 decision (rule fixed in G8_prereg.md Addendum 2026-10-13). Writes ml/runs/G8/showcase/decision.json + results_autogen.md
import json, os, glob
R = "/workspace/work/nutrisole/ml/runs/G8/showcase"; SEL = ["citrus", "apple", "banana", "tomato", "carrot"]; TARGET = 0.60
g3 = json.load(open("/workspace/work/nutrisole/ml/runs/G3/eval_pooled_k11_480/eval_det.json"))["results"][0]["per_class"]
def pooled(tag):
    p = f"{R}/eval_pooled_{tag}/eval_det.json"
    return json.load(open(p))["results"][0]["per_class"] if os.path.exists(p) else None
out = dict(rule="Addendum 2026-10-13 S3", target=TARGET, classes=SEL, seeds={})
for tag in ["show_s0", "show_s1"]:
    pc = pooled(tag)
    if pc is None: out["seeds"][tag] = None; continue
    rows = {c: dict(g3=g3[c]["mAP50"], cand=pc[c]["mAP50"], cand_R=pc[c]["R"], cand_P=pc[c]["P"], g3_R=g3[c]["R"], g3_P=g3[c]["P"], inst=pc[c]["instances"],
                    cand_mAP50_95=pc[c]["mAP50_95"], g3_mAP50_95=g3[c]["mAP50_95"],
                    pass_=bool(pc[c]["mAP50"] >= g3[c]["mAP50"] and pc[c]["mAP50"] >= TARGET)) for c in SEL}
    out["seeds"][tag] = dict(per_class=rows, n_pass=sum(r["pass_"] for r in rows.values()))
def lj(p):
    return json.load(open(p)) if os.path.exists(p) else None
vid = {k: lj(f"{R}/video_dev_{k}/gauntlet.json") for k in ["G3", "G3r5", "show_s0"]}
def fa(v): 
    try: return v["clips"]["neg"]["false_alarms_per_min"]
    except Exception: return None
out["video_fa_min"] = {k: fa(v) for k, v in vid.items()}
lat = lj(f"{R}/latency.json"); out["latency"] = lat
par = lj(f"{R}/parity_show_s0.json"); out["parity"] = par
s0, s1 = out["seeds"].get("show_s0"), out["seeds"].get("show_s1")
c1 = bool(s0 and s1 and s0["n_pass"] >= 4 and s1["n_pass"] >= 4)
f0, fr = out["video_fa_min"].get("show_s0"), out["video_fa_min"].get("G3r5")
c2 = (f0 is not None and fr is not None and f0 <= fr)
c3 = bool(lat and lat["show_s0"]["p95"] <= 1.10 * lat["G3"]["p95"])
c4 = None
def fp(o):
    if isinstance(o, dict):
        if "pass" in o: return o["pass"]
        for v in o.values():
            r = fp(v)
            if r is not None: return r
    return None
if par: c4 = fp(par)
out["criteria"] = {"1_per_class_>=4of5_both_seeds": c1, "2_video_fa_min_le_G3r5": c2, "3_latency_p95_le_1.10x": c3, "4_onnx_parity": c4}
out["PASS"] = bool(c1 and c2 and c3 and (c4 is not False))
out["claimable_classes_seed0"] = [c for c in SEL if s0 and s0["per_class"][c]["pass_"]]
json.dump(out, open(f"{R}/decision.json", "w"), indent=1)
L = ["# G8 showcase results (autogen by decide.py)", "", f"Rule: G8_prereg.md Addendum 2026-10-13 S3; target {TARGET}; pooled n=829, CPU, imgsz 480, conf 0.001, iou 0.7. G3 numbers = historical CPU eval file ml/runs/G3/eval_pooled_k11_480.", ""]
L += ["| class | inst | G3 AP50 | s0 AP50 | s1 AP50 | G3 R | s0 R | G3 AP50-95 | s0 AP50-95 | s0 pass |", "|---|---|---|---|---|---|---|---|---|---|"]
for c in SEL:
    a = s0["per_class"][c] if s0 else {}; b = s1["per_class"][c] if s1 else {}
    L.append(f"| {c} | {a.get('inst')} | {a.get('g3')} | {a.get('cand')} | {b.get('cand')} | {a.get('g3_R')} | {a.get('cand_R')} | {a.get('g3_mAP50_95')} | {a.get('cand_mAP50_95')} | {a.get('pass_')} |")
L += ["", f"Video FA/min (g3clips_dev neg, IouTracker): {out['video_fa_min']}", f"Latency: {lat}", f"Criteria: {out['criteria']}", f"**PASS: {out['PASS']}**; claimable (seed 0): {out['claimable_classes_seed0']}"]
open(f"{R}/results_autogen.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))
