"""2x3 review sheets of MT images with cleaned OWLv2 proposals (thr 0.30, numbered, class abbrev) and a 10x10 grid. Usage: mt_sheet.py OUT.jpg ID..."""
import sys, json, cv2, numpy as np
sys.path.insert(0, "/workspace/work/nutrisole/ml/runs/G9/stageF/scripts"); from build_mt import clean
SEL = {s["id"]: s for s in json.load(open("/workspace/work/cv/g9f/mt_sel.json"))}
AB = ["ban", "app", "man", "cit", "gua", "pom", "lem", "tom", "pot", "cuc", "car", "cap"]; TW, TH = 880, 660; tiles = []
for I in sys.argv[2:]:
    im = cv2.imread(SEL[I]["path"]); H, W = im.shape[:2]; sc = min(TW / W, TH / H); im = cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA); h, w = im.shape[:2]
    for k in range(1, 10):
        cv2.line(im, (int(k * w / 10), 0), (int(k * w / 10), h), (255, 255, 255), 1); cv2.line(im, (0, int(k * h / 10)), (w, int(k * h / 10)), (255, 255, 255), 1)
        cv2.putText(im, str(k), (int(k * w / 10) + 2, 12), 0, .4, (255, 255, 255), 1); cv2.putText(im, str(k), (2, int(k * h / 10) - 2), 0, .4, (255, 255, 255), 1)
    ds = clean(I)
    for n, d in enumerate(ds):
        a, b = (int(d[0] * w), int(d[1] * h)), (int(d[2] * w), int(d[3] * h)); cv2.rectangle(im, a, b, (0, 255, 255), 1)
        cv2.putText(im, f"{n}{AB[d[4]][:2]}", (a[0], a[1] + 9), 0, .32, (0, 0, 0), 2); cv2.putText(im, f"{n}{AB[d[4]][:2]}", (a[0], a[1] + 9), 0, .32, (0, 255, 255), 1)
    t = np.zeros((TH + 22, TW, 3), np.uint8); t[22:22 + h, :w] = im; cv2.putText(t, f"{I} {SEL[I]['intended']} props={len(ds)} {SEL[I]['title'][5:60]}", (4, 16), 0, .45, (255, 255, 255), 1); tiles.append(t)
while len(tiles) % 2: tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(sys.argv[1], np.vstack([np.hstack(tiles[i:i + 2]) for i in range(0, len(tiles), 2)]), [cv2.IMWRITE_JPEG_QUALITY, 80])
