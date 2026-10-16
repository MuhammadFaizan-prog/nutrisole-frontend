"""G9 A3 DEV replay (post-hoc follow-up, docs/cv/gauntlet/G9_A3_addendum.md): A3 = G3 0.35 floor + minHits 3, delta 0.
Same cached-detection replay and metrics as Stage A (g9fp_replay.replay, g9fp_dev summ/val_fp logic, g9fp_dev_extra TTFC-from-visibility).
A0/A1/A2 re-run here only to put all four arms in one table (must equal ml/runs/G9/fp/dev_results.json). Writes dev_results_A3.json."""
import json, os, sys, collections, time
sys.path.insert(0, "/workspace/work/nutrisole/ml/runs/G9/fp/scripts")
from g9fp_replay import replay, NAMES, C
import numpy as np
O = "/workspace/work/nutrisole/ml/runs/G9/fp"
t1 = json.load(open(f"{O}/thresholds_A1.json"))["thresholds_list"]
ARMS = {"A0": ([0.35] * 12, 2, 0.0), "A1": (t1, 2, 0.0), "A2": (t1, 3, 0.0), "A3": ([0.35] * 12, 3, 0.0)}
val = json.load(open(f"{C}/val_dets.json")); negc = json.load(open(f"{C}/devclip_neg_dets.json")); detc = json.load(open(f"{C}/devclip_det_dets.json"))
def val_fp(th):
    e = [r for r in val if not r["gt"]]
    return dict(boxfree_imgs=len(e), false_boxes=sum(1 for r in e for d in r["dets"] if d[5] >= th[d[4]]),
                imgs_with_false_box=sum(1 for r in e if any(d[5] >= th[d[4]] for d in r["dets"])))
out = {}
for a, (thr, mh, dl) in ARMS.items():
    t0 = time.perf_counter()
    mn, shn, rawn, gtn = replay("neg", thr, mh, dl, cache=negc, return_shown=True)
    md, shd, rawd, gtd = replay("det", thr, mh, dl, cache=detc, return_shown=True)
    post_ms_per_frame = 1000 * (time.perf_counter() - t0) / (len(rawn) + len(rawd))
    minutes = len(rawn) / gtn["fps"] / 60
    rows = []
    for si, seg in enumerate(gtd["segments"]):
        fv = next((fi for fi in range(seg["start"], seg["end"] + 1) if any(o["cls"] == seg["cls"] for o in gtd["frames"][fi]["objects"])), None)
        tv = gtd["frames"][fv]["t_ms"] if fv is not None else None; ts = gtd["frames"][seg["start"]]["t_ms"]; r = md["segments_detail"][si]
        first_ok = None if r["ttfc_ms"] is None else ts + r["ttfc_ms"]
        rows.append(dict(seg=si, cls=NAMES[seg["cls"]], seg_correct=r["seg_correct"], ttfc_from_seg_start_ms=None if r["ttfc_ms"] is None else round(r["ttfc_ms"]),
                         ttfc_from_first_visible_ms=None if first_ok is None or tv is None else round(first_ok - tv)))
    v = [r["ttfc_from_first_visible_ms"] for r in rows if r["ttfc_from_first_visible_ms"] is not None]
    s = [r["ttfc_from_seg_start_ms"] for r in rows if r["ttfc_from_seg_start_ms"] is not None]
    out[a] = dict(config=dict(thr=thr, minHits=mh, delta=dl),
                  det=dict(segment_acc=md["segment_acc"], frame_acc=md["frame_acc"], ttfc_ms=md["ttfc_ms"], never_correct=md["never_correct_segments"],
                           id_switches=md["id_switches"], fragmentations=md["fragmentations"], flicker_static=md["label_flicker_per_10s_static"],
                           per_class_recall=md["per_class_recall"]),
                  neg=dict(fa_min=mn["false_alarms_per_min"], false_tracks=mn["false_alarm_tracks"], minutes=mn["minutes"], life_mean_s=mn["false_track_lifetime_mean_s"],
                           life_max_s=mn["false_track_lifetime_max_s"], fa_episodes_min=mn["fa_episodes_per_min"], by_class=mn["false_tracks_by_class"],
                           raw_boxes=sum(len(f) for f in rawn), raw_boxes_per_min=round(sum(len(f) for f in rawn) / minutes, 2)),
                  val_boxfree=val_fp(thr),
                  ttfc=dict(from_segment_start=dict(p50=float(np.percentile(s, 50)), p90=float(np.percentile(s, 90)), n=len(s)),
                            from_first_visibility=dict(p50=float(np.percentile(v, 50)), p90=float(np.percentile(v, 90)), n=len(v)), per_segment=rows),
                  postproc_ms_per_frame_sandbox=round(post_ms_per_frame, 3))
ref = json.load(open(f"{O}/dev_results.json"))
out["parity_vs_stageA"] = {a: (out[a]["det"]["segment_acc"] == ref[a]["det"]["segment_acc"] and out[a]["det"]["frame_acc"] == ref[a]["det"]["frame_acc"]
                               and out[a]["neg"]["fa_min"] == ref[a]["neg"]["fa_min"] and out[a]["det"]["id_switches"] == ref[a]["det"]["id_switches"]) for a in ("A0", "A1", "A2")}
json.dump(out, open(f"{O}/a3/dev_results_A3.json", "w"), indent=1)
for a in ARMS:
    print(a, json.dumps({k: {b: v for b, v in out[a][k].items() if b not in ("per_class_recall", "per_segment")} for k in ("det", "neg", "val_boxfree", "ttfc")}), out[a]["postproc_ms_per_frame_sandbox"])
print("parity", out["parity_vs_stageA"])
