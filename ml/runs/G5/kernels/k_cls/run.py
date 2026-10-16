# NutriSole G5.4 quality classifier on Kaggle (GPU if granted, else CPU): quality2-g5ll (Retinex/physics low-light copies)
# with LEAVE-ONE-LIGHTING-OUT selection: night_sodium_hard and tube_light_hard are never synthesised and never used for
# selection. Selection (stated before results, VAL only): maximise val_lolo rotten recall s.t. val full-image acc >= 0.97;
# ties -> higher val_lolo acc, then fewer epochs. TEST is never shipped to Kaggle. Day/night consistency loss: not
# implemented (needs a custom training loop; deferred), the paired day/night copies share labels only.
import glob, json, os, subprocess, sys, time, shutil
t0 = time.time()
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics==8.4.175"], check=True)
D = "/tmp/data"; os.makedirs(D, exist_ok=True)
t = glob.glob("/kaggle/input/**/cls_g5ll.tar", recursive=True)
if t: subprocess.run(["tar", "-xf", t[0], "-C", D], check=True)
else: shutil.copytree([p for p in glob.glob("/kaggle/input/**/quality2_g5ll", recursive=True) if os.path.isdir(p)][0], f"{D}/quality2_g5ll")
DATA = f"{D}/quality2_g5ll"
for l in ["fresh", "rotten"]: os.makedirs(f"{DATA}/test/{l}", exist_ok=True)
import torch, ultralytics
from ultralytics import YOLO
DEV = 0 if torch.cuda.is_available() else 'cpu'
P = "/kaggle/working/runs"
CFG = [("G5_E224_e12_b64_sgd01", 224, 12), ("G5_E224_e20_b64_sgd01", 224, 20)]
out = dict(torch=torch.__version__, ultralytics=ultralytics.__version__, gpu=(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'kaggle-cpu'), runs={})
def score(m, sz, folder, split_crop):
    st = {}
    for lvl in ["fresh", "rotten"]:
        fs = sorted(glob.glob(f"{DATA}/{folder}/{lvl}/*.jpg"))
        for i in range(0, len(fs), 64):
            for f, r in zip(fs[i:i + 64], m.predict(fs[i:i + 64], imgsz=sz, verbose=False, device=DEV)):
                ok = m.names[int(r.probs.top1)] == lvl
                k = ("crop" if os.path.basename(f).startswith("crop__") else "full") if split_crop else "hard"
                for kk in [k, k + "_rot" if lvl == "rotten" else None]:
                    if kk:
                        st.setdefault(kk, [0, 0]); st[kk][0] += ok; st[kk][1] += 1
    return {**{f"{folder}_{k}": round(v[0] / max(1, v[1]), 4) for k, v in st.items()}, **{f"n_{folder}_{k}": v[1] for k, v in st.items()}}
for name, sz, ep in CFG:
    t1 = time.time()
    try:
        YOLO("yolo26n-cls.pt").train(data=DATA, imgsz=sz, epochs=ep, batch=64, optimizer="SGD", lr0=0.01, cos_lr=True, seed=0, deterministic=True,
                                     device=DEV, workers=4, project=P, name=name, exist_ok=True, verbose=False, plots=False, val=True)
        m = YOLO(f"{P}/{name}/weights/best.pt")
        out["runs"][name] = dict(imgsz=sz, epochs=ep, wall_s=round(time.time() - t1, 1), **score(m, sz, "val", True), **score(m, sz, "val_lolo", False))
    except Exception as e:
        out["runs"][name] = dict(error=repr(e))
    print(name, out["runs"][name], flush=True)
    json.dump(out, open("/kaggle/working/cls_g5_meta.json", "w"), indent=1)
ok = {k: v for k, v in out["runs"].items() if "error" not in v and v["val_full"] >= 0.97}
if ok: out["selected"] = max(ok, key=lambda k: (ok[k]["val_lolo_hard_rot"], ok[k]["val_lolo_hard"], -ok[k]["epochs"]))
for f in glob.glob(f"{P}/*/weights/*.pt"):
    if not f.endswith("best.pt"): os.remove(f)
out["total_wall_s"] = round(time.time() - t0, 1)
json.dump(out, open("/kaggle/working/cls_g5_meta.json", "w"), indent=1)
print("DONE", out.get("selected"), flush=True)
