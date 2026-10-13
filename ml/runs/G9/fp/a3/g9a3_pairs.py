"""G9 A3: per-verified-pair table A0/A1/A2/A3 + false-track durations + post-processing latency.
Usage: python g9a3_pairs.py <merged_replay_dir> <holdout_scores_A3.json> <out_dir>
'frames visible' has no frame-level truth on the holdout: proxy = processed frames with a raw G3 box of the class at >= 0.35 (after area guard),
and the longest run of consecutive such frames, vs the 3 matched frames A3 needs before display."""
import json, glob, os, sys, csv, collections
import numpy as np
NAMES = ["banana","apple","mango","citrus","guava","pomegranate","lemon_lime","tomato","potato","cucumber","carrot","capsicum"]
SHOW = ["citrus","apple","banana","tomato","carrot"]
src, scj, out = sys.argv[1:4]; S = json.load(open(scj)); ARMS = ["A0","A1","A2","A3"]
rep = {os.path.basename(p)[:-5]: json.load(open(p)) for p in glob.glob(f"{src}/*.json")}
rows = []
for p0 in S["all12"]["A0"]["pairs"]:
    c, k = p0["clip"], p0["cls"]; r = rep[c]; ki = NAMES.index(k)
    hits = [any(b[0] == ki for b in bs) for t, n0, bs in r["raw"]]
    run = best = 0; first3 = None
    for i, h in enumerate(hits):
        run = run + 1 if h else 0; best = max(best, run)
        if run == 3 and first3 is None: first3 = round(r["raw"][i][0] / 1000, 2)
    fr = next((round(t / 1000, 2) for t, n0, bs in r["raw"] if any(b[0] == ki for b in bs)), None)
    row = dict(n=p0["n"], clip=c, cls=k, showcase=k in SHOW, clip_dur_s=round(r["dur_s"], 1), proc_fps=round(len(r["raw"]) / r["dur_s"], 1),
               raw_frames_with_class_box=sum(hits), longest_consecutive_run=best, meets_3_consecutive=best >= 3, first_raw_box_s=fr, first_3run_end_s=first3)
    for a in ARMS:
        q = next(x for x in S["all12"][a]["pairs"] if x["clip"] == c and x["cls"] == k)
        row[f"{a}_detected"] = q["detected"]; row[f"{a}_shown_s"] = q["shown_s"]; row[f"{a}_first_correct_s"] = q["ttfc_s"]
    row["A3_added_delay_vs_A0_s"] = round(row["A3_first_correct_s"] - row["A0_first_correct_s"], 2) if row["A3_detected"] and row["A0_detected"] else None
    rows.append(row)
with open(f"{out}/a3_pairs.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
# false-track durations on negative clips + post-processing latency
T = {x["clip"]: x for x in csv.DictReader(open("/workspace/work/nutrisole/ml/runs/G8/review/holdout/clip_level_truth.csv"))}
dur = {}; lat = collections.defaultdict(list)
for a in ARMS:
    L = []
    for c, r in rep.items():
        if T[c]["status"].startswith("excluded") or T[c]["status"] == "positive_verified": continue
        rec = r["rec"][a]; d = collections.defaultdict(float)
        for i, (t, trs) in enumerate(rec):
            t1 = rec[i + 1][0] if i + 1 < len(rec) else r["dur_s"] * 1000
            for x in trs: d[x[0]] += max(0.0, (t1 - t) / 1000)
        L += list(d.values())
    dur[a] = dict(n=len(L), mean_s=round(float(np.mean(L)), 3) if L else None, p50_s=round(float(np.median(L)), 3) if L else None,
                  p90_s=round(float(np.percentile(L, 90)), 3) if L else None, max_s=round(max(L), 2) if L else None, total_s=round(sum(L), 1),
                  share_le_0p3s=round(sum(1 for v in L if v <= 0.3 + 1e-9) / len(L), 3) if L else None)
for r in rep.values():
    for a, v in (r.get("lat_post_ms") or {}).items():
        if v: lat[a].append(v)
res = dict(pairs=rows, false_track_duration_negatives=dur,
           postproc_latency_ms_kaggle={a: dict(p50=round(float(np.median([x[0] for x in v])), 4), p95=round(float(np.median([x[2] for x in v])), 4)) for a, v in lat.items()})
json.dump(res, open(f"{out}/a3_pairs.json", "w"), indent=1)
print(json.dumps(res["false_track_duration_negatives"], indent=1)); print(res["postproc_latency_ms_kaggle"])
for x in rows: print(x)
