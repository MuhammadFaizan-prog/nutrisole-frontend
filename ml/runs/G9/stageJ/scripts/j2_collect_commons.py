"""G9 Stage J2: Wikimedia Commons per-file CC/PD candidates.
  eval2 (J-EVAL ONLY, pilot2): produce in bags/packaging, partly hidden produce, and a few extra apple/citrus. Uploader must hash to the frozen
         eval buckets (sha1 % 10 in 4-9) and must not be a J-train/J-dev person (uploader or artist).
  train2 (J-TRAIN ONLY): apple (train-side uploaders): uploader/artist must not be a J-dev/J-eval/eval2 person.
Banned origins (Pexels, Pixabay, Mixkit, Unsplash) rejected on title, credit, artist and description. Stored <= 640 px."""
import io, os, re, sys, json, time, hashlib, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
UA = {"User-Agent": "NutriSoleResearch/1.0 (https://github.com/MuhammadFaizan-prog/nutrisole-frontend; clydara1@gmail.com)"}
W = "/workspace/work/g9j2"; ROOT = "/workspace/work/nutrisole/ml/runs/G9/stageJ/out"
BAD = re.compile(r"logo|svg|score|film|map|stamp|diagram|book|icon|drawing|painting|illustration|unsplash|pixabay|pexels|mixkit|clipart|cartoon|poster", re.I)
BANNED = re.compile(r"unsplash|pixabay|pexels|mixkit", re.I)
def get(u, t=60):
    for i in range(3):
        try: return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t).read()
        except Exception:
            if i == 2: raise
            time.sleep(3 + 5 * i)
def bucket(s): return int(hashlib.sha1((s or "").encode()).hexdigest(), 16) % 10
def norm(a): return re.sub(r"\s+", " ", (a or "").lower()).strip()
def csearch(q, n=40):
    u = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(dict(action="query", generator="search", gsrsearch=f"{q} filetype:bitmap", gsrnamespace=6,
        gsrlimit=n, prop="imageinfo", iiprop="url|size|mime|extmetadata|user", iiurlwidth=640, format="json"))
    try: d = json.loads(get(u))
    except Exception as e: return []
    out = []
    for pg in (d.get("query", {}).get("pages", {}) or {}).values():
        t = pg["title"]; ii = (pg.get("imageinfo") or [{}])[0]; em = ii.get("extmetadata", {})
        if BAD.search(t) or ii.get("mime") not in ("image/jpeg", "image/png") or min(ii.get("width", 0), ii.get("height", 0)) < 400: continue
        lic = em.get("LicenseShortName", {}).get("value", ""); cred = re.sub("<[^>]+>", "", em.get("Credit", {}).get("value", ""))
        art = re.sub("<[^>]+>", "", em.get("Artist", {}).get("value", ""))[:120]; desc = re.sub("<[^>]+>", "", em.get("ImageDescription", {}).get("value", ""))[:400]
        if not re.search(r"CC|Public domain|PD|CC0", lic, re.I) or re.search(r"\bNC\b|\bND\b|-nc|-nd", lic, re.I) or em.get("NonFree", {}).get("value") == "true": continue
        if BANNED.search(cred + " " + art + " " + desc): continue
        out.append(dict(title=t, page="https://commons.wikimedia.org/wiki/" + urllib.parse.quote(t.replace(" ", "_")), licence=lic, uploader=ii.get("user"), author=art,
                        credit=cred[:150], url=ii.get("thumburl"), original_url=ii.get("url"), licence_url=em.get("LicenseUrl", {}).get("value", ""), query=q))
    return out
Q_EVAL = {"packaging": ["fruit in plastic bag", "apples in plastic bag", "oranges in net bag", "mandarins net bag", "bananas plastic wrap supermarket", "tomatoes packaged supermarket",
                        "carrots plastic bag", "tomatoes punnet", "packaged fruit supermarket shelf", "apples tray cling film", "bagged carrots", "citrus mesh bag", "fruit packaging plastic", "bag of oranges", "bag of apples", "bag of carrots", "tomatoes in plastic",
                        "bananas in bag", "clementines bag", "oranges plastic bag", "apples packaged", "carrots packaged", "tomatoes plastic container", "cherry tomatoes package",
                        "fruit net bag market", "shopping bag fruit vegetables", "satsumas bag", "lemons net bag"],
          "occluded": ["hand holding apple", "hand holding orange fruit", "hand holding tomato", "hand holding banana", "apple partially hidden", "fruit among leaves",
                       "carrot pulled from soil", "tomato among leaves plant", "oranges on tree leaves", "fruit behind glass", "child eating apple", "person holding carrots"],
          "apple": ["apple fruit table", "red apples basket", "apples market stall"], "citrus": ["oranges fruit bowl", "mandarin oranges table", "oranges market stall"]}
Q_TRAIN = {"apple": ["apple fruit", "red apple", "green apple", "apples on table", "apples basket", "apples kitchen", "apples crate", "apple in hand", "fuji apple",
                     "gala apple", "granny smith apple", "apples wooden table", "apple harvest", "golden delicious apple", "apples supermarket", "apple on plate"]}
if __name__ == "__main__":
    mode = sys.argv[1]
    P = json.load(open(f"{ROOT}/j_partitions.json"))["items"]
    def pkeys(up, art):
        ks = set()
        if up: ks.add("u:" + up.lower())
        a = norm(art)
        if a and not re.search(r"^(unknown|anonymous|unbekannt|author unknown)|unknown author", a) and len(a) > 2: ks.add("a:" + a[:80])
        return ks
    persons = {"J-train": set(), "J-dev": set(), "J-eval": set()}
    for v in P.values():
        if v["source"] in ("commons", "commons_t"): persons[v["split"]] |= pkeys(v["uploader"], v["artist"])
    prior = set()
    for p in ("/workspace/work/g9j2/eval2/eval2_cands.json", "/workspace/work/g9j2/train2/train2_cands_commons.json"):
        try: prior |= {v.get("title") for v in json.load(open(p)).values()}
        except Exception: pass
    for p in ("/workspace/work/g9i/cands/cands.json", "/workspace/work/g9j/train/train_cands.json", "/workspace/work/g9h/hset/cands.json", "/workspace/work/g9g/cu/cands.json"):
        try: d = json.load(open(p)); prior |= {v.get("title") for v in (d.values() if isinstance(d, dict) else d)}
        except Exception: pass
    EJ = f"{W}/eval2/eval2_cands.json"; TJ = f"{W}/train2/train2_cands_commons.json"
    E = json.load(open(EJ)) if os.path.exists(EJ) else {}; T = json.load(open(TJ)) if os.path.exists(TJ) else {}
    if mode == "meta":
        jobs = [("eval", c, q) for c, qs in Q_EVAL.items() for q in qs if (len(sys.argv) < 3 or c == sys.argv[2])] + ([("train", c, q) for c, qs in Q_TRAIN.items() for q in qs] if len(sys.argv) < 3 else [])
        with ThreadPoolExecutor(3) as ex: res = list(ex.map(lambda j: (j, csearch(j[2])), jobs))
        st = {"eval_kept": 0, "eval_skip_bucket": 0, "eval_skip_person": 0, "train_kept": 0, "train_skip_person": 0, "dup_title": 0}
        e_persons = set()
        for (side, c, q), rs in res:                       # eval first
            if side != "eval": continue
            for r in rs[:14]:
                if r["title"] in prior: st["dup_title"] += 1; continue
                pk = pkeys(r["uploader"], r["author"])
                if pk & (persons["J-train"] | persons["J-dev"]): st["eval_skip_person"] += 1; continue
                if bucket(r["uploader"] or r["author"]) not in range(4, 10): st["eval_skip_bucket"] += 1; continue
                prior.add(r["title"]); e_persons |= pk; E["e2c" + hashlib.sha1(r["title"].encode()).hexdigest()[:8]] = dict(source="commons_e2", label=c, group=("packaging" if c == "packaging" else "occluded" if c == "occluded" else "supported"), **r); st["eval_kept"] += 1
        for (side, c, q), rs in res:
            if side != "train": continue
            for r in rs[:16]:
                if r["title"] in prior: st["dup_title"] += 1; continue
                pk = pkeys(r["uploader"], r["author"])
                if pk & (persons["J-dev"] | persons["J-eval"] | e_persons): st["train_skip_person"] += 1; continue
                prior.add(r["title"]); T["t2c" + hashlib.sha1(r["title"].encode()).hexdigest()[:8]] = dict(source="commons_t2", label=c, group="supported", **r); st["train_kept"] += 1
        json.dump(E, open(EJ, "w"), indent=0); json.dump(T, open(TJ, "w"), indent=0); print(st)
    elif mode == "dl":
        lim = float(sys.argv[2]); t0 = time.time()
        for D, J, out in ((E, EJ, f"{W}/eval2/img"), (T, TJ, f"{W}/train2/img")):
            todo = [k for k, v in D.items() if "size" not in v and not v.get("fail")]
            for k in todo:
                if time.time() - t0 > lim: break
                try:
                    im = Image.open(io.BytesIO(get(D[k]["url"]))).convert("RGB"); w, h = im.size; s = min(1.0, 640 / max(w, h))
                    if s < 1: im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
                    im.save(f"{out}/{k}.jpg", quality=88); D[k]["size"] = [w, h]; time.sleep(0.4)
                except Exception as e: D[k]["fail"] = str(e)[:80]
            json.dump(D, open(J, "w"), indent=0)
        print("eval2", sum("size" in v for v in E.values()), "/", len(E), "train2 commons", sum("size" in v for v in T.values()), "/", len(T))
