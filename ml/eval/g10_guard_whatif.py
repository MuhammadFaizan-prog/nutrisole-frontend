"""G10 scene-guard WHAT-IF (analysis only; the app default minAreaFrac 0.01 is NOT changed). G3 detections at the rubric score 0.35 on a
DEV image list + a DEV negative list are passed through ml/eval/scene_guard.py at several minAreaFrac values; reports TPs kept
(class-aware IoU >= 0.5, greedy by score), FPs kept on positive images, images with any box on negatives, and the GT share below each
area threshold. Labels are dataset / agent-curated: EXPLORATORY.
  python ml/eval/g10_guard_whatif.py --model best.pt --imgsz 480 --list val.txt --neg negdev.txt --out out.json
"""
import argparse, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scene_guard import scene_guard  # noqa: E402
from size_buckets import gt_of, iou  # noqa: E402
TH = [0.0, 0.001, 0.0025, 0.005, 0.01, 0.02]
ap = argparse.ArgumentParser(); [ap.add_argument(x, required=True) for x in ("--model", "--list", "--neg", "--out")]; ap.add_argument("--imgsz", type=int, default=480)
a = ap.parse_args()
from ultralytics import YOLO
m = YOLO(a.model)
def dets(f):
    r = m.predict(f, imgsz=a.imgsz, conf=0.35, iou=0.7, verbose=False, device="cpu")[0]; H, W = r.orig_shape
    return [dict(box=[b[0] / W, b[1] / H, b[2] / W, b[3] / H], score=float(s), classId=int(c)) for b, s, c in zip(r.boxes.xyxy.numpy(), r.boxes.conf.numpy(), r.boxes.cls.numpy())], W, H
res = {t: dict(tp=0, fp=0, neg_imgs=0, neg_boxes=0) for t in TH}; gt_n = 0; gt_below = {t: 0 for t in TH}
for f in [l.strip() for l in open(a.list) if l.strip()]:
    D, W, H = dets(f); gt = gt_of(f, W, H); gt_n += len(gt)
    for c, b in gt:
        for t in TH: gt_below[t] += ((b[2] - b[0]) * (b[3] - b[1]) / (W * H)) < t
    for t in TH:
        k = sorted(scene_guard(D, maxSameClass=0, minAreaFrac=t), key=lambda d: -d["score"]); used = set()
        for d in k:
            bb = np.array(d["box"]) * [W, H, W, H]; best, bi = 0.5, -1
            for gi, (c, g) in enumerate(gt):
                if gi not in used and c == d["classId"] and iou(bb, g) >= best: best, bi = iou(bb, g), gi
            if bi >= 0: used.add(bi); res[t]["tp"] += 1
            else: res[t]["fp"] += 1
nl = [l.strip() for l in open(a.neg) if l.strip()]
for f in nl:
    D, _, _ = dets(f)
    for t in TH:
        k = scene_guard(D, maxSameClass=0, minAreaFrac=t); res[t]["neg_imgs"] += len(k) > 0; res[t]["neg_boxes"] += len(k)
out = dict(model=a.model, imgsz=a.imgsz, list=a.list, neg=a.neg, n_neg=len(nl), gt_boxes=gt_n, score=0.35, maxSameClass=0,
           label_status="dataset / agent-curated labels; EXPLORATORY", rows=[dict(minAreaFrac=t, **res[t], recall=round(res[t]["tp"] / max(1, gt_n), 4),
           gt_share_below=round(gt_below[t] / max(1, gt_n), 4), neg_image_rate=round(res[t]["neg_imgs"] / max(1, len(nl)), 4)) for t in TH])
json.dump(out, open(a.out, "w"), indent=1); [print(r) for r in out["rows"]]
