"""G10b: tables from g10b_ident.py output (identity only; grading is OFF and not measured). Groups as Stage H h_ident_table.py:
supported = group item|crowd with a NutriSole truth class; negatives = unsupported|printed|cut (must never be named); greyscale separate.
Per (decode floor, guard, frame mode, arm): correct / wrong / abstain on supported, negatives accepted, greyscale verified; Stage H tune and
eval subsets and pooled; per-class correct; items whose outcome changed vs the 1 % guard; verified items under the 96 px close-up gate.
Optional: v8m (henningheyen) wide ID at the tap on the same still (cached by g10b_cache.py) for the identity-level complementarity rows.
  python g10b_ident_table.py IDENT.json [V8M_STAGEH.pkl] OUT.json"""
import json, sys, collections, pickle
import numpy as np
sys.path.insert(0, "/workspace/work/nutrisole"); sys.path.insert(0, "/workspace/work/nutrisole/ml/eval")
from ml.eval.closeup import roi_from_tap, id_policy, crop_rect
from ml.eval.verify import verify_identity, FROZEN_VERIFY
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
D = json.load(open(sys.argv[1])); V8 = pickle.load(open(sys.argv[2], "rb")) if len(sys.argv) > 3 else None; OUT = sys.argv[-1]
R = D["rows"]; SUP = lambda r: r["group"] in ("item", "crowd") and r["truth"] in N; NEG = lambda r: r["group"] in ("unsupported", "printed", "cut")
def summ(rows, key, arm):
    m = collections.Counter(); pcc = collections.Counter(); small = 0
    for r in rows:
        x = r["res"][key]; pred = x["wide"] if arm == "H0" else x["pa"]
        if SUP(r):
            t = N.index(r["truth"]); m["sup"] += 1; m["correct"] += pred == t; m["wrong"] += pred is not None and pred != t; m["abstain"] += pred is None
            pcc[r["truth"]] += pred == t
            if pred == t and (x["side"] or 0) < 96: small += 1
        elif NEG(r): m["neg"] += 1; m["neg_accepted"] += pred is not None; m[f"neg_{r['group']}_accepted"] += pred is not None
        elif r["group"] == "greyscale": m["grey"] += 1; m["grey_named"] += pred is not None
    d = dict(m); d["correct_below_96px"] = small; d["per_class_correct"] = dict(pcc); return d
out = dict(label_status="Stage H agent-triaged labels; EXPLORATORY; 0 human-verified", frozen_verify=D["frozen_verify"], jitter=D["jitter"], n=len(R),
           counts=dict(collections.Counter(f"{r['split']}|{'sup' if SUP(r) else 'neg' if NEG(r) else r['group']}" for r in R)), table={})
for fl in D["floors"]:
    for g in D["guards"]:
        for mode in ("1f", "3f"):
            k = f"{fl}|{g}|{mode}"; b = f"{fl}|0.01|{mode}"
            for arm in ("H0", "P-a"):
                e = dict(tune=summ([r for r in R if r["split"] == "tune"], k, arm), eval=summ([r for r in R if r["split"] == "eval"], k, arm), pooled=summ(R, k, arm))
                f = "wide" if arm == "H0" else "pa"; ch = collections.Counter()
                for r in R:
                    a, c = r["res"][b][f], r["res"][k][f]
                    if a == c: continue
                    t = N.index(r["truth"]) if SUP(r) else None
                    tag = ("sup" if SUP(r) else "neg" if NEG(r) else r["group"]) + ":" + ("none" if a is None else "ok" if a == t else "bad") + "->" + ("none" if c is None else "ok" if c == t else "bad")
                    ch[tag] += 1
                e["changed_vs_1pct"] = dict(ch); out["table"][f"{k}|{arm}"] = e
if V8 is not None:
    LMAP = {"banana": 0, "apple": 1, "orange/orange fruit": 3, "mandarin orange": 3, "clementine": 3, "lemon": 6, "lime": 6, "Tomato": 7, "tomato": 7, "potato": 8, "cucumber/cuke": 9, "carrot": 10, "bell pepper/capsicum": 11}
    items = {json.loads(l)["key"] + "|" + json.loads(l)["set"]: json.loads(l) for l in open("/workspace/work/nutrisole/ml/runs/G9/stageH/out/ident_items.jsonl")}
    rows = []
    for r in R:
        it = items[r["key"] + "|" + r["set"]]; p = V8["preds"][it["img"]]; W, H = p["W"], p["H"]
        for g in (0.01, 0.0):
            dets = [(list(map(float, b)), V8["names"][int(c)], float(s)) for b, s, c in zip(p["xyxy"], p["conf"], p["cls"]) if s >= 0.35 and (b[2] - b[0]) * (b[3] - b[1]) >= g * W * H]
            roi = roi_from_tap(it["tap"], W, H, [d[0] for d in dets]); v = None; unsup = None
            if roi["source"] == "track":
                d = next(x for x in dets if x[0] == roi["box"])
                if d[1] in LMAP: w = id_policy(LMAP[d[1]], d[2], 3); v = w.get("classId") if w["status"] == "identified" else None
                else: unsup = d[1]
            r.setdefault("v8m", {})[str(g)] = dict(wide=v, unsup_at_tap=unsup)
    ic = {}
    for g in ("0.01", "0.0"):
        for fl in (0.35,):
            k = f"{fl}|{g if g != '0.0' else 0.0}|1f"; k = f"{fl}|{float(g)}|1f"
            m = collections.Counter()
            for r in R:
                x = r["res"][k]; v = r["v8m"][g]["wide"]; t = N.index(r["truth"]) if SUP(r) else None
                if SUP(r):
                    m["sup"] += 1; m["g3_correct"] += x["wide"] == t; m["v8m_correct"] += v == t; m["v8m_wrong"] += v is not None and v != t
                    m["oracle_correct"] += (x["wide"] == t) or (v == t); m["v8m_only_correct"] += v == t and x["wide"] != t; m["g3_only_correct"] += x["wide"] == t and v != t
                    m["v8m_only_correct_where_g3_wrong"] += v == t and x["wide"] is not None and x["wide"] != t
                    m["agree_correct"] += v == t and x["wide"] == t; m["agree_wrong"] += v is not None and v == x["wide"] and v != t
                    m["veto_unsup_on_sup"] += x["wide"] is not None and r["v8m"][g]["unsup_at_tap"] is not None
                elif NEG(r):
                    m["neg"] += 1; m["g3_neg_named"] += x["wide"] is not None; m["v8m_neg_named"] += v is not None
                    m["v8m_unsup_at_tap_on_neg"] += r["v8m"][g]["unsup_at_tap"] is not None
                    m["g3_neg_named_vetoed_by_v8m_unsup"] += x["wide"] is not None and r["v8m"][g]["unsup_at_tap"] is not None
                    m["agree_neg_named"] += v is not None and v == x["wide"]
                # P-a with the H2 crop from G3's tapped box is unchanged; v8m only replaces/joins the WIDE vote here
            ic[f"guard_{g}"] = dict(m)
    out["identity_complementarity_1f_floor035"] = dict(note="wide ID only (H0 level), single still, conf 0.35; oracle = either model right (UPPER BOUND, not deployable)", **ic)
json.dump(out, open(OUT, "w"), indent=1)
for k, e in out["table"].items():
    if k.startswith("0.35|") or k.startswith("0.25|"):
        p = e["pooled"]; print(k, "sup", p["sup"], "ok", p.get("correct", 0), "bad", p.get("wrong", 0), "negacc", p.get("neg_accepted", 0), "/", p["neg"], "chg", e["changed_vs_1pct"])
print(json.dumps(out.get("identity_complementarity_1f_floor035"), indent=0))
