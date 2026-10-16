"""G9 Stage B: search Wikimedia Commons for hard-negative target types and download 640-px thumbnails of files whose
per-file licence is CC0 / CC BY / CC BY-SA / public domain. Licence, author, uploader and page are recorded per file.
Usage: commons_fetch.py search|download"""
import json, os, sys, time, re, urllib.parse, urllib.request
OUT = "/workspace/work/cv/g9b/commons"; os.makedirs(f"{OUT}/img", exist_ok=True)
UA = {"User-Agent": "NutriSoleResearch/0.1 (muhammadfaizanali18@gmail.com)"}
Q = {
 "clothing": ["clothing market stall", "textile shop fabric rolls", "colorful clothes hanging market", "sari shop display", "second hand clothes market"],
 "sacks": ["sacks of grain market", "jute sacks warehouse", "rice sacks shop"],
 "fish": ["fish market stall", "dried fish market", "fish vendor"],
 "spices": ["spice market stall", "spice shop display bowls"],
 "signs": ["shop sign street market", "market stall signboard"],
 "packaging": ["supermarket shelf packaged food", "snack packets shop", "juice cartons supermarket", "canned food shelf"],
 "printed_fruit": ["fruit juice packaging", "fruit print fabric", "fruit poster", "fruit sticker label", "fruit mural"],
 "fruit_coloured": ["orange plastic buckets", "yellow raincoat", "red balloons", "orange traffic cones", "red plastic chairs market", "yellow plastic crates", "green plastic basket", "orange ball", "tennis balls"],
 "market_other": ["meat market butcher stall", "flower market stall", "egg vendor market", "bread bakery stall", "pottery market", "umbrella market stall", "household goods market stall", "toy stall market"],
}
Q2 = {
 "night_street": ["night market street lights", "night street shops", "bazaar at night", "street at night shops Iran", "night walk city street", "neon signs street night"],
 "market_crowd": ["bazaar crowd", "street vendors crowd", "busy market street", "covered bazaar shops", "souk shops", "market hall interior"],
 "clothing": ["people walking street clothing", "scarves shop", "shoe shop display", "handbags market stall", "hat stall market", "fabric market Africa"],
 "fish": ["fish auction", "seafood market display", "butcher shop meat hanging"],
 "sacks": ["sacks of potatoes"[:0] or "sacks of flour", "bags of cement", "plastic bags shop"],
 "spices": ["dried chillies market", "nuts dried fruit stall", "grain market bowls", "beans lentils market display"],
 "fruit_coloured": ["orange lanterns", "yellow taxi", "red apples logo sign"[:0] or "red fire hydrant", "orange life jackets", "yellow flowers marigold market", "pumpkin decoration plastic", "round red lanterns", "yellow helmets"],
 "printed_fruit": ["fruit pattern textile", "fruit illustration poster", "fruit shaped toys", "artificial fruit plastic", "fruit wallpaper print"],
 "equipment": ["weighing scale market", "market cart wheelbarrow", "plastic crates stack empty", "umbrellas street vendors"],
 "leafy_other": ["onions market"[:0] or "garlic market", "leafy greens market stall", "melons market"[:0] or "cabbage pile", "okra market", "eggplant market", "grapes market stall", "watermelon pile", "coconut vendor", "pineapple stall", "oil palm fruit"],
}
OK = re.compile(r"^(cc0|cc[- ]by(-sa)?([- ]\d\.\d)?|public domain|pd.*)$", re.I)
def api(params):
    u = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(dict(params, format="json"))
    for i in range(3):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30))
        except Exception as e: time.sleep(2 + 3 * i); err = e
    raise err
if sys.argv[1] in ("search", "search2"):
    man = {} if sys.argv[1] == "search" else json.load(open(f"{OUT}/manifest_search.json"))
    QQ = Q if sys.argv[1] == "search" else Q2
    for typ, qs in QQ.items():
        for q in qs:
            r = api(dict(action="query", generator="search", gsrsearch=f"{q} filetype:bitmap", gsrnamespace=6, gsrlimit=25 if sys.argv[1] == "search" else 30,
                         prop="imageinfo", iiprop="url|extmetadata|user|size|mime", iiurlwidth=640))
            if sys.argv[1] == "search2" and any(v.get("query") == q for v in man.values()): continue
            for p in (r.get("query", {}).get("pages", {}) or {}).values():
                ii = (p.get("imageinfo") or [{}])[0]; md = ii.get("extmetadata", {})
                lic = md.get("LicenseShortName", {}).get("value", "").strip()
                if ii.get("mime") not in ("image/jpeg", "image/png") or not OK.match(lic): continue
                t = p["title"]
                if t in man: continue
                man[t] = dict(title=t, type=typ, query=q, licence=lic, uploader=ii.get("user"), artist=re.sub("<[^>]+>", "", md.get("Artist", {}).get("value", ""))[:120],
                              page=ii.get("descriptionurl"), thumb=ii.get("thumburl"), w=ii.get("width"), h=ii.get("height"))
            print(typ, q, len(man), flush=True); time.sleep(0.3)
            json.dump(man, open(f"{OUT}/manifest_search.json", "w"), indent=0)
    json.dump(man, open(f"{OUT}/manifest_search.json", "w"), indent=0)
else:
    man = json.load(open(f"{OUT}/manifest_search.json")); t0 = time.time(); n = 0
    nxt = max([int(m["file"][2:6]) for m in man.values() if "file" in m] + [-1]) + 1
    for t, m in sorted(man.items()):
        if "file" not in m: m["file"] = f"cm{nxt:04d}.jpg"; nxt += 1
        fn = f"{OUT}/img/{m['file']}"
        if os.path.exists(fn) or not m.get("thumb"): continue
        try:
            data = urllib.request.urlopen(urllib.request.Request(m["thumb"], headers=UA), timeout=30).read(); open(fn, "wb").write(data); n += 1
        except Exception as e: m["dl_error"] = str(e)[:100]
        if time.time() - t0 > float(sys.argv[2] if len(sys.argv) > 2 else 100): break
        time.sleep(0.2)
    json.dump(man, open(f"{OUT}/manifest_search.json", "w"), indent=0); print("downloaded", n, "have", len(os.listdir(f"{OUT}/img")), "of", len(man))
