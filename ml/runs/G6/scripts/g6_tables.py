# G6 tables: detector CPU eval of the G3-init fine-tunes (rp, rpx) vs the G3 control (historical G3/G4/G5 eval files, same
# code path and settings), strict rule per pre-registration, gauntlet rows (G4 control runs + G6 tracking runs + candidates), DEV grid.
import json, os, glob
RR = "/workspace/work/nutrisole/ml/runs"; R6 = f"{RR}/G6"; R5 = f"{RR}/G5"; R4 = f"{RR}/G4"; R3 = f"{RR}/G3"
CL = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
SUP = ["banana", "apple", "citrus", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]


def load(p):
    if not os.path.exists(p): return {}
    return {r["split"]: r for r in json.load(open(p))["results"]}


def neg(p):
    if not os.path.exists(p): return None
    return list(json.load(open(p))["results"].values())[0]["fa_image_rate"]


def kag(k):
    out = {}
    for f in glob.glob(f"{R6}/kaggle/{k}/**/*_metrics.json", recursive=True):
        j = json.load(open(f)); out["_meta"] = dict(gpu=j.get("gpu"), train_wall_s=j.get("train_wall_s"), data_counts=j.get("data_counts"))
        for e in j.get("evals", []): out[e["split"] + "_kaggle"] = e
    return out


M = {"G3 control (CHAMPION; historical eval files)": dict(**load(f"{R3}/eval_det_k11_480/eval_det.json"), **load(f"{R4}/eval_det_G3champ_oiv7c/eval_det.json"), **load(f"{R3}/eval_pooled_k11_480/eval_det.json"), **load(f"{R5}/eval_nostrips_G3champ/eval_det.json"), neg=neg(f"{R3}/neg_fa_k11_480.json"))}
for tag, k, nm in [("G6rp", "nutrisole-g6-ft-rp", "G6 rp (G3 init, replay only)"), ("G6rpx", "nutrisole-g6-ft-rpx", "G6 rpx (G3 init, replay + OIV7c + guava + whole capsicum)")]:
    e = {**load(f"{R6}/eval_det_{tag}/eval_det.json"), **load(f"{R6}/eval_pooled_{tag}/eval_det.json"), **load(f"{R6}/eval_nostrips_{tag}/eval_det.json"), **kag(k), "neg": neg(f"{R6}/neg_fa_{tag}.json")}
    if any(s in e for s in ["test", "pooled", "test_rf"]): M[f"{nm} [{tag}]"] = e
SP = [("test", 557), ("test_rf", 149), ("test_oiv7", 123), ("test_oiv7c", 181), ("pooled", 829), ("test_rf_nostrips", 149)]
o = ["Device: sandbox CPU (2-core aarch64, shared), PyTorch .pt eval via ml/eval/eval_det.py, imgsz 480, conf 0.001, iou 0.7. G3 rows are the historical G3/G4/G5 eval files (same script and settings). `test_rf_nostrips` is a VIEW.", "",
     "| model | " + " | ".join(f"{s} (n={n}) mAP50 / 50-95" for s, n in SP) + " | neg_test img FA (n=80) |", "|---|" + "---|" * (len(SP) + 1)]
for k, v in M.items():
    o.append(f"| {k} | " + " | ".join(f"{v[s]['mAP50']:.3f} / {v[s]['mAP50_95']:.3f}" if s in v else "-" for s, _ in SP) + f" | {v['neg'] if v.get('neg') is not None else '-'} |")
o += ["", "Kaggle-side evals (inside the training kernel, imgsz 480, device as listed; not CPU):", ""]
for k, v in M.items():
    for s in ["val_kaggle", "test_guava_kaggle", "test_capsicum_whole_kaggle"]:
        if s in v: o.append(f"- {k}: {s[:-7]} mAP50 {v[s]['mAP50']} / {v[s]['mAP50_95']} (n={v[s]['n']}, {v[s]['device']})")
    if "_meta" in v: o.append(f"- {k}: train {v['_meta']}")
G3 = M["G3 control (CHAMPION; historical eval files)"]; strict = {}
for sp in ["test_rf", "test_oiv7", "test_oiv7c", "pooled"]:
    o += ["", f"Per-class mAP50, {sp} (instances in brackets):", "", "| model | " + " | ".join(CL) + " |", "|---|" + "---|" * len(CL)]
    for k, v in M.items():
        if sp not in v: continue
        pc = v[sp]["per_class"]
        o.append(f"| {k} | " + " | ".join(f"{pc[c]['mAP50']:.2f} ({pc[c].get('instances', '?')})" if c in pc else "-" for c in CL) + " |")
o += ["", "Strict rule (pre-registered): a supported class dropping > 0.02 mAP50 vs G3 on test_rf, test_oiv7 or test_oiv7c (classes with < 20 instances in a split are reported but not gated):", ""]
for k, v in M.items():
    if k == list(M)[0]: continue
    fails = {}
    for sp in ["test_rf", "test_oiv7", "test_oiv7c"]:
        if sp not in v or sp not in G3: continue
        for c in SUP:
            g, x = G3[sp]["per_class"].get(c), v[sp]["per_class"].get(c)
            if not g or g.get("instances", 0) < 20: continue
            d = round((x["mAP50"] if x else 0) - g["mAP50"], 4)
            if d < -0.02: fails[f"{sp}/{c}"] = d
    pooled_ok = "pooled" in v and v["pooled"]["mAP50"] > G3["pooled"]["mAP50"]
    strict[k] = dict(per_class_fails=fails, pooled=v.get("pooled", {}).get("mAP50"), pooled_gt_g3=pooled_ok, image_pass=pooled_ok and not fails)
    o.append(f"- {k}: pooled {strict[k]['pooled']} (> 0.314: {pooled_ok}); per-class fails {fails or 'none'} -> image gates {'PASS' if strict[k]['image_pass'] else 'FAIL'}")


def grow(p, q, name):
    if not os.path.exists(p): return None
    g = json.load(open(p)); c = g["clips"]; n = json.load(open(q))["clips"]["neg"] if q and os.path.exists(q) else {}
    d, qu, ne = c.get("det", {}), c.get("quality", {}), c.get("neg", {})
    return dict(run=name, tracker=g.get("tracker_kind", "iou"), det_seg=d.get("segment_acc"), det_frame=d.get("frame_acc"), flick_static=d.get("label_flicker_per_10s_static"),
                id_switches=d.get("id_switches"), ids_per_seg=d.get("mean_ids_per_segment"), ttfc_p50=(d.get("ttfc_ms") or {}).get("p50"), ttfc_p90=(d.get("ttfc_ms") or {}).get("p90"),
                q_acc=qu.get("quality_segment_acc"), rot_rec=qu.get("rotten_segment_recall"), grade_flick=qu.get("grade_flicker_per_10s_static"),
                fa_g1neg=ne.get("false_alarms_per_min"), fa_negtest=n.get("false_alarms_per_min"), full_p50_ms=(d.get("latency_full_ms") or {}).get("p50"))


T = f"{R6}/tracking"
rows = [grow(f"{R4}/gauntlet_ff_G3champ_msc0_r1/gauntlet.json", f"{R4}/gauntlet_ff_negtest_G3champ_msc0_r1/gauntlet.json", "G4 G3champ_msc0 r1 (historical)"),
        grow(f"{T}/test_iou_r1/gauntlet.json", f"{T}/negtest_iou_r1/gauntlet.json", "G6 G3 control + IouTracker r1"),
        grow(f"{T}/test_bt_r1/gauntlet.json", f"{T}/negtest_bt_r1/gauntlet.json", "G6 G3 control + ByteTrack r1"),
        grow(f"{T}/test_bt_r2/gauntlet.json", f"{T}/negtest_bt_r2/gauntlet.json", "G6 G3 control + ByteTrack r2")]
for tag in ["G6rp", "G6rpx"]:
    for r in ["r1", "r2"]:
        rows.append(grow(f"{R6}/gauntlet_ff_{tag}_{r}/gauntlet.json", f"{R6}/gauntlet_ff_negtest_{tag}_{r}/gauntlet.json", f"{tag} + IouTracker {r}"))
rows = [r for r in rows if r]
o += ["", "Fixed-frame TEST gauntlet (stride 1; G1 det/quality/neg + G2 negtest clips; sandbox CPU shared; det imgsz 480; cls G3 E224 T=0.25; guard rule 2 off). Latency is sandbox CPU under load, not phone:", ""]
if rows:
    ks = list(rows[0]); o += ["| " + " | ".join(ks) + " |", "|" + "---|" * len(ks)]
    for r in rows: o.append("| " + " | ".join(f"{v:.3f}" if isinstance(v, float) else str(v) for v in r.values()) + " |")
dev = []
p = f"{T}/dev_iou/det_metrics_from_log.json"
if os.path.exists(p):
    d = json.load(open(p)); dev.append(dict(run="IouTracker (G6 dev_iou)", det_seg=d["segment_acc"], flick_static=d["label_flicker_per_10s_static"], id_switches=d["id_switches"], ttfc_p90=d["ttfc_ms"]["p90"]))
for b in [8, 15, 30]:
    p = f"{T}/devdet_bt_b{b}/gauntlet.json"
    if os.path.exists(p):
        d = json.load(open(p))["clips"]["det"]; dev.append(dict(run=f"ByteTrack buffer {b}", det_seg=d["segment_acc"], flick_static=d["label_flicker_per_10s_static"], id_switches=d["id_switches"], ttfc_p90=d["ttfc_ms"]["p90"]))
if dev:
    o += ["", "DEV tracker grid (G3 control; DEV det clip, 24 segments; sandbox CPU):", ""]
    ks = list(dev[0]); o += ["| " + " | ".join(ks) + " |", "|" + "---|" * len(ks)]
    for r in dev: o.append("| " + " | ".join(f"{v:.3f}" if isinstance(v, float) else str(v) for v in r.values()) + " |")
open(f"{R6}/tables.md", "w").write("\n".join(o) + "\n")
json.dump(dict(models=list(M), strict=strict, gauntlet=rows, dev=dev), open(f"{R6}/tables.json", "w"), indent=1)
print("\n".join(o))
