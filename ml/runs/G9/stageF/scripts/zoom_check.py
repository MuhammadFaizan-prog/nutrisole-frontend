"""Zoomed label check: crops (normalised) of labelled images with v2 boxes drawn, 2x2 sheet. Usage: zoom_check.py LABELS OUT I:x0,y0,x1,y1 ..."""
import json, sys, cv2, numpy as np
L = json.load(open(sys.argv[1])); tiles = []
for spec in sys.argv[3:]:
    I, r = spec.split(":"); r = [float(v) for v in r.split(",")]; im = cv2.imread(f"/workspace/work/cv/g9e/commons/img/{I}.jpg"); H, W = im.shape[:2]
    x0, y0, x1, y1 = int(r[0] * W), int(r[1] * H), int(r[2] * W), int(r[3] * H); c = im[y0:y1, x0:x1]; s = min(880 / c.shape[1], 660 / c.shape[0]); c = cv2.resize(c, None, fx=s, fy=s)
    for b in L[I]["boxes"]:
        cv2.rectangle(c, (int((b[0] * W - x0) * s), int((b[1] * H - y0) * s)), (int((b[2] * W - x0) * s), int((b[3] * H - y0) * s)), (255, 255, 0), 1)
    t = np.zeros((682, 880, 3), np.uint8); t[22:22 + c.shape[0], :c.shape[1]] = c; cv2.putText(t, spec, (4, 16), 0, .5, (255, 255, 255), 1); tiles.append(t)
while len(tiles) % 2: tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(sys.argv[2], np.vstack([np.hstack(tiles[i:i + 2]) for i in range(0, len(tiles), 2)]), [cv2.IMWRITE_JPEG_QUALITY, 82])
