"""Thumbnail contact sheets of the MT pool for triage (index numbers in pool order)."""
import json, cv2, numpy as np, os
pool = json.load(open("/workspace/work/cv/g9f/pool.json")); T = list(pool); os.makedirs("/workspace/work/cv/g9f/tri", exist_ok=True)
C, Rr, S = 8, 7, 220
for s in range(0, len(T), C * Rr):
    can = np.full((Rr * (S + 4), C * S, 3), 255, np.uint8)
    for j, t in enumerate(T[s:s + C * Rr]):
        im = cv2.imread(pool[t]["path"]); h, w = im.shape[:2]; sc = S / max(h, w); im = cv2.resize(im, (int(w * sc), int(h * sc)))
        r, c = divmod(j, C); can[r * (S + 4):r * (S + 4) + im.shape[0], c * S:c * S + im.shape[1]] = im
        cv2.putText(can, str(s + j), (c * S + 3, r * (S + 4) + 22), 0, 0.7, (0, 0, 0), 4); cv2.putText(can, str(s + j), (c * S + 3, r * (S + 4) + 22), 0, 0.7, (255, 255, 0), 2)
    cv2.imwrite(f"/workspace/work/cv/g9f/tri/t{s // (C * Rr):02d}.jpg", can, [cv2.IMWRITE_JPEG_QUALITY, 80])
json.dump(T, open("/workspace/work/cv/g9f/tri/order.json", "w"))
