"""G9 Stage J2: list / sample members of CC BY 4.0 Mendeley sources for J-TRAIN ONLY (range reads of the public zips; only sampled members fetched)."""
import io, os, re, sys, json, time, random, zipfile, hashlib, urllib.request
from PIL import Image
UA = {"User-Agent": "NutriSoleResearch/1.0 (https://github.com/MuhammadFaizan-prog/nutrisole-frontend; clydara1@gmail.com)"}
OUT = "/workspace/work/g9j2/train2"; TJ = f"{OUT}/train2_cands_{sys.argv[2]}.json" if len(sys.argv) > 2 and sys.argv[1] == "take" else f"{OUT}/train2_cands.json"
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
    im.save(f"{OUT}/img/{key}.jpg", quality=88); return [w, h]
class RZ(io.RawIOBase):
    def __init__(s, src): s.src = src; s.pos = 0; s._url(); s.size = int(s.cr.split("/")[-1])
    def _url(s):
        r = urllib.request.urlopen(urllib.request.Request(s.src, headers={**UA, "Range": "bytes=0-0"}), timeout=40)
        s.url = r.geturl(); s.cr = r.headers.get("Content-Range"); s.t = time.time()
    def seekable(s): return True
    def readable(s): return True
    def tell(s): return s.pos
    def seek(s, o, wh=0): s.pos = o if wh == 0 else s.pos + o if wh == 1 else s.size + o; return s.pos
    def readinto(s, b):
        if s.pos >= s.size: return 0
        if time.time() - s.t > 200: s._url()
        n = min(len(b), s.size - s.pos); d = get(s.url, 60, {"Range": f"bytes={s.pos}-{s.pos + n - 1}"}); b[:len(d)] = d; s.pos += len(d); return len(d)
PF = "https://data.mendeley.com/public-files/datasets/{d}/files/{f}/file_downloaded"
SRC = {  # src: (dataset id, zip url, authors/title, capture)
 "mb_in":  ("y3649cmgg6", PF.format(d="y3649cmgg6", f="05cb0b26-4ce5-4a97-907d-6e1de8707b41"), "Mango and Banana Dataset (Ripe Unripe): Indian RGB image dataset", "RGB camera, India"),
 "bg_in":  ("56td5w4wz2", PF.format(d="56td5w4wz2", f="4f2c1005-9e8d-4f44-9a4c-f99ac7f30dd2"), "Fruits (Banana and Guava) datasets for non-destructive quality", "Redmi Note 10 Pro phone"),
 "vegnet": ("6nxnjbn9w6", PF.format(d="6nxnjbn9w6", f="ac479be7-48f3-4464-b6f8-edd60a3f7ffb"), "VegNet: Vegetable Dataset with quality (Unripe, Ripe, Old, Dried and Damaged)", "phone/camera, India"),
 "citrus_tw": ("bxfgvsn9kw", "https://data.mendeley.com/public-api/zip/bxfgvsn9kw/download/1", "Huang M.-L., Chen Y.-A. (A Dataset of Citrus Fruit Images)", "Sony DSC-HX300 compact (Taiwan orchards)"),
 "veg_in": ("chv7dmvtfm", "https://data.mendeley.com/public-api/zip/chv7dmvtfm/download/1", "Karwal A., Som A., Patel A.S., Sisodia D. (Vegetable Recognition Dataset)", "self-clicked (markets/fields/households, India)"),
}
def members(src):
    did, url, *_ = SRC[src]
    z = zipfile.ZipFile(io.BufferedReader(RZ(url), 1 << 20))
    return z, [i for i in z.namelist() if i.lower().endswith((".jpg", ".jpeg", ".png"))]
if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "list":
        from collections import Counter
        for src in sys.argv[2:]:
            try: z, names = members(src)
            except Exception as e: print(src, "FAIL", e); continue
            json.dump(names, open(f"{OUT}/members_{src}.json", "w")); print(src, len(names), Counter(os.path.dirname(x) for x in names).most_common(40), flush=True)
    elif mode == "take":   # take SRC REGEX LABEL N SECONDS [EXCLUDE_REGEX]
        src, rx, lab, n, lim = sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]), float(sys.argv[6]); ex = sys.argv[7] if len(sys.argv) > 7 else r"augment|aug_|rotat|flip|resized"
        t0 = time.time(); did, url, title, cap = SRC[src]; z, names = members(src)
        prior = {v.get("src_path") for v in T.values()}
        try: prior |= {v.get("src_path") for v in json.load(open("/workspace/work/g9j/train/train_cands.json")).values()}
        except Exception: pass
        pool = sorted(x for x in names if re.search(rx, x, re.I) and not re.search(ex, x, re.I) and x not in prior)
        random.Random(f"{src}{rx}").shuffle(pool); got = sum(1 for v in T.values() if v["source"] == src and v["label"] == lab and v.get("rx") == rx)
        for nm in pool:
            if got >= n or time.time() - t0 > lim: break
            k = "u" + src[:3] + hashlib.sha1(nm.encode()).hexdigest()[:8]
            if k in T: continue
            try: sz = put(k, z.read(nm))
            except Exception as e: continue
            T[k] = dict(source=src, label=lab, rx=rx, group="supported" if lab in ("apple", "banana", "citrus", "tomato", "carrot") else "unsupported", src_path=nm, size=sz,
                        licence="CC BY 4.0", author=title, uploader=f"Mendeley {did}", page=f"https://data.mendeley.com/datasets/{did}", camera=cap,
                        licence_url="https://creativecommons.org/licenses/by/4.0/"); got += 1
            if got % 10 == 0: save()
        save(); print(src, rx, lab, got, "pool", len(pool))
