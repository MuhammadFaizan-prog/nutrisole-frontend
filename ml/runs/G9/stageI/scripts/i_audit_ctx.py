"""I1 crop-context diagnostic (post-hoc): H2 on (a) the whole source image (only meaningful for centre-tap single-item photos), (b) a
wider crop (Stage H crop box grown by 0.25 per side, clipped), vs the Stage H crop (pad 0.08). Writes out/h2_audit_ctx.jsonl."""
import json, sys, numpy as np, cv2
sys.path.insert(0, "/workspace/work/nutrisole/ml/runs/G9/stageI/scripts")
from i_audit import stageh_tensor, onx
S = "/workspace/work/nutrisole/ml/runs/G9/stageH"; O = "/workspace/work/nutrisole/ml/runs/G9/stageI/out"
R = [json.loads(l) for l in open(f"{S}/out/ident_items.jsonl")]
with open(f"{O}/h2_audit_ctx.jsonl", "w") as f:
    for r in R:
        im = cv2.imread(r["img"]); crop = cv2.imread(r["crop"]); H, W = im.shape[:2]
        # locate the crop inside the image (template match on a downscaled copy) to grow it
        s = 400 / max(H, W); sm = cv2.resize(im, (max(1, round(W * s)), max(1, round(H * s)))); sc = cv2.resize(crop, (max(1, round(crop.shape[1] * s)), max(1, round(crop.shape[0] * s))))
        if sc.shape[0] <= sm.shape[0] and sc.shape[1] <= sm.shape[1] and min(sc.shape[:2]) >= 4:
            _, mv, _, loc = cv2.minMaxLoc(cv2.matchTemplate(sm, sc, cv2.TM_CCOEFF_NORMED)); x, y = round(loc[0] / s), round(loc[1] / s)
        else: mv, x, y = 0.0, 0, 0
        h, w = crop.shape[:2]; g = 0.25; x1, y1 = max(0, round(x - g * w)), max(0, round(y - g * h)); x2, y2 = min(W, round(x + w + g * w)), min(H, round(y + h + g * h))
        f.write(json.dumps(dict(key=r["key"], set=r["set"], match=round(float(mv), 3), crop_xywh=[x, y, w, h], img_hw=[H, W], crop_area_frac=round(w * h / (W * H), 4),
                                full=[float(v) for v in onx(stageh_tensor(im))], pad25=[float(v) for v in onx(stageh_tensor(im[y1:y2, x1:x2]))])) + "\n")
print("done", len(R))
