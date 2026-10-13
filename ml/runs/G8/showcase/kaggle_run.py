# NutriSole G8 showcase detector (G8_prereg.md Addendum 2026-10-13, S2). Free Kaggle T4.
# 5-class head initialised from G3 det_yolo11n_640 best.pt (rows sliced for the selected classes); other 7 classes dropped -> background.
# Locked test splits are NOT present in this kernel (only det/neg/oiv7/hardneg train+val). Seeds 0 and 1.
import glob, json, os, subprocess, sys, time, shutil, copy, random
sys.stdout.reconfigure(line_buffering=True)
t0 = time.time()
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics==8.4.175", "onnx", "onnxslim", "onnxruntime"], check=True)
SEL = [3, 1, 0, 7, 10]  # citrus, apple, banana, tomato, carrot (selection.json)
NAMES12 = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
NAMES5 = [NAMES12[i] for i in SEL]; MAP = {c: i for i, c in enumerate(SEL)}
EPOCHS = int(os.environ.get("EPOCHS", "60")); SEEDS = [0, 1]
OUT = "/kaggle/working"; P = f"{OUT}/runs"
D = "/tmp/data"; os.makedirs(D, exist_ok=True)
tars = glob.glob("/kaggle/input/**/det_v3.tar", recursive=True)
if tars: subprocess.run(["tar", "-xf", tars[0], "-C", D], check=True)
else:
    src = glob.glob("/kaggle/input/**/oiv7/images", recursive=True)[0]; root = os.path.dirname(os.path.dirname(src))
    for s in ["det", "neg", "oiv7", "hardneg"]: shutil.copytree(f"{root}/{s}", f"{D}/{s}")
G3 = glob.glob("/kaggle/input/**/G3_best.pt", recursive=True)[0]
L = {"train": ["det/images/train", "neg/images/train", "oiv7/images/train", "hardneg/images/train"],
     "val": ["det/images/val", "neg/images/val", "oiv7/images/val", "hardneg/images/val"]}
S = "/tmp/s5"; n = {}; inst = {sp: {c: 0 for c in NAMES5} for sp in L}; dropped = {sp: 0 for sp in L}
for sp, ds in L.items():
    fs = sorted(f for d in ds for f in glob.glob(f"{D}/{d}/*.jpg")); lst = []
    for f in fs:
        rel = os.path.relpath(f, D); dst = f"{S}/{rel}"; os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.exists(dst): os.symlink(f, dst)
        lb = f.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"; out = []
        if os.path.exists(lb):
            for l in open(lb):
                v = l.split()
                if not v: continue
                c = int(v[0])
                if c in MAP: out.append(" ".join([str(MAP[c])] + v[1:])); inst[sp][NAMES12[c]] += 1
                else: dropped[sp] += 1
        dl = dst.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"; os.makedirs(os.path.dirname(dl), exist_ok=True)
        open(dl, "w").write("\n".join(out) + ("\n" if out else "")); lst.append(dst)
    n[sp] = len(lst); open(f"{S}/{sp}.txt", "w").write("\n".join(lst) + "\n")
print("counts", n, inst, "dropped boxes", dropped, flush=True)
open(f"{S}/s5.yaml", "w").write(f"path: {S}\ntrain: {S}/train.txt\nval: {S}/val.txt\nnames:\n" + "".join(f"  {i}: {c}\n" for i, c in enumerate(NAMES5)))
import torch, torch.nn as nn, ultralytics
from ultralytics import YOLO

def reshape_head(pt_in, pt_out, rows, nc_new, names, fill_from=None):
    ck = torch.load(pt_in, map_location="cpu", weights_only=False)
    m = (ck.get("ema") or ck["model"]).float(); det = m.model[-1]
    for seq in det.cv3:
        old = seq[-1]; new = nn.Conv2d(old.in_channels, nc_new, 1, bias=True)
        with torch.no_grad():
            if fill_from is None:  # slice rows
                new.weight.copy_(old.weight[rows]); new.bias.copy_(old.bias[rows])
            else:  # expand: rows[j] = target row index for old row j
                new.weight.zero_(); new.bias.fill_(-20.0)
                for j, r in enumerate(rows): new.weight[r] = old.weight[j]; new.bias[r] = old.bias[j]
        seq[-1] = new
    det.nc = nc_new; det.no = nc_new + det.reg_max * 4; m.nc = nc_new; m.yaml["nc"] = nc_new; m.names = {i: c for i, c in enumerate(names)}
    ck2 = dict(model=m.half(), ema=None, train_args=ck.get("train_args", {}), epoch=-1, optimizer=None, date=ck.get("date"), version=ck.get("version"))
    torch.save(ck2, pt_out)

reshape_head(G3, f"{OUT}/G3_sliced5.pt", SEL, 5, NAMES5)
res = dict(selected=NAMES5, sel_ids=SEL, epochs=EPOCHS, data_counts=n, instances=inst, dropped_boxes=dropped, torch=torch.__version__, ultralytics=ultralytics.__version__,
           gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None, runs={})
def val5(pt, tag):
    r = YOLO(pt).val(data=f"{S}/s5.yaml", split="val", imgsz=480, batch=32, device=0, conf=0.001, iou=0.7, plots=False, project=f"{P}/val", name=tag, exist_ok=True, verbose=False)
    per = {}
    for i, c in enumerate(r.ap_class_index):
        p, rc, ap50, ap = r.box.class_result(i); per[r.names[int(c)]] = dict(P=round(float(p), 4), R=round(float(rc), 4), mAP50=round(float(ap50), 4), mAP50_95=round(float(ap), 4))
    return dict(mAP50=round(float(r.box.map50), 4), mAP50_95=round(float(r.box.map), 4), per_class=per)
res["init_sliced_val480"] = val5(f"{OUT}/G3_sliced5.pt", "init"); print("init", res["init_sliced_val480"], flush=True)

# Albumentations: colour-preserving lighting / motion only (no hue, no gray)
import ultralytics.data.augment as UA
_orig = UA.Albumentations.__init__
def _patched(self, *a, **k):
    _orig(self, *a, **k)
    try:
        import albumentations as A
        def mk(cls, *aa, **kw):
            try: return cls(*aa, **kw)
            except Exception: return None
        try: ic = A.ImageCompression(quality_range=(60, 100), p=0.1)
        except Exception: ic = mk(A.ImageCompression, quality_lower=60, quality_upper=100, p=0.1)
        T = [A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.3), A.RandomGamma(gamma_limit=(80, 120), p=0.2),
             A.MotionBlur(blur_limit=(3, 7), p=0.1), mk(A.ISONoise, p=0.1), ic, A.CLAHE(p=0.05)]
        self.transform = A.Compose([t for t in T if t is not None]); self.contains_spatial = False; self.p = 1.0
        print("ALB custom:", self.transform, flush=True)
    except Exception as e:
        print("ALB patch failed, defaults kept:", e, flush=True)
UA.Albumentations.__init__ = _patched

for seed in SEEDS:
    name = f"show5_s{seed}"; ts = time.time()
    try:
        YOLO(f"{OUT}/G3_sliced5.pt").train(data=f"{S}/s5.yaml", imgsz=480, epochs=EPOCHS, patience=100, batch=32, optimizer="SGD", lr0=0.002, lrf=0.1, momentum=0.937,
            warmup_epochs=1, close_mosaic=10, mosaic=1.0, fliplr=0.5, scale=0.5, translate=0.1, hsv_h=0.0, hsv_s=0.3, hsv_v=0.4, cache="ram", seed=seed, deterministic=True,
            device=0, workers=4, project=P, name=name, exist_ok=True, plots=True, verbose=False, pretrained=True)
        best = f"{P}/{name}/weights/best.pt"
        rr = dict(train_wall_s=round(time.time() - ts, 1), val480=val5(best, name))
        exp = f"{OUT}/{name}_12row.pt"; reshape_head(best, exp, SEL, 12, NAMES12, fill_from=True)
        rr["val480_12row_check"] = "see sandbox"
        try:
            p = YOLO(exp).export(format="onnx", imgsz=480, device="cpu", dynamic=False, simplify=True)
            shutil.copyfile(p, f"{OUT}/{name}_12row_raw.onnx"); rr["onnx"] = f"{name}_12row_raw.onnx"
        except Exception as e: rr["onnx_error"] = str(e)[:300]
        res["runs"][name] = rr; print(name, rr, flush=True)
    except Exception as e:
        import traceback; res["runs"][name] = dict(error=traceback.format_exc()[-1500:]); print("ERR", name, e, flush=True)
    json.dump(res, open(f"{OUT}/show_metrics.json", "w"), indent=1)
res["total_wall_s"] = round(time.time() - t0, 1); json.dump(res, open(f"{OUT}/show_metrics.json", "w"), indent=1)
for d in glob.glob(f"{P}/*/weights/last.pt"): os.remove(d)
shutil.rmtree(f"{P}/val", ignore_errors=True)
print("DONE", flush=True)
