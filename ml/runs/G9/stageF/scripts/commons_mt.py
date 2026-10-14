"""G9 Stage F: market-train (MT) candidate pool from Wikimedia Commons (per-file CC0 / CC BY / CC BY-SA / PD; licence, author, uploader,
page recorded). Pool = 586 Stage D candidates (never labelled except S) + new searches (negatives + showcase piles).
Excluded source keys: holdout / overlap / M-dev uploaders (mining_split.csv), Stage D S uploaders, every Stage E (M-DEV + M-TEST +
unused candidate) source key and title. Cap <= 4 images per source key is applied at selection time.
Usage: commons_mt.py search | download [budget_s] | pool"""
import json, os, sys, time, re, csv, urllib.parse, urllib.request
OUT = "/workspace/work/cv/g9f/commons"; os.makedirs(f"{OUT}/img", exist_ok=True)
UA = {"User-Agent": "NutriSoleResearch/0.1 (muhammadfaizanali18@gmail.com)"}
Q = [("neg", q) for q in ["persimmons market stall", "kaki fruit market", "plums market stall", "peaches market stall", "papaya market stall",
      "apricots market stall", "figs market stall", "dragon fruit market", "eggplant market stall", "onions garlic market stall", "pumpkins market stall",
      "watermelons market stall", "fruit print fabric", "fruit pattern shirt", "fruit printed bag", "shopping bags market", "market scales weighing",
      "market crates stacked", "plastic crates market", "wheelbarrow market", "fruit poster wall", "fruit juice stand sign", "toy fruit", "artificial fruit display"]] + \
    [("pos", q) for q in ["oranges heap market", "pile of tangerines", "apples heap market", "red apples crates market", "tomatoes heap market",
      "tomato crates market", "carrots heap market", "bunches of bananas market", "banana bunches stall", "lemons heap market", "kinnow",
      "mosambi", "pomegranates heap", "guavas heap", "mangoes heap market", "potatoes heap market", "cucumbers heap", "capsicum market"]]
OK = re.compile(r"^(cc0|cc[- ]by(-sa)?([- ]\d\.\d)?|public domain|pd.*)$", re.I)
BOT = re.compile(r"bot$", re.I)
def skey(up, artist): return ("author:" + artist.strip()) if (BOT.search(up or "") and artist.strip()) else ("uploader:" + (up or ""))
BAD_UP = set(); BAD_K = set(); BAD_T = set()
for r in csv.DictReader(open("/workspace/work/nutrisole/ml/runs/G9/stageB/mining_split.csv")):
    if r["stageB_role"] in ("holdout_never_used", "excluded_uploader_overlaps_holdout", "M-dev", "M-train"): BAD_UP.add(r["uploader"])
for r in csv.DictReader(open("/workspace/work/nutrisole/ml/runs/G9/stageD/s_manifest.csv")): BAD_UP.add(r["uploader"])
for v in json.load(open("/workspace/work/cv/g9e/commons/manifest.json")).values(): BAD_K.add(v["source_key"]); BAD_T.add(v["title"]); BAD_UP.add(v.get("uploader"))
def api(params):
    u = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(dict(params, format="json"))
    for i in range(3):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30))
        except Exception as e: time.sleep(2 + 3 * i); err = e
    raise err
MF = f"{OUT}/manifest.json"; man = json.load(open(MF)) if os.path.exists(MF) else {}
DT = set(json.load(open("/workspace/work/cv/g9d/commons/manifest.json")))
if sys.argv[1] == "search":
    t0 = time.time()
    for kind, q in Q:
        if any(v["query"] == q for v in man.values()) or time.time() - t0 > 100: continue
        r = api(dict(action="query", generator="search", gsrsearch=f"{q} filetype:bitmap", gsrnamespace=6, gsrlimit=20,
                     prop="imageinfo", iiprop="url|extmetadata|user|size|mime", iiurlwidth=1600))
        for p in (r.get("query", {}).get("pages", {}) or {}).values():
            ii = (p.get("imageinfo") or [{}])[0]; md = ii.get("extmetadata", {}); lic = md.get("LicenseShortName", {}).get("value", "").strip()
            if ii.get("mime") != "image/jpeg" or not OK.match(lic) or max(ii.get("width", 0), ii.get("height", 0)) < 1000: continue
            art = re.sub("<[^>]+>", "", md.get("Artist", {}).get("value", "")).strip()[:120]; k = skey(ii.get("user"), art)
            if ii.get("user") in BAD_UP or k in BAD_K or p["title"] in BAD_T or p["title"] in DT or p["title"] in man: continue
            man[p["title"]] = dict(title=p["title"], query=q, kind=kind, licence=lic, uploader=ii.get("user"), artist=art, source_key=k,
                                   page=ii.get("descriptionurl"), url=ii.get("thumburl"), w=ii.get("width"), h=ii.get("height"))
        json.dump(man, open(MF, "w"), indent=0); time.sleep(0.3)
    print("candidates", len(man), "queries done", len({v["query"] for v in man.values()}), "/", len(Q))
elif sys.argv[1] == "download":
    t0 = time.time(); n = 0; nxt = max([int(m["file"][2:6]) for m in man.values() if "file" in m] + [-1]) + 1
    for t, m in sorted(man.items()):
        if "file" not in m: m["file"] = f"fn{nxt:04d}.jpg"; nxt += 1
        fn = f"{OUT}/img/{m['file']}"
        if os.path.exists(fn) or not m.get("url") or m.get("dl_error"): continue
        try: open(fn, "wb").write(urllib.request.urlopen(urllib.request.Request(m["url"], headers=UA), timeout=40).read()); n += 1
        except Exception as e: m["dl_error"] = str(e)[:100]
        if time.time() - t0 > float(sys.argv[2] if len(sys.argv) > 2 else 100): break
        time.sleep(0.15)
    json.dump(man, open(MF, "w"), indent=0); print("downloaded", n, "have", len(os.listdir(f"{OUT}/img")), "of", len(man))
else:  # pool: merge Stage D candidates (eligible) + new search, write pool.json
    S_files = {json.loads(l) for l in []}
    S = json.load(open("/workspace/work/nutrisole/ml/runs/G9/stageD/s_labels.json"))["items"]; Sf = {i["file"] for i in S}
    pool = {}; why = {}
    for t, v in json.load(open("/workspace/work/cv/g9d/commons/manifest.json")).items():
        k = skey(v.get("uploader"), v.get("artist", "")); f = v.get("file")
        if not f or not os.path.exists(f"/workspace/work/cv/g9d/commons/img/{f}"): why[t] = "no_file"; continue
        if f in Sf: why[t] = "stageD_S"; continue
        if v.get("uploader") in BAD_UP or k in BAD_K or t in BAD_T: why[t] = "excluded_source"; continue
        pool[t] = dict(v, source_key=k, kind="stageD_pool", path=f"/workspace/work/cv/g9d/commons/img/{f}")
    for t, v in man.items():
        if v.get("file") and os.path.exists(f"{OUT}/img/{v['file']}"): pool[t] = dict(v, path=f"{OUT}/img/{v['file']}")
    json.dump(pool, open("/workspace/work/cv/g9f/pool.json", "w"), indent=0)
    import collections; print("pool", len(pool), collections.Counter(why.values()), "sources", len({v["source_key"] for v in pool.values()}))
