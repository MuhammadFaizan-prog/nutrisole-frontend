"""G9 Stage J: per-file licence table for the Stage J extra TRAINING candidates (train_cands.json). Same rules as j_licence.py:
NC/ND, non-free, missing author for CC BY, or a Pexels/Pixabay/Mixkit/stock-site credit -> excluded."""
import json, csv, re
T = json.load(open("/workspace/work/g9j/train/train_cands.json")); OUT = "/workspace/work/nutrisole/ml/runs/G9/stageJ/out"
BAN = re.compile(r"pexels|pixabay|mixkit|unsplash|stocksnap|freepik|shutterstock|istock", re.I); rows = []
for k, v in sorted(T.items()):
    if "size" not in v: continue
    lic = v.get("licence", ""); why = []
    if not re.search(r"CC|public domain|PD|CC0", lic, re.I): why.append(f"licence not free/unknown: {lic!r}")
    if re.search(r"\bNC\b|\bND\b", lic): why.append("NC/ND licence")
    if BAN.search(" ".join(str(v.get(x, "")) for x in ("credit", "author", "title"))): why.append("banned/stock source")
    if lic.upper().startswith("CC BY") and not (v.get("author") or v.get("uploader")): why.append("attribution required but no author")
    rows.append(dict(key=k, source=v["source"], licence=lic, author=(v.get("author") or v.get("uploader", ""))[:150], uploader=v.get("uploader", ""), credit=v.get("credit", "")[:150],
                     source_url=v["page"], file_url=v.get("url") or v.get("src_path", ""), compliant="no" if why else "yes", issue="; ".join(why)))
with open(f"{OUT}/j_licence_train.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
from collections import Counter
bad = [r["key"] for r in rows if r["compliant"] == "no"]
json.dump(dict(n=len(rows), non_compliant=len(bad), excluded_keys=bad, licences=Counter(r["licence"] for r in rows), by_source=Counter(r["source"] for r in rows)), open(f"{OUT}/j_licence_train.json", "w"), indent=1)
print(len(rows), "bad", bad, Counter(r["licence"] for r in rows))
