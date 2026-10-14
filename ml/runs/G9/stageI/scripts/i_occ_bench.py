"""I3 occlusion benchmark on the Stage H extended suite crops (/workspace/work/g9h/occ/crops, read-only; CU-tune for any selection,
CU-check reported once). Per crop: occlusion cues (ml/eval/occlusion.cues, unchanged) from 4 masks + new targeted cues + per-mask ms.
  gc      GrabCut 3 iters at crop size (= Stage H, measure.object_mask)
  gc64    same GrabCut on the crop downscaled to <= 64 px, mask upsampled (nearest)
  sat     saturation Otsu + largest component (measure.object_mask fallback path)
  lab     Lab distance to the border-strip median colour, Otsu threshold, largest component
New cues (ml/eval/occlusion.targeted_cues): sideTouch (max fraction of one crop side covered by the mask inside the GrabCut inset band:
inner truncation), skinFrac (YCrCb skin pixels in a ring just outside the mask: hands), specFrac (low-saturation glare inside the mask:
bags/film), hullGap (largest convexity-defect depth / sqrt(area): bites from overlapping produce).  Resumable -> out/occ_bench.jsonl"""
import json, os, sys, time, cv2, numpy as np
sys.path.insert(0, "/workspace/work/nutrisole")
from ml.eval.occlusion import cues, targeted_cues
from ml.grading.measure import object_mask, _largest_component
CR = "/workspace/work/g9h/occ/crops"; O = "/workspace/work/nutrisole/ml/runs/G9/stageI/out"; OUT = f"{O}/occ_bench.jsonl"
def m_gc(b): return object_mask(b[:, :, ::-1].copy())[0]
def m_gc64(b):
    h, w = b.shape[:2]; s = min(1.0, 64 / max(h, w)); sm = cv2.resize(b, (max(8, round(w * s)), max(8, round(h * s))), interpolation=cv2.INTER_AREA)
    m = object_mask(sm[:, :, ::-1].copy())[0]; return cv2.resize(m.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST).astype(bool)
def m_sat(b):
    s = cv2.GaussianBlur(cv2.cvtColor(b, cv2.COLOR_BGR2HSV)[..., 1], (5, 5), 0); _, th = cv2.threshold(s, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU); return _largest_component(th > 0)
def m_lab(b):
    lab = cv2.cvtColor(cv2.GaussianBlur(b, (5, 5), 0), cv2.COLOR_BGR2LAB).astype(np.float32); h, w = b.shape[:2]; k = max(2, int(0.06 * min(h, w)))
    ring = np.concatenate([lab[:k].reshape(-1, 3), lab[-k:].reshape(-1, 3), lab[:, :k].reshape(-1, 3), lab[:, -k:].reshape(-1, 3)])
    d = np.linalg.norm(lab - np.median(ring, 0), axis=2); d8 = np.clip(d * 255 / max(d.max(), 1e-6), 0, 255).astype(np.uint8)
    _, th = cv2.threshold(d8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU); return _largest_component(th > 0)
M = dict(gc=m_gc, gc64=m_gc64, sat=m_sat, lab=m_lab)
if __name__ == "__main__":
    lim = float(sys.argv[1]); t0 = time.time(); have = {json.loads(l)["k"] for l in open(OUT)} if os.path.exists(OUT) else set()
    files = sorted(f for f in os.listdir(CR) if f.endswith(".png"))
    with open(OUT, "a") as f:
        for fn in files:
            k = fn[:-4]
            if k in have: continue
            if time.time() - t0 > lim: break
            b = cv2.imread(f"{CR}/{fn}"); rec = dict(k=k)
            for n, fnm in M.items():
                t = time.perf_counter(); m = fnm(b); ms = (time.perf_counter() - t) * 1e3
                rec[n] = dict(cues(b, m), **targeted_cues(b, m), ms=round(ms, 2))
            f.write(json.dumps(rec) + "\n"); have.add(k)
    print(len(have), "/", len(files), round(time.time() - t0), "s")
