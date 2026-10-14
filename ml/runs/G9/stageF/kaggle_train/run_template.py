# NutriSole CV G9 Stage F training kernel (free Kaggle T4). Prereg: docs/cv/gauntlet/G9_stageF_prereg.md (commit 9c46e09, before any result).
# F1 = replay-only control: det_v3 train + seeded duplicate sample of det_v3 train (EXTRA entries, matched length)
# F2 = det_v3 train + market-train MT (Commons per-file CC, OWLv2 proposals + agent correction, unboxed piles greyed), EXTRA entries
# Matched schedule = Stage D D1 recipe, 20 epochs, seeds 0/1. All 12 classes. No DEV / M-DEV / M-TEST / holdout material in this kernel.
import glob, json, os, subprocess, sys, time, shutil, base64, random, urllib.request
sys.stdout.reconfigure(line_buffering=True); t0 = time.time()
def log(*a): print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics==8.4.175", "onnx", "onnxslim", "onnxruntime"], check=True)
S = json.loads(base64.b64decode("__MT_JSON_B64__").decode())  # {"items":[{id, split(train|dev), url, boxes:[[x0,y0,x1,y1,cls],...] norm, grey:[[x0,y0,x1,y1],...]}]}
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
s_tr = sorted(built["train"]); EXTRA = int(0.15 * len(base_tr) / 0.85)  # matched number of extra entries for F1 and F2
def mt_list(seed):
    if not s_tr: return []
    neg = [f for f in s_tr if os.path.getsize(f.replace("/images/", "/labels/")[:-4] + ".txt") == 0]; pos = [f for f in s_tr if f not in neg]
    r = random.Random(seed); out = []
    nneg = min(int(0.30 * EXTRA), len(neg) * 40) if neg else 0
    while len(out) < nneg: out.append(neg[len(out) % len(neg)])
    k = 0
    while len(out) < EXTRA: out.append(pos[k % len(pos)] if pos else neg[k % len(neg)]); k += 1
    r.shuffle(out); return out
def rep_list(seed):
    r = random.Random(1000 + seed); return [r.choice(base_tr) for _ in range(EXTRA)]
lists = {}
for a in ARMS:
    sd = int(a[-1]); lists[a] = base_tr + (rep_list(sd) if a.startswith("F1") else mt_list(sd))
def lab(f):
    lp = f.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"; out = []
    if os.path.exists(lp):
        for l in open(lp):
            v = l.split()
            if len(v) >= 5: out.append(v)
    return out
res["data"] = dict(base_train=len(base_tr), mt_train_unique=len(s_tr), mt_train_boxes=sum(len(lab(f)) for f in s_tr), extra_entries=EXTRA, list_len={a: len(v) for a, v in lists.items()},
                   mt_unique_in_list={a: len(set(v[len(base_tr):]) & set(s_tr)) for a, v in lists.items()}, val=len(val), mt_val=len(built["dev"]))
log("data", res["data"])
def yaml(tag, tr, va=f"{D}/val.txt"):
    open(f"{D}/{tag}_train.txt", "w").write("\n".join(tr) + "\n")
    open(f"{D}/{tag}.yaml", "w").write(f"path: {D}\ntrain: {D}/{tag}_train.txt\nval: {va}\nnames:\n" + "".join(f"  {i}: {c}\n" for i, c in enumerate(NAMES)))
    return f"{D}/{tag}.yaml"
for a in lists: yaml(a, lists[a])
yaml("base", base_tr)
yaml("sdev", s_tr[:1], f"{D}/sdev.txt")
import torch, ultralytics
from ultralytics import YOLO
res["env"] = dict(torch=torch.__version__, ultralytics=ultralytics.__version__, gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
def valc(pt, tag, data=f"{D}/base.yaml"):
    r = YOLO(pt).val(data=data, split="val", imgsz=480, batch=32, device=0, conf=0.001, iou=0.7, plots=False, project=f"{P}/val", name=tag, exist_ok=True, verbose=False)
    per = {}
    for i, c in enumerate(r.ap_class_index):
        p, rc, ap50, ap = r.box.class_result(i); per[r.names[int(c)]] = dict(P=round(float(p), 4), R=round(float(rc), 4), AP50=round(float(ap50), 4), AP50_95=round(float(ap), 4))
    return dict(mAP50=round(float(r.box.map50), 4), mAP50_95=round(float(r.box.map), 4), per_class=per)
def save(): json.dump(res, open(f"{OUT}/f_metrics.json", "w"), indent=1)
try: res["G3_val480"] = valc(G3, "g3"); res["G3_mtval480"] = valc(G3, "g3s", f"{D}/sdev.yaml") if built["dev"] else None; log("G3 val", res["G3_val480"]["mAP50"])
except Exception as e: res["G3_val_err"] = str(e)[:300]
save()
for a in ARMS:
    try:
        ts = time.time()
        YOLO(G3).train(data=f"{D}/{a}.yaml", imgsz=640, epochs=EPOCHS, patience=100, batch=32, optimizer="SGD", lr0=0.002, lrf=0.1, momentum=0.937, warmup_epochs=1,
                       cos_lr=True, close_mosaic=5, mosaic=1.0, fliplr=0.5, degrees=10, scale=0.5, translate=0.1, hsv_h=0.0, hsv_s=0.6, hsv_v=0.5, mixup=0.0,
                       cache="ram", seed=int(a[-1]), deterministic=True, device=0, workers=4, project=P, name=a, exist_ok=True, plots=False, verbose=False, pretrained=True)
        best = f"{P}/{a}/weights/best.pt"; shutil.copyfile(best, f"{OUT}/{a}_best.pt")
        res[a] = dict(train_wall_s=round(time.time() - ts, 1), val480=valc(best, a.lower()), mtval480=valc(best, a.lower() + "s", f"{D}/sdev.yaml") if built["dev"] else None)
        p = YOLO(best).export(format="onnx", imgsz=480, device="cpu", dynamic=False, simplify=True); shutil.copyfile(p, f"{OUT}/{a}_raw480.onnx")
        log(a, res[a]["val480"]["mAP50"])
    except Exception as e:
        import traceback; res[f"{a}_error"] = traceback.format_exc()[-1500:]; log(a, "ERR", e)
    save()
    for d in glob.glob(f"{P}/*/weights/last.pt"): os.remove(d)
    for d in glob.glob(f"{D}/**/*.npy", recursive=True): os.remove(d)
res["total_wall_s"] = round(time.time() - t0, 1); save(); shutil.rmtree(f"{P}/val", ignore_errors=True); log("DONE")
