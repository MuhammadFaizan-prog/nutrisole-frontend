"""Summarise G9 Stage C arms into ml/runs/G9/stageC/out/summary.json + markdown tables (stdout)."""
import json, collections
D = "/workspace/work/nutrisole/ml/runs/G9/stageC/dev"; SHOW = ["citrus", "apple", "banana", "tomato", "carrot"]; SMALL = ["<0.25%", "0.25-0.5%", "0.5-1%"]
BINS = ["<0.25%", "0.25-0.5%", "0.5-1%", "1-2.5%", ">=2.5%"]
def L(m, t): return json.load(open(f"{D}/arm_{m}_{t}.json"))
def rec(tab, cls=None, bins=None):
    n = tp = 0
    for k, v in tab.items():
        c, b = k.split("|")
        if (cls is None or c in cls) and (bins is None or b in bins): n += v["n"]; tp += v["tp"]
    return (round(100 * tp / n, 1) if n else None, tp, n)
out = {}; G = ["0.01", "0.005", "0.0025", "0.0"]
for t in ("iou0.3", "iou0.2", "ctr"):
    for m in G:
        a = L(m, t); d, n, p = a["dev_det"], a["dev_neg"], a["probe_SYNTHETIC"]
        out[f"{m}|{t}"] = dict(
            det_pcr={k: v["recall"] for k, v in d["per_class_recall"].items()}, det_frame_acc=d["frame_acc"], det_seg_acc=d["segment_acc"],
            val_R={k: v["R"] for k, v in a["val"].items() if k in SHOW}, val_tp=sum(v["tp"] for v in a["val"].values()), val_false=a["val_false_boxes"],
            val_small_show=rec(a["val_recall_by_bin"], SHOW, SMALL), val_small_carrot=rec(a["val_recall_by_bin"], ["carrot"], SMALL),
            val_bins_show={b: rec(a["val_recall_by_bin"], SHOW, [b]) for b in BINS},
            neg_fa_tracks_min=n["false_alarms_per_min"], neg_tracks=n["false_alarm_tracks"], neg_ep_min=n["fa_episodes_per_min"], neg_frames_box=n["frames_with_any_box"],
            det_idsw=d["id_switches"], det_ids_seg=d["mean_ids_per_segment"], det_frag=d["fragmentations"], det_ttfc=d["ttfc_from_visibility_ms"], det_mixed_false=d["mixed_false_tracks"],
            det_ids_obj=d["ids_per_gt_object"], post_ms=dict(det=d["post_ms"], neg=n["post_ms"], probe=p["post_ms"]),
            probe_pcr={k: v["recall"] for k, v in p["per_class_recall"].items()}, probe_frame_acc=p["frame_acc"], probe_seg_acc=p["segment_acc"],
            probe_small_show=rec(p["object_frame_recall_by_bin"], SHOW, SMALL), probe_small_carrot=rec(p["object_frame_recall_by_bin"], ["carrot"], SMALL),
            probe_bins_show={b: rec(p["object_frame_recall_by_bin"], SHOW, [b]) for b in BINS},
            probe_bins_carrot={b: rec(p["object_frame_recall_by_bin"], ["carrot"], [b]) for b in BINS},
            probe_all_small=rec(p["object_frame_recall_by_bin"], None, SMALL),
            probe_idsw=p["id_switches"], probe_ids_seg=p["mean_ids_per_segment"], probe_frag=p["fragmentations"], probe_ttfc=p["ttfc_from_visibility_ms"],
            probe_never=p["never_correct_segments"], probe_ids_obj=p["ids_per_gt_object"], probe_mixed_false=p["mixed_false_tracks"],
            fallback=p.get("centre_fallback_matches"))
json.dump(out, open("/workspace/work/nutrisole/ml/runs/G9/stageC/out/summary.json", "w"), indent=1)
print(json.dumps({k: out[k] for k in out if k.endswith("iou0.3")}, indent=0)[:9000])
