import json, cv2, numpy as np, sys
C = json.load(open("/workspace/work/g9g/cu/cands.json")); ks = sorted(C); T = 210
for s in range(0, len(ks), 30):
    rows = []
    for r in range(5):
        row = []
        for c in range(6):
            i = s + r * 6 + c; t = np.full((T + 22, T, 3), 40, np.uint8)
            if i < len(ks):
                k = ks[i]; im = cv2.imread(f"/workspace/work/g9g/cu/img/{k}.jpg")
                if im is not None:
                    h, w = im.shape[:2]; sc = T / max(h, w); im = cv2.resize(im, (int(w * sc), int(h * sc))); t[22:22 + im.shape[0], :im.shape[1]] = im
                cv2.putText(t, f"{k[2:]} {C[k]['intended_class'][:6]} {C[k]['intended_condition'][0]}", (2, 16), 0, .45, (255, 255, 255), 1)
            row.append(t)
        rows.append(np.hstack(row))
    cv2.imwrite(f"/workspace/work/g9g/cu/sheet_{s//30}.jpg", np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 80])
