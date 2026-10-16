"""Stage G: collect candidate close-up produce photos from Wikimedia Commons (licensed, attributable).
Output: /workspace/work/g9g/cu/cands.json + 1024-px thumbnails in /workspace/work/g9g/cu/img/. Triage is visual (contact sheets)."""
import json, os, re, sys, time, urllib.parse, urllib.request
UA = {"User-Agent": "NutriSoleResearch/1.0 (clydara1@gmail.com)"}
OUT = "/workspace/work/g9g/cu"; os.makedirs(f"{OUT}/img", exist_ok=True)
Q = [  # (query, intended class, intended condition)
    ("rotting apple", "apple", "rotten"), ("rotten apple mould", "apple", "rotten"), ("apple fruit isolated", "apple", "fresh"), ("red apple close-up", "apple", "fresh"),
    ("rotting banana", "banana", "rotten"), ("overripe banana black", "banana", "rotten"), ("banana fruit isolated", "banana", "fresh"), ("yellow bananas close-up", "banana", "fresh"),
    ("rotting tomato", "tomato", "rotten"), ("mouldy tomato", "tomato", "rotten"), ("tomato fruit isolated", "tomato", "fresh"), ("red tomato close-up", "tomato", "fresh"),
    ("mouldy orange penicillium", "citrus", "rotten"), ("rotting orange fruit", "citrus", "rotten"), ("orange fruit isolated", "citrus", "fresh"), ("mandarin fruit close-up", "citrus", "fresh"),
    ("rotting carrot", "carrot", "rotten"), ("carrot isolated white background", "carrot", "fresh"), ("carrots close-up", "carrot", "fresh"),
    ("mango fruit isolated", "mango", "fresh"), ("guava fruit", "guava", "fresh"), ("pomegranate fruit isolated", "pomegranate", "fresh"),
    ("lemon fruit isolated", "lemon_lime", "fresh"), ("potato tuber isolated", "potato", "fresh"), ("cucumber isolated", "cucumber", "fresh"), ("green bell pepper isolated", "capsicum", "fresh"),
    ("rotten potato", "potato", "rotten"), ("rotting mango", "mango", "rotten"), ("mouldy lemon", "lemon_lime", "rotten"), ("rotten cucumber", "cucumber", "rotten"),
]
Q2 = [("Monilinia fructigena apple", "apple", "rotten"), ("Penicillium digitatum orange", "citrus", "rotten"), ("Penicillium italicum", "citrus", "rotten"), ("Botrytis cinerea tomato fruit", "tomato", "rotten"), ("tomato late blight fruit", "tomato", "rotten"), ("anthracnose banana", "banana", "rotten"), ("rotten banana", "banana", "rotten"), ("mouldy apple", "apple", "rotten"), ("anthracnose mango fruit", "mango", "rotten"), ("carrot soft rot", "carrot", "rotten"), ("bitter rot apple", "apple", "rotten"), ("blossom end rot tomato", "tomato", "rotten")]
BAD = re.compile(r"logo|svg|score|film|panel|show|rating|poster|map|stamp|drawing|painting|illustration|icon|diagram|book|plate \d|botanical", re.I)
def api(p):
    u = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({**p, "format": "json"})
    for i in range(3):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30))
        except Exception as e: time.sleep(2 + 3 * i)
    return {}
cands = json.load(open(f"{OUT}/cands.json")) if os.path.exists(f"{OUT}/cands.json") else {}
for q, cl, cond in (Q2 if len(sys.argv) > 1 else ([] if os.path.exists(f"{OUT}/cands.json") else Q)):
    d = api(dict(action="query", generator="search", gsrsearch=f"{q} filetype:bitmap", gsrnamespace=6, gsrlimit=12, prop="imageinfo",
                 iiprop="url|size|mime|extmetadata|user", iiurlwidth=1024))
    for pid, pg in (d.get("query", {}).get("pages", {}) or {}).items():
        t = pg["title"]; ii = (pg.get("imageinfo") or [{}])[0]
        if BAD.search(t) or ii.get("mime") != "image/jpeg" or min(ii.get("width", 0), ii.get("height", 0)) < 600: continue
        em = ii.get("extmetadata", {}); lic = em.get("LicenseShortName", {}).get("value", "")
        if not re.search(r"CC|Public domain|PD|CC0", lic, re.I): continue
        if t in {c["title"] for c in cands.values()}: continue
        k = f"cu{len(cands):04d}"
        cands[k] = dict(title=t, page="https://commons.wikimedia.org/wiki/" + urllib.parse.quote(t.replace(" ", "_")), licence=lic,
                        user=ii.get("user"), artist=re.sub("<[^>]+>", "", em.get("Artist", {}).get("value", ""))[:120], query=q, intended_class=cl,
                        intended_condition=cond, thumb=ii.get("thumburl"), orig_w=ii.get("width"), orig_h=ii.get("height"))
    time.sleep(0.5)
json.dump(cands, open(f"{OUT}/cands.json", "w"), indent=1); print(len(cands))
n = 0
for k, c in cands.items():
    p = f"{OUT}/img/{k}.jpg"
    if os.path.exists(p): continue
    try:
        open(p, "wb").write(urllib.request.urlopen(urllib.request.Request(c["thumb"], headers=UA), timeout=40).read()); n += 1; time.sleep(0.3)
    except Exception as e: print("dl fail", k, e)
print("downloaded", n)
