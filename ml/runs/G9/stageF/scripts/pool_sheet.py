"""2x2 sheets of whole M-DEV pool images with Stage E-cleaned OWLv2 proposals (thr 0.25; numbered, class abbrev.) and a 10x10 grid.
No model prediction is shown. Usage: pool_sheet.py OUT.jpg ID [ID ...]"""
import sys, cv2, numpy as np
sys.path.insert(0, "/workspace/work/nutrisole/ml/runs/G9/stageE/scripts"); from build_labels import clean
AB = ["ban", "app", "man", "cit", "gua", "pom", "lem", "tom", "pot", "cuc", "car", "cap"]
TW, TH = 880, 660; tiles = []
for I in sys.argv[2:]:
    im = cv2.imread(f"/workspace/work/cv/g9e/commons/img/{I}.jpg"); H, W = im.shape[:2]; sc = min(TW / W, TH / H); im = cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA); h, w = im.shape[:2]
    for k in range(1, 10):
        cv2.line(im, (int(k * w / 10), 0), (int(k * w / 10), h), (255, 255, 255), 1); cv2.line(im, (0, int(k * h / 10)), (w, int(k * h / 10)), (255, 255, 255), 1)
        cv2.putText(im, str(k), (int(k * w / 10) + 2, 12), 0, .4, (255, 255, 255), 1); cv2.putText(im, str(k), (2, int(k * h / 10) - 2), 0, .4, (255, 255, 255), 1)
    ds = clean(I, 0.25)
    for n, d in enumerate(ds):
        a, b = (int(d[0] * w), int(d[1] * h)), (int(d[2] * w), int(d[3] * h)); cv2.rectangle(im, a, b, (0, 255, 255), 1)
        cv2.putText(im, f"{n}{AB[d[4]][:2]}", (a[0], a[1] + 9), 0, .32, (0, 0, 0), 2); cv2.putText(im, f"{n}{AB[d[4]][:2]}", (a[0], a[1] + 9), 0, .32, (0, 255, 255), 1)
    t = np.zeros((TH + 22, TW, 3), np.uint8); t[22:22 + h, :w] = im; cv2.putText(t, f"{I} props={len(ds)} {W}x{H}", (4, 16), 0, .5, (255, 255, 255), 1); tiles.append(t)
while len(tiles) % 2: tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(sys.argv[1], np.vstack([np.hstack(tiles[i:i + 2]) for i in range(0, len(tiles), 2)]), [cv2.IMWRITE_JPEG_QUALITY, 82])
