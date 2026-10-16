"""G9 Stage A DEV: per-class P/R/F1 vs threshold on val stills (n=402), FA/min vs threshold on the DEV neg clip, A1 threshold
choice by the prereg rule (G9_fp_prereg.md section 3), A2 grid (section 4), A0/A1/A2 DEV evaluation. Outputs -> ml/runs/G9/fp/."""
import json, os, sys, csv, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from g9fp_replay import replay, NAMES, C
from tracker import iou
O = "/workspace/work/nutrisole/ml/runs/G9/fp"; GRID = [round(0.35 + 0.05 * i, 2) for i in range(12)]; BASE = 0.35
SHOW = ["citrus", "apple", "banana", "tomato", "carrot"]
val = json.load(open(f"{C}/val_dets.json"))
negc = json.load(open(f"{C}/devclip_neg_dets.json")); detc = json.load(open(f"{C}/devclip_det_dets.json"))

def pr(c, t):
    tp = fp = n = fp_empty = 0
    for r in val:
        g = [b for b in r["gt"] if b[4] == c]; n += len(g); used = set()
        for d in sorted([d for d in r["dets"] if d[4] == c and d[5] >= t], key=lambda d: -d[5]):
            bi, bv = None, 0.5
            for j, b in enumerate(g):
                if j in used: continue
                v = iou(d[:4], b[:4])
                if v >= bv: bi, bv = j, v
            if bi is None:
                fp += 1; fp_empty += (len(r["gt"]) == 0)
            else: used.add(bi); tp += 1
    P = tp / (tp + fp) if tp + fp else None; Rr = tp / n if n else None
    F = 2 * P * Rr / (P + Rr) if P and Rr else 0.0
    return dict(n=n, tp=tp, fp=fp, fp_on_boxfree_imgs=fp_empty, P=None if P is None else round(P, 4), R=None if Rr is None else round(Rr, 4), F1=round(F, 4))

curves = []
for c in range(12):
    for t in GRID:
        thr = [BASE] * 12; thr[c] = t
        neg = replay("neg", thr, cache=negc)
        curves.append(dict(cls=NAMES[c], t=t, **pr(c, t), neg_fa_min_this_class_only=neg["false_alarms_per_min"],
                           neg_false_tracks_of_class=neg["false_tracks_by_class"].get(NAMES[c], 0)))
with open(f"{O}/dev_threshold_curves.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(curves[0])); w.writeheader(); w.writerows(curves)
# ---- A1 rule
thr, why = [], {}
for c in range(12):
    cc = [r for r in curves if r["cls"] == NAMES[c]]; r0 = cc[0]
    if r0["n"] < 10: thr.append(BASE); why[NAMES[c]] = f"n={r0['n']} < 10 val instances: keep 0.35"; continue
    ok = [r for r in cc if r["R"] is not None and r["R"] >= r0["R"] - 0.05 - 1e-9]
    t = max(r["t"] for r in ok); thr.append(t)
    rt = [r for r in cc if r["t"] == t][0]
    why[NAMES[c]] = f"n={r0['n']}: R {r0['R']} -> {rt['R']} (drop {round(100*(r0['R']-rt['R']),1)} pp), FP {r0['fp']} -> {rt['fp']}, P {r0['P']} -> {rt['P']}"
A0 = [BASE] * 12
a0d, a0n = replay("det", A0, cache=detc), replay("neg", A0, cache=negc)
a1d = replay("det", thr, cache=detc)
guard_note = "not triggered"
if a0d["segment_acc"] - a1d["segment_acc"] > 0.042 + 1e-9:  # prereg 3.5: one-time revert of lost-segment classes
    lost = {r0["cls"] for r0, r1 in zip(a0d["segments_detail"], a1d["segments_detail"]) if r0["seg_correct"] and not r1["seg_correct"]}
    for k in lost: thr[NAMES.index(k)] = BASE
    guard_note = f"triggered: reverted {sorted(lost)} to 0.35"; a1d = replay("det", thr, cache=detc)
a1n = replay("neg", thr, cache=negc)
json.dump(dict(rule="G9_fp_prereg.md section 3 (R_c(t) >= R_c(0.35) - 0.05, all 12 classes, largest grid t; n<10 keeps 0.35)",
               grid=GRID, thresholds={NAMES[c]: thr[c] for c in range(12)}, thresholds_list=thr, why=why, det_clip_guard=guard_note,
               model="det_yolo11n_640_raw.onnx sha256 c6fcb32a5fb2f51ba34e88ce9106a52d6bbd12ae385ca8361b292d54e3d340c1, raw 480, class-wise NMS 0.7",
               frozen="frozen before any holdout replay of A1"), open(f"{O}/thresholds_A1.json", "w"), indent=1)
# ---- A2 grid
grid = []
for mh in (2, 3, 4):
    for dl in (0.0, 0.05, 0.10, 0.15):
        d, n = replay("det", thr, mh, dl, cache=detc), replay("neg", thr, mh, dl, cache=negc)
        adm = (d["segment_acc"] >= a0d["segment_acc"] - 0.042 - 1e-9 and d["frame_acc"] >= a0d["frame_acc"] - 0.05 - 1e-9
               and (d["ttfc_ms"]["p90"] or 1e9) <= (a0d["ttfc_ms"]["p90"] or 0) + 500)
        grid.append(dict(minHits=mh, delta=dl, seg=d["segment_acc"], frame=d["frame_acc"], ttfc_p50=d["ttfc_ms"]["p50"], ttfc_p90=d["ttfc_ms"]["p90"],
                         never_correct=d["never_correct_segments"], id_switches=d["id_switches"], frag=d["fragmentations"],
                         neg_fa_min=n["false_alarms_per_min"], life_mean=n["false_track_lifetime_mean_s"], life_max=n["false_track_lifetime_max_s"],
                         fa_episodes_min=n["fa_episodes_per_min"], admissible=adm))
okg = [g for g in grid if g["admissible"]]
pick = sorted(okg, key=lambda g: (g["neg_fa_min"], g["life_mean"], -g["frame"], g["minHits"], g["delta"]))[0] if okg else dict(minHits=2, delta=0.0)
with open(f"{O}/dev_A2_grid.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(grid[0])); w.writeheader(); w.writerows(grid)
json.dump(dict(rule="G9_fp_prereg.md section 4", ref_A0=dict(seg=a0d["segment_acc"], frame=a0d["frame_acc"], ttfc_p90=a0d["ttfc_ms"]["p90"]),
               pick=dict(minHits=pick["minHits"], delta=pick["delta"]), thresholds=thr, n_admissible=len(okg),
               frozen="frozen before any holdout replay of A2"), open(f"{O}/policy_A2.json", "w"), indent=1)
a2d, a2n = replay("det", thr, pick["minHits"], pick["delta"], cache=detc), replay("neg", thr, pick["minHits"], pick["delta"], cache=negc)
# ---- val image-level false boxes on box-free stills, per arm thresholds
def val_fp(th):
    e = [r for r in val if not r["gt"]]
    return dict(boxfree_imgs=len(e), false_boxes=sum(1 for r in e for d in r["dets"] if d[5] >= th[d[4]]),
                imgs_with_false_box=sum(1 for r in e if any(d[5] >= th[d[4]] for d in r["dets"])))
def summ(d, n, th):
    return dict(det=dict(segment_acc=d["segment_acc"], frame_acc=d["frame_acc"], ttfc_ms=d["ttfc_ms"], never_correct=d["never_correct_segments"],
                         id_switches=d["id_switches"], fragmentations=d["fragmentations"], flicker_static=d["label_flicker_per_10s_static"],
                         per_class_recall=d["per_class_recall"]),
                neg=dict(fa_min=n["false_alarms_per_min"], false_tracks=n["false_alarm_tracks"], minutes=n["minutes"], births_min=n["false_track_births_per_min"],
                         life_mean_s=n["false_track_lifetime_mean_s"], life_max_s=n["false_track_lifetime_max_s"], fa_episodes_min=n["fa_episodes_per_min"],
                         by_class=n["false_tracks_by_class"]), val_boxfree=val_fp(th),
                val_recall={NAMES[c]: [r for r in curves if r["cls"] == NAMES[c] and abs(r["t"] - th[c]) < 1e-9][0]["R"] for c in range(12)})
res = dict(A0=summ(a0d, a0n, A0), A1=summ(a1d, a1n, thr), A2=summ(a2d, a2n, thr), A2_policy=dict(minHits=pick["minHits"], delta=pick["delta"]),
           parity_ref_G8_dev_G3=dict(segment_acc=0.5417, frame_acc=0.4365, ttfc_p50=533, ttfc_p90=733, id_switches=68, fragmentations=22, flicker=5.0, neg_fa_min=0.75))
json.dump(res, open(f"{O}/dev_results.json", "w"), indent=1)
for k in ("A0", "A1", "A2"):
    print(k, json.dumps({a: {b: v for b, v in res[k][a].items() if b != "per_class_recall"} for a in ("det", "neg", "val_boxfree")}))
print("thr", dict(zip(NAMES, thr))); print("A2", pick); print(json.dumps(why, indent=0))
