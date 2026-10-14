"""G9 Stage J: choose the PILOT batch (J-eval only) and the TRAINING batch (J-dev + J-train), assign opaque blind ids.
Pilot (frozen, seed 11): per priority class 32 supported group representatives, spread over Commons and the phone dataset of that class
(Commons first up to 16, the rest from the dataset; citrus/carrot take every Commons item there is); ALL J-eval negative representatives
(the Commons negative queries are noisy, so the full pool is needed to reach >= 60 verified negatives); 4 each of lime, guava, pomegranate
(other-produce checks). Source labels are used only to balance the draw; annotators never see them.
Training batch: every J-dev and J-train group representative.
Blind ids: P### (pilot) and T### (training), assigned in a random order unrelated to source or class. Key -> out/j_blind_key.csv (adjudicator only)."""
import json, random, csv, collections
OUT = "/workspace/work/nutrisole/ml/runs/G9/stageJ/out"
P = json.load(open(f"{OUT}/j_partitions.json"))["items"]
reps = {k: v for k, v in P.items() if k == v["group"]}
rng = random.Random(11)
ev = [k for k, v in reps.items() if v["split"] == "J-eval"]; ev.sort(); rng.shuffle(ev)
DS = {"apple": "fruitnet", "banana": "fruitnet", "citrus": "fruitnet", "tomato": "tomato_m", "carrot": "carrot_m"}
pilot = []
for cl, ds in DS.items():
    com = [k for k in ev if reps[k]["label"] == cl and reps[k]["kind"] == "supported" and reps[k]["source"] == "commons"]
    dat = [k for k in ev if reps[k]["label"] == cl and reps[k]["kind"] == "supported" and reps[k]["source"] == ds]
    c = com[:16] if len(com) >= 16 else com; pilot += c + dat[:32 - len(c)]
pilot += [k for k in ev if reps[k]["kind"] != "supported"]
for oc in ("lemon_lime", "guava", "pomegranate"): pilot += [k for k in ev if reps[k]["label"] == oc][:4]
train = sorted(k for k, v in reps.items() if v["split"] in ("J-dev", "J-train"))
rng.shuffle(pilot); rng.shuffle(train)
rows = [dict(blind_id=f"P{i+1:03d}", batch="pilot", key=k) for i, k in enumerate(pilot)] + [dict(blind_id=f"T{i+1:03d}", batch="train", key=k) for i, k in enumerate(train)]
C = json.load(open("/workspace/work/g9i/cands/cands.json")); T = json.load(open("/workspace/work/g9j/train/train_cands.json"))
for r in rows:
    r["page_url"] = (C.get(r["key"]) or T.get(r["key"]) or {}).get("page", "")
    v = reps[r["key"]]; r.update(split=v["split"], source=v["source"], uploader=v["uploader"], source_label=v["label"], source_kind=v["kind"], stageI_item=v.get("item_id") or "")
with open(f"{OUT}/j_blind_key.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
comp = collections.Counter((r["source_kind"], r["source_label"] if r["source_kind"] == "supported" else "-", r["source"]) for r in rows if r["batch"] == "pilot")
summ = dict(pilot=len(pilot), train=len(train), pilot_by_kind=collections.Counter(reps[k]["kind"] for k in pilot),
            pilot_supported=collections.Counter(reps[k]["label"] for k in pilot if reps[k]["kind"] == "supported"),
            pilot_by_source=collections.Counter(reps[k]["source"] for k in pilot), pilot_detail={"|".join(k): n for k, n in sorted(comp.items())},
            train_by_split=collections.Counter(reps[k]["split"] for k in train), train_by_label=collections.Counter(reps[k]["label"] + "/" + reps[k]["kind"] for k in train))
json.dump(summ, open(f"{OUT}/j_batches.json", "w"), indent=1); print(json.dumps(summ, indent=1))
