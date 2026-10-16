"""Failure dump (stage 4d): worst classifier errors by loss and worst detector images by
(missed + false boxes at the app threshold 0.35), as contact sheets + JSON.

  python ml/eval/failures.py --cls best.pt --cls-data /tmp/nsdata/quality2 --temp T \
      --det best.pt --det-root /tmp/nsdata/det --out ml/runs/G1/failures
"""
import argparse
import collections
import glob
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tracker import iou  # noqa: E402

NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]


def sheet(tiles, cols, path):
    if not tiles:
        return
    h = max(t.shape[0] for t in tiles)
    w = max(t.shape[1] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, h - t.shape[0], 0, w - t.shape[1], cv2.BORDER_CONSTANT, value=(0, 0, 0)) for t in tiles]
    rows = [np.hstack(tiles[i:i + cols] + [np.zeros_like(tiles[0])] * (cols - len(tiles[i:i + cols]))) for i in range(0, len(tiles), cols)]
    cv2.imwrite(path, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cls")
    ap.add_argument("--cls-data")
    ap.add_argument("--cls-imgsz", type=int, default=192)
    ap.add_argument("--temp", type=float, default=1.0)
    ap.add_argument("--det")
    ap.add_argument("--det-root")
    ap.add_argument("--imgsz", type=int, default=320)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from ultralytics import YOLO
    os.makedirs(a.out, exist_ok=True)
    rep = {}
    if a.cls:
        m = YOLO(a.cls)
        names = [m.names[i] for i in range(len(m.names))]
        rows = []
        for ci, n in enumerate(names):
            for f in sorted(glob.glob(f"{a.cls_data}/test/{n}/*.jpg")):
                p = m.predict(f, imgsz=a.cls_imgsz, verbose=False, device="cpu")[0].probs.data.numpy().astype(np.float64)
                lg = np.log(np.clip(p, 1e-12, 1)) / a.temp
                pc = np.exp(lg - lg.max())
                pc /= pc.sum()
                rows.append(dict(file=os.path.basename(f), path=f, label=n, pred=names[int(pc.argmax())], p_true=float(pc[ci]), loss=float(-np.log(max(pc[ci], 1e-12)))))
        rows.sort(key=lambda r: -r["loss"])
        worst = rows[:50]
        tiles = []
        for r in worst[:24]:
            im = cv2.imread(r["path"])
            im = cv2.resize(im, (160, int(160 * im.shape[0] / im.shape[1])))
            col = (0, 0, 255) if r["pred"] != r["label"] else (0, 200, 255)
            cv2.putText(im, f"GT {r['label']} p={r['p_true']:.2f}", (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, col, 1, cv2.LINE_AA)
            cv2.putText(im, r["file"].split("__")[0], (3, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.42, col, 1, cv2.LINE_AA)
            tiles.append(im)
        sheet(tiles, 6, f"{a.out}/cls_worst.jpg")
        rep["classifier"] = dict(n=len(rows), errors=sum(r["pred"] != r["label"] for r in rows),
                                 errors_by_produce=dict(collections.Counter(r["file"].split("__")[0] + ":" + r["label"] for r in rows if r["pred"] != r["label"])),
                                 worst50=[{k: r[k] for k in ["file", "label", "pred", "p_true", "loss"]} for r in worst])
    if a.det:
        m = YOLO(a.det)
        rows = []
        confusions = collections.Counter()
        for ip in sorted(glob.glob(f"{a.det_root}/images/test/*.jpg")):
            im = cv2.imread(ip)
            H, W = im.shape[:2]
            lp = ip.replace("/images/", "/labels/").replace(".jpg", ".txt")
            gts = []
            for l in open(lp).read().strip().splitlines():
                if l.strip():
                    c, x, y, w, h = l.split()
                    x, y, w, h = map(float, (x, y, w, h))
                    gts.append((int(c), [(x - w / 2) * W, (y - h / 2) * H, (x + w / 2) * W, (y + h / 2) * H]))
            r = m.predict(im, imgsz=a.imgsz, rect=False, conf=0.35, verbose=False, device="cpu")[0]
            preds = [(int(c), b.tolist(), float(s)) for b, s, c in zip(r.boxes.xyxy.numpy(), r.boxes.conf.numpy(), r.boxes.cls.numpy())]
            used, fn, wrong, missed_cls = set(), 0, 0, []
            for gc, gb in gts:
                best, bj = 0.0, -1
                for j, (pc, pb, ps) in enumerate(preds):
                    if j in used:
                        continue
                    v = iou(gb, pb)
                    if v > best:
                        best, bj = v, j
                if bj >= 0 and best >= 0.5:
                    used.add(bj)
                    if preds[bj][0] != gc:
                        wrong += 1
                        confusions[(NAMES[gc], NAMES[preds[bj][0]])] += 1
                else:
                    fn += 1
                    missed_cls.append(NAMES[gc])
            fp = len(preds) - len(used)
            rows.append(dict(file=os.path.basename(ip), path=ip, gt=len(gts), fn=fn, fp=fp, wrong_class=wrong, score=fn + fp + wrong,
                             gts=gts, preds=preds, negative=len(gts) == 0, missed_cls=missed_cls))
        rows.sort(key=lambda r: -r["score"])
        tiles = []
        for r in rows[:24]:
            im = cv2.imread(r["path"])
            for gc, gb in r["gts"]:
                cv2.rectangle(im, (int(gb[0]), int(gb[1])), (int(gb[2]), int(gb[3])), (255, 255, 255), 2)
            for pc, pb, ps in r["preds"]:
                cv2.rectangle(im, (int(pb[0]), int(pb[1])), (int(pb[2]), int(pb[3])), (0, 0, 255), 2)
                cv2.putText(im, f"{NAMES[pc]} {ps:.2f}", (int(pb[0]) + 2, int(pb[1]) + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
            s = 220 / im.shape[1]
            im = cv2.resize(im, (220, int(im.shape[0] * s)))
            cv2.putText(im, f"FN{r['fn']} FP{r['fp']} WC{r['wrong_class']}", (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
            tiles.append(im)
        sheet(tiles, 6, f"{a.out}/det_worst.jpg")
        neg = [r for r in rows if r["negative"]]
        rep["detector"] = dict(n_images=len(rows), total_gt=sum(r["gt"] for r in rows), missed=sum(r["fn"] for r in rows), false_boxes=sum(r["fp"] for r in rows),
                               wrong_class=sum(r["wrong_class"] for r in rows), negatives=len(neg), negatives_with_any_box=sum(1 for r in neg if r["preds"]),
                               gt_by_class=dict(collections.Counter(NAMES[gc] for r in rows for gc, gb in r["gts"])),
                               missed_by_class=dict(collections.Counter(c for r in rows for c in r["missed_cls"])),
                               top_confusions=[dict(gt=k[0], pred=k[1], n=v) for k, v in confusions.most_common(10)],
                               worst50=[{k: r[k] for k in ["file", "gt", "fn", "fp", "wrong_class"]} for r in rows[:50]])
    json.dump(rep, open(f"{a.out}/failures.json", "w"), indent=1)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("worst50",)} for k, v in rep.items()}, indent=1))


if __name__ == "__main__":
    main()
