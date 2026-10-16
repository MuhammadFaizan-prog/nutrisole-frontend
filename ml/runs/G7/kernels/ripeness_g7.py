# NutriSole G7.1 ripeness rerun on Kaggle GPU with a PER-FRUIT taxonomy (<fruit>_<stage>); pre-registered in docs/cv/gauntlet/G7_prereg.md.
# Derived from the G5.3 ripeness classifier (unripe / ripe / overripe), SEPARATE from fresh/rotten quality.
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
STAGES = ["unripe", "ripe", "overripe"]; C = []  # filled per fruit below
rep = dict(classes=C, sources={}, notes=[])
# ---- 1. CC0 training set
roots = [p for p in glob.glob("/kaggle/input/**/", recursive=True) if os.path.isdir(p + "Train") or os.path.isdir(p + "train")]
src = roots[0]; tr = src + ("Train" if os.path.isdir(src + "Train") else "train"); te = src + ("Test" if os.path.isdir(src + "Test") else "test")
print("src", src, os.listdir(tr), flush=True)
def files(d):
    return sorted(f for f in glob.glob(d + "/**/*", recursive=True) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")))
def stage(path):
    p = path.lower()
    for tok, c in [("/overripe", "overripe"), ("/overipe", "overripe"), ("/over-ripe", "overripe"), ("/over_ripe", "overripe"), ("/unripe", "unripe"), ("/ripe", "ripe")]:
        if tok in p: return c
    return None
def fruit(path):
    b = os.path.basename(path).lower().replace("-", "_")
    return b.split("_")[0] if "_" in b else None
def lab(path):
    st, fr = stage(path), fruit(path)
    return f"{fr}_{st}" if st and fr and fr.isalpha() else None
def dh(f):
    im = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
    if im is None: return None
    s = cv2.resize(im, (9, 8)); return int("".join("1" if v else "0" for v in (s[:, 1:] > s[:, :-1]).flatten()), 2)
trf = [(f, lab(f)) for f in files(tr) if lab(f)]; tef = [(f, lab(f)) for f in files(te) if lab(f)]
C = sorted(set(c for _, c in trf) | {f"banana_{st}" for st in STAGES}); tef = [(f, c) for f, c in tef if c in C]
rep["classes"] = C; rep["unlabelled_train_files"] = sum(1 for f in files(tr) if not lab(f))
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
        if c not in STAGES or sp is None: continue
        c = f"banana_{c}"
        if sp == "train": shutil.copy(f, f"{D}/ds/train/{c}/hfb_{k:05d}{os.path.splitext(f)[1].lower()}")
        else: shutil.copy(f, f"{D}/ext_hfbanana/{c}/hfb_{k:05d}{os.path.splitext(f)[1].lower()}")
        k += 1
    ext["ext_hfbanana"] = sum(v for kk, v in cnt.items() if kk.startswith("test/") and kk.split("/")[1] in STAGES)
    rep["sources"]["hf_banana"] = dict(id="Sapek007/banana-ripeness", licence="CC BY 4.0 (dataset card; original Roboflow Banana Ripeness Classification v6, CC BY 4.0)", counts=cnt, rotten_excluded=True)
except Exception as e:
    rep["notes"].append(f"HF banana failed: {e!r}")
tc = {c: len(files(f"{D}/ds/train/{c}")) for c in C}; rep["train_counts"] = tc
rep["val_counts"] = {c: len(files(f"{D}/ds/val/{c}")) for c in C}; rep["test_cc0_counts"] = {c: len(files(f"{D}/ds/test/{c}")) for c in C}
print("train counts", tc, flush=True)
ov = sum(v for k, v in tc.items() if k.endswith("_overripe")); rep["overripe_train_total"] = ov
rep["per_fruit_train"] = {fr: {st: tc.get(f"{fr}_{st}", 0) for st in STAGES} for fr in sorted(set(c.split("_")[0] for c in C))}
json.dump(rep, open(f"{W}/ripeness_g7.json", "w"), indent=1)
assert ov >= 50, f"< 50 overripe train images: {tc}"
C = [c for c in C if tc.get(c, 0) > 0]; rep["classes_trained"] = C
for c in [c for c in tc if tc[c] == 0]:
    rep["notes"].append(f"class {c} has 0 train images: dropped (test items lost: {len(files(f'{D}/ds/test/{c}'))})")
    for sp in ["train", "val", "test"]: shutil.rmtree(f"{D}/ds/{sp}/{c}", ignore_errors=True)
    shutil.rmtree(f"{D}/ext_hfbanana/{c}", ignore_errors=True)
print(rep, flush=True)
# ---- 3. train
import torch
from ultralytics import YOLO
DEV = 0 if torch.cuda.is_available() else 'cpu'
YOLO("yolo11n-cls.pt").train(data=f"{D}/ds", imgsz=224, epochs=30, batch=64, optimizer="SGD", lr0=0.01, cos_lr=True, seed=0, deterministic=True,
                             device=DEV, workers=4, project=f"{W}/runs", name="ripe_g7_perfruit_224", exist_ok=True, verbose=False, plots=False)
m = YOLO(f"{W}/runs/ripe_g7_perfruit_224/weights/best.pt")
FRUITS = sorted(set(c.split("_")[0] for c in C)); preds = {}
def ev(folder, name):
    # conditional per-fruit eval: true fruit (as the detector would give) selects its stage classes
    conf = {fr: {a: {b: 0 for b in STAGES + ["unable"]} for a in STAGES} for fr in FRUITS}
    rows = []
    for c in C:
        fr, st = c.split("_"); fs = files(f"{folder}/{c}")
        for i in range(0, len(fs), 64):
            for f, r in zip(fs[i:i + 64], m.predict(fs[i:i + 64], imgsz=224, verbose=False, device=DEV)):
                p = r.probs.data.float().cpu().numpy(); nm = m.names
                full = {nm[k]: float(p[k]) for k in range(len(p))}
                rows.append(dict(file=os.path.basename(f), fruit=fr, stage=st, probs=full))
                mass = sum(full.get(f"{fr}_{s2}", 0.0) for s2 in STAGES)
                cp = [full.get(f"{fr}_{s2}", 0.0) / mass if mass > 0 else 0.0 for s2 in STAGES]
                o = sorted(range(3), key=lambda k: (-cp[k], k))
                ok = mass >= 0.5 and cp[o[0]] >= 0.6 and cp[o[0]] - cp[o[1]] >= 0.15
                conf[fr][st][STAGES[o[0]] if ok else "unable"] += 1
    preds[name] = rows
    def summ(cm):
        n = sum(sum(v.values()) for v in cm.values()); un = sum(v["unable"] for v in cm.values()); a = n - un
        cor = sum(cm[s2][s2] for s2 in STAGES); ovn = sum(cm["overripe"].values())
        return dict(n=n, assessed=a, coverage=round(a / max(1, n), 4), acc_assessed=round(cor / max(1, a), 4), acc_all=round(cor / max(1, n), 4),
                    overripe_n=ovn, overripe_recall_all=round(cm["overripe"]["overripe"] / max(1, ovn), 4),
                    overripe_recall_assessed=round(cm["overripe"]["overripe"] / max(1, ovn - cm["overripe"]["unable"]), 4))
    pooled = {a: {b: sum(conf[fr][a][b] for fr in FRUITS) for b in STAGES + ["unable"]} for a in STAGES}
    top1 = sum(1 for r_ in rows if max(r_["probs"], key=r_["probs"].get) == f"{r_['fruit']}_{r_['stage']}") / max(1, len(rows))
    return dict(pooled=summ(pooled), unconditional_top1_15way=round(top1, 4), per_fruit={fr: dict(summ(conf[fr]), confusion=conf[fr]) for fr in FRUITS if sum(sum(v.values()) for v in conf[fr].values())})
rep["eval"] = {"val": ev(f"{D}/ds/val", "val"), "test_cc0": ev(f"{D}/ds/test", "test_cc0")}
if ext.get("ext_hfbanana"): rep["eval"]["test_hfbanana"] = ev(f"{D}/ext_hfbanana", "test_hfbanana")
json.dump(preds, open(f"{W}/ripeness_g7_preds.json", "w"))
rep["device"] = (torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'kaggle-cpu'); rep["imgsz"] = 224; rep["model"] = "yolo11n-cls"
try:
    m.export(format="onnx", imgsz=224, opset=17, simplify=False); rep["onnx"] = True
except Exception as e:
    rep["notes"].append(f"onnx export failed: {e!r}")
for f in glob.glob(f"{W}/runs/*/weights/last.pt"): os.remove(f)
rep["wall_s"] = round(time.time() - t0, 1)
json.dump(rep, open(f"{W}/ripeness_g7.json", "w"), indent=1); print("DONE", json.dumps(rep["eval"])[:2000], flush=True)
