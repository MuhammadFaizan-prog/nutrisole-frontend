"""I1 crop-geometry diagnostic (post-hoc, Stage H items read-only). Recomputes the Stage H close-up box exactly (G3 at the tap ->
roi_from_tap -> object_mask refinement for tap_roi) and scores H2 on crop-geometry variants:
  sh      Stage H crop: box + pad 0.08, resize short side 256, centre crop 224 (what Stage H scored)
  sq15    square context crop around the same box: side = max(w,h)*1.3, shifted inside the frame, resized to 224 (nothing cut off)
  roiX    tap_roi only: ROI frac X (0.6 / 0.9) instead of 0.35 before mask refinement, then sq15 (track boxes unchanged)
  full    whole frame (upper bound for centre-tap single-item photos only)
Resumable; writes out/geom.jsonl. Usage: i_geom.py SECONDS"""
import json, os, sys, time, numpy as np, cv2
sys.path.insert(0, "/workspace/work/nutrisole"); sys.path.insert(0, "/workspace/work/nutrisole/ml/runs/G9/stageG/scripts"); sys.path.insert(0, os.path.dirname(__file__))
from g_models import detect
from ml.eval.closeup import roi_from_tap, crop_rect
from ml.grading.measure import object_mask
from i_audit import stageh_tensor, onx
S = "/workspace/work/nutrisole/ml/runs/G9/stageH"; O = "/workspace/work/nutrisole/ml/runs/G9/stageI/out"; OUT = f"{O}/geom.jsonl"
def refine(im, box):
    x1, y1, x2, y2 = map(int, box); sub = im[y1:y2, x1:x2]; m, _ = object_mask(sub[:, :, ::-1].copy()); ys, xs = np.where(m)
    return [x1 + xs.min(), y1 + ys.min(), x1 + xs.max() + 1, y1 + ys.max() + 1] if len(xs) > 50 else list(box)
def refine_fast(im, box, mx=400):  # same object_mask, on the ROI downscaled to <= mx px (used only for the grown-ROI variants)
    x1, y1, x2, y2 = map(int, box); sub = im[y1:y2, x1:x2]; sc = min(1.0, mx / max(sub.shape[:2])); sm = cv2.resize(sub, (max(1, round(sub.shape[1] * sc)), max(1, round(sub.shape[0] * sc))), interpolation=cv2.INTER_AREA)
    m, _ = object_mask(sm[:, :, ::-1].copy()); ys, xs = np.where(m)
    return [x1 + xs.min() / sc, y1 + ys.min() / sc, x1 + (xs.max() + 1) / sc, y1 + (ys.max() + 1) / sc] if len(xs) > 50 * sc * sc else list(box)
def square_ctx(im, box, grow=0.15):
    H, W = im.shape[:2]; cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2; s = min(max(box[2] - box[0], box[3] - box[1]) * (1 + 2 * grow), W, H)
    x1 = int(round(min(max(0, cx - s / 2), W - s))); y1 = int(round(min(max(0, cy - s / 2), H - s))); s = int(round(s))
    return im[y1:y1 + s, x1:x1 + s]
def sq_tensor(c):
    from i_audit import MEAN, STD
    im = cv2.resize(c, (224, 224), interpolation=cv2.INTER_AREA if min(c.shape[:2]) > 224 else cv2.INTER_LINEAR)[:, :, ::-1].astype(np.float32) / 255
    return ((im - MEAN) / STD).transpose(2, 0, 1)[None].astype(np.float32)
P = lambda x: [round(float(v), 6) for v in onx(x)]
if __name__ == "__main__":
    lim = float(sys.argv[1]); t0 = time.time(); have = {}
    if os.path.exists(OUT):
        for l in open(OUT): r = json.loads(l); have[r["key"] + "|" + r["set"]] = r
    R = [json.loads(l) for l in open(f"{S}/out/ident_items.jsonl")]
    with open(OUT, "a") as f:
        for r in R:
            k = r["key"] + "|" + r["set"]
            if k in have: continue
            if time.time() - t0 > lim: break
            im = cv2.imread(r["img"]); H, W = im.shape[:2]; dets = detect(im); boxes = [d[0] for d in dets]
            ro = roi_from_tap(r["tap"], W, H, boxes); box = ro["box"] if ro["source"] == "track" else refine(im, ro["box"])
            cr = crop_rect(box, W, H, 0.08); sh = im[cr["y"]:cr["y"] + cr["h"], cr["x"]:cr["x"] + cr["w"]]
            rec = dict(key=r["key"], set=r["set"], roi=ro["source"], box=[float(v) for v in box], img_hw=[H, W],
                       sh=P(stageh_tensor(sh)), sq15=P(sq_tensor(square_ctx(im, box))), full=P(stageh_tensor(im)))
            for fr in (0.6, 0.9):
                if ro["source"] == "track": rec[f"roi{fr}"] = rec["sq15"]; continue
                b2 = refine_fast(im, roi_from_tap(r["tap"], W, H, [], roi_frac=fr)["box"]); rec[f"roi{fr}"] = P(sq_tensor(square_ctx(im, b2))); rec[f"box{fr}"] = [float(v) for v in b2]
            f.write(json.dumps(rec) + "\n"); f.flush(); have[k] = rec
    print(len(have), "/", len(R), round(time.time() - t0), "s")
