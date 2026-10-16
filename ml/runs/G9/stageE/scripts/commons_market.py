"""G9 Stage E: collect market set M from Wikimedia Commons (per-file CC0 / CC BY / CC BY-SA / PD only; licence, author, uploader, page
recorded). Excludes: holdout uploaders (+ overlap-excluded), M-dev uploaders, Stage D S uploaders, all 586 Stage D candidate titles.
Assigns split by the prereg rule: source_key = uploader, or credited author for bot uploads; sha1(source_key) % 3 == 0 -> M-TEST.
Usage: commons_market.py search | download [budget_s]"""
import json, os, sys, time, re, csv, hashlib, urllib.parse, urllib.request
OUT = "/workspace/work/cv/g9e/commons"; os.makedirs(f"{OUT}/img", exist_ok=True)
UA = {"User-Agent": "NutriSoleResearch/0.1 (muhammadfaizanali18@gmail.com)"}
POS = ["sabzi mandi", "vegetable market Pakistan", "fruit market Lahore", "fruit stall Karachi", "vegetable vendor cart India",
       "fruit vendor cart", "mandi fruit vegetables", "vegetable market Bangladesh", "fruit market India stall", "Kinnow oranges market",
       "oranges stall market", "tangerines market stall", "apples stall market", "bananas stall market", "banana vendor", "tomato vendor market",
       "carrots vendor market", "vegetable seller street", "fruit seller street", "greengrocer shop front", "market stall fruit display",
       "produce market stall", "farmers market vegetables stall", "vegetable stall Africa market", "fruit stall Africa market",
       "mercado frutas puesto", "marché fruits légumes étal", "Obststand Markt", "bazaar vegetables Afghanistan", "vegetable market Nepal",
       "pomegranate vendor", "mango stall market", "guava vendor", "potatoes onions market stall", "cucumbers market stall",
       "bell peppers stall", "lemons market stall", "limes vendor market",
       "oranges for sale street", "orange vendor", "mandarins for sale", "naranjas mercado", "Orangen Marktstand", "malta fruit Pakistan",
       "apples for sale market", "apple vendor cart", "manzanas mercado", "pommes marché étal", "Äpfel Marktstand", "carrots for sale market",
       "carrot seller", "zanahorias mercado", "Karotten Marktstand", "tomatoes for sale street", "tomates mercado puesto", "bananas for sale street", "plátanos mercado"]
NEG = ["clothing market stall", "clothes bazaar", "shoe stall market", "bags stall market", "market signboard shop", "fruit juice shop sign",
       "printed fruit poster", "fruit carton boxes market", "chili peppers market stall", "onions market stall", "spice market stall",
       "bangles stall bazaar", "toy stall market", "fabric market", "melons market stall", "gourds vegetable market"]
OK = re.compile(r"^(cc0|cc[- ]by(-sa)?([- ]\d\.\d)?|public domain|pd.*)$", re.I)
BAD_UP = set(); BAD_T = set()
for r in csv.DictReader(open("/workspace/work/nutrisole/ml/runs/G9/stageB/mining_split.csv")):
    if r["stageB_role"] in ("holdout_never_used", "excluded_uploader_overlaps_holdout", "M-dev"): BAD_UP.add(r["uploader"])
for r in csv.DictReader(open("/workspace/work/nutrisole/ml/runs/G9/stageD/s_manifest.csv")): BAD_UP.add(r["uploader"])
for m in json.load(open("/workspace/work/cv/g9d/commons/manifest.json")).values(): BAD_T.add(m["title"])
BOT = re.compile(r"bot$", re.I)
def skey(up, artist): return ("author:" + artist.strip()) if (BOT.search(up or "") and artist.strip()) else ("uploader:" + (up or ""))
def split(k): return "M-TEST" if int(hashlib.sha1(k.encode()).hexdigest(), 16) % 3 == 0 else "M-DEV"
def api(params):
    u = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(dict(params, format="json"))
    for i in range(3):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30))
        except Exception as e: time.sleep(2 + 3 * i); err = e
    raise err
MF = f"{OUT}/manifest.json"; man = json.load(open(MF)) if os.path.exists(MF) else {}
if sys.argv[1] == "search":
    t0 = time.time()
    for kind, Q in (("pos", POS), ("neg", NEG)):
        for q in Q:
            if any(v["query"] == q for v in man.values()) or time.time() - t0 > 100: continue
            r = api(dict(action="query", generator="search", gsrsearch=f"{q} filetype:bitmap", gsrnamespace=6, gsrlimit=25,
                         prop="imageinfo", iiprop="url|extmetadata|user|size|mime", iiurlwidth=1280))
            for p in (r.get("query", {}).get("pages", {}) or {}).values():
                ii = (p.get("imageinfo") or [{}])[0]; md = ii.get("extmetadata", {}); lic = md.get("LicenseShortName", {}).get("value", "").strip()
                if ii.get("mime") != "image/jpeg" or not OK.match(lic) or max(ii.get("width", 0), ii.get("height", 0)) < 1000: continue
                if ii.get("user") in BAD_UP or p["title"] in BAD_T or p["title"] in man: continue
                art = re.sub("<[^>]+>", "", md.get("Artist", {}).get("value", "")).strip()[:120]; k = skey(ii.get("user"), art)
                man[p["title"]] = dict(title=p["title"], query=q, kind=kind, licence=lic, uploader=ii.get("user"), artist=art, source_key=k, split=split(k),
                                       page=ii.get("descriptionurl"), url=ii.get("thumburl"), w=ii.get("width"), h=ii.get("height"))
            json.dump(man, open(MF, "w"), indent=0); time.sleep(0.3)
    print("candidates", len(man), {s: sum(1 for v in man.values() if v["split"] == s) for s in ("M-DEV", "M-TEST")})
else:
    t0 = time.time(); n = 0; nxt = max([int(m["file"][1:5]) for m in man.values() if "file" in m] + [-1]) + 1
    for t, m in sorted(man.items()):
        if "file" not in m: m["file"] = f"m{nxt:04d}.jpg"; nxt += 1
        fn = f"{OUT}/img/{m['file']}"
        if os.path.exists(fn) or not m.get("url") or m.get("dl_error"): continue
        try: open(fn, "wb").write(urllib.request.urlopen(urllib.request.Request(m["url"], headers=UA), timeout=40).read()); n += 1
        except Exception as e: m["dl_error"] = str(e)[:100]
        if time.time() - t0 > float(sys.argv[2] if len(sys.argv) > 2 else 100): break
        time.sleep(0.15)
    json.dump(man, open(MF, "w"), indent=0); print("downloaded", n, "have", len(os.listdir(f"{OUT}/img")), "of", len(man))
