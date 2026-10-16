"""Stage G shared model wrappers (sandbox CPU, ONNX Runtime FP32). G3 detector unchanged; condition E224; per-fruit ripeness head
(recorded as a separate chip, never merged into A/B/C); measurements + rules rubric-v0.2-g2."""
import sys, time, cv2, numpy as np, onnxruntime as ort
sys.path.insert(0, "/workspace/work/nutrisole")
from ml.grading.measure import measure
from ml.grading.rules import grade as rules_grade
from ml.eval.closeup import letterbox_transform, detector_to_frame
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
DET = "/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx"; CLS = "/workspace/work/cv/g3models/cls/E_224_e15_b64_sgd01.onnx"
RIPE = "/workspace/work/cv/g7models/ripe/best.onnx"
VERSIONS = dict(detector="G3 det_yolo11n_640_raw imgsz480 sha256 c6fcb32a (conf .35, NMS .7, 1% guard)", condition="E_224_e15_b64_sgd01 (fresh/rotten)",
                ripeness="g7 per-fruit ripeness yolo-cls 224 (15 classes, chip only)", rubric="rubric-v0.2-g2", measure="ml/grading/measure.py (grabcut)")
so = ort.SessionOptions(); so.intra_op_num_threads = 2; so.inter_op_num_threads = 1
_d = ort.InferenceSession(DET, so, providers=["CPUExecutionProvider"]); _c = ort.InferenceSession(CLS, so, providers=["CPUExecutionProvider"])
_r = ort.InferenceSession(RIPE, so, providers=["CPUExecutionProvider"])
RIPE_NAMES = [_r.get_modelmeta().custom_metadata_map.get("names")]; import ast; RIPE_NAMES = [v for k, v in sorted(ast.literal_eval(RIPE_NAMES[0]).items())]
RIPE_FRUIT = {"apple": "apple", "banana": "banana", "mango": "mango", "citrus": "orange", "tomato": "tomato"}

def detect(bgr, conf=0.35, iou=0.7, min_area=0.01):
    """Full-res BGR frame -> detections in FRAME pixels [(box, cls, score)], G3 post-processing."""
    H, W = bgr.shape[:2]; t = letterbox_transform(W, H); nw, nh = round(W * t["sx"]), round(H * t["sy"])
    im = np.full((480, 480, 3), 114, np.uint8); im[t["py"]:t["py"] + nh, t["px"]:t["px"] + nw] = cv2.resize(bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
    x = im[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255
    o = _d.run(None, {_d.get_inputs()[0].name: x})[0][0]; sc = o[4:]; cl = sc.argmax(0); s = sc.max(0); k = s >= conf
    b = o[:4, k].T; cl, s = cl[k], s[k]; bx = np.stack([b[:, 0] - b[:, 2] / 2, b[:, 1] - b[:, 3] / 2, b[:, 0] + b[:, 2] / 2, b[:, 1] + b[:, 3] / 2], 1) if len(b) else np.zeros((0, 4))
    keep = []
    for i in np.argsort(-s):
        if any(cl[j] == cl[i] and _iou(bx[i], bx[j]) > iou for j in keep): continue
        keep.append(i)
    out = []
    for i in keep:
        fb = detector_to_frame(bx[i].tolist(), W, H)
        if (fb[2] - fb[0]) * (fb[3] - fb[1]) >= min_area * W * H: out.append((fb, int(cl[i]), float(s[i])))
    return out

def _iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i; return i / u if u > 0 else 0

def _cls_in(crop):
    h, w = crop.shape[:2]; sc = 224 / min(h, w); im = cv2.resize(crop, (max(224, round(w * sc)), max(224, round(h * sc))), interpolation=cv2.INTER_LINEAR)
    y0, x0 = (im.shape[0] - 224) // 2, (im.shape[1] - 224) // 2; return im[y0:y0 + 224, x0:x0 + 224][:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255

def condition(crop):
    p = _c.run(None, {_c.get_inputs()[0].name: _cls_in(crop)})[0][0]; return dict(fresh=float(p[0]), rotten=float(p[1]))

def ripeness(crop, cls):
    f = RIPE_FRUIT.get(cls)
    if not f: return dict(status="not_applicable")
    p = _r.run(None, {_r.get_inputs()[0].name: _cls_in(crop)})[0][0]; idx = [RIPE_NAMES.index(f"{f}_{s}") for s in ("unripe", "ripe", "overripe")]
    sp = p[idx]; mass = float(sp.sum())
    if mass < 0.5: return dict(status="unknown", mass=round(mass, 3))
    cp = sp / mass; o = np.argsort(-cp)
    if cp[o[0]] < 0.6 or cp[o[0]] - cp[o[1]] < 0.15: return dict(status="unknown", conf=round(float(cp[o[0]]), 3))
    return dict(status="assessed", stage=["unripe", "ripe", "overripe"][o[0]], conf=round(float(cp[o[0]]), 3))

def assess(crop_bgr, cls, timings=None):
    """Existing pipeline on one crop: condition -> measurements -> rules grade (+ ripeness chip). Returns dict incl. quality inputs."""
    T = timings if timings is not None else {}
    t = time.perf_counter(); pr = condition(crop_bgr); T["condition"] = (time.perf_counter() - t) * 1e3
    t = time.perf_counter(); m = measure(crop_bgr[:, :, ::-1].copy(), cls).__dict__; T["measure"] = (time.perf_counter() - t) * 1e3
    t = time.perf_counter(); rp = ripeness(crop_bgr, cls); T["ripeness"] = (time.perf_counter() - t) * 1e3
    t = time.perf_counter(); g = rules_grade(cls, 1.0, pr, m); T["rules"] = (time.perf_counter() - t) * 1e3
    mx = max(pr.values()); mg = abs(pr["fresh"] - pr["rotten"])
    return dict(probs=pr, cond="fresh" if pr["fresh"] >= pr["rotten"] else "rotten", grade=g["grade"], status=g["status"], reasons=g["reasons"],
                blurVar=m["blur_var"], meanV=m["mean_v"], visibleFrac=m["mask_fraction"], maxProb=mx, margin=mg, ripeness=rp)
