# NutriSole G4.4 quality classifier on Kaggle (free T4): quality2-g4ll (strong low-light copies) + val_hard selection.
# Selection (stated before results, VAL only): maximise val_hard rotten recall s.t. val full-image acc >= 0.97;
# ties -> higher val_hard acc, then fewer epochs. TEST is never shipped to Kaggle.
import glob, json, os, subprocess, sys, time, shutil
t0 = time.time()
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics==8.4.175"], check=True)
D = "/tmp/data"; os.makedirs(D, exist_ok=True)
t = glob.glob("/kaggle/input/**/cls_g4ll.tar", recursive=True)
if t: subprocess.run(["tar", "-xf", t[0], "-C", D], check=True)
else: shutil.copytree([p for p in glob.glob("/kaggle/input/**/quality2_g4ll", recursive=True) if os.path.isdir(p)][0], f"{D}/quality2_g4ll")
DATA = f"{D}/quality2_g4ll"
for l in ["fresh", "rotten"]: os.makedirs(f"{DATA}/test/{l}", exist_ok=True)
import torch, ultralytics
from ultralytics import YOLO
P = "/kaggle/working/runs"
CFG = [("G4_E224_e15_b64_sgd01", 224, 15), ("G4_E224_e25_b64_sgd01", 224, 25)]
out = dict(torch=torch.__version__, ultralytics=ultralytics.__version__, gpu=torch.cuda.get_device_name(0), runs={})
def score(m, sz, folder, split_crop):
    st = {}
    for lvl in ["fresh", "rotten"]:
        fs = sorted(glob.glob(f"{DATA}/{folder}/{lvl}/*.jpg"))
        for i in range(0, len(fs), 64):
            for f, r in zip(fs[i:i + 64], m.predict(fs[i:i + 64], imgsz=sz, verbose=False, device=0)):
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
                                     device=0, workers=4, project=P, name=name, exist_ok=True, verbose=False, plots=False, val=True)
        m = YOLO(f"{P}/{name}/weights/best.pt")
        out["runs"][name] = dict(imgsz=sz, epochs=ep, wall_s=round(time.time() - t1, 1), **score(m, sz, "val", True), **score(m, sz, "val_hard", False))
    except Exception as e:
        out["runs"][name] = dict(error=repr(e))
    print(name, out["runs"][name], flush=True)
    json.dump(out, open("/kaggle/working/cls_g4_meta.json", "w"), indent=1)
ok = {k: v for k, v in out["runs"].items() if "error" not in v and v["val_full"] >= 0.97}
if ok: out["selected"] = max(ok, key=lambda k: (ok[k]["val_hard_hard_rot"], ok[k]["val_hard_hard"], -ok[k]["epochs"]))
for f in glob.glob(f"{P}/*/weights/*.pt"):
    if not f.endswith("best.pt"): os.remove(f)
out["total_wall_s"] = round(time.time() - t0, 1)
json.dump(out, open("/kaggle/working/cls_g4_meta.json", "w"), indent=1)
print("DONE", out.get("selected"), flush=True)
