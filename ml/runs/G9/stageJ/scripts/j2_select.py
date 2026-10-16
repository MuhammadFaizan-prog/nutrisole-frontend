"""G9 Stage J2: supplementary blind PILOT2 (J-EVAL ONLY) and TRAINING PACK 2 (J-TRAIN ONLY). Frozen Stage J files (j_blind_key.csv,
j_partitions.json, j_batches.json, j_packs.json) are NOT modified: everything here goes to out/gaps/.
Pilot2 (seed 12): every remaining J-eval group representative of a priority class that is not already in the 265-photo pilot, from the existing
eval-side pool (FruitNet apple/banana/citrus, tomato_m, carrot_m, Commons eval uploaders) with tomato capped at 26 (it is
nearly sufficient), plus all new eval-only Commons candidates that passed j2_audit.py (packaging, partly hidden, apple, citrus).
Training pack 2: every new J-train candidate that passed j2_audit.py (Mendeley CC BY 4.0 sources + Commons train-side apple).
Blind ids: P501... (pilot2) and T501... (train2), so they never collide with P001-P265 / T001-T461. Key -> out/gaps/j2_blind_key.csv (adjudicator only)."""
import json, random, csv, collections
OUT = "/workspace/work/nutrisole/ml/runs/G9/stageJ/out"; GO = f"{OUT}/gaps"
P = json.load(open(f"{OUT}/j_partitions.json"))["items"]; N = json.load(open(f"{GO}/j2_candidates.json"))
pilot1 = {r["key"] for r in csv.DictReader(open(f"{OUT}/j_blind_key.csv"))}
reps = {k: v for k, v in P.items() if k == v["group"] and v["split"] == "J-eval" and k not in pilot1}
rng = random.Random(12); ev = sorted(reps); rng.shuffle(ev)
CAP = {"apple": 99, "citrus": 99, "carrot": 99, "banana": 99, "tomato": 26}
pilot2 = []
for cl, cap in CAP.items():
    com = [k for k in ev if reps[k]["label"] == cl and reps[k]["kind"] == "supported" and reps[k]["source"] == "commons"]
    dat = [k for k in ev if reps[k]["label"] == cl and reps[k]["kind"] == "supported" and reps[k]["source"] != "commons"]
    pilot2 += (com + dat)[:cap]
pilot2 += [k for k, v in sorted(N.items()) if v["split"] == "J-eval"]
train2 = sorted(k for k, v in N.items() if v["split"] == "J-train")
rng.shuffle(pilot2); rng.shuffle(train2)
def meta(k):
    if k in N: v = N[k]; return dict(page_url=v["page"], split=v["split"], source=v["source"], uploader=v["uploader"], source_label=v["label"], source_kind=v["kind"], stageI_item="")
    v = P[k]; C = json.load(open("/workspace/work/g9i/cands/cands.json")) if not hasattr(meta, "C") else meta.C; meta.C = C
    return dict(page_url=C.get(k, {}).get("page", ""), split=v["split"], source=v["source"], uploader=v["uploader"], source_label=v["label"], source_kind=v["kind"], stageI_item=v.get("item_id") or "")
rows = [dict(blind_id=f"P{501 + i}", batch="pilot2", key=k, **meta(k)) for i, k in enumerate(pilot2)] + \
       [dict(blind_id=f"T{501 + i}", batch="train2", key=k, **meta(k)) for i, k in enumerate(train2)]
with open(f"{GO}/j2_blind_key.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
C = collections.Counter
pr = [r for r in rows if r["batch"] == "pilot2"]; tr = [r for r in rows if r["batch"] == "train2"]
summ = dict(pilot2=len(pr), train2=len(tr), pilot2_by_kind=C(r["source_kind"] for r in pr), pilot2_supported=C(r["source_label"] for r in pr if r["source_kind"] == "supported"),
            pilot2_by_source=C(r["source"] for r in pr), pilot2_detail=C(f"{r['source_kind']}|{r['source_label']}|{r['source']}" for r in pr),
            train2_by_label=C(r["source_label"] for r in tr), train2_by_source=C(r["source"] for r in tr), train2_detail=C(f"{r['source_label']}|{r['source']}" for r in tr),
            frozen_stageJ_files_modified=False)
json.dump(summ, open(f"{GO}/j2_batches.json", "w"), indent=1); print(json.dumps(summ, indent=1))
