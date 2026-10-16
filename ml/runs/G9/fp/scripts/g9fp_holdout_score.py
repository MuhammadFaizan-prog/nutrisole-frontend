"""G9 Stage A holdout scoring with the UNCHANGED G8 scorer functions: executes ml/runs/G8/scripts/g8_holdout_score.py up to its
result section (clip_stats / score / boot are byte-identical, truth = ml/runs/G8/review/holdout/clip_level_truth.csv), then
scores configs A0/A1/A2 and the G9 bootstrap pairs. Usage: python g9fp_holdout_score.py <replay_dir> <out_dir>"""
import os, sys, json
G8 = "/workspace/work/nutrisole/ml/runs/G8/scripts/g8_holdout_score.py"
src = open(G8).read(); cut = src.index('res = {"all12"')
ns = {"__file__": G8, "__name__": "g8score"}; exec(compile(src[:cut], G8, "exec"), ns)
score, boot, configs, out, rep, np_ = ns["score"], ns["boot"], ns["configs"], ns["out"], ns["rep"], ns["np"]
SHOW = ns["SHOW"]; collections = ns["collections"]
res = {"all12": {c: score(c) for c in configs}, "show5": {c: score(c, SHOW) for c in configs}}
res["bootstrap"] = {f"{c}_vs_A0 ({v})": boot(res[v]["A0"], res[v][c]) for c in configs if c != "A0" for v in ("all12", "show5")}
lat = collections.defaultdict(list)
for r in rep.values():
    for k, v in r["lat_det_ms"].items():
        if v: lat[k].append(v)
res["kaggle_cpu_det_latency_ms"] = {k: dict(p50=round(float(np_.median([x[0] for x in v])), 1), p95=round(float(np_.median([x[2] for x in v])), 1)) for k, v in lat.items()}
res["replayed_clips"] = len(rep)
json.dump(res, open(f"{out}/holdout_scores.json", "w"), indent=1)
L = [f"| view | config | pairs | detected | clip presence recall | FA/min (neg, {res['all12']['A0']['neg_minutes']} min) | FA tracks | neg clips w/ class FA | TTFC proxy p50 / p90 s | births/min (pos) | tracks per detected pair | label changes / track-min |", "|---|" * 1 + "---|" * 11]
for v in ("all12", "show5"):
    for c in configs:
        s = res[v][c]; L.append(f"| {v} | {c} | {s['pairs_n']} | {s['pairs_detected']} | {s['clip_presence_recall']} | {s['fa_per_min']} | {s['fa_tracks']} | {s['neg_clips_with_class_fa']}/{s['neg_clips']} | {s['ttfc_proxy_s']['p50']} / {s['ttfc_proxy_s']['p90']} | {s['track_births_per_min_positive']} | {s['frag_proxy_tracks_per_detected_pair']} | {s['label_changes_per_track_min']} |")
L += ["", "| class | " + " | ".join(configs) + " |", "|---|" + "---|" * len(configs)]
for k in sorted(res["all12"]["A0"]["per_class"]):
    L.append(f"| {k} | " + " | ".join(f"{res['all12'][c]['per_class'][k]['detected']}/{res['all12'][c]['per_class'][k]['n']}" for c in configs) + " |")
L += ["", "Uploader-level bootstrap (1000), candidate - A0:"] + [f"- {k}: recall diff CI95 {v['recall_diff_ci95']}, FA/min diff CI95 {v['fa_per_min_diff_ci95']} ({v['n_uploaders']} uploaders)" for k, v in res["bootstrap"].items()]
L += ["", "Per negative clip FA tracks (all12): " + "; ".join(f"#{n['n']} {n['clip']} " + "/".join(str(x['fa_tracks']) for x in [next(q for q in res['all12'][c]['negatives'] if q['clip'] == n['clip']) for c in configs]) for n in res["all12"]["A0"]["negatives"]) + f" ({'/'.join(configs)})"]
open(f"{out}/holdout_scores.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))
