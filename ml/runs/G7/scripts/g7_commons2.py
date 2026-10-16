#!/usr/bin/env python3
"""G7 Phase 2 pass 2: more file-namespace searches (multilingual), merged into commons_g7_candidates.json (same metadata fields)."""
import json, re, time, urllib.parse, urllib.request
H = {"User-Agent": "NutriSoleResearch/0.3 (FYP CV benchmark; muhammadfaizanali18@gmail.com)"}
def api(**k):
    k.update(format="json", maxlag="5"); time.sleep(0.5)
    return json.load(urllib.request.urlopen(urllib.request.Request("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(k), headers=H), timeout=40))
P = "/workspace/work/cv/g7src/meta/commons_g7_candidates.json"; C = json.load(open(P))
held = {s["title"] for s in json.load(open("/workspace/work/cv/g6src/meta/commons_selected.json"))}
Q = ["selling vegetables", "selling fruits", "fruit seller", "vegetable seller", "vegetables market", "fruits market", "bazar", "mandi", "sabji",
     "mercado frutas", "mercado verduras", "marché légumes", "marché fruits", "pasar buah", "pasar sayur", "feira frutas", "Wiki Loves Africa market",
     "market Dhaka", "market Lagos", "market Kolkata", "market Karachi", "market Lahore", "market Kathmandu", "market Hanoi", "market Nairobi",
     "street vendor fruits", "banana seller", "mango seller", "orange seller", "watermelon seller", "tomatoes", "carrots", "cucumbers", "apples", "bananas",
     "oranges", "lemons", "guavas", "pomegranates", "potatoes", "peppers vegetables", "grocery store produce", "supermarket fruit", "kitchen vegetables",
     "farmers market", "night market fruit", "fruit cart", "vegetable cart", "thela"]
new = {}
for q in Q:
    try:
        r = api(action="query", list="search", srsearch=f"{q} filetype:video", srnamespace=6, srlimit=50)
        for m in r["query"]["search"]:
            if m["title"] not in C: new.setdefault(m["title"], f"search:{q}")
    except Exception as e: print("ERR", q, e)
T = list(new)
for i in range(0, len(T), 40):
    try: r = api(action="query", titles="|".join(T[i:i + 40]), prop="imageinfo|categories", iiprop="url|size|extmetadata|user|timestamp|mediatype", cllimit=500, clshow="!hidden")
    except Exception as e: print("ERR info", e); continue
    for p in r["query"].get("pages", {}).values():
        if "imageinfo" not in p: continue
        ii = p["imageinfo"][0]; m = ii.get("extmetadata", {})
        g = lambda k: re.sub("<[^>]+>", "", m.get(k, {}).get("value", "") or "")
        C[p["title"]] = dict(how=new.get(p["title"]), held_g6=p["title"] in held, url=ii.get("url"), page=ii.get("descriptionurl"), dur=ii.get("duration"),
                             w=ii.get("width"), h=ii.get("height"), size=ii.get("size"), mediatype=ii.get("mediatype"), uploader=ii.get("user"), upload_ts=ii.get("timestamp"),
                             licence=g("LicenseShortName"), licence_url=g("LicenseUrl"), usage=g("UsageTerms"), artist=g("Artist")[:120], credit=g("Credit")[:200],
                             date=g("DateTimeOriginal")[:25], desc=g("ImageDescription")[:400], cats=[c["title"][9:] for c in p.get("categories", [])])
json.dump(C, open(P, "w"), indent=1, ensure_ascii=False); print("added", len(new), "total", len(C))
