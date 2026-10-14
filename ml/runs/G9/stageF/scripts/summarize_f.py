"""Stage F summary + frozen gates (prereg G9_stageF_prereg.md s6): A1-A8 (Stage D definitions, vs F0 = G3) on DEV, M1-M3 (Stage E
definitions, reject-only) on M-DEV v2, for F1s0/F1s1/F2s0/F2s1 with the fixed g1 guard; raw (none) reported separately.
Admissible = all gates pass for BOTH seeds of an arm. Usage: summarize_f.py OUT.json"""
import json, os, glob, csv, collections, sys
R = "/workspace/work/nutrisole/ml/runs/G9/stageF"; SHOW = ["citrus", "apple", "banana", "tomato", "carrot"]
SMALL = ["<0.25%", "0.25-0.5%", "0.5-1%"]; NORM = ["1-2.5%", ">=2.5%"]
sys.path.insert(0, "/workspace/work/nutrisole/ml/runs/G9/stageD/scripts")
import importlib.util
spec = importlib.util.spec_from_file_location("sd", "/workspace/work/nutrisole/ml/runs/G9/stageD/scripts/summarize_d.py")
src = open("/workspace/work/nutrisole/ml/runs/G9/stageD/scripts/summarize_d.py").read(); ns = {}
exec(src.split("S = {}")[0].split("AP = {}")[0] + "\n" + "def rec" + src.split("def rec", 1)[1].split("S = {}")[0], ns)  # reuse rec() and summ()
summ = ns["summ"]
AP = {}; KM = {}
for f, arms in (("kaggle_out/f1_metrics.json", ["F1s0", "F1s1"]), ("kaggle_out/f2_metrics.json", ["F2s0", "F2s1"])):
    if os.path.exists(f"{R}/{f}"):
        m = json.load(open(f"{R}/{f}")); KM[f] = m
        AP.setdefault("F0", {c: x for c, x in m["G3_val480"]["per_class"].items()} | {"mAP50": m["G3_val480"]["mAP50"]})
        for a in arms:
            if a in m: AP[a] = {c: x for c, x in m[a]["val480"]["per_class"].items()} | {"mAP50": m[a]["val480"]["mAP50"]}
LAT = json.load(open(f"{R}/out/latency_f.json")) if os.path.exists(f"{R}/out/latency_f.json") else {}
S = {}
for f in sorted(glob.glob(f"{R}/dev/*_*.json")):
    a, g = os.path.basename(f)[:-5].split("_", 1); S.setdefault(a, {})[g] = summ(json.load(open(f)))
M = {a: json.load(open(f"{R}/out/mdev_{a}.json")) for a in S if os.path.exists(f"{R}/out/mdev_{a}.json")}
B = S["F0"]["g1"]; BR = S["F0"]["none"]; out = dict(arms={}, ap50=AP, latency=LAT)
for a in S:
    x = S[a]["g1"]; xr = S[a].get("none"); c = {}
    gain = x["val_small_show"]["R"] - B["val_small_show"]["R"]; gc = x["val_small_carrot"]["R"] - B["val_small_carrot"]["R"]
    rawgain = xr["val_small_show"]["R"] - BR["val_small_show"]["R"] if xr else None
    c["A1"] = dict(pass_=gain >= 0.10 and gc >= 0.10 and (rawgain is not None and rawgain >= 0.05), small_show_gain_pp=round(100 * gain, 1), small_carrot_gain_pp=round(100 * gc, 1), raw_gain_pp=round(100 * rawgain, 1) if rawgain is not None else None)
    dn = {k: round(100 * ((x["val_normal_by_class"][k] or 0) - (B["val_normal_by_class"][k] or 0)), 1) for k in SHOW}
    dd = {k: round(100 * (x["dev_det_recall"].get(k, 0) - B["dev_det_recall"].get(k, 0)), 1) for k in B["dev_det_recall"]}
    c["A2"] = dict(pass_=min(dn.values()) >= -2 and min(dd.values()) >= -2, val_normal_pp=dn, dev_det_pp=dd)
    if a in AP and "F0" in AP:
        dap = {k: round(AP[a][k]["AP50"] - AP["F0"][k]["AP50"], 4) for k in AP["F0"] if k != "mAP50" and k in AP[a]}; c["A3"] = dict(pass_=min(dap.values()) >= -0.02, d_ap50=dap)
    else: c["A3"] = dict(pass_=None if a != "F0" else True, note="F0 = reference" if a == "F0" else "AP missing")
    c["A4"] = dict(pass_=x["neg_tracks_min"] <= 1.0 and x["neg_ep_min"] <= 1.0, tracks_min=x["neg_tracks_min"], episodes_min=x["neg_ep_min"])
    dtp = x["val_tp"] - B["val_tp"]; dfp = x["val_fp"] - B["val_fp"]; ratio = round(dfp / dtp, 3) if dtp > 0 else None
    pm = x["probe_mixed_false_min"] / B["probe_mixed_false_min"] if B["probe_mixed_false_min"] else None
    c["A5"] = dict(pass_=dtp > 0 and ratio is not None and ratio <= 1.0 and x["val_boxfree"] <= B["val_boxfree"] + 4 and (pm is None or pm <= 1.5), new_tp=dtp, new_fp=dfp, false_per_recovered=ratio, boxfree=x["val_boxfree"], probe_mixed_false_x=round(pm, 2) if pm else None)
    c["A6"] = dict(pass_=x["ttfc_p90"] is not None and x["ttfc_p90"] <= B["ttfc_p90"] + 100, ttfc_p90=x["ttfc_p90"])
    la = LAT.get(a); l0 = LAT.get("F0")
    c["A7"] = dict(pass_=(la["p95"] <= 1.10 * l0["p95"]) if la and l0 else None, p95=la["p95"] if la else None, f0_p95=l0["p95"] if l0 else None)
    c["A8"] = dict(pass_=x["ids_per_seg"] <= B["ids_per_seg"] + 0.10, ids_per_seg=x["ids_per_seg"])
    if a in M and "F0" in M:
        m, m0 = M[a]["g1"], M["F0"]["g1"]; g1s = (m["small_show"]["R"] or 0) - (m0["small_show"]["R"] or 0); ntp = m["tp"] - m0["tp"]; nfp = m["fp"] - m0["fp"]
        c["M1"] = dict(pass_=g1s >= 0.05, gain_pp=round(100 * g1s, 2))
        c["M2"] = dict(pass_=ntp > 0 and nfp / ntp <= 1.0, new_tp=ntp, new_fp=nfp, ratio=round(nfp / ntp, 2) if ntp > 0 else None)
        c["M3"] = dict(pass_=m["boxfree_fp"] <= m0["boxfree_fp"] + 2, boxfree_fp=m["boxfree_fp"], limit=m0["boxfree_fp"] + 2)
    if a == "F0": c = {k: dict(pass_=True, note="reference") for k in c}
    md = {g: {k: M[a][g][k] for k in ("tp", "fp", "boxfree_fp", "small_show", "small_all", "small_carrot", "normal_show", "fp_tags", "map50", "ap50", "class_confusions", "ignored_in_crowd")} for g in M.get(a, {})}
    out["arms"][a] = dict(dev_g1=x, dev_raw=xr, mdev=md, criteria=c, failed=[k for k, v in c.items() if v["pass_"] is False])
for arm in ("F1", "F2"):
    seeds = [a for a in out["arms"] if a.startswith(arm)]
    out[f"{arm}_admissible"] = len(seeds) >= 2 and all(not out["arms"][s]["failed"] and all(v["pass_"] for v in out["arms"][s]["criteria"].values()) for s in seeds)
adm = [a for a in ("F1", "F2") if out[f"{a}_admissible"]]
out["pick"] = (sorted(adm, key=lambda a: ({"F1": 0, "F2": 1}[a]))[0] if adm else "F0")
json.dump(out, open(sys.argv[1], "w"), indent=1)
print("pick", out["pick"])
for a, v in out["arms"].items():
    x = v["dev_g1"]; xr = v["dev_raw"] or {}; m = v["mdev"].get("g1", {}); mr = v["mdev"].get("raw035", {})
    print(a, "DEV g1 small", x["val_small_show"]["R"], "carrot", x["val_small_carrot"]["R"], "raw small", (xr.get("val_small_show") or {}).get("R"), "tp/fp", x["val_tp"], x["val_fp"], "bf", x["val_boxfree"],
          "| M g1 tp/fp", m.get("tp"), m.get("fp"), "bf", m.get("boxfree_fp"), "| M raw035 small", (mr.get("small_show") or {}).get("R"), "tp/fp", mr.get("tp"), mr.get("fp"), "| fail", v["failed"])
