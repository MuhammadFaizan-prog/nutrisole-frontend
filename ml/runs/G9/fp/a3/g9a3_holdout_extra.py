"""[A3 copy: identical logic to ml/runs/G9/fp/scripts/g9fp_holdout_extra.py; only change = config path from env G9_CFG so A3 is included]
G9 Stage A holdout extras (prereg Addendum A, user additions): verified-negative-window FA, full-video-check candidates,
per-pair TTFC audit, raw-detector vs post-tracking. Usage: python g9fp_holdout_extra.py <replay_dir> <scores_json> <out_dir>"""
import csv, glob, json, os, sys, collections
import numpy as np
NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
R = "/workspace/work/nutrisole"; src, scj, out = sys.argv[1:4]; MODE = sys.argv[4] if len(sys.argv) > 4 else "all"; os.makedirs(out, exist_ok=True)
# MODE all = tiles + presence frames (prereg Addendum A); tiles = absence-check tile moments only (selected BECAUSE a detector fired: biased toward FA); samples = 6 evenly spaced presence-review frames only (unbiased)
rep = {os.path.basename(p)[:-5]: json.load(open(p)) for p in glob.glob(f"{src}/*.json")}
S = json.load(open(scj)); T = list(csv.DictReader(open(f"{R}/ml/runs/G8/review/holdout/clip_level_truth.csv")))
AB = list(csv.DictReader(open(f"{R}/ml/runs/G8/review/absence/absence_check.csv")))
CFG = json.load(open(os.environ.get("G9_CFG", f"{R}/ml/runs/G9/fp/g9fp_config.json"))); ARMS = list(CFG["configs"])
HALF, MIN_S, HI = 1.0, 0.5, 0.70

def merge(iv):
    iv = sorted(iv); o = []
    for a, b in iv:
        if o and a <= o[-1][1]: o[-1][1] = max(o[-1][1], b)
        else: o.append([a, b])
    return o
inwin = lambda t, W: any(a <= t <= b for a, b in W)

def tracks(r, arm):
    rec = r["rec"][arm]; dur = r["dur_s"]; tr = collections.defaultdict(lambda: dict(t=[], dt=[], s=[], c=collections.Counter()))
    for i, (t, ts) in enumerate(rec):
        t1 = rec[i + 1][0] if i + 1 < len(rec) else dur * 1000; dt = max(0.0, (t1 - t) / 1000)
        for x in ts:
            d = tr[x[0]]; d["t"].append(t / 1000); d["dt"].append(dt); d["s"].append(x[2]); d["c"][NAMES[x[1]]] += 1
    return tr

neg_rows, cand, ttfc_rows = [], [], []
tot = {a: collections.Counter() for a in ARMS}
for row in T:
    c = row["clip"]
    if row["status"].startswith("excluded") or c not in rep: continue
    r = rep[c]; D = r["dur_s"]
    if row["status"] != "positive_verified":
        tiles = [float(x["t_s"]) for x in AB if x["clip_id"] == c and x["t_s"]]
        samp = [D * (k + 0.5) / 6 for k in range(6)]
        pts = {"all": tiles + samp, "tiles": tiles, "samples": samp}[MODE]
        W = merge([[max(0, t - HALF), min(D, t + HALF)] for t in pts]); wmin = sum(b - a for a, b in W) / 60
        nr = dict(n=row["n"], clip=c, uploader=row["uploader"], whole_min=round(D / 60, 3), window_min=round(wmin, 3), n_tile_moments=len(tiles))
        for a in ARMS:
            thr = CFG["configs"][a]["thr"]; tr = tracks(r, a)
            wt = [k for k, d in tr.items() if any(inwin(t, W) for t in d["t"])]
            wsec = sum(dt for d in tr.values() for t, dt in zip(d["t"], d["dt"]) if inwin(t, W))
            rawf = [(t / 1000, [b for b in bs if b[1] >= thr[b[0]]]) for t, n0, bs in r["raw"]]
            raw_whole = sum(len(b) for _, b in rawf); raw_win = sum(len(b) for t, b in rawf if inwin(t, W))
            nr.update({f"{a}_fa_whole": len(tr), f"{a}_fa_window": len(wt), f"{a}_window_track_s": round(wsec, 2),
                       f"{a}_raw_boxes_whole": raw_whole, f"{a}_raw_boxes_window": raw_win,
                       f"{a}_raw_frames_with_box_frac": round(sum(1 for _, b in rawf if b) / max(1, len(rawf)), 4)})
            tot[a].update(dict(fa_whole=len(tr), fa_window=len(wt), raw_whole=raw_whole, raw_win=raw_win, wsec=wsec))
            if a == "A0":
                for k, d in tr.items():
                    out_s = sum(dt for t, dt in zip(d["t"], d["dt"]) if not inwin(t, W)); ms = max(d["s"])
                    if out_s >= MIN_S and ms >= HI:
                        also = {}
                        for b in ARMS[1:]:
                            tb = tracks(r, b); cl = d["c"].most_common(1)[0][0]
                            also[b] = any(db["c"].most_common(1)[0][0] == cl and min(db["t"]) <= max(d["t"]) and max(db["t"]) >= min(d["t"]) for db in tb.values())
                        cand.append(dict(n=row["n"], clip=c, track=k, cls=d["c"].most_common(1)[0][0], t_start_s=round(min(d["t"]), 1), t_end_s=round(max(d["t"]), 1),
                                         displayed_s=round(sum(d["dt"]), 2), max_score=round(ms, 3), **{f"also_{b}": v for b, v in also.items()}))
        neg_rows.append(nr)
    else:
        for a in ARMS:
            for p in [q for q in S["all12"][a]["pairs"] if q["clip"] == c]:
                thr = CFG["configs"][a]["thr"]; k = NAMES.index(p["cls"])
                fr = next((t / 1000 for t, n0, bs in r["raw"] if any(b[0] == k and b[1] >= thr[k] for b in bs)), None)
                ttfc_rows.append(dict(arm=a, n=row["n"], clip=c, cls=p["cls"], clip_dur_s=round(D, 1), detected=p["detected"], ttfc_from_clip_start_s=p["ttfc_s"],
                                      first_raw_box_of_class_s=None if fr is None else round(fr, 2), shown_s=p["shown_s"]))
summ = {}
for a in ARMS:
    wm = sum(x["window_min"] for x in neg_rows); hm = sum(x["whole_min"] for x in neg_rows); t = tot[a]
    summ[a] = dict(whole_clip_provisional=dict(minutes=round(hm, 2), fa_tracks=t["fa_whole"], fa_per_min=round(t["fa_whole"] / hm, 3),
                                               raw_boxes_per_min=round(t["raw_whole"] / hm, 2)),
                   verified_windows=dict(minutes=round(wm, 2), fa_tracks=t["fa_window"], fa_per_min=round(t["fa_window"] / wm, 3) if wm else None,
                                         displayed_track_s=round(t["wsec"], 1), raw_boxes_per_min=round(t["raw_win"] / wm, 2) if wm else None,
                                         clips_with_window_fa=sum(1 for x in neg_rows if x[f"{a}_fa_window"])))
    tt = [x["ttfc_from_clip_start_s"] for x in ttfc_rows if x["arm"] == a and x["detected"]]
    summ[a]["ttfc_from_clip_start_s"] = dict(p50=round(float(np.percentile(tt, 50)), 2), p90=round(float(np.percentile(tt, 90)), 2), n=len(tt)) if tt else None
json.dump(dict(summary=summ, negatives=neg_rows, full_video_check_candidates=cand, ttfc_pairs=ttfc_rows,
               defs=f"windows = union of +-{HALF}s around absence-check tile moments and the 6 presence-review frames; candidate = A0 track displayed >= {MIN_S}s outside windows with max score >= {HI}"),
          open(f"{out}/holdout_extra{"" if MODE == "all" else "_" + MODE}.json", "w"), indent=1)
for fn, rows in ((("holdout_neg_windows.csv" if MODE == "all" else f"holdout_neg_windows_{MODE}.csv"), neg_rows),) + ((("full_video_check_candidates.csv", cand), ("holdout_ttfc_pairs.csv", ttfc_rows)) if MODE == "all" else ()):
    if rows:
        with open(f"{out}/{fn}", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(json.dumps(summ, indent=1)); print("candidates", len(cand))
