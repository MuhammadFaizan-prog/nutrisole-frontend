"""Markdown tables for G9_stageD.md from out/summary.json. Usage: tables_d.py"""
import json
S = json.load(open("/workspace/work/nutrisole/ml/runs/G9/stageD/out/summary.json")); C = S["configs"]; SHOW = ["citrus", "apple", "banana", "tomato", "carrot"]
def pct(x): return "n/a" if x is None else f"{100 * x:.1f}%"
arms = [a for a in ("D0", "D1", "D2", "Dctl") if f"{a}/g1" in C]; G = ["none", "g1", "g05", "g025", "ssf60", "ssf50"]
print("| Config | val small showcase R | val small carrot R | val TP / FP | box-free FP | DEV neg tracks/min / episodes/min | probe small showcase R (SYNTH) | probe mixed false/min (SYNTH) | TTFC p90 ms | IDs/seg | Failed |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for a in arms:
    for g in G:
        k = f"{a}/{g}"
        if k not in C: continue
        m = C[k]["metrics"]; f = C[k].get("failed"); f = "raw (diagnostic)" if f is None else (", ".join(f) or "**none (admissible)**")
        print(f"| {k} | {pct(m['val_small_show']['R'])} ({m['val_small_show']['tp']}/{m['val_small_show']['n']}) | {pct(m['val_small_carrot']['R'])} ({m['val_small_carrot']['tp']}/{m['val_small_carrot']['n']}) | {m['val_tp']} / {m['val_fp']} | {m['val_boxfree']} | {m['neg_tracks_min']} / {m['neg_ep_min']} | {pct((m['probe_small_show'] or {}).get('R'))} | {m['probe_mixed_false_min']} | {m['ttfc_p90']} | {m['ids_per_seg']} | {f} |")
print()
print("| Config | A1 gain show / carrot / raw (pp) | A2 worst normal val / DEV det (pp) | A3 worst dAP50 | A5 false per recovered | A7 p95 ms |")
print("|---|---|---|---|---|---|")
for a in arms:
    for g in G[1:]:
        k = f"{a}/{g}"
        if k not in C: continue
        c = C[k]["criteria"]
        a3 = min(c["A3"]["d_ap50"].items(), key=lambda kv: kv[1]) if c["A3"].get("d_ap50") else ("n/a", "")
        print(f"| {k} | {c['A1']['small_show_gain_pp']} / {c['A1']['small_carrot_gain_pp']} / {c['A1']['raw_gain_pp']} | {min(c['A2']['val_normal_pp'].values())} / {min(c['A2']['dev_det_pp'].values())} | {a3[0]} {a3[1]} | {c['A5']['false_per_recovered']} | {c['A7']['p95']} |")
print()
print("| Arm (raw, no guard) | " + " | ".join(f"{c} small R" for c in SHOW) + " | " + " | ".join(f"{c} normal R" for c in SHOW) + " |")
print("|---|" + "---|" * 10)
for a in arms:
    m = C[f"{a}/none"]["metrics"]
    print(f"| {a} | " + " | ".join(pct(m["val_small_by_class"][c]) for c in SHOW) + " | " + " | ".join(pct(m["val_normal_by_class"][c]) for c in SHOW) + " |")
print()
print("| Arm | DEV det frame recall: " + " / ".join(SHOW) + " | frame acc | seg acc | ID switches | missed frac |")
print("|---|---|---|---|---|---|")
for a in arms:
    m = C[f"{a}/g1"]["metrics"]
    print(f"| {a} (g1) | " + " / ".join(f"{m['dev_det_recall'].get(c, 0):.3f}" for c in SHOW) + f" | {m['dev_det_frame_acc']} | {m['dev_det_seg_acc']} | {m['id_switches']} | {m['missed_frac']} |")
print()
ap = S["ap50"]; cls = [c for c in ap.get("D0", {}) if c != "mAP50"]
print("| AP50 (val 480) | " + " | ".join(cls) + " | mAP50 |"); print("|---|" + "---|" * (len(cls) + 1))
for a in ("D0", "D1", "D2", "Dctl"):
    if a in ap: print(f"| {a} | " + " | ".join(str(ap[a].get(c)) for c in cls) + f" | {ap[a]['mAP50']} |")
