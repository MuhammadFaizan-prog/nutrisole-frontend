"""G9 Stage A DEV extras (user additions 2026-10-14 02:20 PKT; reporting only, no re-selection):
raw-detector vs post-tracking metrics on the DEV det/neg clips per arm, and TTFC measured from first GT visibility."""
import json, sys, os, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from g9fp_replay import replay, NAMES, C
import numpy as np
O = "/workspace/work/nutrisole/ml/runs/G9/fp"
t1 = json.load(open(f"{O}/thresholds_A1.json"))["thresholds_list"]; p2 = json.load(open(f"{O}/policy_A2.json"))["pick"]
ARMS = {"A0": ([0.35] * 12, 2, 0.0), "A1": (t1, 2, 0.0), "A2": (t1, p2["minHits"], p2["delta"])}
neg_c = json.load(open(f"{C}/devclip_neg_dets.json")); det_c = json.load(open(f"{C}/devclip_det_dets.json"))
out = {}
for a, (thr, mh, dl) in ARMS.items():
    mn, shn, rawn, gtn = replay("neg", thr, mh, dl, cache=neg_c, return_shown=True)
    md, shd, rawd, gtd = replay("det", thr, mh, dl, cache=det_c, return_shown=True)
    minutes = len(rawn) / gtn["fps"] / 60
    raw = dict(boxes=sum(len(f) for f in rawn), boxes_per_min=round(sum(len(f) for f in rawn) / minutes, 2),
               frames_with_box=sum(1 for f in rawn if f), frames=len(rawn), by_class=dict(collections.Counter(NAMES[d["classId"]] for f in rawn for d in f)))
    post = dict(displayed_tracks=mn["false_alarm_tracks"], fa_min=mn["false_alarms_per_min"], frames_with_displayed_box=mn["frames_with_any_box"],
                life_mean_s=mn["false_track_lifetime_mean_s"], by_class=mn["false_tracks_by_class"])
    # TTFC from first visibility vs scorer's segment start
    rows = []
    for si, seg in enumerate(gtd["segments"]):
        fv = next((fi for fi in range(seg["start"], seg["end"] + 1) if any(o["cls"] == seg["cls"] for o in gtd["frames"][fi]["objects"])), None)
        tv = gtd["frames"][fv]["t_ms"] if fv is not None else None; ts = gtd["frames"][seg["start"]]["t_ms"]
        r = md["segments_detail"][si]
        first_ok = None if r["ttfc_ms"] is None else ts + r["ttfc_ms"]
        rows.append(dict(seg=si, cls=NAMES[seg["cls"]], seg_start_ms=round(ts), first_visible_ms=None if tv is None else round(tv),
                         ttfc_from_seg_start_ms=None if r["ttfc_ms"] is None else round(r["ttfc_ms"]),
                         ttfc_from_first_visible_ms=None if first_ok is None or tv is None else round(first_ok - tv)))
    v = [r["ttfc_from_first_visible_ms"] for r in rows if r["ttfc_from_first_visible_ms"] is not None]
    s = [r["ttfc_from_seg_start_ms"] for r in rows if r["ttfc_from_seg_start_ms"] is not None]
    rawdet_cov = sum(1 for fi, f in enumerate(rawd) if f) / len(rawd)
    out[a] = dict(neg_raw_detector=raw, neg_post_tracking=post,
                  det_raw_detector=dict(boxes_per_min=round(sum(len(f) for f in rawd) / (len(rawd) / gtd["fps"] / 60), 2), frames_with_box_frac=round(rawdet_cov, 4)),
                  det_post_tracking=dict(frame_acc=md["frame_acc"], segment_acc=md["segment_acc"], id_switches=md["id_switches"]),
                  ttfc=dict(from_segment_start=dict(p50=float(np.percentile(s, 50)), p90=float(np.percentile(s, 90)), n=len(s)),
                            from_first_visibility=dict(p50=float(np.percentile(v, 50)), p90=float(np.percentile(v, 90)), n=len(v)), per_segment=rows))
json.dump(out, open(f"{O}/dev_extra.json", "w"), indent=1)
for a in out: print(a, json.dumps({k: v for k, v in out[a].items() if k != "ttfc"}), "TTFC", {k: v for k, v in out[a]["ttfc"].items() if k != "per_segment"})
print([ (r["cls"], r["seg_start_ms"], r["first_visible_ms"]) for r in out["A0"]["ttfc"]["per_segment"][:6]])
