"""G9 Stage I data plan (I2): source-separated close-up CANDIDATES for apple, banana, citrus/orange, tomato, carrot + negatives.
Licensed sources only (never Pexels / Pixabay / Mixkit); nothing requested from the user. Every item records source, licence, uploader/
contributor, page and the intended (source-provided) label. Labels here are SOURCE METADATA, not human labels: exploratory only.
Sources:
  commons   Wikimedia Commons per-file CC/PD; new close-up / in-hand / bagged / packaged / printed / overlap queries; EXIF camera model kept
  fruitnet  FruitNet (Meshram & Patil 2021, Mendeley 10.17632/b6fftwbr2v, CC BY 4.0; phone captures) via the HF mirror
            Project-AgML/FruitNet_quality_classification (cc-by-4.0) rows API: Apple / Banana / Orange (Good + Bad), Lime/Guava/Pomegranate as
            other-class items
  carrot_m  'Good and bad classification of Fresh CARROT' (Mendeley ww83r63rtr v1, CC BY 4.0; Realme 11x phone) via remote-zip range reads
  tomato_m  'TOMATO' (Mendeley hfyth5t3gg v1, CC BY 4.0; Redmi 9 Power phone) via remote-zip range reads
Output /workspace/work/g9i/cands/{cands.json,img/*.jpg (<=640 px)}. Usage: i_collect.py commons|fruitnet|mendeley SECONDS"""
import hashlib, json, os, re, sys, time, random, io, zipfile, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
UA = {"User-Agent": "NutriSoleResearch/1.0 (clydara1@gmail.com)"}; OUT = "/workspace/work/g9i/cands"; CJ = f"{OUT}/cands.json"
C = json.load(open(CJ)) if os.path.exists(CJ) else {}
def save(): json.dump(C, open(CJ, "w"), indent=0)
def get(u, t=40, hdr=None):
    for i in range(3):
        try: return urllib.request.urlopen(urllib.request.Request(u, headers={**UA, **(hdr or {})}), timeout=t).read()
        except Exception as e:
            if i == 2: raise
            time.sleep(2 + 3 * i)
def put(key, raw):
    im = Image.open(io.BytesIO(raw)).convert("RGB"); w, h = im.size; s = min(1.0, 640 / max(w, h))
    if s < 1: im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
    im.save(f"{OUT}/img/{key}.jpg", quality=90); return [w, h]
random.seed(9)
SUPQ = {"apple": ["apple in hand", "apple on table close-up", "apple fruit close up photo", "red apple kitchen", "bruised apple", "apple with blemish"],
        "banana": ["banana in hand", "single banana on table", "banana close up", "overripe banana spots", "banana bunch kitchen counter", "green banana close up"],
        "citrus": ["orange fruit in hand", "orange fruit on table", "mandarin orange close up", "kinnow fruit", "tangerine on table", "orange fruit blemish"],
        "tomato": ["tomato in hand", "tomato on table close up", "tomato on cutting board", "ripe tomato close-up", "green tomato fruit close up", "cracked tomato fruit"],
        "carrot": ["carrot in hand", "carrots on table", "carrot close up", "carrot on cutting board", "single carrot vegetable", "carrots market stall"]}
NEGQ = {"unsupported": ["persimmon on table", "peach fruit in hand", "plum fruit close up", "nectarine fruit", "kiwifruit close up", "papaya fruit table",
                        "onion on table", "beetroot close up", "sweet potato tuber", "radish vegetable close up", "apricot fruit close up", "grapefruit on table"],
        "packaging": ["fruit in plastic bag", "apples in plastic bag", "bananas plastic wrap supermarket", "tomatoes plastic packaging", "carrots bag supermarket",
                      "oranges net bag", "packaged fruit tray supermarket"],
        "printed": ["fruit photo printed poster", "fruit print magazine", "fruit picture on screen", "plastic fruit display", "artificial apple", "fake banana toy"],
        "occluded": ["hand holding fruit partially", "fruit bowl overlapping fruits", "apples pile close up", "fruit partly covered cloth", "half hidden orange fruit"]}
BAD = re.compile(r"logo|svg|score|film|map|stamp|diagram|book|icon|drawing|painting|illustration", re.I)
def csearch(q, n=30):
    u = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(dict(action="query", generator="search", gsrsearch=f"{q} filetype:bitmap", gsrnamespace=6,
        gsrlimit=n, prop="imageinfo", iiprop="url|size|mime|extmetadata|user|metadata", iiurlwidth=640, format="json"))
    try: d = json.loads(get(u))
    except Exception: return []
    out = []
    for pg in (d.get("query", {}).get("pages", {}) or {}).values():
        t = pg["title"]; ii = (pg.get("imageinfo") or [{}])[0]
        if (BAD.search(t) and "printed" not in q and "poster" not in q) or ii.get("mime") not in ("image/jpeg", "image/png") or min(ii.get("width", 0), ii.get("height", 0)) < 400: continue
        em = ii.get("extmetadata", {}); lic = em.get("LicenseShortName", {}).get("value", "")
        if not re.search(r"CC|Public domain|PD|CC0", lic, re.I) or re.search(r"NC|ND", lic): continue
        md = {m["name"]: m["value"] for m in (ii.get("metadata") or []) if isinstance(m, dict) and m.get("name") in ("Make", "Model")}
        out.append(dict(title=t, page="https://commons.wikimedia.org/wiki/" + urllib.parse.quote(t.replace(" ", "_")), licence=lic, uploader=ii.get("user"),
                        artist=re.sub("<[^>]+>", "", em.get("Artist", {}).get("value", ""))[:120], url=ii.get("thumburl"), query=q, camera=" ".join(str(v) for v in md.values())[:60]))
    return out
def prior_titles():
    s = set()
    for p in ("/workspace/work/g9h/hset/cands.json", "/workspace/work/g9g/cu/cands.json"):
        try:
            d = json.load(open(p)); s |= {v.get("title") for v in (d.values() if isinstance(d, dict) else d)}
        except Exception: pass
    return s
mode, lim = sys.argv[1], float(sys.argv[2]); t0 = time.time()
if mode == "commons":
    if not any(v["source"] == "commons" for v in C.values()):
        prior = prior_titles(); seen = set()
        jobs = [(q, c, "supported") for c, qs in SUPQ.items() for q in qs] + [(q, "unknown", g) for g, qs in NEGQ.items() for q in qs]
        with ThreadPoolExecutor(6) as ex: res = list(ex.map(lambda j: (j, csearch(j[0])), jobs))
        n = 0
        for (q, lab, grp), rs in res:
            for r in rs[:14]:
                if r["title"] in seen or r["title"] in prior: continue
                seen.add(r["title"]); C[f"c{n:04d}"] = dict(source="commons", label=lab, group=grp, **r); n += 1
        save(); print("commons meta", n, "new (prior titles excluded:", len(prior), ")")
    todo = [k for k, v in C.items() if v["source"] == "commons" and "size" not in v and not v.get("fail")]
    def dl(k):
        try: C[k]["size"] = put(k, get(C[k]["url"])); time.sleep(0.3)
        except Exception as e: C[k]["fail"] = str(e)[:80]
    with ThreadPoolExecutor(3) as ex:
        for i in range(0, len(todo), 12):
            if time.time() - t0 > lim: break
            list(ex.map(dl, todo[i:i + 12]))
    save()
elif mode == "fruitnet":
    base = "https://datasets-server.huggingface.co/rows?dataset=Project-AgML/FruitNet_quality_classification&config=default&split=train"
    want = {"Apple": ("apple", 40), "Banana": ("banana", 40), "Orange": ("citrus", 40), "Lime": ("lemon_lime", 8), "Guava": ("guava", 8), "Pomegranate": ("pomegranate", 8)}
    have = {} 
    for v in C.values():
        if v["source"] == "fruitnet": have[v["src_class"]] = have.get(v["src_class"], 0) + 1
    offs = random.sample(range(0, 19500, 100), 30)
    for off in offs:
        if time.time() - t0 > lim or all(have.get(c, 0) >= n for c, (_, n) in want.items()): break
        try: d = json.loads(get(f"{base}&offset={off}&length=100", 60))
        except Exception: continue
        crops = d["features"][2]["type"]["names"]; quals = d["features"][1]["type"]["names"]
        rows = d["rows"]; random.shuffle(rows)
        for r in rows[:25]:
            c = crops[r["row"]["crop"]]
            if c not in want or have.get(c, 0) >= want[c][1]: continue
            k = f"fn{r['row_idx']:05d}"
            if k in C: continue
            try: sz = put(k, get(r["row"]["image"]["src"]))
            except Exception: continue
            C[k] = dict(source="fruitnet", label=want[c][0], group="supported", src_class=c, src_quality=quals[r["row"]["label"]], size=sz, licence="CC BY 4.0",
                        uploader="FruitNet (Meshram & Patil)", page="https://data.mendeley.com/datasets/b6fftwbr2v/1", mirror="https://huggingface.co/datasets/Project-AgML/FruitNet_quality_classification", row_idx=r["row_idx"])
            have[c] = have.get(c, 0) + 1
        save()
    print("fruitnet", have)
elif mode == "mendeley":
    class RZ(io.RawIOBase):  # remote zip over HTTP range requests (presigned URL re-resolved on demand)
        def __init__(s, did): s.did = did; s.pos = 0; s._url(); s.size = int(s.cr.split("/")[-1])
        def _url(s):
            r = urllib.request.urlopen(urllib.request.Request(f"https://data.mendeley.com/public-api/zip/{s.did}/download/1", headers={**UA, "Range": "bytes=0-0"}), timeout=40)
            s.url = r.geturl(); s.cr = r.headers.get("Content-Range"); s.t = time.time()
        def seekable(s): return True
        def readable(s): return True
        def tell(s): return s.pos
        def seek(s, o, wh=0): s.pos = o if wh == 0 else s.pos + o if wh == 1 else s.size + o; return s.pos
        def readinto(s, b):
            if s.pos >= s.size: return 0
            if time.time() - s.t > 200: s._url()
            n = min(len(b), s.size - s.pos); d = get(s.url, 60, {"Range": f"bytes={s.pos}-{s.pos + n - 1}"}); b[:len(d)] = d; s.pos += len(d); return len(d)
    for did, src, lab, n, lic, ph in (("ww83r63rtr", "carrot_m", "carrot", 50, "CC BY 4.0", "Realme 11x"), ("hfyth5t3gg", "tomato_m", "tomato", 50, "CC BY 4.0", "Redmi 9 Power")):
        if sum(1 for v in C.values() if v["source"] == src) >= n or time.time() - t0 > lim: continue
        z = zipfile.ZipFile(io.BufferedReader(RZ(did), 1 << 20)); names = [i for i in z.namelist() if i.lower().endswith((".jpg", ".jpeg", ".png"))]
        print(src, len(names), "files; folders:", sorted({os.path.dirname(x) for x in names})[:10])
        random.shuffle(names); got = 0
        for nm in names:
            if got >= n or time.time() - t0 > lim: break
            k = src[:2] + hashlib.sha1(nm.encode()).hexdigest()[:8]
            if k in C: got += 1; continue
            try: sz = put(k, z.read(nm))
            except Exception: continue
            C[k] = dict(source=src, label=lab, group="supported", src_path=nm, src_quality=os.path.basename(os.path.dirname(nm)), size=sz, licence=lic, uploader=f"Mendeley {did}",
                        page=f"https://data.mendeley.com/datasets/{did}/1", camera=ph); got += 1
        save()
print(mode, "total", len(C), {s: sum(1 for v in C.values() if v["source"] == s and "size" in v) for s in ("commons", "fruitnet", "carrot_m", "tomato_m")}, round(time.time() - t0), "s")
