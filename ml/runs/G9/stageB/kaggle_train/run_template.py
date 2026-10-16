# NutriSole CV G9 Stage B training kernel (free Kaggle T4). Prereg: docs/cv/gauntlet/G9_stageB_prereg.md (committed before any result).
# B1 = G3 + agent-verified hard negatives (empty labels) fine-tune; B2 verifier = MobileNetV3-Small produce vs non-produce crops.
# Holdout clips are NOT present here. HN samples come from: Commons thumbnails (downloaded by URL, per-file CC licence recorded in the
# manifest) and video crops from M-train clips (embedded below as JPEG base64; M-dev crops are embedded separately for DEV evaluation only).
import glob, json, os, subprocess, sys, time, shutil, base64, random, urllib.request, urllib.parse, io
sys.stdout.reconfigure(line_buffering=True); t0 = time.time()
def log(*a): print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics==8.4.175", "onnx", "onnxslim", "onnxruntime"], check=True)
HN = json.loads(base64.b64decode("__HN_JSON_B64__").decode())  # {"items":[{id, split(train|dev), kind(commons_whole|commons_crop|video_crop), url?, crop?, b64?, ...}]}
VERIFIER_ONLY = __VONLY__  # v-kernel: same data build, B1 training skipped (B1 came from nutrisole-g9b-train v2)
EPOCHS = int(os.environ.get("EPOCHS", "20")); OUT = "/kaggle/working"; P = f"{OUT}/runs"; D = "/tmp/data"; os.makedirs(D, exist_ok=True)
NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
tars = glob.glob("/kaggle/input/**/det_v3.tar", recursive=True)
if tars: subprocess.run(["tar", "-xf", tars[0], "-C", D], check=True)
else:
    src = glob.glob("/kaggle/input/**/oiv7/images", recursive=True)[0]; root = os.path.dirname(os.path.dirname(src))
    for s in ["det", "neg", "oiv7", "hardneg"]: shutil.copytree(f"{root}/{s}", f"{D}/{s}")
G3 = glob.glob("/kaggle/input/**/G3_best.pt", recursive=True)[0]
import cv2, numpy as np
UA = {"User-Agent": "NutriSoleResearch/0.1 (muhammadfaizanali18@gmail.com)"}
def fetch(url):
    for i in range(4):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read()
        except Exception as e: err = e; time.sleep(3 + 5 * i)
    raise err
VCACHE = {}
def vfile(title):
    if title not in VCACHE:
        r = json.loads(fetch("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(dict(action="query", titles=title, prop="imageinfo", iiprop="url", format="json"))))
        url = list(r["query"]["pages"].values())[0]["imageinfo"][0]["url"]; p = f"/tmp/v_{len(VCACHE)}." + url.rsplit(".", 1)[-1]
        open(p, "wb").write(fetch(url)); VCACHE[title] = p; log("video", title[:60], os.path.getsize(p))
    return VCACHE[title]
def vframe(it, tight=False):  # same frame index + crop geometry the agent reviewed (cv2 seek by frame index, as in the sandbox)
    cap = cv2.VideoCapture(vfile(it["title"])); cap.set(cv2.CAP_PROP_POS_FRAMES, it["fi"]); ok, fr = cap.read()
    if not ok: raise RuntimeError("frame read failed")
    if tight:
        H, W = fr.shape[:2]; b = it["box"]; cx, cy, w, h = (b[0] + b[2]) / 2 * W, (b[1] + b[3]) / 2 * H, (b[2] - b[0]) * W * 1.2, (b[3] - b[1]) * H * 1.2
        return fr[int(max(0, cy - h / 2)):int(min(H, cy + h / 2)), int(max(0, cx - w / 2)):int(min(W, cx + w / 2))]
    a, b_, s = it["crop"]; im = fr[b_:b_ + s, a:a + s]
    return cv2.resize(im, (320, 320)) if s > 320 else im
cache = {}; hn_dir = {sp: f"{D}/hn{sp}/images/{sp}" for sp in ("train", "dev")}
for sp in hn_dir: os.makedirs(hn_dir[sp], exist_ok=True); os.makedirs(hn_dir[sp].replace("/images/", "/labels/"), exist_ok=True)
built = {"train": [], "dev": []}; fails = []
for it in HN["items"]:
    try:
        if it["kind"] == "video_crop": im = vframe(it)
        else:
            if it["url"] not in cache: cache[it["url"]] = fetch(it["url"]); time.sleep(0.3)
            im = cv2.imdecode(np.frombuffer(cache[it["url"]], np.uint8), cv2.IMREAD_COLOR)
            if it["kind"] == "commons_crop":
                H, W = im.shape[:2]; x0, y0, x1, y1 = it["crop"]; im = im[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)]
        p = f"{hn_dir[it['split']]}/{it['id']}.jpg"; cv2.imwrite(p, im, [cv2.IMWRITE_JPEG_QUALITY, 92])
        open(p.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt", "w").write("")  # background-only: empty label
        built[it["split"]].append(p)
    except Exception as e: fails.append([it["id"], str(e)[:120]])
log("HN built", {k: len(v) for k, v in built.items()}, "fails", len(fails), fails[:5])
res = dict(hn_built={k: len(v) for k, v in built.items()}, hn_fail=fails, epochs=EPOCHS)
L = {"train": ["det/images/train", "neg/images/train", "oiv7/images/train", "hardneg/images/train"], "val": ["det/images/val", "neg/images/val", "oiv7/images/val"]}
base_tr = sorted(f for d in L["train"] for f in glob.glob(f"{D}/{d}/*.jpg")); val = sorted(f for d in L["val"] for f in glob.glob(f"{D}/{d}/*.jpg"))
cap = int(0.2 * (len(base_tr) + len(built["train"]))); hn_tr = sorted(built["train"])[:cap]
open(f"{D}/b1_train.txt", "w").write("\n".join(base_tr + hn_tr) + "\n"); open(f"{D}/val.txt", "w").write("\n".join(val) + "\n")
open(f"{D}/b1.yaml", "w").write(f"path: {D}\ntrain: {D}/b1_train.txt\nval: {D}/val.txt\nnames:\n" + "".join(f"  {i}: {c}\n" for i, c in enumerate(NAMES)))
res["b1_data"] = dict(base_train=len(base_tr), hn_train=len(hn_tr), hn_share=round(len(hn_tr) / (len(base_tr) + len(hn_tr)), 4), val=len(val))
log("B1 data", res["b1_data"])
import torch, ultralytics
from ultralytics import YOLO
res["env"] = dict(torch=torch.__version__, ultralytics=ultralytics.__version__, gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
def valc(pt, tag):
    r = YOLO(pt).val(data=f"{D}/b1.yaml", split="val", imgsz=480, batch=32, device=0, conf=0.001, iou=0.7, plots=False, project=f"{P}/val", name=tag, exist_ok=True, verbose=False)
    per = {}
    for i, c in enumerate(r.ap_class_index):
        p, rc, ap50, ap = r.box.class_result(i); per[r.names[int(c)]] = dict(P=round(float(p), 4), R=round(float(rc), 4), AP50=round(float(ap50), 4), AP50_95=round(float(ap), 4))
    return dict(mAP50=round(float(r.box.map50), 4), mAP50_95=round(float(r.box.map), 4), per_class=per)
try: res["G3_val480"] = valc(G3, "g3") if not VERIFIER_ONLY else "skipped"; log("G3 val", res["G3_val480"]["mAP50"])
except Exception as e: res["G3_val_err"] = str(e)[:300]
json.dump(res, open(f"{OUT}/b_metrics.json", "w"), indent=1)
# ---------------- B1 fine-tune
try:
    if VERIFIER_ONLY: raise RuntimeError("skipped: verifier-only kernel")
    ck = torch.load(G3, map_location="cpu", weights_only=False); res["G3_train_args"] = {k: str(v) for k, v in (ck.get("train_args") or {}).items()}
    ts = time.time()
    YOLO(G3).train(data=f"{D}/b1.yaml", imgsz=640, epochs=EPOCHS, patience=100, batch=32, optimizer="SGD", lr0=0.002, lrf=0.1, momentum=0.937, warmup_epochs=1,
                   cos_lr=True, close_mosaic=5, mosaic=1.0, fliplr=0.5, degrees=10, scale=0.5, translate=0.1, hsv_h=0.0, hsv_s=0.6, hsv_v=0.5, mixup=0.0,
                   cache="ram", seed=0, deterministic=True, device=0, workers=4, project=P, name="b1_s0", exist_ok=True, plots=True, verbose=False, pretrained=True)
    best = f"{P}/b1_s0/weights/best.pt"; shutil.copyfile(best, f"{OUT}/B1_s0_best.pt")
    res["B1"] = dict(train_wall_s=round(time.time() - ts, 1), val480=valc(best, "b1"))
    p = YOLO(best).export(format="onnx", imgsz=480, device="cpu", dynamic=False, simplify=True); shutil.copyfile(p, f"{OUT}/B1_raw480.onnx")
    log("B1", res["B1"]["val480"]["mAP50"])
except Exception as e:
    import traceback; res["B1_error"] = traceback.format_exc()[-1500:]; log("B1 ERR", e)
json.dump(res, open(f"{OUT}/b_metrics.json", "w"), indent=1)
# ---------------- verifier crops
def lab(f):
    lp = f.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"; out = []
    if os.path.exists(lp):
        for l in open(lp):
            v = l.split()
            if len(v) >= 5: c, cx, cy, w, h = int(v[0]), *map(float, v[1:5]); out.append([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, c])
    return out
def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i; return i / u if u > 0 else 0
def crop(im, b, s=128, e=1.2):
    H, W = im.shape[:2]; cx, cy = (b[0] + b[2]) / 2 * W, (b[1] + b[3]) / 2 * H; w, h = (b[2] - b[0]) * W * e, (b[3] - b[1]) * H * e
    x0, y0, x1, y1 = int(max(0, cx - w / 2)), int(max(0, cy - h / 2)), int(min(W, cx + w / 2)), int(min(H, cy + h / 2))
    if x1 - x0 < 4 or y1 - y0 < 4: return None
    return cv2.resize(im[y0:y1, x0:x1], (s, s))
g3m = YOLO(G3)
def g3boxes(f):
    r = g3m.predict(f, imgsz=480, conf=0.35, iou=0.7, device=0, verbose=False)[0]
    return [[*map(float, xy), int(c), float(s)] for xy, c, s in zip(r.boxes.xyxyn.tolist(), r.boxes.cls.tolist(), r.boxes.conf.tolist())]
X = {k: [] for k in ("tr_pos", "tr_neg", "val_pos", "val_neg", "hndev_neg", "hntr_neg")}; META = {k: [] for k in X}
random.seed(0); pcount = {}
for split, files in (("tr", base_tr), ("val", val)):
    for f in files:
        im = cv2.imread(f); gt = lab(f)
        for b in gt:
            if split == "tr":
                pcount[b[4]] = pcount.get(b[4], 0) + 1
                if pcount[b[4]] > 700: continue
            c = crop(im, b)
            if c is not None: X[f"{split}_pos"].append(c); META[f"{split}_pos"].append([os.path.basename(f), NAMES[b[4]]])
        for b in g3boxes(f):
            if all(iou(b, g) < 0.1 for g in gt):
                c = crop(im, b)
                if c is not None: X[f"{split}_neg"].append(c); META[f"{split}_neg"].append([os.path.basename(f), NAMES[b[4]], round(b[5], 3)])
for sp, key in (("train", "hntr_neg"), ("dev", "hndev_neg")):
    for f in built[sp]:
        im = cv2.imread(f); bs = g3boxes(f)
        if not bs: bs = [[0.2, 0.2, 0.8, 0.8, -1, 0.0]] if os.path.basename(f)[:2] in ("vc", "cc") else []
        for b in bs:
            c = crop(im, b)
            if c is not None: X[key].append(c); META[key].append([os.path.basename(f), NAMES[b[4]] if b[4] >= 0 else "centre", round(b[5], 3)])
# M-dev real produce crops (agent-verified real produce in M-dev video) for false-rejection on real footage
for it in HN.get("mdev_pos", []):
    try: im = vframe(it, tight=True)
    except Exception as e: log("mdev_pos fail", it["id"], e); continue
    X.setdefault("mdev_pos", []).append(cv2.resize(im, (128, 128))); META.setdefault("mdev_pos", []).append([it["id"], it["cls"]])
res["verifier_data"] = {k: len(v) for k, v in X.items()}; log("verifier data", res["verifier_data"])
json.dump(res, open(f"{OUT}/b_metrics.json", "w"), indent=1)
import torch.nn as nn, torchvision
torch.manual_seed(0); np.random.seed(0)
from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights
dev = "cuda" if torch.cuda.is_available() else "cpu"
MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1); STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
def tens(lst): return ((torch.from_numpy(np.stack([c[:, :, ::-1].copy() for c in lst])).permute(0, 3, 1, 2).float() / 255) - MEAN) / STD
try:
    net = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1); net.classifier[3] = nn.Linear(net.classifier[3].in_features, 1); net = net.to(dev)
    Xp, Xn = X["tr_pos"], X["tr_neg"] + X["hntr_neg"] * 3  # HN-train crops weighted x3 (they are few)
    xs = Xp + Xn; ys = [1] * len(Xp) + [0] * len(Xn); idx = list(range(len(xs)))
    w_pos = len(Xn) / max(1, len(Xp)); opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=1e-4); EP = 12
    sch = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=1e-3, total_steps=EP * ((len(idx) + 127) // 128))
    lossf = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([w_pos], device=dev)); ts = time.time()
    for ep in range(EP):
        net.train(); random.shuffle(idx); tot = 0
        for k in range(0, len(idx), 128):
            bi = idx[k:k + 128]; ims = []
            for i in bi:
                c = xs[i]
                if random.random() < 0.5: c = c[:, ::-1]
                c = np.clip(c.astype(np.float32) * random.uniform(0.75, 1.25) + random.uniform(-20, 20), 0, 255).astype(np.uint8)  # brightness/contrast only, no hue
                ims.append(c)
            xb = tens(ims).to(dev); yb = torch.tensor([ys[i] for i in bi], dtype=torch.float32, device=dev)
            loss = lossf(net(xb).squeeze(1), yb); opt.zero_grad(); loss.backward(); opt.step(); sch.step(); tot += loss.item() * len(bi)
        log("verifier ep", ep, round(tot / len(idx), 4))
    net.eval(); scores = {}
    with torch.no_grad():
        for k, v in X.items():
            if k.startswith("tr_"): continue
            s = []
            for j in range(0, len(v), 256): s += torch.sigmoid(net(tens(v[j:j + 256]).to(dev)).squeeze(1)).cpu().tolist()
            scores[k] = [[*META[k][i], round(x, 5)] for i, x in enumerate(s)]
    json.dump(scores, open(f"{OUT}/verifier_scores.json", "w"))
    net = net.cpu(); torch.save(net.state_dict(), f"{OUT}/verifier_mnv3s_128.pt")
    try: torch.onnx.export(net, torch.zeros(1, 3, 128, 128), f"{OUT}/verifier_mnv3s_128.onnx", input_names=["x"], output_names=["logit"], dynamic_axes={"x": {0: "n"}}, opset_version=17, dynamo=False)
    except Exception as e:
        log("legacy export failed", e); subprocess.run([sys.executable, "-m", "pip", "install", "-q", "onnxscript"], check=False)
        torch.onnx.export(net, torch.zeros(1, 3, 128, 128), f"{OUT}/verifier_mnv3s_128.onnx", input_names=["x"], output_names=["logit"], dynamic_axes={"x": {0: "n"}}, opset_version=17)
    res["verifier"] = dict(train_wall_s=round(time.time() - ts, 1), params=sum(p.numel() for p in net.parameters()), n_pos=len(Xp), n_neg=len(Xn), epochs=EP)
except Exception as e:
    import traceback; res["verifier_error"] = traceback.format_exc()[-1500:]; log("VERIFIER ERR", e)
res["total_wall_s"] = round(time.time() - t0, 1); json.dump(res, open(f"{OUT}/b_metrics.json", "w"), indent=1)
for d in glob.glob(f"{P}/*/weights/last.pt"): os.remove(d)
shutil.rmtree(f"{P}/val", ignore_errors=True); log("DONE")
