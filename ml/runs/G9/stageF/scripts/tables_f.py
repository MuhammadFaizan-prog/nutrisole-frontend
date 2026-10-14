"""Markdown tables for the Stage F report from out/summary.json, kaggle metrics, feasibility and P6 files. Usage: tables_f.py > out/tables.md"""
import json, os, statistics
R = "/workspace/work/nutrisole/ml/runs/G9/stageF"; S = json.load(open(f"{R}/out/summary.json")); A = ["F0", "F1s0", "F1s1", "F2s0", "F2s1"]
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
def pc(x): return "-" if x is None else f"{100 * x:.1f}%"
def r(d): return f"{pc(d['R'])} ({d['tp']}/{d['n']})" if d and d.get("n") else "-"
print("### DEV (val stills 402 + DEV clips; probe SYNTHETIC)\n")
print("| Arm | val small show displayed (g1) | val small carrot (g1) | val small show RAW (>=0.35) | val TP / FP (g1) | box-free FP | DEV neg tracks/min / episodes/min | TTFC p90 | IDs/seg / ID sw | probe mixed false/min (SYNTH) | val mAP50 (480) |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for a in A:
    if a not in S["arms"]: continue
    x = S["arms"][a]["dev_g1"]; xr = S["arms"][a]["dev_raw"]; ap = S["ap50"].get(a, {}).get("mAP50")
    print(f"| {a} | {r(x['val_small_show'])} | {r(x['val_small_carrot'])} | {r(xr['val_small_show'])} | {x['val_tp']} / {x['val_fp']} | {x['val_boxfree']} | {x['neg_tracks_min']} / {x['neg_ep_min']} | {x['ttfc_p90']} | {x['ids_per_seg']} / {x['id_switches']} | {x['probe_mixed_false_min']} | {ap} |")
print("\n### Per-class AP50 on det_v3 val at 480 (Ultralytics val; P / R in brackets)\n")
print("| Class | " + " | ".join(A) + " | max |seed diff| |"); print("|---" * (len(A) + 2) + "|")
for c in N:
    row = []; vals = {}
    for a in A:
        v = S["ap50"].get(a, {}).get(c); vals[a] = v["AP50"] if v else None
        row.append(f"{v['AP50']:.3f} ({v['P']:.2f}/{v['R']:.2f})" if v else "-")
    sd = [abs(vals[f"{k}s0"] - vals[f"{k}s1"]) for k in ("F1", "F2") if vals.get(f"{k}s0") is not None and vals.get(f"{k}s1") is not None]
    print(f"| {c} | " + " | ".join(row) + (f" | {max(sd):.3f} |" if sd else " | - |"))
print("\n### M-DEV v2 (84 real Commons market images, agent-verified)\n")
print("| Arm | g1 TP / FP | g1 box-free FP | g1 class errors | raw035 small show | raw035 small all | raw035 small carrot | raw035 TP / FP | raw035 box-free FP | raw035 wrong-class | raw001 mAP50 | ignored in crowd (raw035) |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|")
for a in A:
    m = S["arms"].get(a, {}).get("mdev", {})
    if not m: continue
    g, q, z = m["g1"], m["raw035"], m["raw001"]
    print(f"| {a} | {g['tp']} / {g['fp']} | {g['boxfree_fp']} | {g['fp_tags'].get('class_error', 0)} | {r(q['small_show'])} | {r(q['small_all'])} | {r(q['small_carrot'])} | {q['tp']} / {q['fp']} | {q['boxfree_fp']} | {q['fp_tags'].get('class_error', 0)} | {z['map50']} | {q['ignored_in_crowd']} |")
print("\n### M-DEV v2 raw AP50 per class (floor 0.01, no guard; thin classes marked *)\n")
thin = {"mango", "guava", "potato", "capsicum"}
print("| Class | " + " | ".join(A) + " |"); print("|---" * (len(A) + 1) + "|")
for c in N:
    print(f"| {c}{'*' if c in thin else ''} | " + " | ".join(str(S["arms"].get(a, {}).get("mdev", {}).get("raw001", {}).get("ap50", {}).get(c, "-")) for a in A) + " |")
print("\n### Gates (fixed g1 post-processing)\n")
G = ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "M1", "M2", "M3"]
print("| Arm | " + " | ".join(G) + " | failed |"); print("|---" * (len(G) + 2) + "|")
for a in A[1:]:
    c = S["arms"].get(a, {}).get("criteria", {})
    def cell(k):
        v = c.get(k, {}); p = v.get("pass_"); t = "pass" if p else ("**fail**" if p is False else "n/a")
        if k == "A1": t += f" ({v.get('small_show_gain_pp')}/{v.get('small_carrot_gain_pp')}/raw {v.get('raw_gain_pp')} pp)"
        if k == "A2": t += f" (min val {min(v.get('val_normal_pp', {0: 0}).values())}, min DEVdet {min(v.get('dev_det_pp', {0: 0}).values())} pp)"
        if k == "A3": t += f" (worst {min(v.get('d_ap50', {0: 0}).values()):+.3f})" if v.get("d_ap50") else ""
        if k == "A4": t += f" ({v.get('tracks_min')}/{v.get('episodes_min')})"
        if k == "A5": t += f" (f/r {v.get('false_per_recovered')}, bf {v.get('boxfree')}, probe x{v.get('probe_mixed_false_x')})"
        if k == "A6": t += f" ({v.get('ttfc_p90')})"
        if k == "A7": t += f" ({v.get('p95')} vs {v.get('f0_p95')})"
        if k == "A8": t += f" ({v.get('ids_per_seg')})"
        if k == "M1": t += f" ({v.get('gain_pp')} pp)"
        if k == "M2": t += f" ({v.get('new_tp')}/{v.get('new_fp')})"
        if k == "M3": t += f" ({v.get('boxfree_fp')} vs {v.get('limit')})"
        return t
    print(f"| {a} | " + " | ".join(cell(k) for k in G) + f" | {', '.join(S['arms'][a]['failed'])} |")
F = f"/workspace/work/cv/g9f/feas"
if os.path.exists(F):
    print("\n### Feasibility arm R (M-DEV v2, raw, never selectable)\n")
    print("| Model / mode | raw035 small show | raw035 small carrot | raw035 TP / FP | raw035 box-free FP | raw001 mAP50 | p50 / p95 ms (isolated run) | peak RSS MB |"); print("|---|---|---|---|---|---|---|---|")
    for t in ("G3", "F2s0"):
        for m in ("base480", "full640", "tile480"):
            if not os.path.exists(f"{F}/eval_{t}_{m}.json"): continue
            e = json.load(open(f"{F}/eval_{t}_{m}.json")); c = json.load(open(f"{F}/cost_{t}_{m}.json"))
            print(f"| {t} {m} | {r(e['raw035']['small_show'])} | {r(e['raw035']['small_carrot'])} | {e['raw035']['tp']} / {e['raw035']['fp']} | {e['raw035']['boxfree_fp']} | {e['raw001']['map50']} | {c['p50_ms']} / {c['p95_ms']} | {c['peak_rss_mb']} |")
