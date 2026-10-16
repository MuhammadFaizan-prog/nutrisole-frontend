"""2x2 sheets of whole images with given labels (boxes red, crowd white, ignore grey). No model prediction shown. Usage: label_sheet.py LABELS.json OUT.jpg ID..."""
import json, sys, cv2, numpy as np
L = json.load(open(sys.argv[1])); TW, TH = 880, 660; tiles = []
AB = ["ban", "app", "man", "cit", "gua", "pom", "lem", "tom", "pot", "cuc", "car", "cap"]
for I in sys.argv[3:]:
    im = cv2.imread(f"/workspace/work/cv/g9e/commons/img/{I}.jpg"); H, W = im.shape[:2]; sc = min(TW / W, TH / H); im = cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA); h, w = im.shape[:2]
    for c in L[I]["crowd"]:
        cv2.rectangle(im, (int(c[0] * w), int(c[1] * h)), (int(c[2] * w), int(c[3] * h)), (255, 255, 255) if c[4] >= 0 else (128, 128, 128), 2)
        cv2.putText(im, ("C" + AB[c[4]]) if c[4] >= 0 else "IGN", (int(c[0] * w) + 3, int(c[1] * h) + 14), 0, .45, (255, 255, 255), 1)
    for b in L[I]["boxes"]:
        cv2.rectangle(im, (int(b[0] * w), int(b[1] * h)), (int(b[2] * w), int(b[3] * h)), (0, 0, 255), 1)
        cv2.putText(im, AB[b[4]][:2], (int(b[0] * w), int(b[1] * h) + 8), 0, .3, (0, 255, 255), 1)
    t = np.zeros((TH + 22, TW, 3), np.uint8); t[22:22 + h, :w] = im; cv2.putText(t, f"{I} boxes={len(L[I]['boxes'])} crowd={len(L[I]['crowd'])}", (4, 16), 0, .5, (255, 255, 255), 1); tiles.append(t)
while len(tiles) % 2: tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(sys.argv[2], np.vstack([np.hstack(tiles[i:i + 2]) for i in range(0, len(tiles), 2)]), [cv2.IMWRITE_JPEG_QUALITY, 82])
