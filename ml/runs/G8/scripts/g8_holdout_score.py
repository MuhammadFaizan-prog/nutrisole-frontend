"""G8 VB8-holdout clip-level scoring (prereg addendum 2026-10-14). Input: Kaggle nutrisole-g8-holdout per-clip replay JSONs
(displayed tracks per processed frame) + ml/runs/G8/review/holdout/clip_level_truth.csv (human clip-level presence).
Usage: python g8_holdout_score.py <replay_dir> <out_dir>"""
import csv, glob, json, os, sys, random, collections
import numpy as np
NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
SHOW = ["citrus", "apple", "banana", "tomato", "carrot"]
MIN_S = 0.5
src, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
T = list(csv.DictReader(open(os.path.join(os.path.dirname(__file__), "..", "review", "holdout", "clip_level_truth.csv"))))
rep = {os.path.basename(p)[:-5]: json.load(open(p)) for p in glob.glob(f"{src}/*.json")}
configs = sorted(next(iter(rep.values()))["rec"].keys())

def clip_stats(r, cfg, classes=None):
    rec = r["rec"][cfg]; dur = r["dur_s"]; disp = collections.defaultdict(float); first = {}; ids = set(); idcls = collections.defaultdict(set)
    lab_changes = 0; last_lab = {}; track_time = 0.0
    for i, (t, trs) in enumerate(rec):
        t1 = rec[i + 1][0] if i + 1 < len(rec) else dur * 1000
        dt = max(0.0, (t1 - t) / 1000)
        shown = [x for x in trs if classes is None or NAMES[x[1]] in classes]
        for c in {NAMES[x[1]] for x in shown}:
            disp[c] += dt; first.setdefault(c, t / 1000)
        for x in shown:
            ids.add(x[0]); idcls[NAMES[x[1]]].add(x[0]); track_time += dt
            if x[0] in last_lab and last_lab[x[0]] != x[1]: lab_changes += 1
            last_lab[x[0]] = x[1]
    return dict(dur=dur, disp=dict(disp), first=first, ids=len(ids), idcls={k: len(v) for k, v in idcls.items()}, lab_changes=lab_changes, track_min=track_time / 60)

def score(cfg, classes=None):
    pairs, neg, extras, excluded = [], [], [], []
    pos_min = 0.0; pos_ids = 0; lab = 0; tmin = 0.0
    for row in T:
        c = row["clip"]
        if row["status"].startswith("excluded"): excluded.append((row["n"], c, row["caveat"])); continue
        if c not in rep: excluded.append((row["n"], c, "NO REPLAY OUTPUT")); continue
        s = clip_stats(rep[c], cfg, classes); lab += s["lab_changes"]; tmin += s["track_min"]
        if row["status"] == "positive_verified":
            pos_min += s["dur"] / 60; pos_ids += s["ids"]
            pres = [k for k in row["present_classes"].split(";") if k and (classes is None or k in classes)]
            for k in pres:
                det = s["disp"].get(k, 0) >= MIN_S
                pairs.append(dict(n=row["n"], clip=c, uploader=row["uploader"], cls=k, detected=det, shown_s=round(s["disp"].get(k, 0), 2),
                                  ttfc_s=(round(s["first"][k], 2) if det else None), tracks_of_cls=s["idcls"].get(k, 0)))
            ex = sorted(k for k, v in s["disp"].items() if v >= MIN_S and k not in row["present_classes"].split(";") and k not in row["to_confirm_classes"].split(";"))
            if ex: extras.append(dict(n=row["n"], clip=c, classes=ex))
        else:
            neg.append(dict(n=row["n"], clip=c, uploader=row["uploader"], minutes=s["dur"] / 60, fa_tracks=s["ids"],
                            fa_classes=sorted(k for k, v in s["disp"].items() if v >= MIN_S)))
    det = [p for p in pairs if p["detected"]]; tt = [p["ttfc_s"] for p in det]
    per_cls = {}
    for k in sorted({p["cls"] for p in pairs}):
        P = [p for p in pairs if p["cls"] == k]; per_cls[k] = dict(n=len(P), detected=sum(p["detected"] for p in P), recall=round(sum(p["detected"] for p in P) / len(P), 3))
    nm = sum(n["minutes"] for n in neg); nt = sum(n["fa_tracks"] for n in neg)
    return dict(config=cfg, classes=("all 12" if classes is None else classes), pairs_n=len(pairs), pairs_detected=len(det),
                clip_presence_recall=round(len(det) / max(1, len(pairs)), 3), per_class=per_cls,
                neg_clips=len(neg), neg_minutes=round(nm, 2), fa_tracks=nt, fa_per_min=round(nt / nm, 3) if nm else None,
                neg_clips_with_class_fa=sum(1 for n in neg if n["fa_classes"]), neg_class_fa=sum(len(n["fa_classes"]) for n in neg),
                ttfc_proxy_s=dict(p50=(round(float(np.percentile(tt, 50)), 2) if tt else None), p90=(round(float(np.percentile(tt, 90)), 2) if tt else None), n=len(tt), missed_pairs=len(pairs) - len(det)),
                track_births_per_min_positive=round(pos_ids / pos_min, 2) if pos_min else None,
                frag_proxy_tracks_per_detected_pair=round(float(np.mean([p["tracks_of_cls"] for p in det])), 2) if det else None,
                label_changes_per_track_min=round(lab / tmin, 3) if tmin else None,
                id_switches="not measurable (no box-level track truth)", pairs=pairs, negatives=neg, unverified_extra_classes=extras, excluded=excluded)

def boot(a, b, n=1000, seed=0):
    """uploader-level bootstrap of (b - a) pooled recall and FA/min."""
    ups = sorted({p["uploader"] for p in a["pairs"]} | {x["uploader"] for x in a["negatives"]}); rng = random.Random(seed); dr, df = [], []
    for _ in range(n):
        S = [rng.choice(ups) for _ in ups]; cnt = collections.Counter(S)
        def rec(x): 
            num = sum(cnt[p["uploader"]] * p["detected"] for p in x["pairs"]); den = sum(cnt[p["uploader"]] for p in x["pairs"]); return num / den if den else None
        def fa(x):
            m = sum(cnt[q["uploader"]] * q["minutes"] for q in x["negatives"]); t = sum(cnt[q["uploader"]] * q["fa_tracks"] for q in x["negatives"]); return t / m if m else None
        ra, rb, fa_, fb = rec(a), rec(b), fa(a), fa(b)
        if ra is not None and rb is not None: dr.append(rb - ra)
        if fa_ is not None and fb is not None: df.append(fb - fa_)
    q = lambda v: [round(float(np.percentile(v, 2.5)), 3), round(float(np.percentile(v, 97.5)), 3)] if v else None
    return dict(n_uploaders=len(ups), recall_diff_ci95=q(dr), fa_per_min_diff_ci95=q(df), resamples=n)

res = {"all12": {c: score(c) for c in configs}, "show5": {c: score(c, SHOW) for c in configs}}
res["bootstrap"] = {"G3_bt_pick_vs_G3 (all12)": boot(res["all12"]["G3"], res["all12"]["G3_bt_pick"]),
                    "show_s0_vs_G3r5 (show5)": boot(res["show5"]["G3r5"], res["show5"]["show_s0"]),
                    "show_s1_vs_G3r5 (show5)": boot(res["show5"]["G3r5"], res["show5"]["show_s1"]),
                    "show_s0_vs_G3 (show5, G3 12-class restricted to 5 at display)": boot(res["show5"]["G3"], res["show5"]["show_s0"])}
lat = collections.defaultdict(list)
for r in rep.values():
    for k, v in r["lat_det_ms"].items():
        if v: lat[k].append(v)
res["kaggle_cpu_det_latency_ms_median_of_clip_percentiles"] = {k: dict(p50=round(float(np.median([x[0] for x in v])), 1), p95=round(float(np.median([x[2] for x in v])), 1)) for k, v in lat.items()}
res["replayed_clips"] = len(rep); res["meta"] = dict(min_display_s=MIN_S, truth="clip-level presence (human, Faizi), not box-level", note="Kaggle free CPU, onnxruntime 1 thread, fixed-frame ~10 fps")
json.dump(res, open(f"{out}/holdout_scores.json", "w"), indent=1)
L = ["| view | config | verified pairs | detected | clip presence recall | FA/min (neg, %s min) | neg clips w/ class FA | TTFC proxy p50 / p90 s | births/min (pos) | tracks per detected pair | label changes / track-min |" % res["all12"]["G3"]["neg_minutes"], "|---|---|---|---|---|---|---|---|---|---|---|"]
for v in ["all12", "show5"]:
    for c in configs:
        s = res[v][c]; L.append(f"| {v} | {c} | {s['pairs_n']} | {s['pairs_detected']} | {s['clip_presence_recall']} | {s['fa_per_min']} | {s['neg_clips_with_class_fa']}/{s['neg_clips']} | {s['ttfc_proxy_s']['p50']} / {s['ttfc_proxy_s']['p90']} | {s['track_births_per_min_positive']} | {s['frag_proxy_tracks_per_detected_pair']} | {s['label_changes_per_track_min']} |")
L += ["", "Per-class clip presence recall (all12 view):", "", "| class | " + " | ".join(configs) + " |", "|---|" + "---|" * len(configs)]
for k in sorted(res["all12"]["G3"]["per_class"]):
    L.append(f"| {k} (n={res['all12']['G3']['per_class'][k]['n']}) | " + " | ".join(f"{res['all12'][c]['per_class'][k]['detected']}/{res['all12'][c]['per_class'][k]['n']}" for c in configs) + " |")
L += ["", "Uploader-level bootstrap (1000) of candidate - reference:", ""] + [f"- {k}: recall diff CI95 {v['recall_diff_ci95']}, FA/min diff CI95 {v['fa_per_min_diff_ci95']} ({v['n_uploaders']} uploaders)" for k, v in res["bootstrap"].items()]
L += ["", "Kaggle CPU detector latency (1 thread, ms, median over clips): " + json.dumps(res["kaggle_cpu_det_latency_ms_median_of_clip_percentiles"])]
open(f"{out}/holdout_scores.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))
