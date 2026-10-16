"""Image-level false alarms on the LOCKED neg_test backgrounds (COCO val2017, no produce).

For each detector: fraction of neg_test images with >=1 box at score >= RUBRIC.detectorMinScore
(0.35, the app's display threshold), mean boxes per image, and the classes that fire.
  python ml/eval/neg_fa.py --model a.pt --model b.pt --imgsz 320 --images /tmp/nsdata2/neg/images/neg_test --out ml/runs/G2/neg_fa.json
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from grading.rules import RUBRIC  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", action="append", required=True)
    ap.add_argument("--imgsz", type=int, default=320)
    ap.add_argument("--images", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--e2e", action="store_true", help="also report the NMS-free one2one head (nms=False) for YOLO26")
    a = ap.parse_args()
    from ultralytics import YOLO
    files = sorted(glob.glob(f"{a.images}/*.jpg"))
    thr = RUBRIC["detectorMinScore"]
    rep = dict(images=a.images, n=len(files), score_threshold=thr, imgsz=a.imgsz, device="cpu", results={})
    for mp in a.model:
        m = YOLO(mp)
        for e2e in ([False, True] if a.e2e else [False]):
            kw = dict(nms=False) if e2e else {}
            n_img, n_box, cls = 0, 0, collections.Counter()
            for f in files:
                r = m.predict(f, imgsz=a.imgsz, conf=thr, device="cpu", verbose=False, **kw)[0]
                k = len(r.boxes)
                n_img += k > 0
                n_box += k
                for c in r.boxes.cls.tolist():
                    cls[m.names[int(c)]] += 1
            rep["results"][mp + (" [one2one]" if e2e else "")] = dict(images_with_false_alarm=n_img, fa_image_rate=round(n_img / len(files), 4),
                                                                     boxes_per_image=round(n_box / len(files), 3), classes=dict(cls.most_common()))
            print(mp, e2e, n_img, len(files), flush=True)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(rep, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
