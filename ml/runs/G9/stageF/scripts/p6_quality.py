"""Stage F P6: does a market-scale detection carry enough pixels for condition / ripeness / defect grading?
(1) M-DEV v2 boxed items: side (sqrt area) in px at the 480 detector input, at the 1280-px Commons rendition, and projected onto a
    1920-px (1080p) and 3840-px (4K) camera frame for the same fraction of the frame.
(2) Empirical stability: the deployed condition classifier (E_224 fresh/rotten, 224 px, centre crop) on native crops of items whose native
    side >= 64 px, vs the same crop degraded to side 12 / 16 / 24 / 32 / 48 px and resized back (what a small detection gives).
    Reported: label flips vs the native prediction and mean max-prob. Not a grade: only a resolution-sensitivity measurement.
(3) Example montage: native vs degraded crops. Usage: p6_quality.py OUT_DIR"""
import json, sys, cv2, numpy as np, onnxruntime as ort, collections, random
OUT = sys.argv[1]; L = json.load(open("/workspace/work/nutrisole/ml/runs/G9/stageF/m_labels_v2.json"))
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
so = ort.SessionOptions(); so.intra_op_num_threads = 2
s = ort.InferenceSession("/workspace/work/cv/g3models/cls/E_224_e15_b64_sgd01.onnx", so, providers=["CPUExecutionProvider"]); di = s.get_inputs()[0].name
def cls(crop):
    h, w = crop.shape[:2]; sc = 224 / min(h, w); im = cv2.resize(crop, (max(224, round(w * sc)), max(224, round(h * sc))), interpolation=cv2.INTER_LINEAR)
    y0, x0 = (im.shape[0] - 224) // 2, (im.shape[1] - 224) // 2; im = im[y0:y0 + 224, x0:x0 + 224][:, :, ::-1].astype(np.float32) / 255
    p = s.run(None, {di: im.transpose(2, 0, 1)[None]})[0][0]; p = np.exp(p - p.max()) / np.exp(p - p.max()).sum() if p.min() < 0 or p.sum() > 1.01 else p
    return int(np.argmax(p)), float(p.max())
sizes = collections.defaultdict(list); big = []
for i, v in L.items():
    if v["status"] != "ok": continue
    im = cv2.imread(f"/workspace/work/cv/g9e/commons/img/{i}.jpg"); H, W = im.shape[:2]
    for b in v["boxes"]:
        bw, bh = (b[2] - b[0]) * W, (b[3] - b[1]) * H; side = (bw * bh) ** .5; frac = (b[2] - b[0]) * (b[3] - b[1])
        sizes["native1280"].append(side); sizes["det480"].append(side * 480 / max(W, H)); sizes["cam1920"].append(side * 1920 / max(W, H)); sizes["cam3840"].append(side * 3840 / max(W, H))
        sizes["frac"].append(frac)
        if side >= 64: big.append((i, b, im[max(0, int(b[1] * H)):int(b[3] * H), max(0, int(b[0] * W)):int(b[2] * W)].copy()))
def pct(a): a = np.array(a); return {f"p{q}": round(float(np.percentile(a, q)), 1) for q in (10, 25, 50, 75, 90)}
res = dict(n_boxes=len(sizes["det480"]), side_px={k: pct(v) for k, v in sizes.items() if k != "frac"},
           share_below={k: {f"<{t}px": round(float(np.mean(np.array(sizes[k]) < t)), 3) for t in (16, 24, 32, 64, 100)} for k in ("det480", "native1280", "cam1920", "cam3840")})
random.seed(0); random.shuffle(big); big = big[:150]; DEG = [12, 16, 24, 32, 48]; flips = {d: 0 for d in DEG}; conf = {d: [] for d in DEG}; nat_conf = []; nat_lab = collections.Counter()
ex = []
for k, (i, b, c) in enumerate(big):
    l0, p0 = cls(c); nat_conf.append(p0); nat_lab[l0] += 1; row = [cv2.resize(c, (128, 128))]
    for d in DEG:
        sc = d / max(c.shape[:2]); small = cv2.resize(c, (max(2, round(c.shape[1] * sc)), max(2, round(c.shape[0] * sc))), interpolation=cv2.INTER_AREA)
        back = cv2.resize(small, (c.shape[1], c.shape[0]), interpolation=cv2.INTER_LINEAR); l, p = cls(back); flips[d] += l != l0; conf[d].append(p)
        row.append(cv2.resize(small, (128, 128), interpolation=cv2.INTER_NEAREST))
    if k < 6: ex.append(np.hstack(row))
res["stability"] = dict(n_items=len(big), classifier="E_224 fresh/rotten (deployed condition model)", native_label_counts=dict(nat_lab), native_mean_maxprob=round(float(np.mean(nat_conf)), 3),
                        degraded={f"{d}px": dict(flip_rate=round(flips[d] / len(big), 3), mean_maxprob=round(float(np.mean(conf[d])), 3)) for d in DEG})
if ex:
    m = np.vstack(ex); hdr = np.zeros((24, m.shape[1], 3), np.uint8)
    for j, t in enumerate(["native"] + [f"{d}px" for d in DEG]): cv2.putText(hdr, t, (j * 128 + 4, 17), 0, .5, (255, 255, 255), 1)
    cv2.imwrite(f"{OUT}/p6_examples.jpg", np.vstack([hdr, m]), [cv2.IMWRITE_JPEG_QUALITY, 88])
json.dump(res, open(f"{OUT}/p6_quality.json", "w"), indent=1); print(json.dumps(res)[:1500])
