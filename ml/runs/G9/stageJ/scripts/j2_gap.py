"""G9 Stage J2: updated training-gap table, partition stats (Stage J frozen partitions + J2 addendum) and readiness JSON (status stays BLOCKED).
Expected-verified yields are the Stage J assumption (Commons 0.55, datasets 0.90), unchanged; nothing here is human-verified.
Outputs: out/gaps/j2_training_gap.csv, j2_partition_stats.json, j2_readiness.json."""
import json, csv, collections
OUT = "/workspace/work/nutrisole/ml/runs/G9/stageJ/out"; GO = f"{OUT}/gaps"
P = json.load(open(f"{OUT}/j_partitions.json")); N = json.load(open(f"{GO}/j2_candidates.json")); Y = json.load(open(f"{GO}/j2_eval_yield_projection.json"))
y = lambda src: 0.55 if src.startswith("commons") else 0.90
PRI = ("apple", "banana", "citrus", "tomato", "carrot")
old = P["training_gap"]; rows = []
newtr = [v for v in N.values() if v["split"] == "J-train"]
for c in PRI:
    cand = [v for v in newtr if v["label"] == c]; exp = round(sum(y(v["source"]) for v in cand))
    srcs = sorted(set(old[c]["sources"]) | {v["source"] for v in cand})
    rows.append(dict(cls=c, stageJ_candidates=old[c]["candidates"], stageJ_expected_verified=old[c]["expected_verified"], j2_new_candidates=len(cand),
                     j2_new_by_source=";".join(f"{s}:{n}" for s, n in sorted(collections.Counter(v["source"] for v in cand).items())), j2_expected_verified=exp,
                     total_expected_verified=old[c]["expected_verified"] + exp, target=150, remaining_shortfall=max(0, 150 - old[c]["expected_verified"] - exp),
                     n_sources=len(srcs), sources=";".join(srcs), human_verified=0))
neg_old = sum(P["splits"]["J-train"]["negatives_by_kind"].values()); negc = [v for v in newtr if v["label"] not in PRI]
nexp = round(sum(y(v["source"]) for v in negc))
rows.append(dict(cls="negatives (real-photo, J-train)", stageJ_candidates=neg_old, stageJ_expected_verified=neg_old, j2_new_candidates=len(negc),
                 j2_new_by_source=";".join(f"{s}:{n}" for s, n in sorted(collections.Counter(v["source"] for v in negc).items())), j2_expected_verified=nexp,
                 total_expected_verified=neg_old + nexp, target=150, remaining_shortfall=max(0, 150 - neg_old - nexp),
                 n_sources=len({v["source"] for v in negc}) + 1, sources="stageJ mix;" + ";".join(sorted({v["source"] for v in negc})), human_verified=0))
with open(f"{GO}/j2_training_gap.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
st = {}
for sp in ("J-train", "J-dev", "J-eval"):
    base = P["splits"][sp]; add = [v for v in N.values() if v["split"] == sp]
    st[sp] = dict(stageJ_groups=base["groups"], stageJ_images=base["images"], j2_added=len(add), total_images=base["images"] + len(add),
                  j2_added_by_label=collections.Counter(v["label"] for v in add), j2_added_by_source=collections.Counter(v["source"] for v in add),
                  stageJ_supported_by_class=base["supported_by_class"], stageJ_negatives_by_kind=base["negatives_by_kind"])
A = json.load(open(f"{GO}/j2_audit_summary.json")); B = json.load(open(f"{GO}/j2_batches.json"))
st["audit"] = dict(new_candidates=A["new_candidates"], kept=A["kept"], quarantined=A["quarantined"], reasons=A["quarantine_reasons"], m_test_content_opened=False,
                   frozen_stageJ_partitions_modified=False, cross_split_neardups_after_j2=0)
json.dump(st, open(f"{GO}/j2_partition_stats.json", "w"), indent=1)
co, cs = Y["combined_optimistic_with_prior_for_new_negatives"], Y["combined_strict_with_low_prior_for_new_negatives"]
rd = dict(status="BLOCKED", stage="G9 Stage J2 (gaps)", human_verified_images=0, genuine_human_exports=0, kappa=None, adjudication=None, ai_rows_used_as_labels=0,
          ai_provenance_preserved="AI_ASSISTED_NOT_HUMAN", training_started=False, kaggle_gpu_used=False,
          blockers=["0 independent human exports for pilot (265) and pilot2 (335); R1 kappa not computable",
                    "R2 (>=20 clean per class, >=60 negatives with sub-quotas) cannot be judged without human labels; exploratory projection only",
                    "T1 (>=150 verified per priority class) not met: 0 verified; expected after training packs 1+2: " + ", ".join(f"{r['cls']} {r['total_expected_verified']}" for r in rows[:5]),
                    "apple training remains short after pack 2 (single new source = Commons, 0.55 yield)",
                    "original byte-to-licence identity chain for the Stage J pilot still unproven beyond the 16 retrieved originals"],
          eval_projection_exploratory=dict(optimistic=dict(supported=co["supported"], negatives=co["negatives"]), strict=dict(supported=cs["supported"], negatives=cs["negatives"])),
          packs=dict(pilot2=B["pilot2"], train2=B["train2"]), next_step="two independent people label pilot + pilot2 and training packs 1+2 on their own copies; a third person adjudicates")
json.dump(rd, open(f"{GO}/j2_readiness.json", "w"), indent=1)
for r in rows: print(r["cls"], r["stageJ_expected_verified"], "+", r["j2_expected_verified"], "=", r["total_expected_verified"], "short", r["remaining_shortfall"], r["j2_new_by_source"])
