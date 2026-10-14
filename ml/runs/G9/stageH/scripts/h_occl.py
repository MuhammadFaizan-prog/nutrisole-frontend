"""Stage H extended occlusion / degradation suite on CU items (DEV; CU-tune for thresholds, CU-check reported). Per item and crop side
S in {96, 192} (INTER_AREA from the native crop, as Stage G): clean, the Stage G conditions (blur, lowlight, jpeg, the Stage G flat
skin block over the left half = 'g_skin50', truncation 40% at the frame edge) and new occluders: flat-ish colour blocks with shading +
sensor noise (red, green, blue, white, black, grey; 30-50%), skin block 30%, synthetic hand (palm + fingers, 3 skin tones), plastic bag
(translucent wrinkled overlay with glare; side 50% and full cover), neighbouring produce (another CU item's skin pasted 30% / 50%),
partial objects (25% / 40% cut; 'trunc40_edge' touches the frame edge, 'trunc40_inner' and 'trunc25_inner' do not).
Writes out/occ_items.jsonl (Stage G assess fields + blockiness + Stage H cues) and saves crops to /workspace/work/g9h/occ/crops.
Usage: h_occl.py MAX_SECONDS"""
import json, os, sys, time, cv2, numpy as np
sys.path.insert(0, "/workspace/work/nutrisole"); sys.path.insert(0, "/workspace/work/nutrisole/ml/runs/G9/stageG/scripts")
from g_models import detect, assess, N
from ml.eval.closeup import roi_from_tap, crop_rect, blockiness
from ml.eval.occlusion import cues
from ml.grading.measure import object_mask
G = "/workspace/work/nutrisole/ml/runs/G9/stageG"; B = "/workspace/work/nutrisole/ml/runs/G9/stageH"
T = json.load(open(f"{G}/cu_triage.json")); L = json.load(open(f"{G}/out/cu_leak_split.json"))
CR = "/workspace/work/g9h/occ/crops"; os.makedirs(CR, exist_ok=True); OUT = f"{B}/out/occ_items.jsonl"; os.makedirs(f"{B}/out", exist_ok=True)
done = {json.loads(l)["id"] for l in open(OUT)} if os.path.exists(OUT) else set()
SKIN = [(60, 90, 140), (95, 140, 205), (40, 70, 110)]  # BGR: medium, light, dark skin tones
COL = dict(red=(30, 30, 200), green=(40, 150, 40), blue=(190, 80, 20), white=(235, 235, 235), black=(20, 20, 20), grey=(128, 128, 128))

def side_mask(h, w, cov, side):
    m = np.zeros((h, w), bool)
    if side == 0: m[:, : int(cov * w)] = True
    elif side == 1: m[:, w - int(cov * w):] = True
    elif side == 2: m[: int(cov * h)] = True
    else: m[h - int(cov * h):] = True
    return m

def shaded(h, w, col, rng, noise=4.0):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); gx, gy = rng.uniform(-0.25, 0.25, 2)
    sh = 1 + gx * (xx / w - 0.5) + gy * (yy / h - 0.5)
    return np.clip(np.array(col, np.float32)[None, None] * sh[..., None] + rng.normal(0, noise, (h, w, 3)), 0, 255)

def hand_mask(h, w, side, rng, cov):
    m = np.zeros((h, w), np.uint8); L_ = max(h, w)
    # palm outside the covered side + 4 fingers reaching cov of the item; built in a canonical 'from the left' frame then rotated
    H, W = (h, w) if side in (0, 1) else (w, h)
    c = np.zeros((H, W), np.uint8); reach = int(cov * W)
    cv2.ellipse(c, (int(-0.15 * W), H // 2), (int(0.35 * W), int(0.45 * H)), 0, 0, 360, 1, -1)
    fw = max(3, int(0.11 * H))
    for i in range(4):
        y = int(H * (0.22 + 0.19 * i + rng.uniform(-0.03, 0.03))); x2 = int(reach * rng.uniform(0.75, 1.05))
        cv2.line(c, (0, y), (x2, y + int(rng.uniform(-0.05, 0.05) * H)), 1, fw); cv2.circle(c, (x2, y), fw // 2, 1, -1)
    if side == 1: c = c[:, ::-1]
    if side in (2, 3): c = c.T if side == 2 else c.T[::-1]
    return cv2.resize(c, (w, h), interpolation=cv2.INTER_NEAREST).astype(bool)

def compose(base, m, over, alpha=1.0, feather=1.5):
    a = cv2.GaussianBlur(m.astype(np.float32), (0, 0), feather)[..., None] * alpha
    return np.clip(base.astype(np.float32) * (1 - a) + over * a, 0, 255).astype(np.uint8)

def bag(h, w, rng):
    o = np.full((h, w, 3), 225, np.float32) + rng.normal(0, 6, (h, w, 3)); wr = np.zeros((h, w), np.float32)
    for _ in range(8):
        p = rng.integers(0, [w, h], (2, 2)); cv2.line(wr, tuple(map(int, p[0])), tuple(map(int, p[1])), 1.0, max(1, w // 40))
    wr = cv2.GaussianBlur(wr, (0, 0), max(1, w / 50)); o += 40 * wr[..., None] - 20
    return np.clip(o, 0, 255)

def neighbour(base, other, side, cov, rng):
    h, w = base.shape[:2]; oh, ow = other.shape[:2]; oc = other[int(oh * .2):int(oh * .8), int(ow * .2):int(ow * .8)]
    D = int(1.0 * max(h, w)); oc = cv2.resize(oc, (D, D), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((h, w, 3), np.float32); m = np.zeros((h, w), np.uint8)
    # disc of diameter D whose chord covers cov of the item from the given side
    if side == 0: cx, cy = int(cov * w - D / 2), h // 2
    elif side == 1: cx, cy = int(w - cov * w + D / 2), h // 2
    elif side == 2: cx, cy = w // 2, int(cov * h - D / 2)
    else: cx, cy = w // 2, int(h - cov * h + D / 2)
    cv2.circle(m, (cx, cy), D // 2, 1, -1)
    x0, y0 = cx - D // 2, cy - D // 2
    for yy in range(h):
        sy = yy - y0
        if 0 <= sy < D:
            xs = np.arange(w); sx = xs - x0; ok = (sx >= 0) & (sx < D); canvas[yy, xs[ok]] = oc[sy, sx[ok]]
    return compose(base, m.astype(bool), canvas, 1.0, 1.2)

def conditions(base, other, rng):
    h, w = base.shape[:2]; out = {}
    out["clean"] = (base, False)
    out["blur"] = (cv2.GaussianBlur(base, (0, 0), 2.0), False)
    x = (base.astype(np.float32) / 255) ** 1.8 * 0.35 * 255 + rng.normal(0, 5, base.shape); out["lowlight"] = (np.clip(x, 0, 255).astype(np.uint8), False)
    out["jpeg"] = (cv2.imdecode(cv2.imencode(".jpg", base, [cv2.IMWRITE_JPEG_QUALITY, 15])[1], 1), False)
    g = base.copy(); g[:, : int(0.5 * w)] = (60, 90, 140); out["g_skin50"] = (g, False)  # Stage G baseline occluder (flat, left half)
    out["trunc40_edge"] = (base[:, : max(4, int(0.6 * w))].copy(), True)
    s = int(rng.integers(0, 4)); cov = float(rng.uniform(0.3, 0.5))
    for k, col in COL.items():
        sd = int(rng.integers(0, 4)); cv_ = float(rng.uniform(0.3, 0.5)); out[f"block_{k}"] = (compose(base, side_mask(h, w, cv_, sd), shaded(h, w, col, rng), 1.0, 0.8), False)
    out["skin30"] = (compose(base, side_mask(h, w, 0.3, s), shaded(h, w, SKIN[0], rng), 1.0, 0.8), False)
    for i, tone in enumerate(SKIN):
        sd = int(rng.integers(0, 4)); m = hand_mask(h, w, sd, rng, float(rng.uniform(0.35, 0.6)))
        hc = shaded(h, w, tone, rng, 5.0); out[f"hand_{i}"] = (compose(base, m, hc, 1.0, 1.0), False)
    sd = int(rng.integers(0, 4)); out["bag_side50"] = (compose(base, side_mask(h, w, 0.5, sd), bag(h, w, rng), 0.62, 2.0), False)
    out["bag_full"] = (compose(base, np.ones((h, w), bool), bag(h, w, rng), 0.5, 0.1), False)
    for cv_ in (0.3, 0.5):
        sd = int(rng.integers(0, 4)); out[f"neigh{int(cv_ * 100)}"] = (neighbour(base, other, sd, cv_, rng), False)
    out["trunc40_inner"] = (base[:, : max(4, int(0.6 * w))].copy(), False)
    out["trunc25_inner"] = (base[: max(4, int(0.75 * h))].copy(), False)
    return out

def at_size(native, s):
    h, w = native.shape[:2]; sc = s / (h * w) ** 0.5
    return cv2.resize(native, (max(2, round(w * sc)), max(2, round(h * sc))), interpolation=cv2.INTER_AREA)

def native_crop(k):
    cls, lab, tap = T["item"][k]; im = cv2.imread(f"/workspace/work/g9g/cu/img/cu{k}.jpg"); H, W = im.shape[:2]
    dets = detect(im); r = roi_from_tap(tap, W, H, [d[0] for d in dets]); box = r["box"]
    if r["source"] == "tap_roi":
        x1, y1, x2, y2 = map(int, box); sub = im[y1:y2, x1:x2]; m, _ = object_mask(sub[:, :, ::-1].copy()); ys, xs = np.where(m)
        if len(xs) > 50: box = [x1 + xs.min(), y1 + ys.min(), x1 + xs.max() + 1, y1 + ys.max() + 1]
    cr = crop_rect(box, W, H, pad=0.08); return im[cr["y"]:cr["y"] + cr["h"], cr["x"]:cr["x"] + cr["w"]], cr["sidePx"]

if __name__ == "__main__":
    t0 = time.time(); lim = float(sys.argv[1]); keys = [k for k in T["item"] if ("cu" + k) not in L["dropped"]]
    NAT = "/workspace/work/g9h/occ/native"; os.makedirs(NAT, exist_ok=True)
    for i, k in enumerate(keys):
        if k in done: continue
        if time.time() - t0 > lim: break
        cls = T["item"][k][0]; rng = np.random.default_rng(1000 + int(k))
        native, side = native_crop(k); cv2.imwrite(f"{NAT}/{k}.png", native)
        ok_ = [j for j in keys if T["item"][j][0] != cls]; ok_ = ok_[int(rng.integers(0, len(ok_)))]
        on = f"{NAT}/{ok_}.png"; other = cv2.imread(on) if os.path.exists(on) else native_crop(ok_)[0]
        row = dict(id=k, cls=cls, label=T["item"][k][1], split=L["split"][k], native_side=side, other=ok_, sizes={})
        for s in (96, 192):
            if s > side * 1.05: continue
            base = at_size(native, s); row["sizes"][s] = {}
            for c, (img, edge) in conditions(base, other, rng).items():
                a = assess(img, cls); m, _ = object_mask(img[:, :, ::-1].copy()); cu = cues(img, m)
                cv2.imwrite(f"{CR}/{k}_{s}_{c}.png", img)
                row["sizes"][s][c] = dict(pF=round(a["probs"]["fresh"], 4), grade=a["grade"], status=a["status"], blur=a["blurVar"], meanV=a["meanV"], vis=a["visibleFrac"],
                                          maxP=round(a["maxProb"], 4), margin=round(a["margin"], 4), side=s, edge=edge, block=blockiness(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)), **cu)
        with open(OUT, "a") as f: f.write(json.dumps(row) + "\n")
        print(k, cls, side, round(time.time() - t0), flush=True)
