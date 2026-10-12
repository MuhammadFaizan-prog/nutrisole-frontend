# G4.3: score OWLv2 proposals against GT (test_rf, test_oiv7: locked splits, read-only) and build the review queue (lvisdrop_val).
import json, os, sys, collections, numpy as np, cv2
P = sys.argv[1]; OUT = "/workspace/work/nutrisole/ml/runs/G4/teacher_owlv2"; os.makedirs(OUT, exist_ok=True)
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
LBL = {"test_rf": "/workspace/work/cv/g3data/det_v3/det/labels/test_rf", "test_oiv7": "/workspace/work/cv/g3data/det_v3/oiv7/labels/test_oiv7",
       "lvisdrop_val": "/workspace/work/cv/g4data/lvisdrop/labels/val"}
IMG = {"lvisdrop_val": "/workspace/work/cv/g4data/lvisdrop/images/val"}
d = json.load(open(P))
def gt(sp, f):
    p = f"{LBL[sp]}/{f.rsplit('.', 1)[0]}.txt"
    out = []
    if os.path.exists(p):
        for l in open(p):
            v = l.split()
            if len(v) == 5:
                c, x, y, w, h = int(v[0]), *map(float, v[1:]); out.append((c, [x - w / 2, y - h / 2, x + w / 2, y + h / 2]))
    return out
def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i + 1e-9)
def nms_cls(dets, thr=0.5):  # per-class NMS (OWLv2 returns one box per query patch)
    keep = []
    for x in sorted(dets, key=lambda z: -z["score"]):
        if all(not (k["cls"] == x["cls"] and iou(k["box"], x["box"]) > thr) for k in keep): keep.append(x)
    return keep
def ap(tp, conf, npos):
    if npos == 0: return None
    o = np.argsort(-np.array(conf)); tp = np.array(tp)[o]; fp = 1 - tp
    tpc, fpc = np.cumsum(tp), np.cumsum(fp); rec = tpc / npos; prec = tpc / np.maximum(tpc + fpc, 1e-9)
    mrec = np.concatenate([[0], rec, [1]]); mpre = np.concatenate([[1], prec, [0]])
    for i in range(len(mpre) - 2, -1, -1): mpre[i] = max(mpre[i], mpre[i + 1])
    xs = np.linspace(0, 1, 101); return float(np.trapezoid(np.interp(xs, mrec, mpre), xs))
res = {}
for sp in ["test_rf", "test_oiv7"]:
    items = d["sets"].get(sp, [])
    per = collections.defaultdict(lambda: dict(tp=[], conf=[], npos=0)); thr_stats = {t: collections.Counter() for t in (0.1, 0.2, 0.3)}; agn = collections.Counter()
    for it in items:
        G = gt(sp, it["file"]); D = nms_cls(it["dets"])
        for c, _ in G: per[c]["npos"] += 1
        used = set()
        for x in sorted(D, key=lambda z: -z["score"]):
            best, bj = 0, -1
            for j, (c, b) in enumerate(G):
                if c == x["cls"] and j not in used and iou(x["box"], b) > best: best, bj = iou(x["box"], b), j
            ok = best >= 0.5
            if ok: used.add(bj)
            per[x["cls"]]["tp"].append(int(ok)); per[x["cls"]]["conf"].append(x["score"])
        for t in thr_stats:
            Dt = [x for x in D if x["score"] >= t]; u = set(); tp = 0
            for x in sorted(Dt, key=lambda z: -z["score"]):
                for j, (c, b) in enumerate(G):
                    if j not in u and c == x["cls"] and iou(x["box"], b) >= 0.5: u.add(j); tp += 1; break
            thr_stats[t]["tp"] += tp; thr_stats[t]["pred"] += len(Dt); thr_stats[t]["gt"] += len(G)
        for c, b in G:  # class-agnostic recall: any proposal (score>=0.1) covers the GT box
            agn["gt"] += 1; agn["hit"] += any(iou(x["box"], b) >= 0.5 for x in D if x["score"] >= 0.1)
    pc = {N[c]: dict(AP50=round(ap(v["tp"], v["conf"], v["npos"]), 4) if v["npos"] else None, n_gt=v["npos"]) for c, v in sorted(per.items()) if v["npos"]}
    vals = [v["AP50"] for v in pc.values() if v["AP50"] is not None]
    res[sp] = dict(n_images=len(items), mAP50_classes_with_gt=round(float(np.mean(vals)), 4) if vals else None, per_class=pc,
                   pr_at_threshold={str(t): dict(P=round(s["tp"] / max(1, s["pred"]), 4), R=round(s["tp"] / max(1, s["gt"]), 4), n_pred=s["pred"], n_gt=s["gt"]) for t, s in thr_stats.items()},
                   class_agnostic_recall_at_0p1=round(agn["hit"] / max(1, agn["gt"]), 4))
    print(sp, json.dumps({k: v for k, v in res[sp].items() if k != "per_class"}))
# review queue: lvisdrop_val proposals (score >= 0.3) not matching an existing LVIS label of the same class
q = []
for it in d["sets"].get("lvisdrop_val", []):
    G = gt("lvisdrop_val", it["file"])
    for x in nms_cls(it["dets"]):
        if x["score"] < 0.3: continue
        if any(c == x["cls"] and iou(x["box"], b) >= 0.5 for c, b in G): continue
        q.append(dict(image=f"lvisdrop/images/val/{it['file']}", proposal_class=N[x["cls"]], prompt=x["prompt"], score=x["score"], box_xyxy_norm=[round(v, 4) for v in x["box"]],
                      status="pending_review", reviewer=None, decision=None))
with open(f"{OUT}/review_queue.jsonl", "w") as f:
    for r in q: f.write(json.dumps(r) + "\n")
res["review_queue"] = dict(n_proposals=len(q), n_images=len({r["image"] for r in q}), by_class=dict(collections.Counter(r["proposal_class"] for r in q)),
                           rule="OWLv2 score >= 0.3, per-class NMS 0.5, not overlapping (IoU>=0.5) an existing LVIS label of the same class", status="ALL pending_review; nothing enters train")
res["teacher"] = dict(model=d["model"], licence=d["licence"], device=d["device"], prompts=d["prompts"], score_floor=d["threshold"])
json.dump(res, open(f"{OUT}/teacher_eval.json", "w"), indent=1); print(res["review_queue"])
# contact sheet of the first 24 queue items for the report
tiles = []
for r in q[:24]:
    im = cv2.imread(f"{IMG['lvisdrop_val']}/{os.path.basename(r['image'])}")
    if im is None: continue
    H, W = im.shape[:2]; b = r["box_xyxy_norm"]; cv2.rectangle(im, (int(b[0] * W), int(b[1] * H)), (int(b[2] * W), int(b[3] * H)), (0, 255, 255), 3)
    im = cv2.resize(im, (256, 192)); cv2.putText(im, f"{r['proposal_class']} {r['score']:.2f}", (4, 16), 0, 0.5, (0, 255, 255), 1); tiles.append(im)
if tiles:
    while len(tiles) % 6: tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(f"{OUT}/review_queue_sample.jpg", np.vstack([np.hstack(tiles[i:i + 6]) for i in range(0, len(tiles), 6)]))
