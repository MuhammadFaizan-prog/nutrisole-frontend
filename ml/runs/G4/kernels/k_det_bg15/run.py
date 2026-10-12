# NutriSole G4 detector training on Kaggle (free T4). Generated from kaggle/g4/det_run_g4.py; bg15 substituted per kernel.
# Same recipe as G3 yolo11n 640 (150 ep max, patience 30, cos LR, close_mosaic 15, seed 0). Variants:
#   hyg_off : det-v3 train/val + the 834 LVIS images dropped by G3 hygiene (ablation A1)
#   bg15    : det-v3 train with backgrounds subsampled to 15% of train (seed 0) (ablation A2; val unchanged)
#   v4      : det-v4 = det-v3 + audited OIV7 lemon/orange (oiv7c) + lemon_lime images oversampled x2 (file copies)
# Locked splits (test, test_rf, test_oiv7) are evaluated unchanged; test_oiv7c is a NEW G4 split.
import glob, json, os, subprocess, sys, time, shutil, random
VARIANT = "bg15"; MODEL = "yolo11n.pt"; IMGSZ = 640; NAME = f"det_yolo11n_640_{VARIANT}"
t0 = time.time()
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics==8.4.175"], check=True)
D = "/tmp/data"; os.makedirs(D, exist_ok=True)
def untar(name):
    t = glob.glob(f"/kaggle/input/**/{name}", recursive=True)
    if t:
        subprocess.run(["tar", "-xf", t[0], "-C", D], check=True); return
    tops = {"det_v3.tar": ["det", "neg", "oiv7", "hardneg"], "lvisdrop.tar": ["lvisdrop"], "oiv7c_v4.tar": ["oiv7c"]}[name]
    for s in tops:  # Kaggle auto-extracted the archive
        c = [p for p in glob.glob(f"/kaggle/input/**/{s}", recursive=True) if os.path.isdir(p + "/images")]
        if not c: raise SystemExit(f"missing {name}/{s}: " + str(glob.glob('/kaggle/input/*/*')[:30]))
        shutil.copytree(c[0], f"{D}/{s}")
untar("det_v3.tar")
NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
L = {"train": ["det/images/train", "neg/images/train", "oiv7/images/train", "hardneg/images/train"],
     "val": ["det/images/val", "neg/images/val", "oiv7/images/val", "hardneg/images/val"],
     "test": ["det/images/test"], "test_rf": ["det/images/test_rf"], "test_oiv7": ["oiv7/images/test_oiv7"]}
if VARIANT == "hyg_off":
    untar("lvisdrop.tar"); L["train"].append("lvisdrop/images/train"); L["val"].append("lvisdrop/images/val")
if VARIANT == "v4":
    untar("oiv7c_v4.tar"); L["train"].append("oiv7c/images/train"); L["val"].append("oiv7c/images/val"); L["test_oiv7c"] = ["oiv7c/images/test_oiv7c"]
lab = lambda f: f.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"
def classes(f):
    p = lab(f)
    return [int(l.split()[0]) for l in open(p) if l.strip()] if os.path.exists(p) else []
n = {}; lists = {}
for sp, ds in L.items():
    lists[sp] = sorted(f for d in ds for f in glob.glob(f"{D}/{d}/*.jpg"))
if VARIANT == "bg15":
    pos = [f for f in lists["train"] if classes(f)]; bg = [f for f in lists["train"] if not classes(f)]
    k = int(round(0.15 / 0.85 * len(pos))); random.Random(0).shuffle(bg)
    lists["train"] = sorted(pos + bg[:k]); n["bg_kept"] = k; n["bg_before"] = len(bg)
if VARIANT == "v4":  # oversample lemon_lime x2 with physical copies (distinct paths)
    dup = [f for f in lists["train"] if 6 in classes(f)]
    os.makedirs(f"{D}/dup/images/train", exist_ok=True); os.makedirs(f"{D}/dup/labels/train", exist_ok=True)
    for f in dup:
        b = os.path.basename(f).rsplit(".", 1)[0] + "_dup1"
        shutil.copy(f, f"{D}/dup/images/train/{b}.jpg"); shutil.copy(lab(f), f"{D}/dup/labels/train/{b}.txt")
    lists["train"] += sorted(glob.glob(f"{D}/dup/images/train/*.jpg")); n["lemon_dup"] = len(dup)
for sp, fs in lists.items():
    n[sp] = len(fs); open(f"{D}/{sp}.txt", "w").write("\n".join(fs) + "\n")
inst = {}
for f in lists["train"]:
    for c in classes(f): inst[NAMES[c]] = inst.get(NAMES[c], 0) + 1
n["train_instances"] = inst; n["train_backgrounds"] = sum(1 for f in lists["train"] if not classes(f))
print(n, flush=True)
open(f"{D}/det.yaml", "w").write(f"path: {D}\n" + "".join(f"{sp}: {D}/{sp}.txt\n" for sp in lists) + "names:\n" + "".join(f"  {i}: {c}\n" for i, c in enumerate(NAMES)))
import torch, ultralytics
from ultralytics import YOLO
P = "/kaggle/working/runs"
YOLO(MODEL).train(data=f"{D}/det.yaml", imgsz=IMGSZ, epochs=150, patience=30, batch=-1, cos_lr=True, close_mosaic=15,
        hsv_h=0.015, hsv_s=0.6, hsv_v=0.5, degrees=10, fliplr=0.5, mixup=0.1, cache="ram", seed=0, deterministic=True,
        save_period=-1, device=0, workers=4, project=P, name=NAME, exist_ok=True, plots=True, verbose=False)
res = dict(model=MODEL, name=NAME, variant=VARIANT, imgsz=IMGSZ, data_counts=n, train_wall_s=round(time.time() - t0, 1), torch=torch.__version__,
           ultralytics=ultralytics.__version__, gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None, evals=[])
bm = YOLO(f"{P}/{NAME}/weights/best.pt")
for sz in [480, 640]:
    for sp in [s for s in ["val", "test", "test_rf", "test_oiv7", "test_oiv7c"] if s in lists]:
        try:
            r = bm.val(data=f"{D}/det.yaml", split=sp, imgsz=sz, batch=32, device=0, conf=0.001, iou=0.7, plots=False,
                       project=f"{P}/{NAME}_val", name=f"{sp}_{sz}", exist_ok=True, verbose=False)
            per = {}
            for i, c in enumerate(r.ap_class_index):
                p, rc, ap50, ap = r.box.class_result(i)
                per[r.names[int(c)]] = dict(P=round(float(p), 4), R=round(float(rc), 4), mAP50=round(float(ap50), 4), mAP50_95=round(float(ap), 4))
            res["evals"].append(dict(split=sp, n=len(lists[sp]), imgsz=sz, device="T4", mAP50=round(float(r.box.map50), 4), mAP50_95=round(float(r.box.map), 4), per_class=per))
            print(sp, sz, res["evals"][-1]["mAP50"], res["evals"][-1]["mAP50_95"], flush=True)
        except Exception as e:
            print("EVAL_FAIL", sp, sz, repr(e), flush=True)
        json.dump(res, open(f"/kaggle/working/{NAME}_metrics.json", "w"), indent=1)
res["total_wall_s"] = round(time.time() - t0, 1)
json.dump(res, open(f"/kaggle/working/{NAME}_metrics.json", "w"), indent=1)
shutil.rmtree(f"{P}/{NAME}_val", ignore_errors=True)
print("DONE", flush=True)
