# NutriSole G6.3 controlled fine-tune FROM THE G3 CONTROL CHECKPOINT (not A1). Kaggle GPU (T4) if granted, else CPU (logged).
# Init: G3 det_yolo11n_640 best.pt (sha256 29cc5212..., the promoted champion's source weights).
# Data: FULL replay of the G3 det-v3 train/val mix (det + COCO neg + OIV7 + G3 hard negatives), minus the G6.1 audit
#       removals (train images that are exact/near duplicates of locked eval images; list g6_removed_basenames.txt).
# Variants (pre-registered in docs/cv/gauntlet/G6.md before results):
#   rp  : replay only (control for "more training from G3")
#   rpx : rp + OIV7c train/val (G4 class-complete Open Images, 967/71) + guava 300 (CC BY 4.0) + deepNIR whole capsicum (CC0)
# Fixed hyper-parameters for both: imgsz 640 (G3's train size; deployed at 480), SGD lr0 0.002 lrf 0.1, warmup 1,
# 40 epochs, cos_lr, close_mosaic 10, seed 0, batch 32, G3's default augmentation. Locked splits evaluated on sandbox CPU.
import glob, json, os, subprocess, sys, time, shutil, random
VARIANT = "__VARIANT__"; IMGSZ = 640; NAME = f"det_yolo11n_g6_{VARIANT}"; EPOCHS = 40
t0 = time.time()
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics==8.4.175"], check=True)
MODEL = glob.glob("/kaggle/input/**/G3_best.pt", recursive=True)[0]
REMOVED = set(open(glob.glob("/kaggle/input/**/g6_removed_basenames.txt", recursive=True)[0]).read().split())
D = "/tmp/data"; os.makedirs(D, exist_ok=True)
def untar(name):
    t = glob.glob(f"/kaggle/input/**/{name}", recursive=True)
    if t:
        subprocess.run(["tar", "-xf", t[0], "-C", D], check=True); return
    tops = {"det_v3.tar": ["det", "neg", "oiv7", "hardneg"], "oiv7c_v4.tar": ["oiv7c"]}[name]
    for s in tops:
        c = [p for p in glob.glob(f"/kaggle/input/**/{s}", recursive=True) if os.path.isdir(p + "/images")]
        if not c: raise SystemExit(f"missing {name}/{s}: " + str(glob.glob('/kaggle/input/*/*')[:30]))
        shutil.copytree(c[0], f"{D}/{s}")
untar("det_v3.tar")
NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
L = {"train": ["det/images/train", "neg/images/train", "oiv7/images/train", "hardneg/images/train"],
     "val": ["det/images/val", "neg/images/val", "oiv7/images/val", "hardneg/images/val"]}
def yolo_to_box_lines(src_lbl, cls_id):
    out = []
    for l in open(src_lbl).read().split("\n"):
        v = l.split()
        if len(v) < 5: continue
        xs = list(map(float, v[1:]))
        if len(xs) == 4: cx, cy, w, h = xs
        else:
            px, py = xs[0::2], xs[1::2]; cx, cy, w, h = (min(px) + max(px)) / 2, (min(py) + max(py)) / 2, max(px) - min(px), max(py) - min(py)
        if w > 0.004 and h > 0.004: out.append(f"{cls_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
    return out
def import_ext(tag, root, split_map, cls_id, cap=None, seed=0):
    for src_sp, dst_sp in split_map.items():
        imgs = sorted(glob.glob(f"{root}/{src_sp}/images/*"))
        if cap and src_sp == "train":
            random.Random(seed).shuffle(imgs); imgs = sorted(imgs[:cap])
        os.makedirs(f"{D}/{tag}/images/{dst_sp}", exist_ok=True); os.makedirs(f"{D}/{tag}/labels/{dst_sp}", exist_ok=True)
        k = 0
        for f in imgs:
            lb = f.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"
            if not os.path.exists(lb): continue
            lines = yolo_to_box_lines(lb, cls_id)
            if not lines: continue
            b = f"{tag}_{k:05d}"; shutil.copy(f, f"{D}/{tag}/images/{dst_sp}/{b}.jpg"); open(f"{D}/{tag}/labels/{dst_sp}/{b}.txt", "w").write("\n".join(lines) + "\n"); k += 1
        L.setdefault(dst_sp, []).append(f"{tag}/images/{dst_sp}")
if VARIANT == "rpx":
    untar("oiv7c_v4.tar"); L["train"].append("oiv7c/images/train"); L["val"].append("oiv7c/images/val")
    gr = [p[:-len("/data.yaml")] for p in glob.glob("/kaggle/input/**/data.yaml", recursive=True) if os.path.isdir(p[:-len("data.yaml")] + "train/images") and "very good" in open(p).read()]
    print("guava roots", gr, flush=True)
    import_ext("guava", gr[0], {"train": "train", "valid": "val", "test": "test_guava"}, 4, cap=300)
    cr = [p for p in glob.glob("/kaggle/input/**/capsicum", recursive=True) if os.path.isdir(p + "/train/images")]
    print("capsicum roots", cr, flush=True)
    import_ext("capw", cr[0], {"train": "train", "valid": "val", "test": "test_capsicum_whole"}, 11)
lab = lambda f: f.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"
def classes(f):
    p = lab(f)
    return [int(l.split()[0]) for l in open(p) if l.strip()] if os.path.exists(p) else []
n = {}; lists = {}
for sp, ds in L.items():
    lists[sp] = sorted(f for d in ds for f in glob.glob(f"{D}/{d}/*.jpg"))
before = len(lists["train"])
lists["train"] = [f for f in lists["train"] if f[len(D) + 1:] not in REMOVED]  # entries like det/images/train/<file>.jpg
n["audit_removed_from_train"] = before - len(lists["train"])
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
dev = "0" if torch.cuda.is_available() else "cpu"
P = "/kaggle/working/runs"
YOLO(MODEL).train(data=f"{D}/det.yaml", imgsz=IMGSZ, epochs=EPOCHS, patience=100, batch=32 if dev == "0" else 16, optimizer="SGD", lr0=0.002, lrf=0.1,
        momentum=0.937, warmup_epochs=1, cos_lr=True, close_mosaic=10, cache="ram", seed=0, deterministic=True,
        device=dev, workers=4, project=P, name=NAME, exist_ok=True, plots=True, verbose=False, time=(None if dev == "0" else 10.5))
res = dict(model=MODEL, name=NAME, variant=VARIANT, imgsz=IMGSZ, epochs=EPOCHS, data_counts=n, train_wall_s=round(time.time() - t0, 1), torch=torch.__version__,
           ultralytics=ultralytics.__version__, gpu=(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "kaggle-cpu"), evals=[])
bm = YOLO(f"{P}/{NAME}/weights/best.pt")
for sp in [s for s in ["val", "test_guava", "test_capsicum_whole"] if s in lists]:
    try:
        r = bm.val(data=f"{D}/det.yaml", split=sp, imgsz=480, batch=16, device=dev, conf=0.001, iou=0.7, plots=False,
                   project=f"{P}/{NAME}_val", name=f"{sp}_480", exist_ok=True, verbose=False)
        per = {}
        for i, c in enumerate(r.ap_class_index):
            p, rc, ap50, ap = r.box.class_result(i)
            per[r.names[int(c)]] = dict(P=round(float(p), 4), R=round(float(rc), 4), mAP50=round(float(ap50), 4), mAP50_95=round(float(ap), 4))
        res["evals"].append(dict(split=sp, n=len(lists[sp]), imgsz=480, device=res["gpu"], mAP50=round(float(r.box.map50), 4), mAP50_95=round(float(r.box.map), 4), per_class=per))
        print(sp, res["evals"][-1]["mAP50"], flush=True)
    except Exception as e:
        print("EVAL_FAIL", sp, repr(e), flush=True)
    json.dump(res, open(f"/kaggle/working/{NAME}_metrics.json", "w"), indent=1)
json.dump(res, open(f"/kaggle/working/{NAME}_metrics.json", "w"), indent=1)
print("DONE", round(time.time() - t0), flush=True)
