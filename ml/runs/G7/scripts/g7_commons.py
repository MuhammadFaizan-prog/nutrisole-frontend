#!/usr/bin/env python3
"""G7 Phase 2: discover more Wikimedia Commons videos (official MediaWiki Action API only, polite pacing, UA with contact).
Sources: categorymembers walk (depth 2) of the categories named in the G7 instructions + file-namespace search queries +
the 7 named candidate files. Collects imageinfo (url, size, duration, uploader) + extmetadata (licence, artist, date,
description) + categories. Marks files already held (G6 38). Writes g7src/meta/commons_g7_candidates.json.
Never downloads here; never touches Pexels/Pixabay/Mixkit."""
import json, re, time, urllib.parse, urllib.request, os, sys
OUT = "/workspace/work/cv/g7src/meta"; os.makedirs(OUT, exist_ok=True)
H = {"User-Agent": "NutriSoleResearch/0.3 (FYP CV benchmark; muhammadfaizanali18@gmail.com)"}
def api(**k):
    k.update(format="json", maxlag="5")
    for i in range(5):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(k), headers=H), timeout=40))
            if "error" in r and r["error"].get("code") == "maxlag":
                time.sleep(5 * (i + 1)); continue
            time.sleep(0.5); return r
        except Exception as e:
            time.sleep(5 * (i + 1)); err = e
    raise RuntimeError(err)
VID = re.compile(r"\.(webm|ogv|mpg|mpeg|ogg|mp4)$", re.I)
ROOTS = ["Category:Videos of fruit", "Category:Fruit and vegetable markets", "Category:Fruit markets", "Category:Videos of markets",
         "Category:Videos of vegetables", "Category:Vegetable markets", "Category:Videos of street vendors", "Category:Videos of food markets",
         "Category:Fruit vendors", "Category:Vegetable vendors", "Category:Videos of bananas", "Category:Videos of apples", "Category:Videos of mangoes",
         "Category:Videos of tomatoes", "Category:Videos of oranges", "Category:Videos of fruit shops", "Category:Videos of bazaars"]
QUERIES = ["fruit market video", "vegetable market video", "fruit vendor", "vegetable vendor", "fruit stall", "sabzi mandi", "bazaar fruit",
           "mango market", "banana market", "tomato market", "guava", "orange fruit seller", "apple market", "carrot market", "cucumber vendor",
           "capsicum", "pomegranate", "lemon seller", "fruit shop", "greengrocer", "farmers market vegetables", "wet market", "souk vegetables"]
NAMED = ["File:Traditional floating fruits market.webm", "File:Vegetable vendor selling vegetables in a Bangalore street.webm",
         "File:Haikou wholesale fruit market panorama - 01.ogv", "File:Vegetable Market (Amman).webm", "File:Fresh mango.webm",
         "File:Fresh Pepper 🌶️ Video.webm", "File:Market Movements.webm"]
files, seen, how = {}, set(), {}
def walk(cat, d):
    if cat in seen or d < 0: return
    seen.add(cat); cont = {}
    while True:
        try: r = api(action="query", list="categorymembers", cmtitle=cat, cmlimit=500, cmtype="file|subcat", **cont)
        except Exception as e: print("ERR", cat, e); return
        for m in r.get("query", {}).get("categorymembers", []):
            t = m["title"]
            if t.startswith("Category:"): walk(t, d - 1)
            elif VID.search(t): how.setdefault(t, f"cat:{cat}")
        if "continue" in r: cont = {"cmcontinue": r["continue"]["cmcontinue"]}
        else: break
for c in ROOTS: walk(c, 2)
print("cats walked", len(seen), "videos", len(how), flush=True)
for q in QUERIES:
    try:
        r = api(action="query", list="search", srsearch=f"{q} filetype:video", srnamespace=6, srlimit=100)
        for m in r["query"]["search"]:
            if VID.search(m["title"]): how.setdefault(m["title"], f"search:{q}")
    except Exception as e: print("ERR search", q, e)
for t in NAMED: how.setdefault(t, "named")
print("total titles", len(how), flush=True)
held = {s["title"] for s in json.load(open("/workspace/work/cv/g6src/meta/commons_selected.json"))}
T = list(how); out = {}
for i in range(0, len(T), 40):
    try:
        r = api(action="query", titles="|".join(T[i:i + 40]), prop="imageinfo|categories", iiprop="url|size|extmetadata|user|timestamp|mediatype", cllimit=500, clshow="!hidden")
    except Exception as e:
        print("ERR info", e); continue
    for p in r["query"].get("pages", {}).values():
        if "imageinfo" not in p: out[p.get("title")] = dict(missing=True, how=how.get(p.get("title"))); continue
        ii = p["imageinfo"][0]; m = ii.get("extmetadata", {})
        g = lambda k: re.sub("<[^>]+>", "", m.get(k, {}).get("value", "") or "")
        out[p["title"]] = dict(how=how.get(p["title"]), held_g6=p["title"] in held, url=ii.get("url"), page=ii.get("descriptionurl"), dur=ii.get("duration"),
                               w=ii.get("width"), h=ii.get("height"), size=ii.get("size"), mediatype=ii.get("mediatype"), uploader=ii.get("user"), upload_ts=ii.get("timestamp"),
                               licence=g("LicenseShortName"), licence_url=g("LicenseUrl"), usage=g("UsageTerms"), artist=g("Artist")[:120], credit=g("Credit")[:200],
                               date=g("DateTimeOriginal")[:25], desc=g("ImageDescription")[:400], cats=[c["title"][9:] for c in p.get("categories", [])])
json.dump(out, open(f"{OUT}/commons_g7_candidates.json", "w"), indent=1, ensure_ascii=False)
print("wrote", len(out), "held", sum(1 for v in out.values() if v.get("held_g6")))
