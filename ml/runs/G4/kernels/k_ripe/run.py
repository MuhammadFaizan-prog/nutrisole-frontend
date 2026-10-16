# NutriSole G4.5 ripeness classifier (unripe / ripe / overripe), SEPARATE from fresh/rotten quality.
# Train: Kaggle "Fruit-Ripeness-Dataset" (asadullahprl, CC0; apple/banana/mango/orange/tomato, 300x300).
# External tests (never trained on): Mendeley "Annotated Banana Ripeness Stage Dataset" 10.17632/56c75hvm7r.2 (CC BY 4.0,
# YOLO boxes -> crops, its own test split) and Mendeley "Tomato fruits dataset" 10.17632/x4s2jz55dx.1 (CC BY 4.0; ripe/unripe only).
import glob, json, os, random, shutil, subprocess, sys, time, zipfile, hashlib
t0 = time.time()
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics==8.4.175", "rarfile"], check=True)
import cv2, numpy as np, requests
W = "/kaggle/working"; D = "/tmp/ripe"; os.makedirs(D, exist_ok=True)
C = ["unripe", "ripe", "overripe"]
rep = dict(classes=C, sources={}, notes=[])
# ---- 1. CC0 training set
roots = [p for p in glob.glob("/kaggle/input/**/", recursive=True) if os.path.isdir(p + "Train") or os.path.isdir(p + "train")]
src = roots[0]; tr = src + ("Train" if os.path.isdir(src + "Train") else "train"); te = src + ("Test" if os.path.isdir(src + "Test") else "test")
print("src", src, os.listdir(tr), flush=True)
def files(d):
    return sorted(f for f in glob.glob(d + "/**/*", recursive=True) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")))
def lab(path):
    p = path.lower()
    for c in ["overripe", "unripe", "ripe"]:
        if f"/{c}" in p: return c
    return None
def dh(f):
    im = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
    if im is None: return None
    s = cv2.resize(im, (9, 8)); return int("".join("1" if v else "0" for v in (s[:, 1:] > s[:, :-1]).flatten()), 2)
trf = [(f, lab(f)) for f in files(tr) if lab(f)]; tef = [(f, lab(f)) for f in files(te) if lab(f)]
rep["sources"]["kaggle_cc0"] = dict(id="asadullahprl/fruits-ripeness-classification-dataset", licence="CC0", n_train_pool=len(trf), n_test=len(tef),
                                     fruit_tokens={k: sum(k in f.lower() for f, _ in trf) for k in ["apple", "banana", "mango", "orange", "tomato"]})
# leakage check: test images with a near-duplicate (dHash Hamming <= 4) in the train pool
th = [dh(f) for f, _ in trf]; th = np.array([h for h in th if h is not None], dtype=np.uint64)
dup = 0
for f, _ in tef:
    h = dh(f)
    if h is not None and len(th) and min(bin(int(x) ^ h).count("1") for x in th) <= 4: dup += 1
rep["sources"]["kaggle_cc0"]["test_near_dup_in_train"] = dup
random.Random(0).shuffle(trf); nv = int(0.15 * len(trf))
for sp, items in [("train", trf[nv:]), ("val", trf[:nv]), ("test", tef)]:
    for c in C: os.makedirs(f"{D}/ds/{sp}/{c}", exist_ok=True)
    for i, (f, c) in enumerate(items):
        shutil.copy(f, f"{D}/ds/{sp}/{c}/{sp}_{i:05d}{os.path.splitext(f)[1].lower()}")
# ---- 2. external tests
def mendeley(ds, ver, want):
    r = requests.get(f"https://data.mendeley.com/public-api/datasets/{ds}/files?folder_id=root&version={ver}", timeout=60).json()
    f = [x for x in r if x["filename"] == want][0]
    p = f"{D}/{want}"
    with requests.get(f["content_details"]["download_url"], stream=True, timeout=600) as s:
        s.raise_for_status()
        with open(p, "wb") as o:
            for ch in s.iter_content(1 << 22): o.write(ch)
    return p
ext = {}
try:
    p = mendeley("56c75hvm7r", 2, "BANANA_DATASET.zip"); z = zipfile.ZipFile(p); z.extractall(f"{D}/ban"); os.remove(p)
    imgs = [f for f in files(f"{D}/ban") if "/test/" in f.lower()]
    n = 0
    for c in C: os.makedirs(f"{D}/ext_banana/{c}", exist_ok=True)
    for f in imgs:
        lp = f.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"
        if not os.path.exists(lp): continue
        im = cv2.imread(f); H, Wd = im.shape[:2]
        for k, l in enumerate(open(lp).read().split("\n")):
            v = l.split()
            if len(v) < 5: continue
            c, x, y, w, h = int(v[0]), *map(float, v[1:5])
            x1, y1, x2, y2 = int((x - w / 2) * Wd), int((y - h / 2) * H), int((x + w / 2) * Wd), int((y + h / 2) * H)
            cr = im[max(0, y1):y2, max(0, x1):x2]
            if cr.size == 0 or min(cr.shape[:2]) < 24 or c > 2: continue
            cv2.imwrite(f"{D}/ext_banana/{C[c]}/{n:05d}.jpg", cr); n += 1
    ext["ext_banana"] = n; rep["sources"]["mendeley_banana"] = dict(doi="10.17632/56c75hvm7r.2", licence="CC BY 4.0", class_ids="0 unripe,1 ripe,2 overripe (dataset README)", crops=n, test_images=len(imgs))
    shutil.rmtree(f"{D}/ban", ignore_errors=True)
except Exception as e:
    rep["notes"].append(f"banana external test failed: {e!r}")
try:
    p = mendeley("x4s2jz55dx", 1, "Dataset.rar")
    subprocess.run(["bash", "-c", f"cd {D} && (7z x -y -otom {p} >/dev/null || (apt-get -qq install -y unrar >/dev/null 2>&1; mkdir -p tom; cd tom; unrar x -o+ {p} >/dev/null))"], check=False)
    tom = files(f"{D}/tom"); n = 0
    for c in ["unripe", "ripe"]: os.makedirs(f"{D}/ext_tomato/{c}", exist_ok=True)
    for f in tom:
        pl = f.lower()
        if "multi" not in pl and "ternary" not in pl and "three" not in pl and "3" not in os.path.dirname(pl): continue
        c = "unripe" if "/unripe" in pl else "ripe" if "/ripe" in pl else None
        if c: shutil.copy(f, f"{D}/ext_tomato/{c}/{n:05d}.jpg"); n += 1
    if n == 0:  # fall back: any folder named ripe/unripe
        for f in tom:
            pl = f.lower(); c = "unripe" if "/unripe" in pl else "ripe" if "/ripe/" in pl else None
            if c: shutil.copy(f, f"{D}/ext_tomato/{c}/{n:05d}.jpg"); n += 1
    ext["ext_tomato"] = n; rep["sources"]["mendeley_tomato"] = dict(doi="10.17632/x4s2jz55dx.1", licence="CC BY 4.0", images=n, dirs=sorted({os.path.dirname(f)[len(D):] for f in tom})[:20])
except Exception as e:
    rep["notes"].append(f"tomato external test failed: {e!r}")
print(rep, flush=True)
# ---- 3. train
import torch
from ultralytics import YOLO
YOLO("yolo11n-cls.pt").train(data=f"{D}/ds", imgsz=224, epochs=30, batch=64, optimizer="SGD", lr0=0.01, cos_lr=True, seed=0, deterministic=True,
                             device=0, workers=4, project=f"{W}/runs", name="ripe_yolo11n_cls_224", exist_ok=True, verbose=False, plots=False)
m = YOLO(f"{W}/runs/ripe_yolo11n_cls_224/weights/best.pt")
def ev(folder, classes):
    conf = {a: {b: 0 for b in C} for a in classes}
    for a in classes:
        fs = files(f"{folder}/{a}")
        for i in range(0, len(fs), 64):
            for r in m.predict(fs[i:i + 64], imgsz=224, verbose=False, device=0):
                conf[a][m.names[int(r.probs.top1)]] += 1
    n = sum(sum(v.values()) for v in conf.values())
    return dict(n=n, acc=round(sum(conf[a][a] for a in classes) / max(1, n), 4), recall={a: round(conf[a][a] / max(1, sum(conf[a].values())), 4) for a in classes}, confusion=conf)
rep["eval"] = {"val": ev(f"{D}/ds/val", C), "test_cc0": ev(f"{D}/ds/test", C)}
if ext.get("ext_banana"): rep["eval"]["ext_banana_crops"] = ev(f"{D}/ext_banana", C)
if ext.get("ext_tomato"): rep["eval"]["ext_tomato_2cls"] = ev(f"{D}/ext_tomato", ["unripe", "ripe"])
rep["device"] = torch.cuda.get_device_name(0); rep["imgsz"] = 224; rep["model"] = "yolo11n-cls"
try:
    m.export(format="onnx", imgsz=224, opset=17, simplify=False); rep["onnx"] = True
except Exception as e:
    rep["notes"].append(f"onnx export failed: {e!r}")
for f in glob.glob(f"{W}/runs/*/weights/last.pt"): os.remove(f)
rep["wall_s"] = round(time.time() - t0, 1)
json.dump(rep, open(f"{W}/ripeness_g4.json", "w"), indent=1); print("DONE", json.dumps(rep["eval"])[:2000], flush=True)
