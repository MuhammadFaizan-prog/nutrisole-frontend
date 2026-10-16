"""G10b Phase 1 (identity, DEV only): end-to-end identity behaviour of the FROZEN G3 + H2 pipeline when ONLY the scene-guard minAreaFrac
changes (0 = no guard, 0.0025, 0.005, 0.01 shipped default). Items = the 378 Stage H identity items (ml/runs/G9/stageH/out/ident_items.jsonl:
CU / CU-neg / H-val / H-eval, all DEV; Stage H tune and eval subsets reported separately). Nothing is tuned here.

Per item and frame: G3 ONNX (c6fcb32a, 480 letterbox, the Stage G g_models.detect decode) at a decode floor (0.35 = Stage H convention; 0.25 =
device DET_DECODE_FLOOR) -> scene guard (ml/eval/scene_guard.py, maxSameClass 0) -> tapped detection (smallest box containing the tap,
closeup.roi_from_tap) -> wide ID via DEFAULT_ID (idMinScore 0.5, idMinHits 3).
  * 1-frame  = Stage H convention: one still, hits assumed 3 (h_ident.py).
  * 3-frame  = burstWide over 3 frames (device debugPipeline.burstWide): 2 deterministic mild jitters (shift +-1.5 %, scale 0.98/1.02, brightness
    0.92/1.08; AGENT-DESIGNED, not a Stage H set) + the original still; H2 crop from the original (last) frame.
Then H2 v2 (20898d7c, h_ident.h2_probs preprocessing) on the 8 %-padded crop of the tapped box and FROZEN_VERIFY (P-a, tau .4, margin 0,
maxUnknown .5). Arms: H0 = wide-only, P-a = wide + H2 agree. No tap-ROI GrabCut refinement is needed: without a tapped box the wide ID is
'unable' and P-a cannot verify. Grading stays OFF (not run); only the 96 px close-up gate side is recorded. Labels: agent-triaged, EXPLORATORY.
  python g10b_ident.py OUT.json
"""
import json, sys, time, collections, hashlib
import cv2, numpy as np, onnxruntime as ort
sys.path.insert(0, "/workspace/work/nutrisole")
from ml.eval.closeup import letterbox_transform, detector_to_frame, roi_from_tap, crop_rect, id_policy
from ml.eval.verify import verify_identity, FROZEN_VERIFY
from ml.eval.scene_guard import scene_guard
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
DET = "/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx"; H2 = "/workspace/work/g9h/h2v2/h2_mnv3s.onnx"
SHA = {DET: "c6fcb32a", H2: "20898d7c"}
for p, s in SHA.items(): assert hashlib.sha256(open(p, "rb").read()).hexdigest().startswith(s), p
so = ort.SessionOptions(); so.intra_op_num_threads = 2; so.inter_op_num_threads = 1
_d = ort.InferenceSession(DET, so, providers=["CPUExecutionProvider"]); _h = ort.InferenceSession(H2, so, providers=["CPUExecutionProvider"])
GUARDS = [0.0, 0.0025, 0.005, 0.01]; FLOORS = [0.35, 0.25]

def _iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i; return i / u if u > 0 else 0

def detect_all(bgr, conf):
    """g_models.detect with min_area=0 (guard applied afterwards): frame-pixel boxes [(box, cls, score)]."""
    H, W = bgr.shape[:2]; t = letterbox_transform(W, H); nw, nh = round(W * t["sx"]), round(H * t["sy"])
    im = np.full((480, 480, 3), 114, np.uint8); im[t["py"]:t["py"] + nh, t["px"]:t["px"] + nw] = cv2.resize(bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
    x = im[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255
    o = _d.run(None, {_d.get_inputs()[0].name: x})[0][0]; sc = o[4:]; cl = sc.argmax(0); s = sc.max(0); k = s >= conf
    b = o[:4, k].T; cl, s = cl[k], s[k]
    bx = np.stack([b[:, 0] - b[:, 2] / 2, b[:, 1] - b[:, 3] / 2, b[:, 0] + b[:, 2] / 2, b[:, 1] + b[:, 3] / 2], 1) if len(b) else np.zeros((0, 4))
    keep = []
    for i in np.argsort(-s):
        if any(cl[j] == cl[i] and _iou(bx[i], bx[j]) > 0.7 for j in keep): continue
        keep.append(i)
    return [(detector_to_frame(bx[i].tolist(), W, H), int(cl[i]), float(s[i])) for i in keep]

def guard(dets, W, H, g):
    D = [dict(box=[b[0] / W, b[1] / H, b[2] / W, b[3] / H], classId=c, score=s, _b=b) for b, c, s in dets]
    return [(d["_b"], d["classId"], d["score"]) for d in scene_guard(D, maxSameClass=0, minAreaFrac=g)]

def tapped(dets, tap, W, H):
    r = roi_from_tap(tap, W, H, [d[0] for d in dets])
    return next(d for d in dets if d[0] == r["box"]) if r["source"] == "track" else None

def h2_probs(crop):
    h, w = crop.shape[:2]; sc = 256 / min(h, w); im = cv2.resize(crop, (max(256, round(w * sc)), max(256, round(h * sc))), interpolation=cv2.INTER_AREA if sc < 1 else cv2.INTER_LINEAR)
    y0, x0 = (im.shape[0] - 224) // 2, (im.shape[1] - 224) // 2; im = im[y0:y0 + 224, x0:x0 + 224][:, :, ::-1].astype(np.float32) / 255
    x = ((im - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)).transpose(2, 0, 1)[None]
    return [float(v) for v in _h.run(None, {"images": x})[0][0]]

JIT = [dict(dx=0.015, dy=-0.01, s=0.98, b=0.92), dict(dx=-0.015, dy=0.01, s=1.02, b=1.08)]
def jitter(im, tap, j):
    H, W = im.shape[:2]; M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, j["s"]); M[0, 2] += j["dx"] * W; M[1, 2] += j["dy"] * H
    out = np.clip(cv2.warpAffine(im, M, (W, H), borderMode=cv2.BORDER_REFLECT).astype(np.float32) * j["b"], 0, 255).astype(np.uint8)
    tx, ty = M @ np.array([tap[0] * W, tap[1] * H, 1.0]); return out, [tx / W, ty / H]

def burst_wide(td):
    ok = [d for d in td if d is not None]
    if not ok: return dict(status="unable", reason="nothing_detected_at_tap")
    cnt = collections.Counter(d[1] for d in ok); cls, hits = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[0]
    return id_policy(cls, min(d[2] for d in ok if d[1] == cls), hits)

if __name__ == "__main__":
    import os; R = [json.loads(l) for l in open("/workspace/work/nutrisole/ml/runs/G9/stageH/out/ident_items.jsonl")]; R = R[:int(os.environ.get("LIMIT", 0)) or None]
    rows = []; t0 = time.time(); h2cache = {}
    for n, r in enumerate(R):
        im = cv2.imread(r["img"]); H, W = im.shape[:2]
        frames = [jitter(im, r["tap"], j) for j in JIT] + [(im, r["tap"])]
        raw = {fl: [detect_all(f, fl) for f, _ in frames] for fl in FLOORS}
        res = {}
        for fl in FLOORS:
            for g in GUARDS:
                gd = [guard(d, W, H, g) for d in raw[fl]]; td = [tapped(gd[i], frames[i][1], W, H) for i in range(3)]
                last = td[2]
                for mode in ("1f", "3f"):
                    wide = (id_policy(last[1], last[2], 3) if last else dict(status="unable")) if mode == "1f" else burst_wide(td)
                    rec = dict(wide=wide.get("classId") if wide["status"] == "identified" else None, wide_status=wide["status"], tapped_box_area=None, side=None, h2top=None, pa=None)
                    if last is not None:
                        b = last[0]; rec["tapped_box_area"] = round((b[2] - b[0]) * (b[3] - b[1]) / (W * H), 5); rec["tapped_cls"] = last[1]; rec["tapped_score"] = round(last[2], 4)
                        cr = crop_rect(b, W, H, pad=0.08); rec["side"] = cr["sidePx"]
                        key = (round(cr["x"]), round(cr["y"]), cr["w"], cr["h"])
                        if key not in h2cache: h2cache[key] = h2_probs(im[cr["y"]:cr["y"] + cr["h"], cr["x"]:cr["x"] + cr["w"]])
                        p = h2cache[key]; rec["h2top"] = int(np.argmax(p))
                    else: p = [1 / 13] * 13
                    v = verify_identity(dict(status=wide["status"], classId=wide.get("classId")), None, p, FROZEN_VERIFY)
                    rec["pa"] = v["classId"] if v["status"] == "verified" else None; rec["pa_reason"] = v.get("reason")
                    res[f"{fl}|{g}|{mode}"] = rec
        h2cache = {}
        rows.append(dict(key=r["key"], set=r["set"], split=r["split"], group=r["group"], truth=r["truth"], W=W, H=H, res=res))
        if n % 50 == 49: print(n + 1, round(time.time() - t0), flush=True)
    json.dump(dict(guards=GUARDS, floors=FLOORS, frozen_verify=FROZEN_VERIFY, jitter=JIT, models=SHA, rows=rows), open(sys.argv[1], "w"))
    print("done", len(rows), round(time.time() - t0))
