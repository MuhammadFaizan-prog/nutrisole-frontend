"""Render a review sheet for one M-DEV image: OWLv2 proposals (non-G3) numbered and coloured by class, plus a 10x10 normalised grid
(labels 0-9 = tenths) so missed targets / crowd regions can be added in normalised coordinates. Optionally render the current labels
(after edits) instead of proposals. Usage: review_sheet.py ID MODE(props|labels|raw) OUT.jpg [min_score] [crop x1,y1,x2,y2]"""
import json, sys, cv2
I, MODE, OUT = sys.argv[1], sys.argv[2], sys.argv[3]; MS = float(sys.argv[4]) if len(sys.argv) > 4 else 0.12
CROP = [float(v) for v in sys.argv[5].split(",")] if len(sys.argv) > 5 else [0, 0, 1, 1]
AB = ["ban", "app", "man", "cit", "gua", "pom", "lem", "tom", "pot", "cuc", "car", "cap"]
COL = [(0, 220, 255), (0, 0, 255), (0, 160, 255), (0, 120, 255), (120, 255, 120), (80, 0, 160), (0, 255, 200), (60, 60, 230), (60, 120, 160), (0, 160, 0), (0, 100, 255), (255, 0, 255)]
im = cv2.imread(f"/workspace/work/cv/g9e/commons/img/{I}.jpg"); H, W = im.shape[:2]
x0, y0, x1, y1 = int(CROP[0] * W), int(CROP[1] * H), int(CROP[2] * W), int(CROP[3] * H); im = im[y0:y1, x0:x1]
sc = 1400 / max(im.shape[:2]); im = cv2.resize(im, None, fx=sc, fy=sc); h, w = im.shape[:2]
def P(bx, by): return int((bx * W - x0) * sc), int((by * H - y0) * sc)
for k in range(1, 10):  # grid in full-image tenths
    gx = P(k / 10, 0)[0]; gy = P(0, k / 10)[1]
    if 0 < gx < w: cv2.line(im, (gx, 0), (gx, h), (255, 255, 255), 1); cv2.putText(im, str(k), (gx + 2, 14), 0, 0.45, (255, 255, 255), 1)
    if 0 < gy < h: cv2.line(im, (0, gy), (w, gy), (255, 255, 255), 1); cv2.putText(im, str(k), (2, gy - 3), 0, 0.45, (255, 255, 255), 1)
if MODE == "props":
    ds = json.load(open("/workspace/work/cv/g9e/owl_props.json"))["images"][I + ".jpg"]["dets"]
    items = [(n, d["box"], d["cls"], d["score"]) for n, d in enumerate(ds) if d["cls"] >= 0 and d["score"] >= MS]
elif MODE == "clean":
    sys.path.insert(0, "/workspace/work/nutrisole/ml/runs/G9/stageE/scripts"); from build_labels import clean
    items = [(n, d[:4], d[4], d[5]) for n, d in enumerate(clean(I, MS))]
elif MODE == "labels":
    L = json.load(open("/workspace/work/cv/g9e/labels_work.json"))[I]
    items = [(n, b[:4], b[4], 1.0) for n, b in enumerate(L["boxes"])]
    for b in L.get("crowd", []):
        a, c = P(b[0], b[1]), P(b[2], b[3]); cv2.rectangle(im, a, c, (255, 255, 255), 3); cv2.putText(im, ("CROWD " + AB[b[4]]) if b[4] >= 0 else "IGNORE", (a[0] + 3, a[1] + 18), 0, 0.6, (255, 255, 255), 2)
else: items = []
for n, b, c, s in items:
    a, e = P(b[0], b[1]), P(b[2], b[3]); cv2.rectangle(im, a, e, COL[c], 2)
    t = f"{n}{AB[c][0:2]}"; cv2.putText(im, t, (a[0], max(10, a[1] - 2)), 0, 0.42, (0, 0, 0), 3); cv2.putText(im, t, (a[0], max(10, a[1] - 2)), 0, 0.42, COL[c], 1)
cv2.imwrite(OUT, im, [cv2.IMWRITE_JPEG_QUALITY, 85]); print(I, MODE, len(items), "items")
