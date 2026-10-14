"""Render 2x2 sheets of v1 crowd-region crops (native pixels, OWLv2 region proposals numbered; no model prediction shown).
Usage: crowd_sheet.py OUT.jpg I:k [I:k ...]   (k = v1 crowd index; 'I:all' = whole image with v1 labels; 'I:raw' = whole raw image)"""
import json, sys, cv2, numpy as np
sys.path.insert(0, "/workspace/work/nutrisole/ml/runs/G9/stageF/scripts"); import build_labels_v2 as B
AB = ["ban", "app", "man", "cit", "gua", "pom", "lem", "tom", "pot", "cuc", "car", "cap"]
TW, TH = 880, 660; tiles = []
for spec in sys.argv[2:]:
    I, k = spec.split(":"); im = cv2.imread(f"/workspace/work/cv/g9e/commons/img/{I}.jpg"); H, W = im.shape[:2]
    if k in ("all", "raw"): reg = [0, 0, 1, 1, -1]; items = []
    else: reg = B.V1[I]["crowd"][int(k)]; items = B.region_props(I, reg) if reg[4] >= 0 else B.region_props(I, reg[:4] + [0])
    if k == "all": items = [b + [1] for b in B.V1[I]["boxes"]] if I in B.V1 else []
    pad = 0.03; x0, y0 = max(0, reg[0] - pad), max(0, reg[1] - pad); x1, y1 = min(1, reg[2] + pad), min(1, reg[3] + pad)
    cx0, cy0, cx1, cy1 = int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H); crop = im[cy0:cy1, cx0:cx1]
    sc = min(TW / crop.shape[1], TH / crop.shape[0]); crop = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC if sc > 1 else cv2.INTER_AREA)
    def p(x, y): return int((x * W - cx0) * sc), int((y * H - cy0) * sc)
    if k not in ("all", "raw"): cv2.rectangle(crop, p(reg[0], reg[1]), p(reg[2], reg[3]), (255, 255, 255), 1)
    if k == "all":
        for c in B.V1[I].get("crowd", []): cv2.rectangle(crop, p(c[0], c[1]), p(c[2], c[3]), (255, 255, 255), 2); cv2.putText(crop, "C" + (AB[c[4]] if c[4] >= 0 else "IGN"), p(c[0] + .005, c[1] + .03), 0, .5, (255, 255, 255), 2)
    for n, d in enumerate(items):
        a, b = p(d[0], d[1]), p(d[2], d[3]); cv2.rectangle(crop, a, b, (0, 255, 255) if k != "all" else (0, 0, 255), 1)
        cv2.putText(crop, str(n), (a[0] + 1, a[1] + 11), 0, 0.35, (0, 0, 0), 2); cv2.putText(crop, str(n), (a[0] + 1, a[1] + 11), 0, 0.35, (0, 255, 255), 1)
    med = np.median([((d[2] - d[0]) * W * (d[3] - d[1]) * H) ** .5 for d in items]) if items else 0
    t = np.zeros((TH + 26, TW, 3), np.uint8); t[26:26 + crop.shape[0], :crop.shape[1]] = crop
    cv2.putText(t, f"{I}:{k} {AB[reg[4]] if reg[4] >= 0 else 'IGN'} props={len(items)} med_side={med:.0f}px region={[round(v,2) for v in reg[:4]]}", (4, 18), 0, 0.55, (255, 255, 255), 1); tiles.append(t)
while len(tiles) % 2: tiles.append(np.zeros_like(tiles[0]))
rows = [np.hstack(tiles[i:i + 2]) for i in range(0, len(tiles), 2)]; cv2.imwrite(sys.argv[1], np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 82])
