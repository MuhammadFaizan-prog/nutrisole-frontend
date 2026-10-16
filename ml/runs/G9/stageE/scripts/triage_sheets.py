"""Triage contact sheets of downloaded M-DEV candidates (M-TEST is never opened). Usage: triage_sheets.py KIND OUTPREFIX [per_sheet]"""
import json, sys, os, cv2, numpy as np
D = "/workspace/work/cv/g9e/commons"; man = json.load(open(f"{D}/manifest.json"))
kind, pre = sys.argv[1], sys.argv[2]; per = int(sys.argv[3]) if len(sys.argv) > 3 else 30
ids = sorted(m["file"] for m in man.values() if m["split"] == "M-DEV" and m["kind"] == kind and "file" in m and os.path.exists(f"{D}/img/{m['file']}"))
W, H, C = 320, 240, 6
for s in range(0, len(ids), per):
    chunk = ids[s:s + per]; rows = (len(chunk) + C - 1) // C; sheet = np.full((rows * (H + 22), C * W, 3), 255, np.uint8)
    for i, f in enumerate(chunk):
        im = cv2.imread(f"{D}/img/{f}")
        if im is None: continue
        h, w = im.shape[:2]; sc = min(W / w, H / h); im = cv2.resize(im, (int(w * sc), int(h * sc)))
        r, c = divmod(i, C); y, x = r * (H + 22) + 22, c * W; sheet[y:y + im.shape[0], x:x + im.shape[1]] = im
        cv2.putText(sheet, f[:-4], (x + 4, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 200), 2)
    cv2.imwrite(f"{pre}_{s // per:02d}.jpg", sheet, [cv2.IMWRITE_JPEG_QUALITY, 80])
print(len(ids), "images ->", (len(ids) + per - 1) // per, "sheets")
