"""Score crop-geometry variants (out/geom.jsonl). Variant choice on TUNE only (max H2-only correct on supported tune with tune error
(wrong + negatives accepted)/(sup+neg) no worse than Stage H's sh); eval reported once as POST-HOC DIAGNOSTIC (Stage H unchanged).
Also re-scores H-final (P-a, FROZEN_VERIFY unchanged) with the picked geometry. Writes out/geom_scores.json."""
import json, sys, collections
sys.path.insert(0, "/workspace/work/nutrisole"); sys.path.insert(0, "/workspace/work/nutrisole/ml/runs/G9/stageI/scripts")
from i_audit_table import score  # noqa
O = "/workspace/work/nutrisole/ml/runs/G9/stageI/out"; S = "/workspace/work/nutrisole/ml/runs/G9/stageH/out"
G = {json.loads(l)["key"] + "|" + json.loads(l)["set"]: json.loads(l) for l in open(f"{O}/geom.jsonl")}
R = [json.loads(l) for l in open(f"{S}/ident_items.jsonl")]
rows = []
for r in R:
    g = G[r["key"] + "|" + r["set"]]
    rows.append(dict(key=r["key"], set=r["set"], split=r["split"], group=r["group"], truth=r["truth"], roi=g["roi"], hw=[1, 1], wide=r["wide"].get("classId") if r["wide"]["status"] == "identified" else None,
                     stored=r["h2"], **{v: g[v] for v in ("sh", "sq15", "roi0.6", "roi0.9", "full")}))
V = ("sh", "sq15", "roi0.6", "roi0.9", "full")
def err(d): return (d.get("h2only_wrong", 0) + d.get("neg_h2_accept", 0)) / max(d["sup"] + d["neg"], 1)
tu = [r for r in rows if r["split"] == "tune"]; ev = [r for r in rows if r["split"] == "eval"]
out = dict(note="POST-HOC DIAGNOSTIC on Stage H frozen items; Stage H results unchanged. 'sh' must reproduce Stage H.",
           sh_matches_stored=sum(1 for r in rows if max(abs(a - b) for a, b in zip(r["sh"], r["stored"])) < 1e-3), n=len(rows))
out["tune"] = {v: dict(score(tu, v), err=round(err(score(tu, v)), 4)) for v in V}
cands = [v for v in V if v != "full" and out["tune"][v]["err"] <= out["tune"]["sh"]["err"] + 1e-9]
pick = max(cands, key=lambda v: (out["tune"][v]["h2only_correct"], out["tune"][v]["pa_correct"])) if cands else "sh"
out["pick_on_tune"] = pick; out["pick_rule"] = "max tune H2-only correct s.t. tune error <= Stage H crop's tune error ('full' excluded: not a deployable crop)"
out["eval_posthoc"] = {v: dict(score(ev, v), err=round(err(score(ev, v)), 4)) for v in V}
out["eval_posthoc_by_roi"] = {s: {v: score([r for r in ev if r["roi"] == s], v) for v in V} for s in ("track", "tap_roi")}
json.dump(out, open(f"{O}/geom_scores.json", "w"), indent=1)
print("sh reproduces stored:", out["sh_matches_stored"], "/", len(rows), "| pick", pick)
K = ("top1_correct", "h2only_correct", "h2only_wrong", "top13_unknown", "pa_correct", "pa_wrong", "neg_h2_accept", "neg_pa_accept", "p5_top1", "err")
for s in ("tune", "eval_posthoc"):
    print(s); [print(f"  {v:7s}", {k: out[s][v].get(k) for k in K}) for v in V]
for s in ("track", "tap_roi"): print(s, {v: (out["eval_posthoc_by_roi"][s][v].get("top1_correct"), out["eval_posthoc_by_roi"][s][v].get("sup")) for v in V})
