# NutriSole G5.3 ripeness classifier (unripe / ripe / overripe), SEPARATE from fresh/rotten quality.
# G5 fixes: (1) the CC0 train folder is spelled "Overipe" -> alias to overripe; (2) every class must have >= 50 train
# images (assert BEFORE training); (3) adds HF Sapek007/banana-ripeness (CC BY 4.0, Roboflow "Banana Ripeness
# Classification" v6): its train+valid go into training, its own test split is a separate held-out test; its "rotten"
# folder is NOT a ripeness class (quality is a separate model) and is excluded. Mendeley external tests dropped
# (public API returned non-JSON in G4). Device: GPU if Kaggle gives one, else CPU.
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
    for tok, c in [("/overripe", "overripe"), ("/overipe", "overripe"), ("/over-ripe", "overripe"), ("/over_ripe", "overripe"), ("/unripe", "unripe"), ("/ripe", "ripe")]:
        if tok in p: return c
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
# ---- 2. HF banana ripeness (CC BY 4.0)
ext = {}
try:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "huggingface_hub"], check=True)
    from huggingface_hub import hf_hub_download
    zp = hf_hub_download(repo_id="Sapek007/banana-ripeness", filename="banana_ripeness_dataset.zip", repo_type="dataset", local_dir=D)
    zipfile.ZipFile(zp).extractall(f"{D}/hfb"); os.remove(zp)
    hf = files(f"{D}/hfb"); cnt = {}
    def hlab(f):
        p = f.lower().replace("\\", "/").split("/")
        for c in ["unripe", "overripe", "ripe", "rotten"]:
            if c in p: return c
        return None
    def hsplit(f):
        p = f.lower().split("/")
        return "test" if "test" in p else "train" if ("train" in p or "valid" in p) else None
    k = 0
    for c in C: os.makedirs(f"{D}/ext_hfbanana/{c}", exist_ok=True)
    for f in hf:
        c, sp = hlab(f), hsplit(f)
        cnt[f"{sp}/{c}"] = cnt.get(f"{sp}/{c}", 0) + 1
        if c not in C or sp is None: continue
        if sp == "train": shutil.copy(f, f"{D}/ds/train/{c}/hfb_{k:05d}{os.path.splitext(f)[1].lower()}")
        else: shutil.copy(f, f"{D}/ext_hfbanana/{c}/hfb_{k:05d}{os.path.splitext(f)[1].lower()}")
        k += 1
    ext["ext_hfbanana"] = sum(v for kk, v in cnt.items() if kk.startswith("test/") and kk.split("/")[1] in C)
    rep["sources"]["hf_banana"] = dict(id="Sapek007/banana-ripeness", licence="CC BY 4.0 (dataset card; original Roboflow Banana Ripeness Classification v6, CC BY 4.0)", counts=cnt, rotten_excluded=True)
except Exception as e:
    rep["notes"].append(f"HF banana failed: {e!r}")
tc = {c: len(files(f"{D}/ds/train/{c}")) for c in C}; rep["train_counts"] = tc
rep["val_counts"] = {c: len(files(f"{D}/ds/val/{c}")) for c in C}; rep["test_cc0_counts"] = {c: len(files(f"{D}/ds/test/{c}")) for c in C}
print("train counts", tc, flush=True)
assert all(v >= 50 for v in tc.values()), f"class with < 50 train images: {tc}"
print(rep, flush=True)
# ---- 3. train
import torch
from ultralytics import YOLO
DEV = 0 if torch.cuda.is_available() else 'cpu'
YOLO("yolo11n-cls.pt").train(data=f"{D}/ds", imgsz=224, epochs=30, batch=64, optimizer="SGD", lr0=0.01, cos_lr=True, seed=0, deterministic=True,
                             device=DEV, workers=4, project=f"{W}/runs", name="ripe_yolo11n_cls_224", exist_ok=True, verbose=False, plots=False)
m = YOLO(f"{W}/runs/ripe_yolo11n_cls_224/weights/best.pt")
def ev(folder, classes):
    conf = {a: {b: 0 for b in C} for a in classes}
    for a in classes:
        fs = files(f"{folder}/{a}")
        for i in range(0, len(fs), 64):
            for r in m.predict(fs[i:i + 64], imgsz=224, verbose=False, device=DEV):
                conf[a][m.names[int(r.probs.top1)]] += 1
    n = sum(sum(v.values()) for v in conf.values())
    return dict(n=n, acc=round(sum(conf[a][a] for a in classes) / max(1, n), 4), recall={a: round(conf[a][a] / max(1, sum(conf[a].values())), 4) for a in classes}, confusion=conf)
rep["eval"] = {"val": ev(f"{D}/ds/val", C), "test_cc0": ev(f"{D}/ds/test", C)}
if ext.get("ext_hfbanana"): rep["eval"]["test_hfbanana"] = ev(f"{D}/ext_hfbanana", C)
rep["device"] = (torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'kaggle-cpu'); rep["imgsz"] = 224; rep["model"] = "yolo11n-cls"
try:
    m.export(format="onnx", imgsz=224, opset=17, simplify=False); rep["onnx"] = True
except Exception as e:
    rep["notes"].append(f"onnx export failed: {e!r}")
for f in glob.glob(f"{W}/runs/*/weights/last.pt"): os.remove(f)
rep["wall_s"] = round(time.time() - t0, 1)
json.dump(rep, open(f"{W}/ripeness_g5.json", "w"), indent=1); print("DONE", json.dumps(rep["eval"])[:2000], flush=True)
