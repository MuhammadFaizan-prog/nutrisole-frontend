# G4 fixed-frame gauntlet table: one row per tag (G1 clips + negtest clip).
import json, os, sys, glob
R = "/workspace/work/nutrisole/ml/runs/G4"
def row(tag):
    p, q = f"{R}/gauntlet_ff_{tag}/gauntlet.json", f"{R}/gauntlet_ff_negtest_{tag}/gauntlet.json"
    if not os.path.exists(p): return None
    g = json.load(open(p))["clips"]; n = json.load(open(q))["clips"]["neg"] if os.path.exists(q) else {}
    d, qu, ne = g.get("det", {}), g.get("quality", {}), g.get("neg", {})
    f = lambda x, k: x.get(k)
    return dict(tag=tag, det_seg=f(d, "segment_acc"), det_frame=f(d, "frame_acc"), det_flick_static=f(d, "label_flicker_per_10s_static"), det_flick_all=f(d, "label_flicker_per_10s_all"),
                ttfc_p90=(d.get("ttfc_ms") or {}).get("p90"), q_seg_acc=f(qu, "quality_segment_acc"), q_det_seg=f(qu, "segment_acc"), q_rot=f(qu, "rotten_segment_recall"),
                q_flick=f(qu, "label_flicker_per_10s_static"), q_grade_flick=f(qu, "grade_flicker_per_10s_static"),
                fa_g1neg=f(ne, "false_alarms_per_min"), fa_ep_g1neg=f(ne, "fa_episodes_per_min"), fa_negtest=f(n, "false_alarms_per_min"), fa_ep_negtest=f(n, "fa_episodes_per_min"),
                det_p50=(d.get("latency_det_ms") or {}).get("p50"))
tags = sys.argv[1:] or sorted({os.path.basename(p)[len("gauntlet_ff_"):] for p in glob.glob(f"{R}/gauntlet_ff_*") if "negtest" not in p})
rows = [r for r in (row(t) for t in tags) if r]
keys = list(rows[0].keys()) if rows else []
print("| " + " | ".join(keys) + " |"); print("|" + "---|" * len(keys))
for r in rows: print("| " + " | ".join(str(round(v, 3)) if isinstance(v, float) else str(v) for v in r.values()) + " |")
json.dump(rows, open(f"{R}/gauntlet_ff_table.json", "w"), indent=1)
