"""G9 Stage J: extra licensed phone-style TRAINING candidates for the weak classes (citrus, carrot). Never eval.
Sources (CC BY 4.0, checked via the Mendeley public API, 2026-10-15):
  citrus_tw  'A Dataset of Citrus Fruit Images' (Huang M.-L., Chen Y.-A.; NCUT Taiwan) Mendeley bxfgvsn9kw (dataset CC BY 4.0), Sony DSC-HX300 compact
             camera at 200-500 mm, orchard; ORIGINAL images only (the Augmentation folders are flips/rotations and are skipped)
  rejected:  Orange fruits Dataset 3x8jjd2f72 (CC BY 4.0, phone) ships as one 6 GB RAR inside the zip: not range-readable;
             Oranges in the field 93f32zgkxz is CC BY-NC 3.0 (NC: not allowed); Zenodo 18904638 is a Roboflow aggregate (mixed provenance)
  veg_in     'Vegetable Recognition Dataset' (Karwal, Som, Patel, Sisodia; MIET Meerut) Mendeley chv7dmvtfm, self-clicked in markets/fields/households
  veg_bd     'A Comprehensive Image Dataset of Vegetables Grown in Bangladesh' (Sumona et al.) Mendeley rtx9ngb68j, Poco F3 phone, street stalls
  commons_t  Wikimedia Commons per-file CC/PD, new citrus/carrot queries; uploaders already in J-dev/J-eval are dropped (source separation)
Files are read out of the public zips with HTTP range requests (only sampled members are downloaded); stored <= 640 px in /workspace/work/g9j/train.
Usage: j_collect.py list|mendeley|commons SECONDS"""
import io, os, re, sys, json, time, random, zipfile, hashlib, urllib.request, urllib.parse
sys.path.insert(0, "/workspace/work/nutrisole/ml/runs/G9/stageI/scripts")
from PIL import Image
UA = {"User-Agent": "NutriSoleResearch/1.0 (clydara1@gmail.com)"}; OUT = "/workspace/work/g9j/train"; TJ = f"{OUT}/train_cands.json"
T = json.load(open(TJ)) if os.path.exists(TJ) else {}
def save(): json.dump(T, open(TJ, "w"), indent=0)
def get(u, t=60, hdr=None):
    for i in range(3):
        try: return urllib.request.urlopen(urllib.request.Request(u, headers={**UA, **(hdr or {})}), timeout=t).read()
        except Exception:
            if i == 2: raise
            time.sleep(2 + 3 * i)
def put(key, raw):
    im = Image.open(io.BytesIO(raw)); im.draft("RGB", (1280, 1280)); im = im.convert("RGB"); w, h = im.size; s = min(1.0, 640 / max(w, h))
    if s < 1: im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
    im.save(f"{OUT}/img/{key}.jpg", quality=90); return [w, h]
class RZ(io.RawIOBase):
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
SRC = {"citrus_tw": ("bxfgvsn9kw", "Huang M.-L., Chen Y.-A. (A Dataset of Citrus Fruit Images)", "Sony DSC-HX300 compact (Taiwan orchards)"),
       "veg_in": ("chv7dmvtfm", "Karwal A., Som A., Patel A.S., Sisodia D. (Vegetable Recognition Dataset)", "self-clicked (markets/fields/households, India)"),
       "veg_bd": ("rtx9ngb68j", "Sumona R.B., Biswas J.P., Rahman M.A., Hasan M., Chaki S.", "Poco F3 phone (Dhaka markets)")}
# member filters: (regex on path, class label, n)
WANT = {"citrus_tw": [(r"/Original/", "citrus", 60)], "veg_in": [(r"carrot", "carrot", 60), (r"tomato", "tomato", 3)],
        "veg_bd": [(r"carrot", "carrot", 40), (r"(?<!\w)lime", "lemon_lime", 10), (r"capsicum", "capsicum", 10)]}
mode, lim = sys.argv[1], float(sys.argv[2]); t0 = time.time(); random.seed(10)
if mode in ("list", "mendeley"):
    for src, (did, auth, cap) in SRC.items():
        if time.time() - t0 > lim: break
        try: z = zipfile.ZipFile(io.BufferedReader(RZ(did), 1 << 20))
        except Exception as e: print(src, "zip fail", e); continue
        names = [i for i in z.namelist() if i.lower().endswith((".jpg", ".jpeg", ".png"))]
        if mode == "list":
            from collections import Counter
            print(src, len(names), Counter(os.path.dirname(x) for x in names).most_common(60)); continue
        for rx, lab, n in WANT[src]:
            pool = [x for x in names if re.search(rx, x, re.I) and not re.search(r"augment|aug_|rotat|flip|resized", x, re.I)]
            if lab == "citrus": pool = [x for x in pool if not re.search(r"canker|melanose|spot|rot|scab|greening|disease", x, re.I)] or pool
            random.shuffle(pool); got = sum(1 for v in T.values() if v["source"] == src and v["label"] == lab)
            for nm in pool:
                if got >= n or time.time() - t0 > lim: break
                k = "t" + src[:3] + hashlib.sha1(nm.encode()).hexdigest()[:8]
                if k in T: continue
                try: sz = put(k, z.read(nm))
                except Exception: continue
                T[k] = dict(source=src, label=lab, group="supported", src_path=nm, size=sz, licence="CC BY 4.0", author=auth, uploader=f"Mendeley {did}",
                            page=f"https://data.mendeley.com/datasets/{did}/1", camera=cap, licence_url="https://creativecommons.org/licenses/by/4.0/"); got += 1
            save(); print(src, lab, got, "pool", len(pool))
elif mode == "commons":
    # same search/licence filter as Stage I i_collect.csearch (copied: the Stage I module runs its CLI on import)
    BAD = re.compile(r"logo|svg|score|film|map|stamp|diagram|book|icon|drawing|painting|illustration|unsplash|pixabay|pexels|mixkit", re.I)
    def csearch(q, n=40):
        u = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(dict(action="query", generator="search", gsrsearch=f"{q} filetype:bitmap", gsrnamespace=6,
            gsrlimit=n, prop="imageinfo", iiprop="url|size|mime|extmetadata|user|metadata", iiurlwidth=640, format="json"))
        try: d = json.loads(get(u))
        except Exception: return []
        out = []
        for pg in (d.get("query", {}).get("pages", {}) or {}).values():
            t = pg["title"]; ii = (pg.get("imageinfo") or [{}])[0]; em = ii.get("extmetadata", {})
            if BAD.search(t) or ii.get("mime") not in ("image/jpeg", "image/png") or min(ii.get("width", 0), ii.get("height", 0)) < 400: continue
            lic = em.get("LicenseShortName", {}).get("value", ""); cred = re.sub("<[^>]+>", "", em.get("Credit", {}).get("value", ""))
            if not re.search(r"CC|Public domain|PD|CC0", lic, re.I) or re.search(r"NC|ND", lic) or BAD.search(cred): continue
            md = {m["name"]: m["value"] for m in (ii.get("metadata") or []) if isinstance(m, dict) and m.get("name") in ("Make", "Model")}
            out.append(dict(title=t, page="https://commons.wikimedia.org/wiki/" + urllib.parse.quote(t.replace(" ", "_")), licence=lic, uploader=ii.get("user"),
                            author=re.sub("<[^>]+>", "", em.get("Artist", {}).get("value", ""))[:120], credit=cred[:150], url=ii.get("thumburl"), query=q,
                            camera=" ".join(str(v) for v in md.values())[:60]))
        return out
    Q = {"citrus": ["orange fruit kitchen", "oranges on plate", "mandarin fruit", "clementines", "kinnow", "satsuma mandarin fruit", "tangerine fruit",
                    "navel orange", "oranges market stall", "orange fruit hand", "malta orange fruit", "peeled mandarin"],
         "carrot": ["carrots kitchen", "fresh carrots", "carrot vegetable", "carrots bunch", "carrot root", "carrots market stall", "carrots table",
                    "orange carrots", "carrot harvest", "carrots basket", "carrot peeled", "baby carrots"]}
    S = json.load(open("/workspace/work/nutrisole/ml/runs/G9/stageJ/out/j_partitions.json"))
    blocked_up = set(S["uploaders_dev_eval"]); C0 = json.load(open("/workspace/work/g9i/cands/cands.json"))
    prior = {v.get("title") for v in C0.values()} | {v.get("title") for v in T.values()}
    for p in ("/workspace/work/g9h/hset/cands.json", "/workspace/work/g9g/cu/cands.json"):
        try: d = json.load(open(p)); prior |= {v.get("title") for v in (d.values() if isinstance(d, dict) else d)}
        except Exception: pass
    from concurrent.futures import ThreadPoolExecutor
    if not any(v["source"] == "commons_t" for v in T.values()):
        jobs = [(q, c) for c, qs in Q.items() for q in qs]
        with ThreadPoolExecutor(4) as ex: res = list(ex.map(lambda j: (j, csearch(j[0])), jobs))
        n = 0; skipped = 0
        for (q, lab), rs in res:
            for r in rs[:12]:
                if r["title"] in prior: continue
                if r["uploader"] in blocked_up: skipped += 1; continue
                prior.add(r["title"]); T[f"tcm{n:04d}"] = dict(source="commons_t", label=lab, group="supported", **r); n += 1
        save(); print("commons_t meta", n, "skipped (uploader in dev/eval):", skipped)
    todo = [k for k, v in T.items() if v["source"] == "commons_t" and "size" not in v and not v.get("fail")]
    def dl(k):
        try: T[k]["size"] = put(k, get(T[k]["url"])); time.sleep(0.3)
        except Exception as e: T[k]["fail"] = str(e)[:80]
    with ThreadPoolExecutor(3) as ex:
        for i in range(0, len(todo), 12):
            if time.time() - t0 > lim: break
            list(ex.map(dl, todo[i:i + 12]))
    save(); print("commons_t downloaded", sum(1 for v in T.values() if v["source"] == "commons_t" and "size" in v), "of", sum(1 for v in T.values() if v["source"] == "commons_t"))
