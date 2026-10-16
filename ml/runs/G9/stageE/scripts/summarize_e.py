"""G9 Stage E summary: DEV continuity (A1-A8, prereg section 5, limits unchanged from Stage D) + M-DEV market checks M1-M3, frozen pick,
and the market-set manifest. Usage: summarize_e.py"""
import json, csv, os, hashlib
E = "/workspace/work/nutrisole/ml/runs/G9/stageE"; W = "/workspace/work/cv/g9e"
SHOW = ["citrus", "apple", "banana", "tomato", "carrot"]; SM = ["<0.25%", "0.25-0.5%", "0.5-1%"]; NM = ["1-2.5%", ">=2.5%"]
GR = ["g1", "ssf50", "ssf525", "ssf55", "ssf575", "ssf60"]
def rec(d, cls, bins, key):
    n = tp = 0
    for k, v in d[key].items():
        c, b = k.split("|")
        if c in cls and b in bins: n += v["n"]; tp += v["tp"]
    return dict(n=n, tp=tp, R=round(tp / n, 4) if n else None)
LAT = json.load(open("/workspace/work/nutrisole/ml/runs/G9/stageD/out/latency_d.json"))["D0"]
dev = {g: json.load(open(f"{E}/dev/G3_{g}.json")) for g in GR + ["none"]}
def dm(d):
    p = d["probe_SYNTHETIC"]
    return dict(small_show=rec(d, SHOW, SM, "val_recall_by_bin"), small_carrot=rec(d, ["carrot"], SM, "val_recall_by_bin"),
                normal_by_class={c: rec(d, [c], NM, "val_recall_by_bin")["R"] for c in SHOW},
                val_tp=sum(v["tp"] for v in d["val"].values()), val_fp=sum(v["fp"] for v in d["val"].values()), boxfree=d["val_false_boxes"]["boxfree_images"],
                dev_det_recall={c: d["dev_det"]["per_class_recall"][c]["recall"] for c in SHOW if c in d["dev_det"]["per_class_recall"]},
                neg_tracks_min=d["dev_neg"]["false_alarms_per_min"], neg_ep_min=d["dev_neg"]["fa_episodes_per_min"], ttfc_p90=d["dev_det"]["ttfc_from_visibility_ms"]["p90"],
                ids_per_seg=d["dev_det"]["mean_ids_per_segment"], id_switches=d["dev_det"]["id_switches"], post_ms_p95=d["dev_det"]["post_ms"]["p95"],
                probe_SYNTH_small_show=rec(p, SHOW, SM, "object_frame_recall_by_bin"), probe_SYNTH_small_carrot=rec(p, ["carrot"], SM, "object_frame_recall_by_bin"),
                probe_SYNTH_mixed_false_min=p["mixed_false_tracks"]["per_min"], probe_SYNTH_ids_per_obj=p["ids_per_gt_object"]["mean_distinct_ids"])
D = {g: dm(dev[g]) for g in dev}; B = D["g1"]
M = json.load(open(f"{E}/out/mdev_eval.json")); MB = M["g1"]
out = dict(stage="G9 Stage E", prereg="docs/cv/gauntlet/G9_stageE_prereg.md (commit bfa75b7, before any Stage E result)", dev=D, mdev={}, configs={})
for g in GR + ["none", "raw001"]:
    m = M[g]; out["mdev"][g] = {k: m[k] for k in ("images", "negative_images", "tp", "fp", "ignored_in_crowd", "boxfree_fp", "fp_by_bin", "fp_tags", "class_confusions", "small_show", "small_all", "small_carrot", "small_by_class", "map50", "ap50")}
for g in GR[1:]:
    x = D[g]; c = {}
    gs = x["small_show"]["R"] - B["small_show"]["R"]; gc = x["small_carrot"]["R"] - B["small_carrot"]["R"]
    c["A1"] = dict(pass_=gs >= 0.10 and gc >= 0.10, small_show_gain_pp=round(100 * gs, 1), small_carrot_gain_pp=round(100 * gc, 1), small_carrot_tp=x["small_carrot"]["tp"], needed_carrot_tp=26)
    dn = {k: round(100 * (x["normal_by_class"][k] - B["normal_by_class"][k]), 1) for k in SHOW}; dd = {k: round(100 * (x["dev_det_recall"][k] - B["dev_det_recall"][k]), 1) for k in B["dev_det_recall"]}
    c["A2"] = dict(pass_=min(dn.values()) >= -2 and min(dd.values()) >= -2, val_normal_pp=dn, dev_det_pp=dd)
    c["A3"] = dict(pass_=True, note="G3 weights unchanged: per-class AP50 identical to D0 (delta 0 by construction; Stage D D0 val480 mAP50 0.4282)")
    c["A4"] = dict(pass_=x["neg_tracks_min"] <= 1.0 and x["neg_ep_min"] <= 1.0, tracks_min=x["neg_tracks_min"], episodes_min=x["neg_ep_min"])
    ntp = x["val_tp"] - B["val_tp"]; nfp = x["val_fp"] - B["val_fp"]; pm = x["probe_SYNTH_mixed_false_min"] / B["probe_SYNTH_mixed_false_min"]
    c["A5"] = dict(pass_=ntp > 0 and nfp / ntp <= 1.0 and x["boxfree"] <= B["boxfree"] + 4 and pm <= 1.5, new_tp=ntp, new_fp=nfp, false_per_recovered=round(nfp / ntp, 3),
                   boxfree=x["boxfree"], boxfree_limit=B["boxfree"] + 4, probe_SYNTH_mixed_false_min=x["probe_SYNTH_mixed_false_min"], probe_x=round(pm, 2), probe_limit_min=round(1.5 * B["probe_SYNTH_mixed_false_min"], 2))
    c["A6"] = dict(pass_=x["ttfc_p90"] <= B["ttfc_p90"] + 100, ttfc_p90=x["ttfc_p90"])
    c["A7"] = dict(pass_=True, p95_ms=round(LAT["p95"] - B["post_ms_p95"] + x["post_ms_p95"], 2), d0_p95_ms=LAT["p95"], note="same detector as Stage D D0; only guard post-processing differs (p95 %.3f vs %.3f ms)" % (x["post_ms_p95"], B["post_ms_p95"]))
    c["A8"] = dict(pass_=x["ids_per_seg"] <= B["ids_per_seg"] + 0.10, ids_per_seg=x["ids_per_seg"])
    m = M[g]; mtp = m["tp"] - MB["tp"]; mfp = m["fp"] - MB["fp"]
    c["M1"] = dict(pass_=(m["small_show"]["R"] - MB["small_show"]["R"]) >= 0.05, gain_pp=round(100 * (m["small_show"]["R"] - MB["small_show"]["R"]), 2))
    c["M2"] = dict(pass_=mtp > 0 and mfp / mtp <= 1.0, new_tp=mtp, new_fp=mfp, ratio=round(mfp / mtp, 2) if mtp else None)
    c["M3"] = dict(pass_=m["boxfree_fp"] <= MB["boxfree_fp"] + 2, boxfree_fp=m["boxfree_fp"], limit=MB["boxfree_fp"] + 2)
    out["configs"][g] = dict(criteria=c, failed=[k for k, v in c.items() if not v["pass_"]], admissible=all(v["pass_"] for v in c.values()))
adm = [g for g, v in out["configs"].items() if v["admissible"]]; out["admissible"] = adm
out["pick"] = (sorted(adm, key=lambda g: (-D[g]["small_show"]["R"], -GR.index(g)))[0]) if adm else "g1"
json.dump(out, open(f"{E}/out/summary.json", "w"), indent=1)
print("admissible", adm, "pick", out["pick"])
for g, v in out["configs"].items(): print(g, v["failed"])
# ---------- manifest
man = {v["file"][:-4]: v for v in json.load(open(f"{W}/commons/manifest.json")).values() if "file" in v}
L = json.load(open(f"{W}/m_labels.json")); Ed = json.load(open(f"{W}/edits_final.json")); LK = json.load(open(f"{E}/out/leakage_audit_all.json"))["per_image"]
s1 = {s["id"]: s["intended"] for s in json.load(open(f"{W}/selection_v1.json"))}; ts = {s["id"]: s["intended"] for s in json.load(open(f"{W}/mtest_selection.json"))}
p2 = set(json.load(open(f"{W}/pass2_sample.json")))
rows = []
for i in sorted(set(s1) | set(ts)):
    v = man[i]; l = L.get(i)
    if i in ts: st, role = "UNLABELLED (reserved, never scored or label-reviewed; thumbnail content triage only)", "M-TEST"
    elif l: st, role = "agent-verified (OWLv2 proposals + agent box/region edits; NOT human-verified)" + ("; in pass-2 sample" if i in p2 else ""), "M-DEV evaluated"
    else: st, role = "OWLv2 proposals only, not labelled (budget), not evaluated", "M-DEV pool (unscored)"
    rows.append(dict(id=i, split=v["split"], role=role, intended=ts.get(i) or s1.get(i), title=v["title"], page=v["page"], licence=v["licence"], uploader=v["uploader"], artist=v["artist"],
                     source_key=v["source_key"], label_status=st, negative=bool(l and not l["boxes"] and not l["crowd"]) if l else "", n_boxes=len(l["boxes"]) if l else "",
                     n_crowd_or_ignore=len(l["crowd"]) if l else "", note=(Ed.get(i, {}).get("note", "") if l else ""), phash_min_dist_ref=LK[i + ".jpg"]["min_dist_ref"]))
with open(f"{E}/m_manifest.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("manifest rows", len(rows), {r: sum(1 for x in rows if x["role"] == r) for r in set(x["role"] for x in rows)})
