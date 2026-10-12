#!/usr/bin/env python3
"""G6.1 OWLv2 review-queue ordering (1 172 G4 proposals, all pending_review). Does NOT accept or change any label.
Priority = uncertainty (teacher score near 0.5) + suspected-mistake flags + training impact (class rarity in G3 train).
Suspected-mistake flags: G3 control disagrees (different class at IoU>=0.5), large box (group/pile, area>0.25),
tiny box (<12 px at 480), same-box cross-class teacher proposal (citrus<->lemon_lime etc.), lemon_lime/citrus.
G3 control = det_yolo11n_640_raw.onnx @480, conf 0.25, class-wise NMS 0.7 (sandbox CPU, onnxruntime).
Out: ml/runs/G6/audit/owl_review_queue_prioritised.csv (+ json summary)."""
import json, csv, os, collections
import cv2, numpy as np, onnxruntime as ort
Q = "/workspace/work/nutrisole/ml/runs/G4/teacher_owlv2/review_queue.jsonl"
IMG = "/workspace/work/cv/g4data/"
OUT = "/workspace/work/nutrisole/ml/runs/G6/audit"; os.makedirs(OUT, exist_ok=True)
NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
TRAIN_INST = json.load(open("/workspace/work/cv/g6data/audit/audit.json"))["class_instances"]["train"]
det = ort.InferenceSession("/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx", providers=["CPUExecutionProvider"])
S = 480


def g3(path):
    im = cv2.imread(path); h, w = im.shape[:2]; r = S / max(h, w)
    rs = cv2.resize(im, (int(round(w * r)), int(round(h * r)))); c = np.full((S, S, 3), 114, np.uint8)
    py, px = (S - rs.shape[0]) // 2, (S - rs.shape[1]) // 2; c[py:py + rs.shape[0], px:px + rs.shape[1]] = rs
    x = c[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255
    o = det.run(None, {det.get_inputs()[0].name: x})[0][0].T
    sc = o[:, 4:]; cl = sc.argmax(1); cf = sc.max(1); k = cf >= 0.25; o, cl, cf = o[k], cl[k], cf[k]
    res = []
    for c_ in set(cl.tolist()):
        m = cl == c_; b = o[m, :4]; xywh = [[float(bx - bw / 2), float(by - bh / 2), float(bw), float(bh)] for bx, by, bw, bh in b]
        for i in np.array(cv2.dnn.NMSBoxes(xywh, cf[m].tolist(), 0.25, 0.7)).flatten():
            x0, y0, bw, bh = xywh[i]
            res.append((int(c_), float(cf[m][i]), [(x0 - px) / r / w, (y0 - py) / r / h, (x0 + bw - px) / r / w, (y0 + bh - py) / r / h]))
    return res, w, h


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - ix * iy
    return ix * iy / u if u > 0 else 0


items = [json.loads(l) for l in open(Q)]
cache = {}
for it in items:
    p = IMG + it["image"]
    if p not in cache: cache[p] = g3(p)
byimg = collections.defaultdict(list)
for k, it in enumerate(items): byimg[it["image"]].append(k)
maxinst = max(TRAIN_INST.values())
rows = []
for k, it in enumerate(items):
    preds, w, h = cache[IMG + it["image"]]; b = it["box_xyxy_norm"]; c = it["proposal_class"]
    best = max(((iou(b, pb), NAMES[pc], s) for pc, s, pb in preds), default=(0, None, 0))
    g3_agree = best[0] >= 0.5 and best[1] == c; g3_conflict = best[0] >= 0.5 and best[1] != c
    area = (b[2] - b[0]) * (b[3] - b[1]); sc480 = 480 / max(w, h)
    minpx = min((b[2] - b[0]) * w, (b[3] - b[1]) * h) * sc480
    cross = any(items[j]["proposal_class"] != c and iou(b, items[j]["box_xyxy_norm"]) >= 0.5 for j in byimg[it["image"]] if j != k)
    flags = [f for f, v in [("g3_conflict", g3_conflict), ("group_box", area > 0.25), ("tiny_box", minpx < 12),
                            ("teacher_cross_class", cross), ("citrus_lemon_lime", c in ("citrus", "lemon_lime")),
                            ("g3_missed", best[0] < 0.5)] if v]
    unc = 1 - abs(it["score"] - 0.5) * 2
    rarity = 1 - TRAIN_INST.get(c, 0) / maxinst
    pr = round(1.0 * unc + 0.6 * ("g3_conflict" in flags) + 0.4 * ("teacher_cross_class" in flags) + 0.3 * ("group_box" in flags)
               + 0.2 * ("tiny_box" in flags) + 0.5 * rarity + 0.15 * ("citrus_lemon_lime" in flags), 4)
    rows.append(dict(queue_idx=k, image=it["image"], proposal_class=c, teacher_score=it["score"], box_xyxy_norm=b,
                     g3_best_iou=round(best[0], 3), g3_best_class=best[1], g3_best_conf=round(best[2], 3),
                     flags="|".join(flags), uncertainty=round(unc, 3), rarity=round(rarity, 3), priority=pr,
                     status="pending_review", decision=""))
rows.sort(key=lambda r: -r["priority"])
for i, r in enumerate(rows): r["rank"] = i + 1
with open(f"{OUT}/owl_review_queue_prioritised.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["rank"] + [k for k in rows[0] if k != "rank"]); w.writeheader(); w.writerows(rows)
summ = dict(n=len(rows), n_images=len(byimg), by_class=dict(collections.Counter(r["proposal_class"] for r in rows)),
            flags=dict(collections.Counter(f for r in rows for f in r["flags"].split("|") if f)),
            g3_agree=sum(r["g3_best_iou"] >= 0.5 and r["g3_best_class"] == r["proposal_class"] for r in rows),
            top20=[(r["rank"], r["image"], r["proposal_class"], r["teacher_score"], r["flags"]) for r in rows[:20]],
            note="ordering only; all 1 172 items remain pending_review (no human review in sandbox); nothing enters training")
json.dump(summ, open(f"{OUT}/owl_review_queue_summary.json", "w"), indent=1)
print(json.dumps({k: summ[k] for k in ["n", "n_images", "by_class", "flags", "g3_agree"]}, indent=1))
