# NutriSole CV G9 Stage D training kernel (free Kaggle T4). Prereg: docs/cv/gauntlet/G9_stageD_prereg.md (committed before any result).
# D-ctl = G3 fine-tuned on the original training set only (replay control, analysis only)
# D1    = G3 fine-tuned on the original training set + agent-verified small/overlapping/piled set S (Commons, per-file CC licence), S <= 15%
# D2    = D1 + small-object augmentation: offline zoom-out collages (2x2 / 3x3 of fully labelled images, ~20%) + online scale 0.9
# Recipe otherwise identical to Stage B B1. All 12 classes kept. No DEV clip, no holdout, no M-dev material is present in this kernel.
import glob, json, os, subprocess, sys, time, shutil, base64, random, urllib.request
sys.stdout.reconfigure(line_buffering=True); t0 = time.time()
def log(*a): print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics==8.4.175", "onnx", "onnxslim", "onnxruntime"], check=True)
S = json.loads(base64.b64decode("__S_JSON_B64__").decode())  # {"items":[{id, split(train|dev), url, boxes:[[x0,y0,x1,y1,cls],...] norm, grey:[[x0,y0,x1,y1],...]}]}
EPOCHS = int(os.environ.get("EPOCHS", "20")); OUT = "/kaggle/working"; P = f"{OUT}/runs"; D = "/tmp/data"; os.makedirs(D, exist_ok=True)
ARMS = [a for a in "__ARMS__".split(",") if a]
NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
tars = glob.glob("/kaggle/input/**/det_v3.tar", recursive=True)
if tars: subprocess.run(["tar", "-xf", tars[0], "-C", D], check=True)
else:
    src = glob.glob("/kaggle/input/**/oiv7/images", recursive=True)[0]; root = os.path.dirname(os.path.dirname(src))
    for s_ in ["det", "neg", "oiv7", "hardneg"]: shutil.copytree(f"{root}/{s_}", f"{D}/{s_}")
G3 = glob.glob("/kaggle/input/**/G3_best.pt", recursive=True)[0]
import cv2, numpy as np
UA = {"User-Agent": "NutriSoleResearch/0.1 (muhammadfaizanali18@gmail.com)"}
def fetch(url):
    for i in range(5):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read()
        except Exception as e: err = e; time.sleep(3 + 5 * i)
    raise err
built = {"train": [], "dev": []}; fails = []
for sp in built:
    os.makedirs(f"{D}/s{sp}/images/{sp}", exist_ok=True); os.makedirs(f"{D}/s{sp}/labels/{sp}", exist_ok=True)
for it in S["items"]:
    try:
        im = cv2.imdecode(np.frombuffer(fetch(it["url"]), np.uint8), cv2.IMREAD_COLOR); H, W = im.shape[:2]; time.sleep(0.2)
        for g in it.get("grey", []): im[int(g[1] * H):int(g[3] * H), int(g[0] * W):int(g[2] * W)] = 114
        p = f"{D}/s{it['split']}/images/{it['split']}/{it['id']}.jpg"; cv2.imwrite(p, im, [cv2.IMWRITE_JPEG_QUALITY, 92])
        open(p.replace("/images/", "/labels/")[:-4] + ".txt", "w").write("".join(f"{b[4]} {(b[0]+b[2])/2:.6f} {(b[1]+b[3])/2:.6f} {b[2]-b[0]:.6f} {b[3]-b[1]:.6f}\n" for b in it["boxes"]))
        built[it["split"]].append(p)
    except Exception as e: fails.append([it["id"], str(e)[:120]])
log("S built", {k: len(v) for k, v in built.items()}, "fails", len(fails), fails[:5])
res = dict(s_built={k: len(v) for k, v in built.items()}, s_fail=fails, epochs=EPOCHS, arms=ARMS)
L = {"train": ["det/images/train", "neg/images/train", "oiv7/images/train", "hardneg/images/train"], "val": ["det/images/val", "neg/images/val", "oiv7/images/val"]}
base_tr = sorted(f for d in L["train"] for f in glob.glob(f"{D}/{d}/*.jpg")); val = sorted(f for d in L["val"] for f in glob.glob(f"{D}/{d}/*.jpg"))
open(f"{D}/val.txt", "w").write("\n".join(val) + "\n"); open(f"{D}/sdev.txt", "w").write("\n".join(sorted(built["dev"])) + "\n")
s_tr = sorted(built["train"]); rep = max(1, int(0.15 * len(base_tr) / max(1, 0.85 * len(s_tr)))) if s_tr else 0
s_rep = s_tr * rep
while s_rep and len(s_rep) / (len(base_tr) + len(s_rep)) > 0.15: s_rep = s_rep[:-1]
def lab(f):
    lp = f.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"; out = []
    if os.path.exists(lp):
        for l in open(lp):
            v = l.split()
            if len(v) >= 5: c, cx, cy, w, h = int(v[0]), *map(float, v[1:5]); out.append([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, c])
    return out
# ---- D2 offline zoom-out collages: whole fully-labelled images shrunk into a 2x2 or 3x3 grid (no unlabelled produce is pasted)
random.seed(0); labelled = [f for f in base_tr + s_tr if lab(f)]; col = []
cdir = f"{D}/col/images/train"; os.makedirs(cdir, exist_ok=True); os.makedirs(cdir.replace("/images/", "/labels/"), exist_ok=True)
NCOL = int(0.25 * (len(base_tr) + len(s_rep))) if "D2" in ARMS else 0
for k in range(NCOL):
    g = random.choice([2, 2, 3]); cs = 640 // g; can = np.full((640, 640, 3), 114, np.uint8); lines = []
    for r in range(g):
        for c in range(g):
            f = random.choice(labelled); im = cv2.imread(f); H, W = im.shape[:2]; sc = cs / max(H, W); w, h = max(1, int(W * sc)), max(1, int(H * sc))
            ox, oy = c * cs + (cs - w) // 2, r * cs + (cs - h) // 2; can[oy:oy + h, ox:ox + w] = cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA)
            for b in lab(f):
                x0, y0, x1, y1 = (ox + b[0] * w) / 640, (oy + b[1] * h) / 640, (ox + b[2] * w) / 640, (oy + b[3] * h) / 640
                if (x1 - x0) * 640 >= 2 and (y1 - y0) * 640 >= 2: lines.append(f"{b[4]} {(x0+x1)/2:.6f} {(y0+y1)/2:.6f} {x1-x0:.6f} {y1-y0:.6f}\n")
    p = f"{cdir}/col{k:05d}.jpg"; cv2.imwrite(p, can, [cv2.IMWRITE_JPEG_QUALITY, 92]); open(p.replace("/images/", "/labels/")[:-4] + ".txt", "w").write("".join(lines)); col.append(p)
lists = {"Dctl": base_tr, "D1": base_tr + s_rep, "D2": base_tr + s_rep + col}
res["data"] = dict(base_train=len(base_tr), s_train_unique=len(s_tr), s_repeat=rep, s_train_in_list=len(s_rep), s_share_D1=round(len(s_rep) / max(1, len(lists["D1"])), 4),
                   collages=len(col), collage_share_D2=round(len(col) / max(1, len(lists["D2"])), 4), val=len(val), s_dev=len(built["dev"]))
log("data", res["data"])
def yaml(tag, tr, va=f"{D}/val.txt"):
    open(f"{D}/{tag}_train.txt", "w").write("\n".join(tr) + "\n")
    open(f"{D}/{tag}.yaml", "w").write(f"path: {D}\ntrain: {D}/{tag}_train.txt\nval: {va}\nnames:\n" + "".join(f"  {i}: {c}\n" for i, c in enumerate(NAMES)))
    return f"{D}/{tag}.yaml"
for a in lists: yaml(a, lists[a])
yaml("sdev", s_tr[:1], f"{D}/sdev.txt")
import torch, ultralytics
from ultralytics import YOLO
res["env"] = dict(torch=torch.__version__, ultralytics=ultralytics.__version__, gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
def valc(pt, tag, data=f"{D}/Dctl.yaml"):
    r = YOLO(pt).val(data=data, split="val", imgsz=480, batch=32, device=0, conf=0.001, iou=0.7, plots=False, project=f"{P}/val", name=tag, exist_ok=True, verbose=False)
    per = {}
    for i, c in enumerate(r.ap_class_index):
        p, rc, ap50, ap = r.box.class_result(i); per[r.names[int(c)]] = dict(P=round(float(p), 4), R=round(float(rc), 4), AP50=round(float(ap50), 4), AP50_95=round(float(ap), 4))
    return dict(mAP50=round(float(r.box.map50), 4), mAP50_95=round(float(r.box.map), 4), per_class=per)
def save(): json.dump(res, open(f"{OUT}/d_metrics.json", "w"), indent=1)
try: res["G3_val480"] = valc(G3, "g3"); res["G3_sdev480"] = valc(G3, "g3s", f"{D}/sdev.yaml") if built["dev"] else None; log("G3 val", res["G3_val480"]["mAP50"])
except Exception as e: res["G3_val_err"] = str(e)[:300]
save()
for a in ARMS:
    try:
        ts = time.time()
        YOLO(G3).train(data=f"{D}/{a}.yaml", imgsz=640, epochs=EPOCHS, patience=100, batch=32, optimizer="SGD", lr0=0.002, lrf=0.1, momentum=0.937, warmup_epochs=1,
                       cos_lr=True, close_mosaic=5, mosaic=1.0, fliplr=0.5, degrees=10, scale=0.9 if a == "D2" else 0.5, translate=0.1, hsv_h=0.0, hsv_s=0.6, hsv_v=0.5, mixup=0.0,
                       cache="disk" if a == "D2" else "ram", seed=0, deterministic=True, device=0, workers=4, project=P, name=a, exist_ok=True, plots=False, verbose=False, pretrained=True)
        best = f"{P}/{a}/weights/best.pt"; shutil.copyfile(best, f"{OUT}/{a}_best.pt")
        res[a] = dict(train_wall_s=round(time.time() - ts, 1), val480=valc(best, a.lower()), sdev480=valc(best, a.lower() + "s", f"{D}/sdev.yaml") if built["dev"] else None)
        p = YOLO(best).export(format="onnx", imgsz=480, device="cpu", dynamic=False, simplify=True); shutil.copyfile(p, f"{OUT}/{a}_raw480.onnx")
        log(a, res[a]["val480"]["mAP50"])
    except Exception as e:
        import traceback; res[f"{a}_error"] = traceback.format_exc()[-1500:]; log(a, "ERR", e)
    save()
    for d in glob.glob(f"{P}/*/weights/last.pt"): os.remove(d)
    for d in glob.glob(f"{D}/**/*.npy", recursive=True): os.remove(d)
res["total_wall_s"] = round(time.time() - t0, 1); save(); shutil.rmtree(f"{P}/val", ignore_errors=True); log("DONE")
