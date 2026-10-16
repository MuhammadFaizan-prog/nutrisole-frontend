"""G9 Stage J: per-file licence audit of the 742 Stage I candidates.
Commons: re-query extmetadata (LicenseShortName, Artist, Credit, UsageTerms, AttributionRequired) per title so the audit does not rely on the
values stored at collection time; a file is NON-COMPLIANT if its licence is missing, NC/ND, non-free/fair use, or if its Credit/Artist/
description says it comes from Pexels, Pixabay or Mixkit (banned for this project), or if attribution is required and no author is given.
Dataset sources (FruitNet, Mendeley carrot/tomato): licence checked per source (CC BY 4.0), author = dataset authors, URL = dataset page.
Output: ml/runs/G9/stageJ/out/j_licence.csv + j_licence.json (summary + excluded keys)."""
import json, re, csv, time, urllib.parse, urllib.request, sys
UA = {"User-Agent": "NutriSoleResearch/1.0 (clydara1@gmail.com)"}
C = json.load(open("/workspace/work/g9i/cands/cands.json"))
OUT = "/workspace/work/nutrisole/ml/runs/G9/stageJ/out"
BAN = re.compile(r"pexels|pixabay|mixkit", re.I)
STOCK = re.compile(r"unsplash|stocksnap|burst\.shopify|freepik|shutterstock|istock", re.I)
CACHE = "/workspace/work/g9j/commons_meta.json"
try: M = json.load(open(CACHE))
except Exception: M = {}
def strip(s): return re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", s or "")).strip()
titles = [v["title"] for v in C.values() if v["source"] == "commons" and v["title"] not in M]
for i in range(0, len(titles), 40):
    b = titles[i:i + 40]
    u = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(dict(action="query", titles="|".join(b), prop="imageinfo",
        iiprop="extmetadata|user|url", format="json", iiextmetadatafilter="LicenseShortName|Artist|Credit|UsageTerms|AttributionRequired|ImageDescription|NonFree|Copyrighted|LicenseUrl"))
    for t in range(3):
        try: d = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read()); break
        except Exception as e: time.sleep(3); d = None
    if not d: continue
    norm = {n["to"]: n["from"] for n in d["query"].get("normalized", [])}
    for pg in d["query"]["pages"].values():
        ii = (pg.get("imageinfo") or [{}])[0]; em = ii.get("extmetadata", {})
        M[norm.get(pg["title"], pg["title"])] = dict(missing="missing" in pg, user=ii.get("user"), **{k: strip(v.get("value", "")) if isinstance(v, dict) else "" for k, v in em.items()})
    json.dump(M, open(CACHE, "w")); time.sleep(0.5)
DS_AUTH = {"fruitnet": ("Meshram, V. & Patil, K. (FruitNet, 2021)", "CC BY 4.0"), "carrot_m": ("Mendeley dataset ww83r63rtr authors", "CC BY 4.0"),
           "tomato_m": ("Mendeley dataset hfyth5t3gg authors", "CC BY 4.0")}
rows = []
for k, v in sorted(C.items()):
    if v["source"] == "commons":
        m = M.get(v["title"], {}); lic = m.get("LicenseShortName") or v.get("licence", ""); art = m.get("Artist") or v.get("artist", "")
        cred = m.get("Credit", ""); desc = m.get("ImageDescription", "")[:300]; why = []
        if not m: why.append("metadata not re-fetched")
        if m.get("missing"): why.append("file deleted from Commons")
        if not re.search(r"CC|public domain|PD|CC0|no restrictions", lic, re.I): why.append(f"licence not free/unknown: {lic!r}")
        if re.search(r"\bNC\b|\bND\b|non-?commercial|no.?deriv", lic, re.I): why.append("NC/ND licence")
        if m.get("NonFree", "").lower() in ("true", "1"): why.append("non-free flag")
        if BAN.search(cred + " " + art + " " + desc + " " + v["title"]): why.append("banned source (Pexels/Pixabay/Mixkit) in credit/author/description")
        if STOCK.search(cred + " " + art + " " + desc): why.append("stock-photo-site origin (Unsplash etc.): excluded conservatively, same family as the banned sites")
        attr_req = m.get("AttributionRequired", "").lower() == "true" or lic.upper().startswith("CC BY")
        if attr_req and not (art or v.get("uploader")): why.append("attribution required but no author")
        rows.append(dict(key=k, source="commons", licence=lic, author=(art or v.get("uploader", ""))[:150], uploader=v.get("uploader", ""), credit=cred[:150],
                         source_url=v["page"], file_url=v.get("url", ""), licence_url=m.get("LicenseUrl", ""), compliant="no" if why else "yes", issue="; ".join(why)))
    else:
        a, lic = DS_AUTH[v["source"]]; why = [] if v.get("licence") == lic else [f"licence mismatch {v.get('licence')}"]
        rows.append(dict(key=k, source=v["source"], licence=lic, author=a, uploader=v.get("uploader", ""), credit=v.get("mirror", ""), source_url=v["page"],
                         file_url=v.get("mirror", "") or v["page"], licence_url="https://creativecommons.org/licenses/by/4.0/", compliant="no" if why else "yes", issue="; ".join(why)))
with open(f"{OUT}/j_licence.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
bad = [r for r in rows if r["compliant"] == "no"]
from collections import Counter
summ = dict(n=len(rows), compliant=len(rows) - len(bad), non_compliant=len(bad), excluded_keys=[r["key"] for r in bad],
            issues=Counter(i.split(":")[0] for r in bad for i in r["issue"].split("; ")), licences=Counter(r["licence"] for r in rows),
            commons_refetched=sum(1 for v in C.values() if v["source"] == "commons" and v["title"] in M))
json.dump(summ, open(f"{OUT}/j_licence.json", "w"), indent=1); print(json.dumps(summ, indent=1)[:3000])
for r in bad: print(r["key"], r["issue"][:120], r["source_url"][:90])
