"""Stage D summary + frozen acceptance (prereg section 5) for every arm x guard on DEV. Usage: summarize_d.py OUT.json
Reads dev/{ARM}_{GUARD}.json, kernel metrics (AP50), out/latency_d.json."""
import json, os, glob
R = "/workspace/work/nutrisole/ml/runs/G9/stageD"; SHOW = ["citrus", "apple", "banana", "tomato", "carrot"]
SMALL = ["<0.25%", "0.25-0.5%", "0.5-1%"]; NORM = ["1-2.5%", ">=2.5%"]; GUARDS = ["g1", "g05", "g025", "ssf60", "ssf50", "none"]
AP = {}
for p, keys in (("/workspace/work/cv/g9d/kout_ctl/d_metrics.json", {"D0": "G3_val480", "Dctl": "Dctl"}), ("/workspace/work/cv/g9d/kout_d12/d_metrics.json", {"D1": "D1", "D2": "D2"})):
    if os.path.exists(p):
        m = json.load(open(p))
        for a, k in keys.items():
            v = m.get(k); v = v["val480"] if v and "val480" in v else v
            if v: AP[a] = {c: x["AP50"] for c, x in v["per_class"].items()} | {"mAP50": v["mAP50"]}
LAT = json.load(open(f"{R}/out/latency_d.json")) if os.path.exists(f"{R}/out/latency_d.json") else {}
def rec(d, cls, bins, key="val_recall_by_bin"):
    n = tp = 0
    for k, v in d[key].items():
        c, b = k.split("|")
        if c in cls and b in bins: n += v["n"]; tp += v["tp"]
    return dict(n=n, tp=tp, R=round(tp / n, 4) if n else None)
def summ(d):
    tp = sum(v["tp"] for v in d["val"].values()); fp = sum(v["fp"] for v in d["val"].values())
    p = d.get("probe_SYNTHETIC", {})
    return dict(val_small_show=rec(d, SHOW, SMALL), val_small_carrot=rec(d, ["carrot"], SMALL),
                val_small_by_class={c: rec(d, [c], SMALL)["R"] for c in SHOW}, val_normal_by_class={c: rec(d, [c], NORM)["R"] for c in SHOW},
                val_tp=tp, val_fp=fp, val_boxfree=d["val_false_boxes"]["boxfree_images"], val_PR={c: dict(P=round(v["tp"] / (v["tp"] + v["fp"]), 3) if v["tp"] + v["fp"] else None, R=v["R"]) for c, v in d["val"].items()},
                dev_det_recall={c: d["dev_det"]["per_class_recall"][c]["recall"] for c in SHOW if c in d["dev_det"]["per_class_recall"]},
                dev_det_frame_acc=d["dev_det"]["frame_acc"], dev_det_seg_acc=d["dev_det"]["segment_acc"], ttfc_p90=(d["dev_det"]["ttfc_from_visibility_ms"] or {}).get("p90"),
                ids_per_seg=d["dev_det"]["mean_ids_per_segment"], id_switches=d["dev_det"]["id_switches"], fragmentations=d["dev_det"]["fragmentations"], missed_frac=d["dev_det"]["missed_frac"],
                dev_det_mixed_false=d["dev_det"]["mixed_false_tracks"]["n"],
                neg_tracks_min=d["dev_neg"]["false_alarms_per_min"], neg_ep_min=d["dev_neg"]["fa_episodes_per_min"],
                probe_small_show=rec(p, SHOW, SMALL, "object_frame_recall_by_bin") if p else None, probe_small_carrot=rec(p, ["carrot"], SMALL, "object_frame_recall_by_bin") if p else None,
                probe_mixed_false_min=p["mixed_false_tracks"]["per_min"] if p else None, probe_ids_per_obj=p["ids_per_gt_object"]["mean_distinct_ids"] if p else None)
S = {}
for f in sorted(glob.glob(f"{R}/dev/*_*.json")):
    a, g = os.path.basename(f)[:-5].split("_", 1); S.setdefault(a, {})[g] = summ(json.load(open(f)))
B = S["D0"]["g1"]; BR = S["D0"]["none"]; out = dict(configs={}, ap50=AP, latency=LAT)
for a in S:
    for g in S[a]:
        x = S[a][g]; c = {}
        if g == "none": out["configs"][f"{a}/{g}"] = dict(metrics=x, note="raw pre-guard diagnostic, never displayed"); continue
        gain = x["val_small_show"]["R"] - B["val_small_show"]["R"]; gc = x["val_small_carrot"]["R"] - B["val_small_carrot"]["R"]
        rawgain = S[a]["none"]["val_small_show"]["R"] - BR["val_small_show"]["R"] if "none" in S[a] else None
        c["A1"] = dict(pass_=gain >= 0.10 and gc >= 0.10 and (a == "D0" or (rawgain is not None and rawgain >= 0.05)), small_show_gain_pp=round(100 * gain, 1), small_carrot_gain_pp=round(100 * gc, 1), raw_gain_pp=round(100 * rawgain, 1) if rawgain is not None else None)
        dn = {k: round(100 * (x["val_normal_by_class"][k] - B["val_normal_by_class"][k]), 1) for k in SHOW}
        dd = {k: round(100 * (x["dev_det_recall"].get(k, 0) - B["dev_det_recall"].get(k, 0)), 1) for k in B["dev_det_recall"]}
        c["A2"] = dict(pass_=min(dn.values()) >= -2 and min(dd.values()) >= -2, val_normal_pp=dn, dev_det_pp=dd)
        ap = AP.get(a); 
        if ap and "D0" in AP:
            dap = {k: round(ap[k] - AP["D0"][k], 4) for k in AP["D0"] if k != "mAP50" and k in ap}; c["A3"] = dict(pass_=min(dap.values()) >= -0.02, d_ap50=dap)
        else: c["A3"] = dict(pass_=None, note="AP missing")
        c["A4"] = dict(pass_=x["neg_tracks_min"] <= 1.0 and x["neg_ep_min"] <= 1.0, tracks_min=x["neg_tracks_min"], episodes_min=x["neg_ep_min"])
        dtp = x["val_tp"] - B["val_tp"]; dfp = x["val_fp"] - B["val_fp"]; ratio = round(dfp / dtp, 3) if dtp > 0 else None
        pm = x["probe_mixed_false_min"] / B["probe_mixed_false_min"] if B["probe_mixed_false_min"] else None
        c["A5"] = dict(pass_=dtp > 0 and ratio <= 1.0 and x["val_boxfree"] <= B["val_boxfree"] + 4 and (pm is None or pm <= 1.5), new_tp=dtp, new_fp=dfp, false_per_recovered=ratio,
                       boxfree=x["val_boxfree"], probe_mixed_false_x=round(pm, 2) if pm else None)
        c["A6"] = dict(pass_=x["ttfc_p90"] is not None and x["ttfc_p90"] <= B["ttfc_p90"] + 100, ttfc_p90=x["ttfc_p90"])
        la = LAT.get(a) or LAT.get(f"{a}_{g}"); l0 = LAT.get("D0")
        c["A7"] = dict(pass_=(la["p95"] <= 1.10 * l0["p95"]) if la and l0 else None, p95=la["p95"] if la else None, d0_p95=l0["p95"] if l0 else None)
        c["A8"] = dict(pass_=x["ids_per_seg"] <= B["ids_per_seg"] + 0.10, ids_per_seg=x["ids_per_seg"])
        adm = a in ("D0", "D1", "D2") and all(v["pass_"] for v in c.values())
        out["configs"][f"{a}/{g}"] = dict(metrics=x, criteria=c, admissible=adm, failed=[k for k, v in c.items() if v["pass_"] is False], selectable=a != "Dctl")
order = {"g1": 0, "g05": 1, "ssf60": 2, "ssf50": 3, "g025": 4}
adm = [(k, v) for k, v in out["configs"].items() if v.get("admissible")]
if adm:
    best = max(v["metrics"]["val_small_show"]["R"] for k, v in adm)
    tied = [k for k, v in adm if v["metrics"]["val_small_show"]["R"] >= best - 0.01]
    pick = sorted(tied, key=lambda k: ({"D1": 0, "D2": 1, "D0": 2}[k.split("/")[0]], order[k.split("/")[1]]))[0]
else: pick = "D0/g1"
out["pick"] = pick; out["admissible"] = [k for k, v in adm]
json.dump(out, open(__import__("sys").argv[1], "w"), indent=1)
print("pick", pick, "admissible", out["admissible"])
for k, v in out["configs"].items():
    m = v["metrics"]; print(k, "small", m["val_small_show"]["R"], "carrot", m["val_small_carrot"]["R"], "tp/fp", m["val_tp"], m["val_fp"], "bf", m["val_boxfree"], "neg", m["neg_tracks_min"], m["neg_ep_min"],
          "probeS", (m["probe_small_show"] or {}).get("R"), "pmf", m["probe_mixed_false_min"], "ttfc", m["ttfc_p90"], "fail", v.get("failed"))
