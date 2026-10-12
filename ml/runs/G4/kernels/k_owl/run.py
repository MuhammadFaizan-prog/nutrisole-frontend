# G4.3 open-vocabulary teacher pilot: OWLv2 (google/owlv2-base-patch16-ensemble, Apache-2.0) on Kaggle.
# Writes PROPOSALS ONLY (nothing goes to train). Images: locked test_rf + test_oiv7 (for teacher P/R vs GT; read-only use)
# and the 144 hygiene-dropped LVIS val images (a review-queue pilot: LVIS labels there are not exhaustive).
import glob, json, os, subprocess, sys, time, torch
t0 = time.time()
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "transformers>=4.44"], check=False)
from transformers import Owlv2Processor, Owlv2ForObjectDetection
from PIL import Image
dev = "cuda" if torch.cuda.is_available() else "cpu"
M = "google/owlv2-base-patch16-ensemble"
proc = Owlv2Processor.from_pretrained(M); model = Owlv2ForObjectDetection.from_pretrained(M).to(dev).eval()
NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
PROMPTS = {"banana": ["a banana"], "apple": ["an apple"], "mango": ["a mango"], "citrus": ["an orange", "a kinnow mandarin", "a malta orange"],
           "guava": ["a guava"], "pomegranate": ["a pomegranate"], "lemon_lime": ["a lemon", "a lime"], "tomato": ["a tomato"],
           "potato": ["a potato"], "cucumber": ["a cucumber"], "carrot": ["a carrot"], "capsicum": ["a bell pepper", "a capsicum"]}
texts = [p for c in NAMES for p in PROMPTS[c]]; owner = [NAMES.index(c) for c in NAMES for p in PROMPTS[c]]
def find(sub):
    c = glob.glob(f"/kaggle/input/**/{sub}", recursive=True)
    return c[0] if c else None
D = "/tmp/d"; os.makedirs(D, exist_ok=True)
for tar in ["det_v3.tar", "lvisdrop.tar"]:
    t = glob.glob(f"/kaggle/input/**/{tar}", recursive=True)
    if t: subprocess.run(["tar", "-xf", t[0], "-C", D, "--wildcards", "*test_rf*", "*test_oiv7*", "*lvisdrop/*/val/*"], check=False)
sets = {"test_rf": sorted(glob.glob(f"{D}/det/images/test_rf/*.jpg")) or sorted(glob.glob(find("det") + "/images/test_rf/*.jpg")),
        "test_oiv7": sorted(glob.glob(f"{D}/oiv7/images/test_oiv7/*.jpg")) or sorted(glob.glob(find("oiv7") + "/images/test_oiv7/*.jpg")),
        "lvisdrop_val": sorted(glob.glob(f"{D}/lvisdrop/images/val/*.jpg")) or sorted(glob.glob((find("lvisdrop") or "/x") + "/images/val/*.jpg"))}
print({k: len(v) for k, v in sets.items()}, dev, flush=True)
out = {}
with torch.no_grad():
    for sp, files in sets.items():
        res = []
        for f in files:
            im = Image.open(f).convert("RGB"); W, H = im.size
            inp = proc(text=[texts], images=im, return_tensors="pt").to(dev)
            o = model(**inp)
            S = max(W, H)  # OWLv2 pads to a square: boxes are relative to the padded square
            pp = getattr(proc, "post_process_object_detection", None) or proc.image_processor.post_process_object_detection
            r = pp(outputs=o, threshold=0.05, target_sizes=torch.tensor([[S, S]], device=dev))[0]
            dets = []
            for b, s, l in zip(r["boxes"].tolist(), r["scores"].tolist(), r["labels"].tolist()):
                x1, y1, x2, y2 = [max(0.0, v) for v in b]
                dets.append(dict(box=[x1 / W, y1 / H, min(x2, W) / W, min(y2, H) / H], cls=owner[l], prompt=texts[l], score=round(s, 4)))
            res.append(dict(file=os.path.basename(f), w=W, h=H, dets=dets))
        out[sp] = res
        print(sp, "done", round(time.time() - t0), flush=True)
        json.dump(dict(model=M, licence="Apache-2.0", device=dev, threshold=0.05, prompts=PROMPTS, sets=out), open("/kaggle/working/owlv2_proposals.json", "w"))
print("DONE", round(time.time() - t0), flush=True)
