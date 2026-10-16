"""G9 Stage J2: EXPLORATORY eval-yield projection. Uses the AI_ASSISTED_NOT_HUMAN visual review (never ground truth, never adjudication input,
never a training label) only to estimate per-(source, source_kind, source_label) survival rates on the 265-photo pilot, then applies those rates
to pilot2. Output: out/gaps/j2_eval_yield_projection.json. Gates are the frozen R2 counts (>= 20 clean per priority class, >= 100 total,
>= 60 negatives with sub-quotas unsupported+other >= 25, printed >= 10, packaging >= 10, occluded >= 10)."""
import csv, json, sys, collections
sys.path.insert(0, "/workspace/work/nutrisole/ml/runs/G9/stageJ/scripts")
import j_agree as J
OUT = "/workspace/work/nutrisole/ml/runs/G9/stageJ/out"; GO = f"{OUT}/gaps"; B = f"{OUT}/handoff/20261015_visual_review"
ai = {r["item_id"]: r for r in csv.DictReader(open(f"{B}/AI_ASSISTED_NOT_HUMAN/nutrisole_G9J_AI_visual_review_265.csv", encoding="utf-8-sig"))}
det = {r["item_id"]: r for r in csv.DictReader(open(f"{B}/G9J_AI_per_image_review.csv", encoding="utf-8-sig"))}
k1 = [r for r in csv.DictReader(open(f"{OUT}/j_blind_key.csv")) if r["batch"] == "pilot"]
k2 = [r for r in csv.DictReader(open(f"{GO}/j2_blind_key.csv")) if r["batch"] == "pilot2"]
NEG = ("unsupported", "other_class", "printed", "occluded", "cut", "supported_packaged")
def role(i):
    r = ai[i]; return J.role_of(r["label"], int(r["cut"] or 0), int(r["bag"] or 0), r["other_produce_name"])
def stratum(r):
    if r["source"] == "commons_e2" and r["source_kind"] in ("packaging", "occluded"): return f"commons_e2|{r['source_kind']}|-"   # new targeted queries: no pilot precedent
    src = "commons" if r["source"].startswith("commons") else r["source"]
    return f"{src}|{r['source_kind']}|{r['source_label'] if r['source_kind'] == 'supported' else '-'}"
# pilot (AI) counts, optimistic (every AI label) and strict (AI high confidence and no review flag)
p_opt, p_strict = collections.Counter(), collections.Counter()
rates = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0]))   # stratum -> outcome -> [opt, strict, n]
nstr = collections.Counter(stratum(r) for r in k1)
for r in k1:
    i = r["blind_id"]; ro, c = role(i); hi = det[i]["confidence"] == "high" and not det[i]["review_flags"]
    out = f"supported:{c}" if ro == "supported" else ro if ro in NEG else "excluded"
    p_opt[out] += 1; p_strict[out] += hi; rates[stratum(r)][out][0] += 1; rates[stratum(r)][out][1] += hi
def gates(cnt):
    sup = {c: cnt.get(f"supported:{c}", 0) for c in ("apple", "banana", "citrus", "tomato", "carrot")}
    neg = {k: cnt.get(k, 0) for k in NEG}
    return dict(supported=sup, supported_total=sum(sup.values()), negatives=neg, negatives_total=sum(neg.values()),
                per_class_ge20={c: v >= 20 for c, v in sup.items()}, total_ge100=sum(sup.values()) >= 100, negatives_ge60=sum(neg.values()) >= 60,
                unsupported_ge25=neg["unsupported"] + neg["other_class"] >= 25, printed_ge10=neg["printed"] >= 10, packaging_ge10=neg["supported_packaged"] >= 10, occluded_ge10=neg["occluded"] >= 10)
# pilot2 projection: stratum rates from the pilot; strata with no pilot precedent (new packaging/occluded queries) get the pilot rate of the same kind
# (Commons packaging/occluded) and, as a stated alternative, a 0.25 / 0.15 prior.
n2 = collections.Counter(stratum(r) for r in k2)
proj_opt, proj_strict, unknown = collections.Counter(), collections.Counter(), {}
for s, n in n2.items():
    if s in nstr:
        for out, (o, st, _) in rates[s].items(): proj_opt[out] += n * o / nstr[s]; proj_strict[out] += n * st / nstr[s]
    else: unknown[s] = n
alt = collections.Counter({"supported_packaged": 0.25 * n2.get("commons_e2|packaging|-", 0), "occluded": 0.15 * n2.get("commons_e2|occluded|-", 0)})
alt_low = collections.Counter({"supported_packaged": 0.15 * n2.get("commons_e2|packaging|-", 0), "occluded": 0.08 * n2.get("commons_e2|occluded|-", 0)})
comb = lambda a, b: collections.Counter({k: round(a.get(k, 0) + b.get(k, 0), 1) for k in set(a) | set(b)})
res = dict(note="EXPLORATORY ONLY. AI_ASSISTED_NOT_HUMAN labels estimate survival rates; human-verified count is 0; nothing here is a label.",
           pilot_ai_optimistic=gates(p_opt), pilot_ai_strict=gates(p_strict),
           pilot_strata_n=dict(nstr), pilot_rates={s: {o: [v[0], v[1]] for o, v in d.items()} for s, d in rates.items()},
           pilot2_strata_n=dict(n2), pilot2_strata_without_pilot_precedent=unknown,
           pilot2_projected_optimistic=gates(proj_opt), pilot2_projected_strict=gates(proj_strict),
           combined_optimistic=gates(comb(p_opt, proj_opt)), combined_strict=gates(comb(p_strict, proj_strict)),
           combined_optimistic_with_prior_for_new_negatives=gates(comb(comb(p_opt, proj_opt), alt)),
           combined_strict_with_prior_for_new_negatives=gates(comb(comb(p_strict, proj_strict), alt)),
           combined_strict_with_low_prior_for_new_negatives=gates(comb(comb(p_strict, proj_strict), alt_low)),
           priors=dict(packaging=[0.15, 0.25], occluded=[0.08, 0.15], basis="assumption: targeted Commons queries are noisy; Stage J pilot Commons negative queries survived poorly"))
json.dump(res, open(f"{GO}/j2_eval_yield_projection.json", "w"), indent=1)
for k in ("pilot_ai_optimistic", "pilot_ai_strict", "combined_optimistic", "combined_strict", "combined_optimistic_with_prior_for_new_negatives", "combined_strict_with_prior_for_new_negatives", "combined_strict_with_low_prior_for_new_negatives"):
    g = res[k]; print(k, {c: round(v, 1) for c, v in g["supported"].items()}, "neg", {c: round(v, 1) for c, v in g["negatives"].items()}, round(g["negatives_total"], 1))
print("no precedent:", unknown)
