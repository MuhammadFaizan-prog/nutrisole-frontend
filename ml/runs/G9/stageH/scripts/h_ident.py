"""Stage H P1 identity harness (DEV). Builds the identity item list and runs H0 (wide G3 at the tap on the still, id_policy) and H1 (G3
re-run on the padded full-res crop) and, when the H2 ONNX exists, H2 (13-way close-up classifier on the crop + 4 half-crops).
Sets: CU graded items (Stage G triage, CU-tune / CU-check), CU negatives (unsupported / printed / greyscale / cut / crowd; split by uploader
as Stage G), H-val / H-eval (new Commons, agent triage I / W / N). Tune = CU-tune + CU-neg tune + H-val; eval = CU-check + CU-neg check + H-eval.
Writes out/ident_items.jsonl (resumable by key). Usage: h_ident.py SECONDS [h2]"""
import json, os, sys, time, hashlib, cv2, numpy as np
sys.path.insert(0, "/workspace/work/nutrisole"); sys.path.insert(0, "/workspace/work/nutrisole/ml/runs/G9/stageG/scripts")
from g_models import detect, N
from ml.eval.closeup import roi_from_tap, crop_rect, id_policy
from ml.grading.measure import object_mask
G = "/workspace/work/nutrisole/ml/runs/G9/stageG"; B = "/workspace/work/nutrisole/ml/runs/G9/stageH"; CR = "/workspace/work/g9h/ident"; os.makedirs(CR, exist_ok=True)
OUT = f"{B}/out/ident_items.jsonl"; H2P = "/workspace/work/g9h/h2/h2_mnv3s.onnx"
T = json.load(open(f"{G}/cu_triage.json")); L = json.load(open(f"{G}/out/cu_leak_split.json")); CC = json.load(open("/workspace/work/g9g/cu/cands.json"))
HC = json.load(open("/workspace/work/g9h/hset/cands.json"))

def items():
    out = []
    for k, (cls, lab, tap) in T["item"].items():
        if ("cu" + k) in L["dropped"]: continue
        out.append(dict(key="cu" + k, set="cu", split="tune" if L["split"][k] == "tune" else "eval", group="item", truth=cls, img=f"/workspace/work/g9g/cu/img/cu{k}.jpg", tap=tap, label=lab))
    for grp, nm in [("unsupported", "unsupported"), ("printed_or_art", "printed"), ("grayscale_photo", "greyscale"), ("processed_cut", "cut"), ("crowd", "crowd")]:
        for k in T[grp]:
            if ("cu" + k) in L["dropped"]: continue
            u = CC["cu" + k]["user"] or CC["cu" + k]["artist"]; sp = "tune" if int(hashlib.sha1(u.encode()).hexdigest(), 16) % 10 < 6 else "eval"
            truth = CC["cu" + k]["intended_class"] if nm in ("crowd", "greyscale") else "unknown"
            out.append(dict(key="cu" + k, set="cuneg", split=sp, group=nm, truth=truth, img=f"/workspace/work/g9g/cu/img/cu{k}.jpg", tap=[0.5, 0.5]))
    for s, sp in (("val", "tune"), ("eval", "eval")):
        order = json.load(open(f"/workspace/work/g9h/sheets/{s}_order.json")); tr = json.load(open(f"{B}/h{s}_triage.json"))
        for code, grp in (("I", "item"), ("W", "crowd"), ("N", None)):
            for i, v in tr[code].items():
                k = order[int(i)]
                out.append(dict(key=k, set="h" + s, split=sp, group=grp or v, truth=v if code != "N" else "unknown", img=f"/workspace/work/g9h/hset/img/{k}.jpg", tap=[0.5, 0.5]))
    return out

def native_crop(im, tap):
    H, W = im.shape[:2]; dets = detect(im); r = roi_from_tap(tap, W, H, [d[0] for d in dets]); box = r["box"]; wide = dict(status="unable", reason="no detection at tap")
    if r["source"] == "track":
        d = next(x for x in dets if x[0] == r["box"]); wide = {**id_policy(d[1], d[2], 3), "score": round(d[2], 4), "rawClass": d[1]}
    else:
        x1, y1, x2, y2 = map(int, box); sub = im[y1:y2, x1:x2]; m, _ = object_mask(sub[:, :, ::-1].copy()); ys, xs = np.where(m)
        if len(xs) > 50: box = [x1 + xs.min(), y1 + ys.min(), x1 + xs.max() + 1, y1 + ys.max() + 1]
    cr = crop_rect(box, W, H, pad=0.08)
    return im[cr["y"]:cr["y"] + cr["h"], cr["x"]:cr["x"] + cr["w"]], wide, r["source"], cr["sidePx"]

def h1(crop, wide_cls):
    t = time.perf_counter(); dets = detect(crop); ms = (time.perf_counter() - t) * 1e3; h, w = crop.shape[:2]
    hit = [d for d in dets if d[0][0] <= w / 2 <= d[0][2] and d[0][1] <= h / 2 <= d[0][3]]
    best = max(hit, key=lambda d: (d[0][2] - d[0][0]) * (d[0][3] - d[0][1])) if hit else None
    return dict(classId=best[1] if best else None, score=round(best[2], 4) if best else 0.0, hasWide=any(d[1] == wide_cls for d in dets) if wide_cls is not None else False,
                n=len(dets), ms=round(ms, 2))

_s = None
def h2_probs(crop):
    global _s
    import onnxruntime as ort
    if _s is None:
        so = ort.SessionOptions(); so.intra_op_num_threads = 2; _s = ort.InferenceSession(H2P, so, providers=["CPUExecutionProvider"])
    h, w = crop.shape[:2]; sc = 256 / min(h, w); im = cv2.resize(crop, (max(256, round(w * sc)), max(256, round(h * sc))), interpolation=cv2.INTER_AREA if sc < 1 else cv2.INTER_LINEAR)
    y0, x0 = (im.shape[0] - 224) // 2, (im.shape[1] - 224) // 2; im = im[y0:y0 + 224, x0:x0 + 224][:, :, ::-1].astype(np.float32) / 255
    x = ((im - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)).transpose(2, 0, 1)[None]
    t = time.perf_counter(); p = _s.run(None, {"images": x})[0][0]; return [round(float(v), 5) for v in p], (time.perf_counter() - t) * 1e3

def halves(crop):
    h, w = crop.shape[:2]; return [crop[:, : w // 2], crop[:, w // 2:], crop[: h // 2], crop[h // 2:]]

if __name__ == "__main__":
    lim = float(sys.argv[1]); use_h2 = len(sys.argv) > 2 and os.path.exists(H2P); t0 = time.time()
    have = {}
    if os.path.exists(OUT):
        for l in open(OUT): r = json.loads(l); have[r["key"] + "|" + r["set"]] = r
    rows = []
    for it in items():
        kk = it["key"] + "|" + it["set"]; r = have.get(kk)
        if r and (not use_h2 or "h2" in r): continue
        if time.time() - t0 > lim: break
        cp = f"{CR}/{it['set']}_{it['key']}.png"
        if r is None:
            im = cv2.imread(it["img"]); crop, wide, src, side = native_crop(im, it["tap"]); cv2.imwrite(cp, crop)
            wc = wide.get("classId") if wide["status"] == "identified" else None
            r = {**it, "wide": wide, "roi": src, "side": side, "h1": h1(crop, wc), "crop": cp}
        if use_h2:
            crop = cv2.imread(cp); p, ms = h2_probs(crop); r["h2"] = p; r["h2_ms"] = round(ms, 2); r["h2_halves"] = [h2_probs(c)[0] for c in halves(crop)]
        have[kk] = r
    with open(OUT, "w") as f:
        for r in have.values(): f.write(json.dumps(r) + "\n")
    print(len(have), "done", round(time.time() - t0), "s; h2" if use_h2 else "")
