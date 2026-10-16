"""Stage H: collect independent licensed close-up candidates from Wikimedia Commons (per-file CC / PD; never Pexels/Pixabay/Mixkit).
Groups: 12 supported classes (whole items), unsupported produce (unknown), printed/drawn/plastic fruit (unknown), cut/sliced/peeled
items (unknown). Output /workspace/work/g9h/hset/cands.json (title, page, licence, user, artist, query, label, group) + 512-px thumbs.
Usage: h_collect.py meta | dl SECONDS"""
import json, os, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
UA = {"User-Agent": "NutriSoleResearch/1.0 (clydara1@gmail.com)"}
OUT = "/workspace/work/g9h/hset"; os.makedirs(f"{OUT}/img", exist_ok=True)
SUP = {
 "banana": ["banana fruit", "bananas bunch", "Musa banana yellow", "ripe banana", "green banana"],
 "apple": ["apple fruit", "red apple", "green apple fruit", "Malus domestica fruit", "apples close-up"],
 "mango": ["mango fruit", "Mangifera indica fruit", "ripe mango", "mangoes market", "green mango fruit"],
 "citrus": ["orange fruit", "Citrus sinensis fruit", "mandarin orange fruit", "kinnow", "tangerine fruit"],
 "guava": ["guava fruit", "Psidium guajava fruit", "guavas", "pink guava fruit", "guava green fruit"],
 "pomegranate": ["pomegranate fruit", "Punica granatum fruit", "pomegranates", "pomegranate whole"],
 "lemon_lime": ["lemon fruit", "lime fruit", "Citrus limon fruit", "key lime", "lemons"],
 "tomato": ["tomato fruit", "tomatoes", "Solanum lycopersicum fruit", "red tomato", "cherry tomato"],
 "potato": ["potato tuber", "potatoes", "Solanum tuberosum tuber", "raw potato", "red potatoes"],
 "cucumber": ["cucumber", "cucumbers", "Cucumis sativus fruit", "cucumber vegetable"],
 "carrot": ["carrot", "carrots", "Daucus carota root", "carrot vegetable", "orange carrots"],
 "capsicum": ["bell pepper", "red bell pepper", "green bell pepper", "yellow bell pepper", "Capsicum annuum bell pepper"],
}
UNS = ["persimmon fruit", "Diospyros kaki fruit", "plum fruit", "Prunus domestica fruit", "peach fruit", "Prunus persica fruit", "papaya fruit",
       "Carica papaya fruit", "kiwifruit", "kiwi fruit", "avocado fruit", "Persea americana fruit", "pear fruit", "apricot fruit", "lychee fruit",
       "onion bulb", "red onion", "eggplant", "aubergine", "nectarine", "quince fruit", "fig fruit", "passion fruit", "dragon fruit",
       "radish", "sweet potato", "zucchini", "chili peppers", "garlic bulb", "ginger root", "beetroot", "coconut", "turnip", "jujube fruit",
       "loquat fruit", "apple guava", "sapodilla fruit", "custard apple", "star fruit", "grapefruit pomelo"]
PRINT = ["fruit sticker label", "plastic fruit", "artificial fruit", "fruit still life painting", "fruit illustration", "fruit poster",
         "fruit print advertisement", "fruit emoji", "fruit toy", "fruit magnet", "fake fruit decoration", "fruit drawing"]
CUT = ["apple cut in half", "sliced apple", "orange cut in half", "sliced orange", "mango cut", "mango slices", "peeled banana",
       "banana slices", "sliced cucumber", "sliced tomato", "tomato cut in half", "pomegranate opened seeds", "halved lemon", "lemon slices",
       "sliced carrot", "grated carrot", "cut potato", "french fries raw potato", "guava cut", "bell pepper sliced", "cut guava", "mashed potato"]
BAD = re.compile(r"logo|svg|score|film|map|stamp|diagram|book|icon", re.I)
def api(p):
    u = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({**p, "format": "json"})
    for i in range(3):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30))
        except Exception: time.sleep(2 + 3 * i)
    return {}
def search(q, n):
    d = api(dict(action="query", generator="search", gsrsearch=f"{q} filetype:bitmap", gsrnamespace=6, gsrlimit=n, prop="imageinfo",
                 iiprop="url|size|mime|extmetadata|user", iiurlwidth=512))
    out = []
    for pg in (d.get("query", {}).get("pages", {}) or {}).values():
        t = pg["title"]; ii = (pg.get("imageinfo") or [{}])[0]
        if BAD.search(t) or ii.get("mime") not in ("image/jpeg", "image/png") or min(ii.get("width", 0), ii.get("height", 0)) < 400: continue
        em = ii.get("extmetadata", {}); lic = em.get("LicenseShortName", {}).get("value", "")
        if not re.search(r"CC|Public domain|PD|CC0", lic, re.I) or re.search(r"NC|ND", lic): continue
        out.append(dict(title=t, page="https://commons.wikimedia.org/wiki/" + urllib.parse.quote(t.replace(" ", "_")), licence=lic, user=ii.get("user"),
                        artist=re.sub("<[^>]+>", "", em.get("Artist", {}).get("value", ""))[:120], thumb=ii.get("thumburl"), query=q))
    return out
if sys.argv[1] == "meta":
    C = {}; seen = set()
    jobs = [(q, c, "supported", 40) for c, qs in SUP.items() for q in qs] + [(q, "unknown", "unsupported", 30) for q in UNS] + \
           [(q, "unknown", "printed", 30) for q in PRINT] + [(q, "unknown", "cut", 30) for q in CUT]
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(lambda j: (j, search(j[0], j[3])), jobs))
    for (q, lab, grp, _), rs in res:
        for r in rs:
            if r["title"] in seen: continue
            seen.add(r["title"]); k = f"h{len(C):05d}"; C[k] = {**r, "label": lab, "group": grp}
    json.dump(C, open(f"{OUT}/cands.json", "w"), indent=0)
    import collections; print(len(C), collections.Counter((v["group"], v["label"]) for v in C.values()))
else:
    # sequential, rate-limited (Commons returns 429 to parallel bots): round-robin over (group, label) with caps, backoff on 429
    import collections, random, numpy as np, cv2
    C = json.load(open(f"{OUT}/cands.json")); lim = float(sys.argv[2]); t0 = time.time()
    CAP = dict(supported=50, unsupported=200, printed=80, cut=130)
    by = collections.defaultdict(list)
    for k, c in C.items(): by[(c["group"], c["label"])].append(k)
    for v in by.values(): random.Random(0).shuffle(v)
    have = lambda k: os.path.exists(f"{OUT}/img/{k}.jpg")
    order = []; q = {g: sorted(v, key=lambda k: not have(k))[: CAP[g[0]]] for g, v in by.items()}
    while any(q.values()):
        for g in list(q):
            if q[g]: order.append(q[g].pop(0))
    json.dump(order, open(f"{OUT}/selected.json", "w"))
    n = 0; wait = 1.0
    for k in order:
        if time.time() - t0 > lim: break
        if have(k) or os.path.exists(f"{OUT}/img/{k}.fail"): continue
        u = re.sub(r"/\d+px-", "/500px-", C[k]["thumb"])
        try:
            b = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read()
            im = cv2.imdecode(np.frombuffer(b, np.uint8), cv2.IMREAD_COLOR)
            if im is not None: cv2.imwrite(f"{OUT}/img/{k}.jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 92]); n += 1
            wait = max(1.0, wait * 0.9)
        except urllib.error.HTTPError as e:
            if e.code == 429: wait = min(30, wait * 2)
            elif e.code in (404, 400): open(f"{OUT}/img/{k}.fail", "w").write(str(e.code))
        except Exception: pass
        time.sleep(wait)
    left = sum(1 for k in order if not have(k) and not os.path.exists(f"{OUT}/img/{k}.fail"))
    print("downloaded", n, "remaining", left, "wait", round(wait, 1), flush=True)
