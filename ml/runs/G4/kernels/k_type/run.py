# NutriSole G4 two-stage experiment, stage 2: produce TYPE crop classifier (11 classes with data + 'other'), yolo11n-cls 128 on T4.
import glob, json, os, subprocess, sys, time, shutil
t0 = time.time()
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics==8.4.175"], check=True)
D = "/tmp/t"; os.makedirs(D, exist_ok=True)
t = glob.glob("/kaggle/input/**/typecrops.tar", recursive=True)
if t: subprocess.run(["tar", "-xf", t[0], "-C", D], check=True)
else: shutil.copytree([p for p in glob.glob("/kaggle/input/**/typecrops", recursive=True) if os.path.isdir(p)][0], f"{D}/typecrops")
DATA = f"{D}/typecrops"
for c in os.listdir(f"{DATA}/train"): os.makedirs(f"{DATA}/test/{c}", exist_ok=True)
import torch
from ultralytics import YOLO
YOLO("yolo11n-cls.pt").train(data=DATA, imgsz=128, epochs=20, batch=128, optimizer="SGD", lr0=0.01, cos_lr=True, seed=0, deterministic=True,
                             device=0, workers=4, project="/kaggle/working/runs", name="type_yolo11n_cls_128", exist_ok=True, verbose=False, plots=False)
m = YOLO("/kaggle/working/runs/type_yolo11n_cls_128/weights/best.pt")
res = dict(model="yolo11n-cls", imgsz=128, device=torch.cuda.get_device_name(0), names=m.names, val={})
for c in sorted(os.listdir(f"{DATA}/val")):
    fs = sorted(glob.glob(f"{DATA}/val/{c}/*.jpg")); ok = 0
    for i in range(0, len(fs), 128):
        for r in m.predict(fs[i:i + 128], imgsz=128, verbose=False, device=0): ok += m.names[int(r.probs.top1)] == c
    res["val"][c] = dict(n=len(fs), recall=round(ok / max(1, len(fs)), 4))
for f in glob.glob("/kaggle/working/runs/*/weights/last.pt"): os.remove(f)
res["wall_s"] = round(time.time() - t0, 1); json.dump(res, open("/kaggle/working/type_g4.json", "w"), indent=1); print("DONE", res, flush=True)
