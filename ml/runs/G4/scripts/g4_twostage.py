# G4.3b two-stage experiment (CPU, onnxruntime): stage 1 = G3 yolo11n@480 boxes used CLASS-AGNOSTICALLY (proxy for a
# class-agnostic produce detector; a dedicated 1-class detector was not trained in G4), stage 2 = type crop classifier.
# Single-stage arm = same boxes with the detector's own class. Same top-K boxes, same AP code, so the comparison is fair.
import sys, os, json, glob, time, collections, numpy as np, cv2, onnxruntime as ort
sys.path.insert(0, "/workspace/work/nutrisole/ml/eval"); from geometry import letterbox, dst_to_src
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
DET = "/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx"; TYPE = sys.argv[1]; K = 30
so = ort.SessionOptions(); so.intra_op_num_threads = 2
det = ort.InferenceSession(DET, so, providers=["CPUExecutionProvider"]); di = det.get_inputs()[0].name
typ = ort.InferenceSession(TYPE, so, providers=["CPUExecutionProvider"]); ti = typ.get_inputs()[0].name
meta = json.load(open(sys.argv[2]))  # type_g4.json from the kernel (names)
TN = [meta["names"][str(i)] if isinstance(meta["names"], dict) else meta["names"][i] for i in range(len(meta["names"]))]
def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i + 1e-9)
def raw_boxes(out, conf=0.001):
    p = out[0].T  # (N, 4+nc) xywh + class scores
    sc = p[:, 4:]; cls = sc.argmax(1); s = sc.max(1); keep = s >= conf; p, cls, s = p[keep], cls[keep], s[keep]
    b = np.stack([p[:, 0] - p[:, 2] / 2, p[:, 1] - p[:, 3] / 2, p[:, 0] + p[:, 2] / 2, p[:, 1] + p[:, 3] / 2], 1)
    o = np.argsort(-s); sel = []
    for i in o:  # class-agnostic NMS 0.7 (both arms share these boxes)
        if all(iou(b[i], b[j]) <= 0.7 for j in sel): sel.append(i)
        if len(sel) >= K: break
    return [(b[i], int(cls[i]), float(s[i])) for i in sel]
def cls_prep(crop, sz=128):
    im = cv2.resize(crop, (sz, sz), interpolation=cv2.INTER_LINEAR)[:, :, ::-1].astype(np.float32) / 255.0
    return im.transpose(2, 0, 1)[None]
def ap(tp, conf, npos):
    o = np.argsort(-np.array(conf)); tp = np.array(tp)[o]; fp = 1 - tp; tpc, fpc = np.cumsum(tp), np.cumsum(fp)
    rec = tpc / npos; prec = tpc / np.maximum(tpc + fpc, 1e-9); mrec = np.concatenate([[0], rec, [1]]); mpre = np.concatenate([[1], prec, [0]])
    for i in range(len(mpre) - 2, -1, -1): mpre[i] = max(mpre[i], mpre[i + 1])
    xs = np.linspace(0, 1, 101); return float(np.trapezoid(np.interp(xs, mrec, mpre), xs))
res = {}
for sp, lst in [("test_rf", "/workspace/work/cv/g3data/det_v3/test_rf.txt"), ("test_oiv7", "/workspace/work/cv/g3data/det_v3/test_oiv7.txt"), ("test_oiv7c", "/workspace/work/cv/g4data/test_oiv7c.txt")]:
    files = [l.strip() for l in open(lst) if l.strip()]
    arms = {"single": collections.defaultdict(lambda: [[], []]), "two_stage": collections.defaultdict(lambda: [[], []])}; npos = collections.Counter(); lat = []
    for f in files:
        im = cv2.imread(f); H, W = im.shape[:2]
        lp = f.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"
        G = []
        if os.path.exists(lp):
            for l in open(lp):
                v = l.split()
                if len(v) == 5: c, x, y, w, h = int(v[0]), *map(float, v[1:]); G.append((c, [(x - w / 2) * W, (y - h / 2) * H, (x + w / 2) * W, (y + h / 2) * H])); npos[c] += 1
        t0 = time.perf_counter(); x, tf = letterbox(im, 480); bx = raw_boxes(det.run(None, {di: x})[0]); t1 = time.perf_counter()
        preds = {"single": [], "two_stage": []}
        for b, c, s in bx:
            bb = dst_to_src(list(b), tf); preds["single"].append((bb, c, s))
            pw, ph = 0.1 * (bb[2] - bb[0]), 0.1 * (bb[3] - bb[1])
            cr = im[int(max(0, bb[1] - ph)):int(min(H, bb[3] + ph)), int(max(0, bb[0] - pw)):int(min(W, bb[2] + pw))]
            if cr.size == 0 or min(cr.shape[:2]) < 4: continue
            p = typ.run(None, {ti: cls_prep(cr)})[0][0]; k = int(p.argmax())
            if TN[k] == "other": continue
            preds["two_stage"].append((bb, N.index(TN[k]), s * float(p[k])))
        lat.append(((t1 - t0) * 1000, (time.perf_counter() - t0) * 1000))
        for arm, P in preds.items():
            used = set()
            for bb, c, s in sorted(P, key=lambda z: -z[2]):
                best, bj = 0.0, -1
                for j, (gc, gb) in enumerate(G):
                    if gc == c and j not in used:
                        v = iou(bb, gb)
                        if v > best: best, bj = v, j
                ok = best >= 0.5
                if ok: used.add(bj)
                arms[arm][c][0].append(int(ok)); arms[arm][c][1].append(s)
    out = {}
    for arm, d in arms.items():
        pc = {N[c]: round(ap(d[c][0], d[c][1], npos[c]), 4) if d[c][0] else 0.0 for c in sorted(npos)}
        out[arm] = dict(mAP50=round(float(np.mean(list(pc.values()))), 4), per_class=pc)
    la = np.array(lat); res[sp] = dict(n_images=len(files), gt_instances={N[c]: n for c, n in sorted(npos.items())}, **out,
                                         latency_ms=dict(det_p50=round(float(np.median(la[:, 0])), 1), det_plus_type_p50=round(float(np.median(la[:, 1])), 1), boxes_classified_max=K))
    print(sp, json.dumps({a: res[sp][a]["mAP50"] for a in ("single", "two_stage")}), res[sp]["latency_ms"], flush=True)
res["setup"] = dict(stage1=DET + " (class-agnostic NMS 0.7, top-30, conf>=0.001)", stage2=TYPE, imgsz_det=480, imgsz_type=128, device="sandbox CPU x2, onnxruntime",
                    note="stage 1 is the G3 multi-class detector used class-agnostically (proxy); a dedicated class-agnostic detector is G5 work; mAP from this script's own AP code (101-pt), not Ultralytics")
os.makedirs("/workspace/work/nutrisole/ml/runs/G4/two_stage", exist_ok=True)
json.dump(res, open("/workspace/work/nutrisole/ml/runs/G4/two_stage/two_stage.json", "w"), indent=1)
