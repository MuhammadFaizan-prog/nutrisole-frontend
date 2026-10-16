# G4 detector comparison: CPU eval (onnx-free ultralytics .pt eval on sandbox CPU), conf 0.001 iou 0.7.
import json, os, sys
R = "/workspace/work/nutrisole/ml/runs"
def load(p, sz=None):
    if not os.path.exists(p): return {}
    return {(r["split"]): r for r in json.load(open(p))["results"] if sz is None or r["imgsz"] == sz}
def neg(p):
    if not os.path.exists(p): return None
    d = json.load(open(p)); r = list(d["results"].values())[0]; return r["fa_image_rate"]
M = {"G1champ (yolo26n 320; raw-head eval as in G1-G3 docs)": dict(imgsz=320, **load(f"{R}/G1/eval_det_yolo26n_320/eval_det.json", 320), **load(f"{R}/G3/eval_det_G1champ_oiv7/eval_det.json"), **load(f"{R}/G3/eval_pooled_G1/eval_det.json")),
     "G3champ control (yolo11n 640->480)": dict(imgsz=480, **load(f"{R}/G3/eval_det_k11_480/eval_det.json"), **load(f"{R}/G4/eval_det_G3champ_oiv7c/eval_det.json"), **load(f"{R}/G3/eval_pooled_k11_480/eval_det.json"), neg=neg(f"{R}/G3/neg_fa_k11_480.json"))}
for tag, nm in [("A1hyg", "A1 hygiene off"), ("A2bg15", "A2 backgrounds 15%"), ("det4", "det-v4 (oiv7c + lemon_lime x2)")]:
    e = load(f"{R}/G4/eval_det_{tag}/eval_det.json")
    if e: M[f"{nm} [{tag}] yolo11n 640->480"] = dict(imgsz=480, **e, **load(f"{R}/G4/eval_pooled_{tag}/eval_det.json"), neg=neg(f"{R}/G4/neg_fa_{tag}.json"))
SP = [("test", 557), ("test_rf", 149), ("test_oiv7", 123), ("test_oiv7c", 181), ("pooled", 829)]
out = ["| model | imgsz | " + " | ".join(f"{s} (n={n or '?'}) mAP50 / 50-95" for s, n in SP) + " | neg_test FA img rate (n=80, conf 0.35) |", "|---|---|" + "---|" * (len(SP) + 1)]
for k, v in M.items():
    c = [f"{v[s]['mAP50']:.3f} / {v[s]['mAP50_95']:.3f}" if s in v else "-" for s, _ in SP]
    out.append(f"| {k} | {v['imgsz']} | " + " | ".join(c) + f" | {v.get('neg') if v.get('neg') is not None else '-'} |")
CL = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
for sp in ["test_rf", "pooled", "test_oiv7c"]:
    out += ["", f"Per-class mAP50 on {sp}:", "", "| model | " + " | ".join(CL) + " |", "|---|" + "---|" * len(CL)]
    for k, v in M.items():
        if sp in v: out.append(f"| {k} | " + " | ".join(f"{v[sp]['per_class'][c]['mAP50']:.2f}" if c in v[sp]["per_class"] else "-" for c in CL) + " |")
# strict-rule per-class deltas on test_rf vs G1 champion and vs G3 control
base = {"G1": M["G1champ (yolo26n 320; raw-head eval as in G1-G3 docs)"]["test_rf"]["per_class"], "G3": M["G3champ control (yolo11n 640->480)"]["test_rf"]["per_class"]}
deltas = {}
for k, v in M.items():
    if "test_rf" not in v: continue
    pc = v["test_rf"]["per_class"]
    deltas[k] = {b: {c: round(pc.get(c, {"mAP50": 0})["mAP50"] - bb[c]["mAP50"], 4) for c in bb} for b, bb in base.items()}
out += ["", "test_rf per-class regressions > 1 pt (strict rule), vs G1 champion | vs G3 control:", ""]
for k, d in deltas.items():
    r1 = {c: x for c, x in d["G1"].items() if x < -0.01}; r3 = {c: x for c, x in d["G3"].items() if x < -0.01}
    out.append(f"- {k}: vs G1 {r1 or 'none'} | vs G3 {r3 or 'none'}")
open(f"{R}/G4/det_table.md", "w").write("\n".join(out) + "\n"); json.dump(dict(models=list(M), deltas=deltas), open(f"{R}/G4/det_deltas.json", "w"), indent=1)
print("\n".join(out))
