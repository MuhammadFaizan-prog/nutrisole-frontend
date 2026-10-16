# DEV selection (G6_prereg deviation): highest DEV det-clip segment acc; ties -> lower static label flicker, then smaller buffer. (FA tie-break dropped: neg clip not run on DEV for budget.)
import json
R = "/workspace/work/nutrisole/ml/runs/G6/tracking"
rows = []
for b in [8, 15, 30]:
    d = json.load(open(f"{R}/devdet_bt_b{b}/gauntlet.json"))["clips"]["det"]
    rows.append(dict(params={"track_buffer": b}, seg=d["segment_acc"], flick=d["label_flicker_per_10s_static"], id_switches=d["id_switches"]))
best = sorted(rows, key=lambda r: (-r["seg"], r["flick"], r["params"]["track_buffer"]))[0]
print(json.dumps(dict(params=best["params"], rows=rows)))
