# G5 tables: detector CPU eval (+ new views), fixed-frame gauntlet (G4 rows reused for unchanged configs), DEV temporal sweep.
import json, os, glob
RR = "/workspace/work/nutrisole/ml/runs"; R5 = f"{RR}/G5"; R4 = f"{RR}/G4"; R3 = f"{RR}/G3"
CL = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
SHARED = [c for c in CL if c != "guava"]


def load(p, sz=None):
    if not os.path.exists(p): return {}
    return {r["split"]: r for r in json.load(open(p))["results"] if sz is None or r["imgsz"] == sz}


def neg(p):
    if not os.path.exists(p): return None
    return list(json.load(open(p))["results"].values())[0]["fa_image_rate"]


def kag(tag):  # Kaggle T4 metrics for the new external splits (eval device T4, imgsz 480)
    out = {}
    for f in glob.glob(f"{R5}/kaggle/*-{tag}/*{tag}*_metrics.json")+glob.glob(f"{R5}/kaggle/*-{tag}/**/*{tag}_metrics.json", recursive=True):
        for e in json.load(open(f)).get("evals", []):
            if e["imgsz"] == 480 and e["split"] in ("test_guava", "test_capsicum_whole", "val"): out[e["split"] + "_T4"] = e
    return out


M = {"G1 champion yolo26n (raw-head eval)": dict(imgsz=320, **load(f"{RR}/G1/eval_det_yolo26n_320/eval_det.json", 320), **load(f"{R3}/eval_det_G1champ_oiv7/eval_det.json"), **load(f"{R3}/eval_pooled_G1/eval_det.json")),
     "G3 control yolo11n (CHAMPION)": dict(imgsz=480, **load(f"{R3}/eval_det_k11_480/eval_det.json"), **load(f"{R4}/eval_det_G3champ_oiv7c/eval_det.json"), **load(f"{R3}/eval_pooled_k11_480/eval_det.json"), **load(f"{R5}/eval_nostrips_G3champ/eval_det.json"), neg=neg(f"{R3}/neg_fa_k11_480.json")),
     "A1 hygiene off (G4)": dict(imgsz=480, **load(f"{R4}/eval_det_A1hyg/eval_det.json"), **load(f"{R4}/eval_pooled_A1hyg/eval_det.json"), **load(f"{R5}/eval_nostrips_A1hyg/eval_det.json"), neg=neg(f"{R4}/neg_fa_A1hyg.json"))}
for tag, nm in [("det4", "det-v4 (G4 kernel, OIV7 citrus + lemon_lime x2)"), ("det4h", "det-v4hyg (G4 kernel; TEST-INFORMED)"), ("g5hn", "G5 g5hn = A1 + video hard negatives"), ("g5hnc", "G5 g5hnc = g5hn + guava + whole capsicum"), ("ft0", "G5 ft0 = A1 fine-tune @480 (1500-img subset, Kaggle CPU)"), ("fthn", "G5 fthn = ft0 recipe + video hard negatives"), ("fthnc", "G5 fthnc = fthn + guava + whole capsicum")]:
    e = load(f"{R5}/eval_det_{tag}/eval_det.json")
    e = e or load(f"{R5}/eval_pooled_{tag}/eval_det.json")
    if e: M[f"{nm} [{tag}]"] = {"imgsz": 480, **e, **load(f"{R5}/eval_pooled_{tag}/eval_det.json"), **load(f"{R5}/eval_nostrips_{tag}/eval_det.json"), **kag(tag), "neg": neg(f"{R5}/neg_fa_{tag}.json")}
SP = [("test", 557), ("test_rf", 149), ("test_oiv7", 123), ("test_oiv7c", 181), ("pooled", 829), ("test_rf_nostrips", 149)]
o = ["Device: sandbox CPU (2-core aarch64), PyTorch .pt eval, conf 0.001, iou 0.7. `test_rf_nostrips` is a G5 VIEW (test_rf with the 110 sliced capsicum-strip boxes removed); the locked test_rf is unchanged.", "",
     "| model | imgsz | " + " | ".join(f"{s} (n={n}) mAP50 / 50-95" for s, n in SP) + " | neg_test img FA (n=80, conf 0.35) |", "|---|---|" + "---|" * (len(SP) + 1)]
for k, v in M.items():
    o.append(f"| {k} | {v['imgsz']} | " + " | ".join(f"{v[s]['mAP50']:.3f} / {v[s]['mAP50_95']:.3f}" if s in v else "-" for s, _ in SP) + f" | {v['neg'] if v.get('neg') is not None else '-'} |")
o += ["", "New external splits (Kaggle T4 eval inside the training kernel, imgsz 480; not CPU):", "", "| model | test_guava mAP50 (n) | test_capsicum_whole mAP50 (n) |", "|---|---|---|"]
for k, v in M.items():
    g, c = v.get("test_guava_T4"), v.get("test_capsicum_whole_T4")
    if g or c: o.append(f"| {k} | {g['mAP50'] if g else '-'} ({g['n'] if g else '-'}) | {c['mAP50'] if c else '-'} ({c['n'] if c else '-'}) |")
for sp in ["test_rf", "pooled", "test_oiv7c"]:
    o += ["", f"Per-class mAP50, {sp}:", "", "| model | " + " | ".join(CL) + " | shared-class mean | new-class (guava) |", "|---|" + "---|" * (len(CL) + 2)]
    for k, v in M.items():
        if sp not in v: continue
        pc = v[sp]["per_class"]; sh = [pc[c]["mAP50"] for c in SHARED if c in pc]
        o.append(f"| {k} | " + " | ".join(f"{pc[c]['mAP50']:.2f}" if c in pc else "-" for c in CL) + f" | {sum(sh)/len(sh):.3f} | {pc['guava']['mAP50'] if 'guava' in pc else 'no GT'} |")
base = {"G1": M["G1 champion yolo26n (raw-head eval)"]["test_rf"]["per_class"], "G3": M["G3 control yolo11n (CHAMPION)"]["test_rf"]["per_class"]}
deltas = {}
o += ["", "Strict rule: test_rf per-class drops > 1 pt vs G1 champion | vs G3 control:", ""]
for k, v in M.items():
    if "test_rf" not in v: continue
    pc = v["test_rf"]["per_class"]
    deltas[k] = {b: {c: round(pc.get(c, {"mAP50": 0})["mAP50"] - bb[c]["mAP50"], 4) for c in bb} for b, bb in base.items()}
    r1 = {c: x for c, x in deltas[k]["G1"].items() if x < -0.01}; r3 = {c: x for c, x in deltas[k]["G3"].items() if x < -0.01}
    o.append(f"- {k}: vs G1 {r1 or 'none'} | vs G3 {r3 or 'none'}")


def grow(R, tag):
    p, q = f"{R}/gauntlet_ff_{tag}/gauntlet.json", f"{R}/gauntlet_ff_negtest_{tag}/gauntlet.json"
    if not os.path.exists(p): return None
    g = json.load(open(p)); c = g["clips"]; n = json.load(open(q))["clips"]["neg"] if os.path.exists(q) else {}
    d, qu, ne = c.get("det", {}), c.get("quality", {}), c.get("neg", {})
    return dict(run=tag, temporal=g.get("temporal"), det_seg=d.get("segment_acc"), det_frame=d.get("frame_acc"), flick_static=d.get("label_flicker_per_10s_static"), flick_all=d.get("label_flicker_per_10s_all"),
                ttfc_p90=(d.get("ttfc_ms") or {}).get("p90"), q_acc=qu.get("quality_segment_acc"), rot_rec=qu.get("rotten_segment_recall"), grade_flick=qu.get("grade_flicker_per_10s_static"),
                fa_g1neg=ne.get("false_alarms_per_min"), ep_g1neg=ne.get("fa_episodes_per_min"), fa_negtest=n.get("false_alarms_per_min"), ep_negtest=n.get("fa_episodes_per_min"), det_p50=(d.get("latency_det_ms") or {}).get("p50"))


rows = [grow(R4, "G3champ_msc0_r1"), grow(R4, "G3champ_msc0_r2"), grow(R4, "A1hyg_r1"), grow(R4, "A1hyg_r2")]
rows += [grow(R5, os.path.basename(p)[len("gauntlet_ff_"):]) for p in sorted(glob.glob(f"{R5}/gauntlet_ff_*")) if "negtest" not in p]
rows = [r for r in rows if r]
o += ["", "Fixed-frame TEST gauntlet (stride 1; G1 det/quality/neg clips + G2 negtest clip; sandbox CPU; det imgsz 480; cls G3 E224 T=0.25; guard rule 2 off). G3champ_msc0 / A1hyg rows are the G4 runs (same code path, temporal off).", ""]
if rows:
    ks = list(rows[0]); o += ["| " + " | ".join(ks) + " |", "|" + "---|" * len(ks)]
    for r in rows: o.append("| " + " | ".join((f"{v:.3f}" if isinstance(v, float) else (json.dumps(v) if isinstance(v, dict) else str(v))) for v in r.values()) + " |")
dev = []
for p in sorted(glob.glob(f"{R5}/dev/dev_*/gauntlet.json")):
    t = os.path.basename(os.path.dirname(p))[4:]; g = json.load(open(p))["clips"]; q = f"{R5}/dev/devneg_{t}/gauntlet.json"
    nn = json.load(open(q))["clips"]["neg"] if os.path.exists(q) else {}
    d = g.get("det", {}); ne = g.get("neg", {})
    dev.append(dict(run=t, det_seg=d.get("segment_acc"), det_frame=d.get("frame_acc"), flick_static=d.get("label_flicker_per_10s_static"), flick_all=d.get("label_flicker_per_10s_all"), ttfc_p90=(d.get("ttfc_ms") or {}).get("p90"), fa_devneg=ne.get("false_alarms_per_min"), fa_devneg2=nn.get("false_alarms_per_min")))
if dev:
    o += ["", "DEV temporal-window sweep (G3 DEV clips: det + neg, plus G3 devneg clip; no classifier). C = G3 control, A = A1; wN = temporal window N:", ""]
    ks = list(dev[0]); o += ["| " + " | ".join(ks) + " |", "|" + "---|" * len(ks)]
    for r in dev: o.append("| " + " | ".join(f"{v:.3f}" if isinstance(v, float) else str(v) for v in r.values()) + " |")
open(f"{R5}/tables.md", "w").write("\n".join(o) + "\n")
json.dump(dict(models=list(M), deltas=deltas, gauntlet=rows, dev=dev), open(f"{R5}/tables.json", "w"), indent=1)
print("\n".join(o))
