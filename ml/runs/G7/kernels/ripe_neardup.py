# G7.1 helper (CPU): which CC0 ripeness TEST images have a near-duplicate (dHash Hamming <= 4) in the train pool.
# Reproduces the exact file order/naming of nutrisole-g7-ripeness (test_{i:05d}) so the flags join to ripeness_g7_preds.json.
import glob, os, json
import cv2, numpy as np
roots = [p for p in glob.glob("/kaggle/input/**/", recursive=True) if os.path.isdir(p + "Train") or os.path.isdir(p + "train")]
src = roots[0]; tr = src + ("Train" if os.path.isdir(src + "Train") else "train"); te = src + ("Test" if os.path.isdir(src + "Test") else "test")
def files(d): return sorted(f for f in glob.glob(d + "/**/*", recursive=True) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")))
def stage(path):
    p = path.lower()
    for tok, c in [("/overripe", "overripe"), ("/overipe", "overripe"), ("/over-ripe", "overripe"), ("/over_ripe", "overripe"), ("/unripe", "unripe"), ("/ripe", "ripe")]:
        if tok in p: return c
    return None
def fruit(path):
    b = os.path.basename(path).lower().replace("-", "_"); return b.split("_")[0] if "_" in b else None
def lab(path):
    st, fr = stage(path), fruit(path); return f"{fr}_{st}" if st and fr and fr.isalpha() else None
def dh(f):
    im = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
    if im is None: return None
    s = cv2.resize(im, (9, 8)); return int("".join("1" if v else "0" for v in (s[:, 1:] > s[:, :-1]).flatten()), 2)
trf = [(f, lab(f)) for f in files(tr) if lab(f)]; tef = [(f, lab(f)) for f in files(te) if lab(f)]
C = sorted(set(c for _, c in trf) | {f"banana_{s}" for s in ["unripe", "ripe", "overripe"]}); tef = [(f, c) for f, c in tef if c in C]
th = [h for h in (dh(f) for f, _ in trf) if h is not None]
out = []
for i, (f, c) in enumerate(tef):
    h = dh(f); d = min(bin(x ^ h).count("1") for x in th) if h is not None else None
    out.append(dict(name=f"test_{i:05d}{os.path.splitext(f)[1].lower()}", orig=os.path.basename(f), cls=c, min_hamming=d, near_dup=(d is not None and d <= 4)))
json.dump(out, open("/kaggle/working/ripe_test_neardup.json", "w"), indent=1)
print("near-dup", sum(o["near_dup"] for o in out), "of", len(out))
