# G6.1 lemon_lime vs citrus confusion, G3 control ONNX (det_yolo11n_640_raw.onnx) @480, conf 0.25, class-wise NMS 0.7, sandbox CPU.
# For each GT box of citrus / lemon_lime: class of the best-IoU prediction with IoU >= 0.5 (else 'missed'). Splits test_oiv7c (n=181), test (n=557).
import json, collections, sys
sys.argv = ["x"]; import importlib.util
spec = importlib.util.spec_from_file_location("q", "/workspace/work/cv/g6_owl_queue.py")
src = open("/workspace/work/cv/g6_owl_queue.py").read().split("items = [json.loads")[0]  # reuse g3() + iou() only
ns = {}; exec(src, ns)
NAMES = ns["NAMES"]; out = {}
for sp, lst in [("test_oiv7c", "/workspace/work/cv/g4data/test_oiv7c.txt"), ("test", "/workspace/work/cv/g3data/det_v3/test.txt")]:
    cm = collections.defaultdict(collections.Counter)
    for p in open(lst).read().split():
        lp = p.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"
        gts = [l.split() for l in open(lp).read().splitlines() if l.strip()]
        gts = [(int(g[0]), *map(float, g[1:5])) for g in gts if int(g[0]) in (3, 6)]
        if not gts: continue
        preds, w, h = ns["g3"](p)
        for c, x, y, bw, bh in gts:
            b = [x - bw / 2, y - bh / 2, x + bw / 2, y + bh / 2]
            best = max(((ns["iou"](b, pb), NAMES[pc]) for pc, s, pb in preds), default=(0, None))
            cm[NAMES[c]][best[1] if best[0] >= 0.5 else "missed"] += 1
    out[sp] = {k: dict(v) for k, v in cm.items()}
    print(sp, out[sp], flush=True)
json.dump(dict(model="G3 control det_yolo11n_640_raw.onnx", imgsz=480, conf=0.25, iou_match=0.5, device="sandbox CPU onnxruntime", result=out),
          open("/workspace/work/nutrisole/ml/runs/G6/audit/g3_confusion_lemon_citrus.json", "w"), indent=1)
