# G7.3: apply the post-hoc (honestly framed) ByteTrack rule from G7_prereg.md section 3 to the EXISTING G6 TEST runs.
import json
T = "/workspace/work/nutrisole/ml/runs/G6/tracking"
ld = lambda t: json.load(open(f"{T}/{t}/gauntlet.json"))
c, b1, b2 = ld("test_iou_r1"), ld("test_bt_r1"), ld("test_bt_r2")
nc, nb1, nb2 = ld("negtest_iou_r1"), ld("negtest_bt_r1"), ld("negtest_bt_r2")
def strip(o):
    if isinstance(o, dict): return {k: strip(v) for k, v in o.items() if not any(s in k for s in ("latency", "ms_p", "_ms", "p50_ms", "fps"))}
    if isinstance(o, list): return [strip(v) for v in o]
    return o
def g(r, clip, *keys):
    v = r["clips"][clip]
    for k in keys: v = v[k]
    return v
def fa(r, clip):
    x = r["clips"][clip]
    for k in ("fa_per_min", "false_alarms_per_min", "fa_episodes_per_min"):
        if k in x: return x[k]
    return None
rows = {}
rows["det_seg_acc"] = (g(c, "det", "segment_acc"), g(b1, "det", "segment_acc"), "not lower")
rows["det_frame_acc"] = (g(c, "det", "frame_acc"), g(b1, "det", "frame_acc"), "not lower")
rows["id_switches_det"] = (g(c, "det", "id_switches"), g(b1, "det", "id_switches"), ">= 20% fewer")
rows["ttfc_p90_ms_det"] = (g(c, "det", "ttfc_ms", "p90"), g(b1, "det", "ttfc_ms", "p90"), "<= 1000 and <= 1.25x control")
print("clips:", list(c["clips"].keys()), list(nc["clips"].keys()))
for k in c["clips"]:
    print(k, {kk: vv for kk, vv in c["clips"][k].items() if not isinstance(vv, (list, dict))})
rows["fa_per_min_G1neg"] = (c["clips"]["neg"]["false_alarms_per_min"], b1["clips"]["neg"]["false_alarms_per_min"], "not higher")
rows["fa_per_min_G2negtest"] = (nc["clips"]["neg"]["false_alarms_per_min"], nb1["clips"]["neg"]["false_alarms_per_min"], "not higher")
rows["quality_acc"] = (g(c, "quality", "quality_segment_acc"), g(b1, "quality", "quality_segment_acc"), "not lower")
rows["rotten_seg_recall"] = (g(c, "quality", "rotten_segment_recall"), g(b1, "quality", "rotten_segment_recall"), "not lower")
ok = {}
for k, (cv, bv, rule) in rows.items():
    if rule == "not lower": ok[k] = bv >= cv
    elif rule == "not higher": ok[k] = bv <= cv
    elif rule.startswith(">= 20%"): ok[k] = bv <= 0.8 * cv
    else: ok[k] = bv <= 1000 and bv <= 1.25 * cv
NT = ("wall_s", "effective_fps", "latency", "_ms", "ms")
def nontiming(r):
    def f(o):
        if isinstance(o, dict): return {k: f(v) for k, v in o.items() if not (k in ("wall_s", "effective_fps", "latency_overall") or "latency" in k)}
        if isinstance(o, list): return [f(v) for v in o]
        return o
    return f(r["clips"])
ok["r1_eq_r2"] = nontiming(b1) == nontiming(b2) and nontiming(nb1) == nontiming(nb2)
out = dict(framing="POST-HOC / exploratory: rule written in G7_prereg.md after the G6 TEST numbers were known; cannot be confirmatory. "
           "Outcome can only make ByteTrack the recommended candidate for a phone / labelled-real-footage A/B; app default stays IouTracker (flag OFF).",
           source="ml/runs/G6/tracking/{test_iou_r1,test_bt_r1,test_bt_r2,negtest_*}/gauntlet.json (G6 runs, sandbox CPU, G3 control det ONNX raw 480 + E224 cls 224 T=0.25, fixed-frame stride 1, synthetic clips from locked TEST images)",
           rows={k: dict(iou=v[0], bytetrack_b15=v[1], rule=v[2], pass_=ok[k]) for k, v in rows.items()}, r1_eq_r2=ok["r1_eq_r2"],
           all_pass=all(ok.values()))
out["outcome"] = ("ByteTrack b15 meets the post-hoc movable rule -> recommended candidate for the phone / labelled-footage A/B; app default unchanged (IouTracker)."
                  if out["all_pass"] else "ByteTrack b15 does NOT meet the post-hoc rule; IouTracker stays, ByteTrack eval-only.")
json.dump(out, open("/workspace/work/nutrisole/ml/runs/G7/tracking/bytetrack_posthoc_decision.json", "w"), indent=1)
for k, v in out["rows"].items(): print(k, v)
print("r1=r2", ok["r1_eq_r2"], "ALL", out["all_pass"])
