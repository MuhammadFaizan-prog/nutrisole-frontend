"""G7.4 citrus-family ambiguity output ("citrus (lemon/orange?)"). Mirrors native/src/cv/pipeline/postprocess.ts
`markCitrusAmbiguity` (parity: native/tests/cvCitrus.test.ts replays ml/eval/fixtures/citrus_parity.json).

Rule (pre-registered in docs/cv/gauntlet/G7_prereg.md section 4): for a kept box (raw head, class-wise NMS) whose top class
is citrus (3) or lemon_lime (6), read the OTHER citrus-family class score at the SAME anchor; the box is ambiguous when
other >= ratio * top. Behind config, default OFF. Ratio chosen on OIV7c val only, then measured once on test_oiv7c.

Usage: python ml/eval/citrus_ambiguity.py --onnx DET.onnx --out ml/runs/G7/citrus  (sandbox CPU, onnxruntime, imgsz 480)
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

CITRUS, LEMON = 3, 6
DEFAULT = dict(enabled=False, ratio=0.5, citrusId=CITRUS, lemonId=LEMON)


def mark(top_cls: int, scores: list[float], ratio: float, citrus_id: int = CITRUS, lemon_id: int = LEMON) -> bool:
    if top_cls not in (citrus_id, lemon_id):
        return False
    other = lemon_id if top_cls == citrus_id else citrus_id
    return scores[other] >= ratio * scores[top_cls]


def letterbox_run(sess, path, S=480):
    import cv2
    im = cv2.imread(path); h, w = im.shape[:2]; r = S / max(h, w)
    rs = cv2.resize(im, (int(round(w * r)), int(round(h * r)))); c = np.full((S, S, 3), 114, np.uint8)
    py, px = (S - rs.shape[0]) // 2, (S - rs.shape[1]) // 2; c[py:py + rs.shape[0], px:px + rs.shape[1]] = rs
    x = c[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255
    o = sess.run(None, {sess.get_inputs()[0].name: x})[0][0].T  # (N, 4 + nc)
    return o, (r, px, py, w, h)


def detect(o, geo, conf):
    """Class-wise NMS 0.7 (cv2), returns (cls, score, box_norm_xyxy, full_score_vector)."""
    import cv2
    r, px, py, w, h = geo
    sc = o[:, 4:]; cl = sc.argmax(1); cf = sc.max(1); k = cf >= conf
    o, cl, cf, sc = o[k], cl[k], cf[k], sc[k]
    res = []
    for c_ in sorted(set(cl.tolist())):
        m = np.where(cl == c_)[0]; b = o[m, :4]
        xywh = [[float(bx - bw / 2), float(by - bh / 2), float(bw), float(bh)] for bx, by, bw, bh in b]
        for i in np.array(cv2.dnn.NMSBoxes(xywh, cf[m].tolist(), conf, 0.7)).flatten():
            x0, y0, bw, bh = xywh[i]
            res.append((int(c_), float(cf[m][i]), [(x0 - px) / r / w, (y0 - py) / r / h, (x0 + bw - px) / r / w, (y0 + bh - py) / r / h], sc[m][i].astype(float).tolist()))
    return res


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - ix * iy
    return ix * iy / u if u > 0 else 0


def collect(sess, list_or_dir, conf):
    """Per GT citrus/lemon box: best-IoU kept prediction with IoU >= 0.5 -> (gt_cls, pred_cls, pred_scores) or missed."""
    import glob
    files = sorted(glob.glob(list_or_dir + "/*.jpg")) if os.path.isdir(list_or_dir) else [l.strip() for l in open(list_or_dir) if l.strip()]
    items = []
    for p in files:
        lp = p.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"
        gts = [l.split() for l in open(lp).read().splitlines() if l.strip()] if os.path.exists(lp) else []
        gts = [(int(g[0]), *map(float, g[1:5])) for g in gts if int(g[0]) in (CITRUS, LEMON)]
        if not gts:
            continue
        o, geo = letterbox_run(sess, p)
        preds = detect(o, geo, conf)
        for c, x, y, bw, bh in gts:
            b = [x - bw / 2, y - bh / 2, x + bw / 2, y + bh / 2]
            best = max(((iou(b, pb), pc, ps) for pc, s, pb, ps in preds), default=(0, None, None), key=lambda t: t[0])
            items.append(dict(gt=c, pred=(best[1] if best[0] >= 0.5 else None), scores=(best[2] if best[0] >= 0.5 else None), file=os.path.basename(p)))
    return len(files), items


def score(items, ratio):
    out = {}
    for g, name in [(LEMON, "lemon_lime"), (CITRUS, "citrus")]:
        it = [i for i in items if i["gt"] == g]
        n = len(it); missed = sum(i["pred"] is None for i in it); other = sum(i["pred"] is not None and i["pred"] not in (CITRUS, LEMON) for i in it)
        fam = [i for i in it if i["pred"] in (CITRUS, LEMON)]
        amb = [i for i in fam if ratio is not None and mark(i["pred"], i["scores"], ratio)]
        hard = [i for i in fam if i not in amb]
        correct = sum(i["pred"] == g for i in hard); wrong = sum(i["pred"] != g for i in hard)
        base_correct = sum(i["pred"] == g for i in fam); base_wrong = sum(i["pred"] != g for i in fam)
        amb_on_correct = sum(i["pred"] == g for i in amb)
        out[name] = dict(n_gt=n, missed=missed, other_class=other, family_matched=len(fam), correct=correct, ambiguous=len(amb), wrong=wrong,
                         baseline_correct=base_correct, baseline_wrong=base_wrong,
                         wrong_rate=round(wrong / max(1, len(fam)), 4), baseline_wrong_rate=round(base_wrong / max(1, len(fam)), 4),
                         ambiguous_rate_on_correct=round(amb_on_correct / max(1, base_correct), 4))
    tw = out["lemon_lime"]["wrong"] + out["citrus"]["wrong"]; bw = out["lemon_lime"]["baseline_wrong"] + out["citrus"]["baseline_wrong"]
    bc = out["lemon_lime"]["baseline_correct"] + out["citrus"]["baseline_correct"]
    ac = round((out["lemon_lime"]["ambiguous_rate_on_correct"] * out["lemon_lime"]["baseline_correct"] + out["citrus"]["ambiguous_rate_on_correct"] * out["citrus"]["baseline_correct"]) / max(1, bc), 4)
    out["pooled"] = dict(wrong=tw, baseline_wrong=bw, wrong_reduction=round(1 - tw / max(1, bw), 4), ambiguous_rate_on_correct=ac)
    return out


def make_parity_fixture(path):
    import random
    rnd = random.Random(0); cases = []
    for _ in range(200):
        sc = [round(rnd.random(), 4) for _ in range(12)]
        top = int(np.argmax(sc)); ratio = rnd.choice([0.3, 0.4, 0.5, 0.6, 0.7])
        cases.append(dict(top=top, scores=sc, ratio=ratio, expected=mark(top, sc, ratio)))
    for top in (CITRUS, LEMON):  # exact-boundary cases
        sc = [0.0] * 12; sc[top] = 0.8; sc[LEMON if top == CITRUS else CITRUS] = 0.4
        cases.append(dict(top=top, scores=sc, ratio=0.5, expected=mark(top, sc, 0.5)))
    json.dump(dict(cases=cases), open(path, "w"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--onnx"); ap.add_argument("--out"); ap.add_argument("--fixture", action="store_true")
    a = ap.parse_args()
    if a.fixture:
        make_parity_fixture(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "citrus_parity.json")); print("wrote fixture"); raise SystemExit
    import onnxruntime as ort
    sess = ort.InferenceSession(a.onnx, providers=["CPUExecutionProvider"]); os.makedirs(a.out, exist_ok=True)
    RATIOS = [0.3, 0.4, 0.5, 0.6, 0.7]
    res = dict(model=os.path.basename(a.onnx), imgsz=480, nms_iou=0.7, iou_match=0.5, device="sandbox CPU, onnxruntime", ratios=RATIOS,
               note="val = OIV7c val (selection only); test_oiv7c measured once with the selected ratio")
    for conf in (0.35, 0.25):  # 0.35 = rubric detectorMinScore (primary); 0.25 = G6 audit setting (comparability)
        nv, val = collect(sess, "/workspace/work/cv/g4data/oiv7c/images/val", conf)
        grid = {str(r): score(val, r) for r in RATIOS}
        ok = [r for r in RATIOS if grid[str(r)]["pooled"]["ambiguous_rate_on_correct"] <= 0.25]
        pick = max(ok, key=lambda r: (grid[str(r)]["pooled"]["wrong_reduction"], -grid[str(r)]["pooled"]["ambiguous_rate_on_correct"])) if ok else None
        nt, test = collect(sess, "/workspace/work/cv/g4data/test_oiv7c.txt", conf)
        t_off, t_on = score(test, None), (score(test, pick) if pick is not None else None)
        rec = None
        if t_on:
            l0, l1 = t_off["lemon_lime"]["wrong_rate"], t_on["lemon_lime"]["wrong_rate"]
            rec = bool((l0 > 0 and (l0 - l1) / l0 >= 0.30) and t_on["pooled"]["ambiguous_rate_on_correct"] <= 0.25)
        res[f"conf_{conf}"] = dict(val=dict(n_images=nv, grid=grid, picked_ratio=pick), test_oiv7c=dict(n_images=nt, off=t_off, on=t_on), recommend_enable=rec)
        print(conf, "pick", pick, "test off", t_off["pooled"], "on", t_on and t_on["pooled"], "rec", rec, flush=True)
    json.dump(res, open(os.path.join(a.out, "citrus_ambiguity.json"), "w"), indent=1)
