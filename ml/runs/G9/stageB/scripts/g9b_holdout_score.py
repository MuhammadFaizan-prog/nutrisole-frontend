"""G9 Stage B holdout scoring (record only; the decision is fixed by the DEV gates in G9_stageB_prereg.md).
Adapted exactly like ml/runs/G9/fp/scripts/g9fp_holdout_score.py: executes ml/runs/G8/scripts/g8_holdout_score.py up to its result
section (clip_stats / score / boot byte-identical, truth = ml/runs/G8/review/holdout/clip_level_truth.csv), then scores arms B0/B1/B2.
Verified-window FA/min: runs ml/runs/G9/fp/a3/g9a3_holdout_extra.py (unchanged) once per arm on a per-arm view of the replay
(the Stage B kernel stores raw boxes per detector model, the G9 extra script expects one raw list per clip, so raw = raw[model of arm];
thr = 0.35 floor for every class, as deployed). Usage: python g9b_holdout_score.py <replay_dir> <out_dir>"""
import os, sys, json, subprocess, tempfile, collections
G8 = "/workspace/work/nutrisole/ml/runs/G8/scripts/g8_holdout_score.py"
EXTRA = "/workspace/work/nutrisole/ml/runs/G9/fp/a3/g9a3_holdout_extra.py"
ARMMODEL = {"B0": "G3", "B1": "B1", "B2": "G3"}
src = open(G8).read(); cut = src.index('res = {"all12"')
ns = {"__file__": G8, "__name__": "g8score"}; exec(compile(src[:cut], G8, "exec"), ns)
score, boot, configs, out, rep, np_ = ns["score"], ns["boot"], ns["configs"], ns["out"], ns["rep"], ns["np"]
SHOW = ns["SHOW"]; replay = sys.argv[1]
assert configs == ["B0", "B1", "B2"], configs
res = {"all12": {c: score(c) for c in configs}, "show5": {c: score(c, SHOW) for c in configs}}
res["bootstrap"] = {f"{c}_vs_B0 ({v})": boot(res[v]["B0"], res[v][c]) for c in configs if c != "B0" for v in ("all12", "show5")}
# pairs recovered / lost vs B0
key = lambda p: (p["n"], p["cls"])
b0 = {key(p): p["detected"] for p in res["all12"]["B0"]["pairs"]}
res["pairs_vs_B0"] = {}
for c in configs:
    d = {key(p): p["detected"] for p in res["all12"][c]["pairs"]}
    res["pairs_vs_B0"][c] = dict(detected=sum(d.values()), of=len(d),
                                 recovered=[f"#{k[0]} {k[1]}" for k in d if d[k] and not b0[k]], lost=[f"#{k[0]} {k[1]}" for k in d if b0[k] and not d[k]])
# CPU latency per processed frame (Kaggle CPU, 1 thread/clip): detector + post (+ verifier for B2); verifier calls per frame
lat = collections.defaultdict(list); calls = collections.Counter(); nproc = 0
for r in rep.values():
    nproc += r["n_processed"]
    for k, v in r["lat_arm_all"].items(): lat[k] += v
    for k, v in r["verifier_calls"].items(): calls[k] += v
res["kaggle_cpu_arm_latency_ms"] = {k: dict(p50=round(float(np_.percentile(v, 50)), 1), p95=round(float(np_.percentile(v, 95)), 1), n=len(v)) for k, v in lat.items()}
res["verifier_calls_per_frame"] = {k: round(calls[k] / nproc, 4) for k in configs}
res["replayed_clips"] = len(rep)
json.dump(res, open(f"{out}/holdout_scores.json", "w"), indent=1)
# verified windows (unchanged G9 extra script, per arm)
ext = {}
for arm in configs:
    td = tempfile.mkdtemp(); rd = f"{td}/rep"; os.makedirs(rd)
    for c, r in rep.items():
        r2 = dict(r); r2["rec"] = {arm: r["rec"][arm]}; r2["raw"] = [[t, len(bs), bs] for t, bs in r["raw"][ARMMODEL[arm]]]
        json.dump(r2, open(f"{rd}/{c}.json", "w"))
    cfgp = f"{td}/cfg.json"; json.dump({"configs": {arm: {"thr": [0.35] * 12}}}, open(cfgp, "w"))
    sc = f"{td}/s.json"; json.dump({"all12": {arm: res["all12"][arm]}}, open(sc, "w"))
    od = f"{out}/extra_{arm}"; os.makedirs(od, exist_ok=True)
    for mode in ("samples", "all"):
        subprocess.run([sys.executable, EXTRA, rd, sc, od, mode], check=True, env=dict(os.environ, G9_CFG=cfgp), stdout=subprocess.DEVNULL)
    ext[arm] = dict(samples=json.load(open(f"{od}/holdout_extra_samples.json"))["summary"][arm], union=json.load(open(f"{od}/holdout_extra.json"))["summary"][arm])
res["extra"] = ext
json.dump(res, open(f"{out}/holdout_scores.json", "w"), indent=1)
L = ["| arm | pairs detected /22 | recovered vs B0 | lost vs B0 | showcase pairs /14 | FA/min whole clip (provisional) | FA/min verified review windows | FA/min union windows | mixed-scene extra-class clips | TTFC proxy p50 / p90 s | births/min (pos) | label changes / track-min | Kaggle CPU p50 / p95 ms | verifier calls / frame |", "|---" * 14 + "|"]
for c in configs:
    a = res["all12"][c]; s5 = res["show5"][c]; pv = res["pairs_vs_B0"][c]; e = ext[c]
    L.append(f"| {c} | {pv['detected']}/{pv['of']} | {', '.join(pv['recovered']) or '-'} | {', '.join(pv['lost']) or '-'} | {s5['pairs_detected']}/{s5['pairs_n']} | "
             f"{a['fa_per_min']} ({a['fa_tracks']} tr, {a['neg_minutes']} min) | {e['samples']['verified_windows']['fa_per_min']} ({e['samples']['verified_windows']['fa_tracks']} tr, {e['samples']['verified_windows']['minutes']} min) | "
             f"{e['union']['verified_windows']['fa_per_min']} ({e['union']['verified_windows']['fa_tracks']}) | {len(a['unverified_extra_classes'])} | {a['ttfc_proxy_s']['p50']} / {a['ttfc_proxy_s']['p90']} | "
             f"{a['track_births_per_min_positive']} | {a['label_changes_per_track_min']} | {res['kaggle_cpu_arm_latency_ms'][c]['p50']} / {res['kaggle_cpu_arm_latency_ms'][c]['p95']} | {res['verifier_calls_per_frame'][c]} |")
L += ["", "| class | " + " | ".join(configs) + " |", "|---|" + "---|" * len(configs)]
for k in sorted(res["all12"]["B0"]["per_class"]):
    L.append(f"| {k} | " + " | ".join(f"{res['all12'][c]['per_class'][k]['detected']}/{res['all12'][c]['per_class'][k]['n']}" for c in configs) + " |")
L += ["", "Uploader-level bootstrap (1000), arm - B0:"] + [f"- {k}: recall diff CI95 {v['recall_diff_ci95']}, FA/min diff CI95 {v['fa_per_min_diff_ci95']} ({v['n_uploaders']} uploaders)" for k, v in res["bootstrap"].items()]
L += ["", "Per negative clip FA tracks (all12, B0/B1/B2): " + "; ".join(f"#{n['n']} {n['clip']} " + "/".join(str(next(q for q in res['all12'][c]['negatives'] if q['clip'] == n['clip'])['fa_tracks']) for c in configs) for n in res["all12"]["B0"]["negatives"])]
L += ["", "Mixed-scene extra classes (shown >= 0.5 s on verified-positive clips, class not in truth): " + "; ".join(f"{c}: " + (", ".join(f"#{x['n']} {'/'.join(x['classes'])}" for x in res['all12'][c]['unverified_extra_classes']) or "-") for c in configs)]
open(f"{out}/holdout_scores.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))
