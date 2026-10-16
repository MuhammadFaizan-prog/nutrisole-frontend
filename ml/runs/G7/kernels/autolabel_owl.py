# NutriSole G7 Phase 3 stage 2 (Kaggle): OWLv2 open-vocabulary proposals on the adaptive keyframes produced by
# ml/autolabel/extract.py (G3 + ByteTrack, sandbox CPU), plus the ripeness hue-shift table (addendum A item 5) on the CC0 test.
# PROPOSALS ONLY: nothing here is ground truth. Model google/owlv2-base-patch16-ensemble (Apache-2.0).
import glob, json, os, subprocess, sys, time, tarfile
import numpy as np
t0 = time.time(); W = "/kaggle/working"
def find(name):
    c = glob.glob(f"/kaggle/input/**/{name}", recursive=True); return c[0] if c else None
# ---------- (a) ripeness hue-shift on CC0 Test (same labelling functions as ripeness_g7.py) ----------
try:
    import cv2, onnxruntime as ort
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "onnxruntime", "opencv-python-headless"], check=False); import cv2, onnxruntime as ort
def stage(path):
    p = path.lower()
    for tok, c in [("/overripe", "overripe"), ("/overipe", "overripe"), ("/over-ripe", "overripe"), ("/over_ripe", "overripe"), ("/unripe", "unripe"), ("/ripe", "ripe")]:
        if tok in p: return c
def fruit(path):
    b = os.path.basename(path).lower().replace("-", "_"); return b.split("_")[0] if "_" in b else None
def lab(path):
    st, fr = stage(path), fruit(path); return f"{fr}_{st}" if st and fr and fr.isalpha() else None
def prep(im, s=224):
    h, w = im.shape[:2]; k = s / min(h, w); nh, nw = max(s, int(round(h * k))), max(s, int(round(w * k)))
    im = cv2.resize(im, (nw, nh)); y0, x0 = (nh - s) // 2, (nw - s) // 2; im = im[y0:y0 + s, x0:x0 + s]
    return np.ascontiguousarray(im[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255.0)
def hue(im, d):
    if d == 0: return im
    h = cv2.cvtColor(im, cv2.COLOR_BGR2HSV); h[..., 0] = ((h[..., 0].astype(np.int32) + int(round(d / 2))) % 180).astype(np.uint8)
    return cv2.cvtColor(h, cv2.COLOR_HSV2BGR)
try:
    man = json.load(open(find("model_manifest.json"))); C = man["classes"]; s = ort.InferenceSession(find("ripeness_best.onnx"), providers=["CPUExecutionProvider"])
    roots = [p for p in glob.glob("/kaggle/input/**/", recursive=True) if os.path.isdir(p + "Test") or os.path.isdir(p + "test")]
    te = roots[0] + ("Test" if os.path.isdir(roots[0] + "Test") else "test")
    items = [(f, lab(f)) for f in sorted(glob.glob(te + "/**/*", recursive=True)) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")) and lab(f) in C]
    nd = {}
    ndp = find("ripe_test_neardup.json")
    if ndp: nd = {r["orig"]: r["near_dup"] for r in json.load(open(ndp))}
    rows = []
    for d in [0, -5, 5, -10, 10, -20, 20]:
        res = {"all": [0, 0, 0, 0], "dedup": [0, 0, 0, 0]}
        for f, c in items:
            im = cv2.imread(f)
            if im is None: continue
            p = s.run(None, {s.get_inputs()[0].name: prep(hue(im, d))})[0][0]; fr = c.split("_")[0]
            idx = [i for i, n in enumerate(C) if n.startswith(fr + "_")]; pred = C[idx[int(np.argmax(p[idx]))]]
            for k in (["all"] + (["dedup"] if not nd.get(os.path.basename(f), False) else [])):
                r = res[k]; r[0] += pred == c; r[1] += 1
                if c.endswith("overripe"): r[2] += pred == c; r[3] += 1
        rows.append(dict(hue_shift_deg=d, **{f"{k}_stage_acc": round(v[0] / max(1, v[1]), 4) for k, v in res.items()},
                         **{f"{k}_overripe_recall": round(v[2] / max(1, v[3]), 4) for k, v in res.items()}, n_all=res["all"][1], n_dedup=res["dedup"][1]))
        print("hue", rows[-1], flush=True)
    json.dump(dict(model="G7 per-fruit ripeness ONNX", split="CC0 Test (asadullahprl), conditional per-fruit argmax", device="Kaggle CPU",
                   neardup_join=bool(ndp), rows=rows), open(f"{W}/ripeness_hue_shift.json", "w"), indent=1)
except Exception as e:
    print("hue-shift failed", repr(e), flush=True)
# ---------- (a2) overripe audit sheets: 24 random TRAIN overripe images per fruit (CC0 set), for visual audit ----------
try:
    import random
    rr = [p for p in glob.glob("/kaggle/input/**/", recursive=True) if os.path.isdir(p + "Train") or os.path.isdir(p + "train")][0]
    trd = rr + ("Train" if os.path.isdir(rr + "Train") else "train")
    allf = [f for f in glob.glob(trd + "/**/*", recursive=True) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
    for fr in ["apple", "banana", "mango", "orange", "tomato"]:
        for st in ["overripe", "ripe"]:
            fs = sorted(f for f in allf if lab(f) == f"{fr}_{st}"); random.Random(0).shuffle(fs); fs = fs[:24]
            ims = [cv2.resize(cv2.imread(f), (160, 160)) for f in fs if cv2.imread(f) is not None]
            if not ims: continue
            while len(ims) % 8: ims.append(np.zeros((160, 160, 3), np.uint8))
            cv2.imwrite(f"{W}/audit_{fr}_{st}.jpg", np.vstack([np.hstack(ims[i:i + 8]) for i in range(0, len(ims), 8)]))
    print("audit sheets done", flush=True)
except Exception as e:
    print("audit failed", repr(e), flush=True)
# ---------- (b) OWLv2 on keyframes ----------
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "transformers>=4.44"], check=False)
import torch
from transformers import Owlv2Processor, Owlv2ForObjectDetection
from PIL import Image
dev = "cuda" if torch.cuda.is_available() else "cpu"; torch.set_num_threads(os.cpu_count() or 4)
M = "google/owlv2-base-patch16-ensemble"; proc = Owlv2Processor.from_pretrained(M); model = Owlv2ForObjectDetection.from_pretrained(M).to(dev).eval()
NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
PROMPTS = {"banana": ["a banana"], "apple": ["an apple"], "mango": ["a mango"], "citrus": ["an orange", "a kinnow mandarin"], "guava": ["a guava"],
           "pomegranate": ["a pomegranate"], "lemon_lime": ["a lemon", "a lime"], "tomato": ["a tomato"], "potato": ["a potato"], "cucumber": ["a cucumber"],
           "carrot": ["a carrot"], "capsicum": ["a bell pepper", "a capsicum"]}
OTHER = ["an onion", "a cabbage", "a chili pepper", "an eggplant", "a watermelon", "a pineapple", "a grape bunch", "a person's hand", "a plastic bag"]
texts = [p for c in NAMES for p in PROMPTS[c]] + OTHER; owner = [NAMES.index(c) for c in NAMES for p in PROMPTS[c]] + [-1] * len(OTHER)
D = "/tmp/kf"; os.makedirs(D, exist_ok=True)
for t in sorted(glob.glob("/kaggle/input/**/keyframes_*.tar", recursive=True)):
    tarfile.open(t).extractall(D)
files = sorted(glob.glob(f"{D}/*/keyframes/*.jpg")); print("keyframes", len(files), dev, flush=True)
out = {}; OUT = f"{W}/owlv2_keyframes.json"
with torch.no_grad():
    for i, f in enumerate(files):
        im = Image.open(f).convert("RGB"); Wd, Hd = im.size; S = max(Wd, Hd)
        o = model(**proc(text=[texts], images=im, return_tensors="pt").to(dev))
        pp = getattr(proc, "post_process_object_detection", None) or proc.image_processor.post_process_object_detection
        r = pp(outputs=o, threshold=0.08, target_sizes=torch.tensor([[S, S]], device=dev))[0]
        dets = []
        for b, sc, l in zip(r["boxes"].tolist(), r["scores"].tolist(), r["labels"].tolist()):
            x1, y1, x2, y2 = [max(0.0, v) for v in b]
            dets.append(dict(box=[round(x1 / Wd, 5), round(y1 / Hd, 5), round(min(x2, Wd) / Wd, 5), round(min(y2, Hd) / Hd, 5)], cls=owner[l], prompt=texts[l], score=round(sc, 4)))
        clip, name = f.split("/")[-3], os.path.basename(f); out.setdefault(clip, {})[name] = dets
        if i % 50 == 0 or i == len(files) - 1:
            json.dump(dict(model=M, licence="Apache-2.0", device=dev, threshold=0.08, prompts=PROMPTS, other_prompts=OTHER, n_done=i + 1, n=len(files), clips=out), open(OUT, "w"))
            print(i + 1, "/", len(files), round(time.time() - t0), flush=True)
        if time.time() - t0 > 11.3 * 3600: print("time cap", flush=True); break
print("DONE", round(time.time() - t0), flush=True)
