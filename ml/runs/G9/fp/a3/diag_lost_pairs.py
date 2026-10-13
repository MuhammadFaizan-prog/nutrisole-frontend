"""G9 A3 step 2: per-frame diagnosis of the two pairs A2 lost on the holdout (lemon_lime #1 c6e08132a, carrot #16 ca1cbf110),
from the Stage A Kaggle replay JSONs (raw = G3 boxes at the 0.35 floor after the area guard, rec = displayed tracks per config).
Usage: python diag_lost_pairs.py <stageA_hold_dir> [<a3_hold_dir>]  -> diag_lost_pairs.csv / .md"""
import json, sys, csv
NAMES = ["banana","apple","mango","citrus","guava","pomegranate","lemon_lime","tomato","potato","cucumber","carrot","capsicum"]
T1 = json.load(open("/workspace/work/nutrisole/ml/runs/G9/fp/thresholds_A1.json"))["thresholds"]
src = sys.argv[1]; a3 = sys.argv[2] if len(sys.argv) > 2 else None
rows, md = [], []
for clip, cls in (("c6e08132a", "lemon_lime"), ("ca1cbf110", "carrot")):
    r = json.load(open(f"{src}/{clip}.json")); c = NAMES.index(cls); t1 = T1[cls]
    recs = dict(r["rec"])
    if a3:
        r3 = json.load(open(f"{a3}/{clip}.json")); recs["A3"] = r3["rec"]["A3"]
    cfgs = [k for k in ("A0", "A1", "A2", "A3") if k in recs]
    dur = r["dur_s"]; shown = {k: 0.0 for k in cfgs}
    n_box035 = n_boxt1 = 0; first = {}
    for i, (t, nraw, boxes) in enumerate(r["raw"]):
        t1_ = r["raw"][i + 1][0] if i + 1 < len(r["raw"]) else dur * 1000; dt = (t1_ - t) / 1000
        sc = max([s for k, s in boxes if k == c], default=None)
        other = sorted({NAMES[k] for k, s in boxes if k != c})
        disp = {}
        for k in cfgs:
            tt, trs = recs[k][i]; assert abs(tt - t) < 0.2
            d = [x for x in trs if x[1] == c]; disp[k] = (max(x[2] for x in d) if d else None)
            if d: shown[k] += dt; first.setdefault(k, t / 1000)
        n_box035 += sc is not None; n_boxt1 += sc is not None and sc >= t1
        if sc is not None or any(v is not None for v in disp.values()):
            if sc is None: stage = "no box of this class (track matched by a box of another class; label kept by hysteresis)"
            elif sc < t1: stage = "removed by A1 threshold"
            else: stage = "passes threshold"
            rows.append(dict(clip=clip, cls=cls, t_s=round(t / 1000, 2), raw_boxes_all=nraw, g3_score=sc, passes_035=sc is not None,
                             passes_tA1=(sc is not None and sc >= t1), **{f"{k}_shown": int(disp[k] is not None) for k in cfgs},
                             **{f"{k}_track_score": disp[k] for k in cfgs}, other_classes=";".join(other), stage=stage))
    md.append(dict(clip=clip, cls=cls, dur=round(dur, 2), frames=len(r["raw"]), t1=t1, n_box035=n_box035, n_boxt1=n_boxt1,
                   shown={k: round(v, 2) for k, v in shown.items()}, first={k: round(v, 2) for k, v in first.items()}))
with open("diag_lost_pairs.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
json.dump(md, open("diag_lost_pairs_summary.json", "w"), indent=1); print(json.dumps(md, indent=1))
for x in rows: print(x)
