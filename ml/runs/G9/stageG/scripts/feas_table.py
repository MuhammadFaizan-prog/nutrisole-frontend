"""Stage G feasibility analysis: gate grid on CU-tune (selection rule from the prereg), frozen gate reported on CU-check.
Consistency (flip vs native reference, consecutive flips) is reported separately from correctness (fresh/rotten vs the
source-derived, agent-verified label). No A/B/C correctness is claimed (no independent A/B/C labels)."""
import json, sys, itertools, collections
sys.path.insert(0, "/workspace/work/nutrisole")
from ml.eval.closeup import quality_reasons, GradeGate, DEFAULT_GATE
B = "/workspace/work/nutrisole/ml/runs/G9/stageG"; R = [json.loads(l) for l in open(f"{B}/out/feas_items.jsonl")]
BL = {json.loads(l)["id"]: json.loads(l) for l in open(f"{B}/out/feas_block.jsonl")}
for it in R:  # attach the 8x8 blockiness feature (same crops, recomputed deterministically by feas_g.py FEAT=1)
    b = BL[it["id"]]
    for s_, d in it["sizes"].items():
        for c, r in d.items(): r["block"] = b["sizes"][s_][c]
    for s_, d in it["stab"].items():
        for c, seq in d.items():
            for r, v in zip(seq, b["stab"][s_][c]): r["block"] = v
SIZES = [32, 64, 96, 128, 192, 256]; DEG = ["blur", "lowlight", "jpeg", "occlusion", "truncation"]
GRADED = {"A", "B", "C", "Reject"}

def q(r): return dict(sidePx=r["side"], blurVar=r["blur"], meanV=r["meanV"], touchesEdge=r["edge"], visibleFrac=r["vis"], maxProb=r["maxP"], margin=r["margin"], blockiness=r.get("block"))
def ok(r, P): return r["grade"] in GRADED and not quality_reasons(q(r), P)
def rate(a, b): return round(a / b, 3) if b else None

def size_table(items, P):
    """Per crop size and condition: naive (condition label always emitted) vs gated (single frame)."""
    out = {}
    for s in SIZES:
        for c in ["clean"] + DEG:
            n = nf = ng = gf = gfl = nc = ncor = gc = gcor = emit_ship = 0
            for it in items:
                r = it["sizes"].get(str(s), {}).get(c)
                if not r: continue
                ref = it["ref"]; n += 1
                nf += r["cond"] != ref["cond"]; nc += 1; ncor += r["cond"] == it["label"]
                emit_ship += r["grade"] in GRADED
                if ok(r, P):
                    ng += 1; gcor += r["cond"] == it["label"]; gc += 1
                    if ref["grade"] in GRADED: gf += 1; gfl += r["grade"] != ref["grade"]
            out[f"{s}/{c}"] = dict(n=n, naive_cond_flip=rate(nf, n), naive_correct=rate(ncor, nc), shipped_rubric_emit=rate(emit_ship, n),
                                   gated_accept=rate(ng, n), gated_grade_flip=rate(gfl, gf), gated_correct=rate(gcor, gc), n_gated=ng)
    return out

def temporal(items, P, frames, mode):
    """Gate over the 5 jittered consecutive frames per (item, size, clean|jpeg)."""
    res = collections.defaultdict(lambda: dict(n=0, graded=0, agree_ref=0, consec_pairs=0, consec_flips=0))
    for it in items:
        for s, d in it["stab"].items():
            for c, seq in d.items():
                key = f"{'ge' if int(s) >= P['minSidePx'] else 'lt'}{P['minSidePx']}/{c}"; g = GradeGate({**P, "minFrames": frames, "mode": mode}); last = None
                e = res[key]; e["n"] += 1; graded = None
                for r in seq:
                    dec = g.push(dict(ok=ok(r, P), grade=r["grade"], pFresh=r["pF"], reasons=[]))
                    if dec["status"] == "graded" and graded is None: graded = dec["grade"]
                oks = [r["grade"] for r in seq if ok(r, P)]
                for a, b in zip(seq, seq[1:]):
                    if ok(a, P) and ok(b, P): e["consec_pairs"] += 1; e["consec_flips"] += a["grade"] != b["grade"]
                if graded: e["graded"] += 1; e["agree_ref"] += graded == it["ref"]["grade"]
    return {k: dict(v, graded_rate=rate(v["graded"], v["n"]), consec_flip=rate(v["consec_flips"], v["consec_pairs"]), graded_agree_ref=rate(v["agree_ref"], v["graded"])) for k, v in res.items()}

def degraded_emission(items, P):
    n = e = 0; nc = ec = 0; by = collections.Counter()
    for it in items:
        for s_, d in it["sizes"].items():
            if int(s_) < P["minSidePx"]:
                for c, r in d.items(): n += 1; e += ok(r, P)  # sub-threshold crops: any grade is a violation
                continue
            for c in DEG: n += 1; e += ok(d[c], P); by[c] += ok(d[c], P)
            nc += 1; ec += ok(d["clean"], P)
    return dict(n_degraded_or_small=n, emitted=e, emitted_by_condition=dict(by), rate=rate(e, n), clean_accept=rate(ec, nc), n_clean=nc)

def pick_checks(tune):
    """Step 1 (DEV, disclosed as added after the first table showed lowlight / JPEG passing the default checks): at the candidate
    96 px, choose minMeanV x minVisibleFrac x maxBlockiness minimising degraded/sub-threshold emissions on CU-tune subject to clean
    acceptance >= 0.70 (G-A5). Ties -> higher clean acceptance, then the looser thresholds."""
    rows = []
    for mv, vf, bk in itertools.product([40, 60, 80], [0.25, 0.35, 0.45], [1.4, 1.5, 1.6]):
        P = {**DEFAULT_GATE, "minSidePx": 96, "minMeanV": mv, "minVisibleFrac": vf, "maxBlockiness": bk}; d = degraded_emission(tune, P)
        rows.append(dict(minMeanV=mv, minVisibleFrac=vf, maxBlockiness=bk, **d))
    feas = [r for r in rows if (r["clean_accept"] or 0) >= 0.70]
    best = min(feas, key=lambda r: (r["emitted"], -(r["clean_accept"] or 0), r["minMeanV"], r["minVisibleFrac"], -r["maxBlockiness"])) if feas else None
    return best, rows

def pick(tune, base):
    """Prereg rule: smallest T with gated grade flip <= 10% (clean) and <= 15% (degraded, after checks) at size T, gated correctness
    >= naive correctness at T; then smallest frames (1/3/5, or score mode) with consecutive flip <= 5%. Ties -> stricter."""
    log = []
    for T in SIZES:
        P = {**base, "minSidePx": T}; st = size_table(tune, P)
        cl = st[f"{T}/clean"]; dg = [st[f"{T}/{c}"] for c in DEG]
        dflip = max([d["gated_grade_flip"] for d in dg if d["gated_grade_flip"] is not None] or [0])
        okc = cl["gated_grade_flip"] is not None and cl["gated_grade_flip"] <= 0.10 and dflip <= 0.15 and (cl["gated_correct"] or 0) >= (cl["naive_correct"] or 0)
        log.append(dict(T=T, clean_flip=cl["gated_grade_flip"], degraded_max_flip=dflip, gated_correct=cl["gated_correct"], naive_correct=cl["naive_correct"], n_gated=cl["n_gated"], passes=okc))
        if okc: break
    T = next((l["T"] for l in log if l["passes"]), None)
    flog = []; chosen = None
    if T:
        P = {**base, "minSidePx": T}
        for fr, mode in [(1, "count"), (3, "count"), (3, "score"), (5, "count"), (5, "score")]:
            tm = temporal(tune, P, fr, mode); k = f"ge{T}/clean"; v = tm.get(k, {})
            flog.append(dict(frames=fr, mode=mode, graded_rate=v.get("graded_rate"), consec_flip=v.get("consec_flip"), graded_agree_ref=v.get("graded_agree_ref")))
        # consec_flip is frame-level and the same for every N; the N-rule is judged on graded_agree_ref (agreement with the native
        # reference after the gate) >= 0.95 i.e. flip <= 5%
        # Prereg: smallest N (or the stability rule) with consecutive-frame grade flip <= 5%; ties -> stricter. consec_flip is a
        # per-frame quantity and is identical for every N, so every candidate ties; the tie-break picks the strictest candidate
        # that still meets G-A5 (gate acceptance >= 0.70), count mode before score mode at equal N. Agreement with the native
        # reference after the gate is reported alongside (it is what more frames buy).
        okf = [f for f in flog if f["consec_flip"] is not None and f["consec_flip"] <= 0.05 and (f["graded_rate"] or 0) >= 0.70]
        if okf: chosen = max(okf, key=lambda f: (f["frames"], f["mode"] == "count"))
    return T, log, flog, chosen

if __name__ == "__main__":
    tune = [r for r in R if r["split"] == "tune"]; check = [r for r in R if r["split"] == "check"]
    best, grid = pick_checks(tune)
    base = {**DEFAULT_GATE, **({k: best[k] for k in ("minMeanV", "minVisibleFrac", "maxBlockiness")} if best else {})}
    T, log, flog, chosen = pick(tune, base)
    P = {**base, "minSidePx": T or 96, **({"minFrames": chosen["frames"], "mode": chosen["mode"]} if chosen else {})}
    res = dict(n_items=len(R), n_tune=len(tune), n_check=len(check), label_counts=collections.Counter(r["label"] for r in R),
               ref_grades=collections.Counter(r["ref"]["grade"] for r in R), native_side={"min": min(r["native_side"] for r in R), "median": sorted(r["native_side"] for r in R)[len(R) // 2]},
               selection=dict(size_log=log, chosen_size=T, frames_log=flog, chosen_frames=chosen), frozen_gate=P,
               tune_table=size_table(tune, P), check_table=size_table(check, P), check_temporal=temporal(check, P, P["minFrames"], P["mode"]),
               check_temporal_candidate96x3=temporal(check, {**base, "minSidePx": 96}, 3, "count"),
               checks_step=dict(best=best, grid=grid), check_degraded_emission=degraded_emission(check, P), tune_degraded_emission=degraded_emission(tune, P),
               check_degraded_emission_default_checks=degraded_emission(check, {**DEFAULT_GATE, "maxBlockiness": 99}),
               ref_correct_all=rate(sum(r["ref"]["cond"] == r["label"] for r in R), len(R)))
    json.dump(res, open(f"{B}/out/feasibility.json", "w"), indent=1)
    print("checks", best); print(json.dumps(res["selection"])[:3000]); print("frozen", P); print("check_emis", res["check_degraded_emission"], "default", res["check_degraded_emission_default_checks"]); print(res["ref_grades"], res["label_counts"], res["ref_correct_all"])
