"""Stage H P1 identity comparison. Arms: H0 (wide G3 at the tap, id_policy), H1 (P-c: wide + G3 on the full-res crop agrees), H2-only
(close-up classifier alone with reject), P-a (wide + H2 agree), P-b (P-a + H1 veto). Grid + frozen selection on TUNE (CU-tune, CU-neg tune,
H-val); reported once on EVAL (CU-check, CU-neg check, H-eval). Also the Stage G approach-simulation H0 on CU-check (e2e_approach.json) and
the user-assisted fallback as a separate UX arm. Writes out/identity.json. Usage: h_ident_table.py"""
import json, sys, itertools, collections, numpy as np
sys.path.insert(0, "/workspace/work/nutrisole")
from ml.eval.verify import verify_identity, user_confirm, DEFAULT_VERIFY
B = "/workspace/work/nutrisole/ml/runs/G9/stageH/out"; G = "/workspace/work/nutrisole/ml/runs/G9/stageG/out"
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
R = [json.loads(l) for l in open(f"{B}/ident_items.jsonl")]; HAS_H2 = all("h2" in r for r in R)
SUP = lambda r: r["group"] in ("item", "crowd") and r["truth"] in N
NEG = lambda r: r["group"] in ("unsupported", "printed", "cut")
def wide(r): return dict(status="identified", classId=r["wide"]["classId"]) if r["wide"]["status"] == "identified" else dict(status="unable")
def h1(r): return dict(classId=r["h1"]["classId"], score=r["h1"]["score"], hasWide=r["h1"]["hasWide"]) if r["h1"]["classId"] is not None else None
UNIF = [1 / 13] * 13
def run(rs, P):
    m = collections.Counter(); per = []
    for r in rs:
        v = verify_identity(wide(r), h1(r), r.get("h2", UNIF), P); ver = v["status"] == "verified"
        if SUP(r):
            t = N.index(r["truth"]); m["sup"] += 1; wc = r["wide"]["status"] == "identified" and r["wide"]["classId"] == t
            m["correct"] += ver and v["classId"] == t; m["wrong"] += ver and v["classId"] != t; m["abstain"] += not ver
            m["wide_correct"] += wc; m["legit_rejected"] += wc and not ver
            m["sup_item"] += r["group"] == "item"; m["correct_item"] += r["group"] == "item" and ver and v["classId"] == t
        elif NEG(r):
            m["neg"] += 1; m["false_accept"] += ver; m[f"neg_{r['group']}"] += 1; m[f"fa_{r['group']}"] += ver
        elif r["group"] == "greyscale":
            m["grey"] += 1; m["grey_verified"] += ver
        per.append((r, v))
    d = dict(m); s = max(m["sup"], 1)
    d.update(correct_rate=round(m["correct"] / s, 4), wrong_rate=round(m["wrong"] / s, 4), abstain_rate=round(m["abstain"] / s, 4),
             correct_item_rate=round(m["correct_item"] / max(m["sup_item"], 1), 4), fa_rate=round(m["false_accept"] / max(m["neg"], 1), 4),
             legit_rejected_rate=round(m["legit_rejected"] / max(m["wide_correct"], 1), 4))
    return d, per
tune = [r for r in R if r["split"] == "tune"]; ev = [r for r in R if r["split"] == "eval"]
ARMS = {"H0": dict(DEFAULT_VERIFY, policy="H0"), "H1 (P-c)": dict(DEFAULT_VERIFY, policy="P-c")}
out = dict(n_tune=len(tune), n_eval=len(ev), has_h2=HAS_H2, counts={s: dict(collections.Counter(f"{r['set']}|{r['group']}" for r in R if r["split"] == s)) for s in ("tune", "eval")})
pick = None
if HAS_H2:
    grid = []
    for pol, tau, mg, mu in itertools.product(["P-a", "P-b"], [0.4, 0.5, 0.6, 0.7, 0.8, 0.9], [0.0, 0.1, 0.2, 0.3, 0.5], [0.1, 0.2, 0.3, 0.5]):
        P = dict(DEFAULT_VERIFY, policy=pol, tau=tau, margin=mg, maxUnknown=mu); d, _ = run(tune, P)
        err = (d.get("wrong", 0) + d.get("false_accept", 0)) / max(d["sup"] + d["neg"], 1)
        grid.append((err, d["correct_rate"], P, d))
    feas = [g for g in grid if g[1] >= 0.60]
    if feas: feas.sort(key=lambda g: (g[0], -g[1], g[2]["policy"] != "P-b", -g[2]["tau"], -g[2]["margin"], g[2]["maxUnknown"])); pick = feas[0][2]; rule = "min tune error s.t. correct >= 0.60"
    else:
        lo = [g for g in grid if g[0] <= 0.03] or grid
        lo.sort(key=lambda g: (-g[1], g[0], g[2]["policy"] != "P-b", -g[2]["tau"])); pick = lo[0][2]; rule = "INFEASIBLE (no setting reaches correct 0.60 on tune): max correct s.t. tune error <= 3%"
    out.update(selection_rule=rule, pick=pick, n_grid=len(grid), n_feasible=len(feas))
    # H2-only at the same thresholds (comparison arm)
    ARMS.update({"H2-only": dict(pick, policy="H2-only"), "P-a": dict(pick, policy="P-a"), "P-b": dict(pick, policy="P-b"), "H-final": pick})
for name, P in ARMS.items():
    dt, _ = run(tune, P); de, per = run(ev, P)
    out.setdefault("arms", {})[name] = dict(params=P, tune=dt, eval=de)
    out["arms"][name]["eval_by_set"] = {s: run([r for r in ev if r["set"] == s], P)[0] for s in ("cu", "cuneg", "heval")}
# Stage G approach simulation on CU-check (H0 as reported by Stage G) and what the H-final verification would do to its identified items
A = json.load(open(f"{G}/e2e_approach.json")); Rk = {r["key"]: r for r in R if r["set"] == "cu"}
ap = dict(n=len(A), identified=sum(1 for v in A.values() if v["id_class"]), correct=sum(1 for v in A.values() if v["id_class"] and v["id_correct"]),
          graded=sum(1 for v in A.values() if v["grade"]), graded_wrong_id=sum(1 for v in A.values() if v["grade"] and not v["id_correct"]))
if HAS_H2:
    kept = []; 
    for k, v in A.items():
        r = Rk.get("cu" + k)
        if not v["id_class"] or r is None: continue
        w = dict(status="identified", classId=N.index(v["id_class"])); vv = verify_identity(w, h1(r), r["h2"], pick)
        kept.append(dict(id=k, truth=v["cls"], wide=v["id_class"], wide_correct=bool(v["id_correct"]), graded_stageG=bool(v["grade"]), verified=vv["status"] == "verified", reason=vv.get("reason")))
    ap["with_H_final"] = dict(verified=sum(x["verified"] for x in kept), verified_correct=sum(x["verified"] and x["wide_correct"] for x in kept),
                              verified_wrong=sum(x["verified"] and not x["wide_correct"] for x in kept),
                              stageG_wrong_id_grades_blocked=sum(1 for x in kept if x["graded_stageG"] and not x["wide_correct"] and not x["verified"]),
                              stageG_wrong_id_grades=sum(1 for x in kept if x["graded_stageG"] and not x["wide_correct"]), items=kept)
out["cu_check_approach"] = ap
# user-assisted fallback UX arm (eval): oracle user picks the true class if offered, else 'something else'; careless user taps the first suggestion
if HAS_H2:
    ux = collections.Counter()
    for r in ev:
        v = verify_identity(wide(r), h1(r), r["h2"], pick)
        if v["status"] == "verified" or not (SUP(r) or NEG(r)): continue
        sg = v.get("suggestions", []); t = N.index(r["truth"]) if SUP(r) else None
        ux["unable_" + ("sup" if SUP(r) else "neg")] += 1
        o = user_confirm(v, t if t in sg else None); c = user_confirm(v, sg[0] if sg else None)
        if SUP(r): ux["offered_true"] += t in sg; ux["oracle_confirmed"] += o["status"] == "user_confirmed"; ux["careless_wrong"] += c["status"] == "user_confirmed" and c["classId"] != t
        else: ux["oracle_neg_confirmed"] += o["status"] == "user_confirmed"; ux["careless_neg_confirmed"] += c["status"] == "user_confirmed"
    out["user_fallback_eval"] = dict(ux)
json.dump(out, open(f"{B}/identity.json", "w"), indent=1)
for n, a in out["arms"].items():
    e = a["eval"]; print(f"{n:10s} eval sup={e['sup']} correct={e['correct_rate']} wrong={e['wrong_rate']} abst={e['abstain_rate']} item_correct={e['correct_item_rate']} FA={e.get('false_accept',0)}/{e['neg']} legit_rej={e['legit_rejected_rate']} | tune correct={a['tune']['correct_rate']} wrong={a['tune']['wrong_rate']} FA={a['tune'].get('false_accept',0)}/{a['tune']['neg']}")
print({k: v for k, v in ap.items() if k != "with_H_final"}, ap.get("with_H_final", {}).get("verified"), {k: v for k, v in ap.get("with_H_final", {}).items() if k != "items"}); print(out.get("pick"), out.get("selection_rule")); print(out.get("user_fallback_eval"))
