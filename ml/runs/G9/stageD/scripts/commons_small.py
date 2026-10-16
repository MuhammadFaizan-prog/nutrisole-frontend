"""G9 Stage D Exp1: search Wikimedia Commons for scenes with many small / overlapping / piled produce of the 12 classes and download
1600-px renditions of files with a per-file CC0 / CC BY / CC BY-SA / PD licence (licence, author, uploader, page recorded).
Uploaders that appear in the holdout (or were excluded for holdout overlap) are skipped. Usage: commons_small.py search|download [budget_s]"""
import json, os, sys, time, re, csv, urllib.parse, urllib.request
OUT = "/workspace/work/cv/g9d/commons"; os.makedirs(f"{OUT}/img", exist_ok=True)
UA = {"User-Agent": "NutriSoleResearch/0.1 (muhammadfaizanali18@gmail.com)"}
Q = ["carrots market stall", "pile of carrots", "carrots for sale", "carrot heap market", "vegetable market stall carrots tomatoes",
     "tomatoes market stall", "pile of tomatoes", "tomatoes for sale market", "apples market stall", "pile of apples", "apples for sale",
     "oranges market stall", "pile of oranges", "citrus fruit stall", "mandarins market", "bananas market stall", "bunches of bananas market",
     "fruit stall market", "vegetable stall market", "greengrocer display", "farmers market vegetables", "lemons limes market",
     "potatoes market stall", "cucumbers market", "bell peppers market", "pomegranates market", "mangoes market stall", "guava market",
     "sabzi mandi", "fruit vendor cart", "vegetable vendor India", "bazaar fruit vegetables Pakistan"]
OK = re.compile(r"^(cc0|cc[- ]by(-sa)?([- ]\d\.\d)?|public domain|pd.*)$", re.I)
BAD_UP = set()
for r in csv.DictReader(open("/workspace/work/nutrisole/ml/runs/G9/stageB/mining_split.csv")):
    if r["stageB_role"] in ("holdout_never_used", "excluded_uploader_overlaps_holdout"): BAD_UP.add(r["uploader"])
def api(params):
    u = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(dict(params, format="json"))
    for i in range(3):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30))
        except Exception as e: time.sleep(2 + 3 * i); err = e
    raise err
MF = f"{OUT}/manifest.json"; man = json.load(open(MF)) if os.path.exists(MF) else {}
if sys.argv[1] == "search":
    for q in Q:
        if any(v["query"] == q for v in man.values()): continue
        r = api(dict(action="query", generator="search", gsrsearch=f"{q} filetype:bitmap", gsrnamespace=6, gsrlimit=30,
                     prop="imageinfo", iiprop="url|extmetadata|user|size|mime", iiurlwidth=1600))
        for p in (r.get("query", {}).get("pages", {}) or {}).values():
            ii = (p.get("imageinfo") or [{}])[0]; md = ii.get("extmetadata", {}); lic = md.get("LicenseShortName", {}).get("value", "").strip()
            if ii.get("mime") != "image/jpeg" or not OK.match(lic) or max(ii.get("width", 0), ii.get("height", 0)) < 1200: continue
            if ii.get("user") in BAD_UP or p["title"] in man: continue
            man[p["title"]] = dict(title=p["title"], query=q, licence=lic, uploader=ii.get("user"), artist=re.sub("<[^>]+>", "", md.get("Artist", {}).get("value", ""))[:120],
                                   page=ii.get("descriptionurl"), url=ii.get("thumburl"), w=ii.get("width"), h=ii.get("height"))
        print(q, len(man), flush=True); time.sleep(0.3); json.dump(man, open(MF, "w"), indent=0)
else:
    t0 = time.time(); n = 0; nxt = max([int(m["file"][2:6]) for m in man.values() if "file" in m] + [-1]) + 1
    for t, m in sorted(man.items()):
        if "file" not in m: m["file"] = f"sd{nxt:04d}.jpg"; nxt += 1
        fn = f"{OUT}/img/{m['file']}"
        if os.path.exists(fn) or not m.get("url") or m.get("dl_error"): continue
        try: open(fn, "wb").write(urllib.request.urlopen(urllib.request.Request(m["url"], headers=UA), timeout=40).read()); n += 1
        except Exception as e: m["dl_error"] = str(e)[:100]
        if time.time() - t0 > float(sys.argv[2] if len(sys.argv) > 2 else 100): break
        time.sleep(0.2)
    json.dump(man, open(MF, "w"), indent=0); print("downloaded", n, "have", len(os.listdir(f"{OUT}/img")), "of", len(man))
