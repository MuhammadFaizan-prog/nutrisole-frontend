# NutriSole G7 night/lighting quality classifier (prereg section 5 + addendum A item 5): G3 E224 recipe (yolo26n-cls, 224, 15 ep,
# batch 64, SGD 0.01, cos_lr, seed 0) on q2g3crop train + ONE offline lighting-augmented copy of every train image.
# N1: RandomGamma + PlanckianJitter(blackbody 3000-15000K) + ISONoise + mild MotionBlur, default hsv_h 0.015.
# N2 (reduced-hue, colour-preserving): RandomGamma + ISONoise + mild MotionBlur + PlanckianJitter narrowed to 5000-7500K, hsv_h 0.0.
# Val/test untouched; TEST is evaluated locally only (removed here). Selection between arms happens locally on the prereg gate.
import glob, json, os, subprocess, sys, time, shutil, random
t0 = time.time()
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics==8.4.175"], check=True)
import cv2, numpy as np, albumentations as A
D = "/tmp/data"; os.makedirs(D, exist_ok=True)
tars = glob.glob("/kaggle/input/**/cls_g3.tar", recursive=True)
if tars: subprocess.run(["tar", "-xf", tars[0], "-C", D], check=True)
else:  # v2 fix: Kaggle auto-extracts the uploaded tar -> dataset holds q2g3crop/ dirs, no cls_g3.tar (same fallback as G3 cls_run_g3.py)
    src = [p for p in glob.glob("/kaggle/input/**/q2g3crop", recursive=True) if os.path.isdir(p)][0]; shutil.copytree(src, f"{D}/q2g3crop")
BASE = f"{D}/q2g3crop"; shutil.rmtree(f"{BASE}/test", ignore_errors=True)
def pj(lo, hi):
    try: return A.PlanckianJitter(mode="blackbody", temperature_limit=(lo, hi), p=0.7)
    except TypeError: return A.PlanckianJitter(mode="blackbody", temperature_range=(lo, hi), p=0.7)
def mk(name, planck):
    T = A.Compose([A.RandomGamma(gamma_limit=(60, 160), p=0.8), planck, A.ISONoise(p=0.5), A.MotionBlur(blur_limit=(3, 7), p=0.3)])
    dst = f"{D}/{name}"; shutil.copytree(BASE, dst)
    os.makedirs(f"{dst}/test/fresh", exist_ok=True); os.makedirs(f"{dst}/test/rotten", exist_ok=True)
    random.seed(0); np.random.seed(0)
    n = 0
    for f in sorted(glob.glob(f"{BASE}/train/*/*.jpg")):
        im = cv2.imread(f)
        if im is None: continue
        out = T(image=cv2.cvtColor(im, cv2.COLOR_BGR2RGB))["image"]
        cv2.imwrite(f"{dst}/train/{f.split('/')[-2]}/aug__{os.path.basename(f)}", cv2.cvtColor(out, cv2.COLOR_RGB2BGR)); n += 1
    return dst, n
import torch, ultralytics
from ultralytics import YOLO
P = "/kaggle/working/runs"; out = dict(torch=torch.__version__, ultralytics=ultralytics.__version__, albumentations=A.__version__, gpu=torch.cuda.get_device_name(0), runs={})
for name, planck, hsv_h in [("N1_light_aug", pj(3000, 15000), 0.015), ("N2_light_aug_reduced_hue", pj(5000, 7500), 0.0)]:
    t1 = time.time()
    try:
        data, n = mk(name, planck)
        YOLO("yolo26n-cls.pt").train(data=data, imgsz=224, epochs=15, batch=64, optimizer="SGD", lr0=0.01, cos_lr=True, seed=0, deterministic=True,
                                     hsv_h=hsv_h, device=0, workers=4, project=P, name=name, exist_ok=True, verbose=False, plots=False, val=True)
        out["runs"][name] = dict(aug_images=n, hsv_h=hsv_h, wall_s=round(time.time() - t1, 1))
    except Exception as e:
        out["runs"][name] = dict(error=repr(e))
    print(name, out["runs"][name], flush=True)
    for f in glob.glob(f"{P}/{name}/weights/*.pt"):
        if not f.endswith("best.pt"): os.remove(f)
    json.dump(out, open("/kaggle/working/night_g7_meta.json", "w"), indent=1)
out["total_wall_s"] = round(time.time() - t0, 1); json.dump(out, open("/kaggle/working/night_g7_meta.json", "w"), indent=1); print("DONE", flush=True)
