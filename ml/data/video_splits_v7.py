"""G7 Phase 4: web-video splits v7, grouped by uploader (proxy for recording/source identity). Deterministic.

G6's 38 clips keep their G6 split exactly (dev 22 / LOCKED holdout 15 / train_only 1); the locked 15-clip holdout is untouched.
New G7 Commons clips (roles from ml/runs/G7/video_v7/inspection_g7.json, agent inspection, not human):
  reject            -> excluded (not counted)
  weak_exploratory  -> weak_exploratory (never a benchmark)
  negative          -> negatives_v7 (false-alarm evaluation only, never trained)
  produce           -> by uploader group: an uploader that already has a G6 holdout clip -> holdout_v7_pending (same source
                       family stays on the evaluation side); otherwise groups ordered by md5(uploader) and cut 40 / 30 / 30 into
                       holdout_v7_pending (reserved; becomes the human-verified holdout only after a person verifies its labels;
                       never trained), dev_v7, train_v7_weak (machine-proposed labels; usable for weak training only after review).
No split here contains human-verified labels yet; the counts say so explicitly.
  python ml/data/video_splits_v7.py
"""
import csv
import hashlib
import json
import os

R = "/workspace/work/nutrisole"
G6 = list(csv.DictReader(open(f"{R}/ml/runs/G6/video_benchmark/manifest.csv")))
I = {k: v for k, v in json.load(open(f"{R}/ml/runs/G7/video_v7/inspection_g7.json")).items() if not k.startswith("_")}
SEL = {"c" + hashlib.md5(s["title"].encode()).hexdigest()[:8]: s for s in json.load(open("/workspace/work/cv/g7src/meta/commons_g7_selected.json"))}
rows = []
hold_up = {r["uploader"] for r in G6 if r["split"] == "holdout"}
for r in G6:
    rows.append(dict(clip_id=r["clip_id"], origin="G6", uploader=r["uploader"], licence=r["licence"], page=r["page"], dur_s=r["dur_s"],
                     role="produce" if r["clip_id"] != "c0be28daa" else "negative(hardneg source)", split=r["split"] + (" (LOCKED)" if r["split"] == "holdout" else ""),
                     counts_toward_60=True, labels="machine proposals only"))
prod = {}
for cid, v in I.items():
    s = SEL.get(cid, {}); up = s.get("uploader", "?")
    base = dict(clip_id=cid, origin="G7", uploader=up, licence=s.get("licence"), page=s.get("page"), dur_s=s.get("dur"), role=v["role"],
                counts_toward_60=bool(v.get("counts")), labels="machine proposals only")
    if v["role"] == "reject":
        base["split"] = "excluded"
    elif v["role"] == "weak_exploratory":
        base["split"] = "weak_exploratory"
    elif v["role"] == "negative":
        base["split"] = "negatives_v7"
    elif up in hold_up:
        base["split"] = "holdout_v7_pending"
    else:
        prod.setdefault(up, []).append(base); continue
    rows.append(base)
ups = sorted(prod, key=lambda u: hashlib.md5(u.encode()).hexdigest())
n = len(ups)
for i, u in enumerate(ups):
    sp = "holdout_v7_pending" if i < round(0.4 * n) else "dev_v7" if i < round(0.7 * n) else "train_v7_weak"
    for b in prod[u]:
        b["split"] = sp; rows.append(b)
os.makedirs(f"{R}/ml/runs/G7/video_v7", exist_ok=True)
with open(f"{R}/ml/runs/G7/video_v7/splits_v7.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
cnt = {}
for r in rows:
    cnt.setdefault(r["split"], [0, 0, set()]); c = cnt[r["split"]]; c[0] += 1; c[1] += int(r["counts_toward_60"]); c[2].add(r["uploader"])
summ = dict(total_files=len(rows), counted_independent=sum(int(r["counts_toward_60"]) for r in rows),
            distinct_uploaders_counted=len({r["uploader"] for r in rows if r["counts_toward_60"]}),
            human_verified_clips=0, by_split={k: dict(files=v[0], counted=v[1], uploaders=len(v[2])) for k, v in sorted(cnt.items())})
json.dump(summ, open(f"{R}/ml/runs/G7/video_v7/splits_v7_summary.json", "w"), indent=1); print(json.dumps(summ, indent=1))
