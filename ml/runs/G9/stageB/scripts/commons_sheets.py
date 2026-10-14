"""Contact sheets of Commons stills on which G3 fired (>= 0.35 after area guard), whole image with all G3 boxes drawn, for agent review."""
import json, os, sys, cv2, numpy as np
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
D = "/workspace/work/cv/g9b/commons"; O = "/workspace/work/cv/g9b/csheets"; os.makedirs(O, exist_ok=True)
d = json.load(open(f"{D}/g3_dets.json")); m = {v["file"]: v for v in json.load(open(f"{D}/manifest_search.json")).values() if "file" in v}
fs = sorted(f for f, v in d.items() if v.get("boxes")); tiles = []
for f in fs:
    im = cv2.imread(f"{D}/img/{f}"); H, W = im.shape[:2]
    for b in d[f]["boxes"]:
        cv2.rectangle(im, (int(b[0] * W), int(b[1] * H)), (int(b[2] * W), int(b[3] * H)), (0, 0, 255), max(2, W // 200))
        cv2.putText(im, f"{N[b[4]][:6]} {b[5]:.2f}", (int(b[0] * W) + 2, int(b[1] * H) + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6 * W / 640, (0, 255, 255), 2)
    s = 300 / max(H, W); im = cv2.resize(im, (int(W * s), int(H * s))); t = np.full((300, 300, 3), 255, np.uint8); t[:im.shape[0], :im.shape[1]] = im
    t = cv2.copyMakeBorder(t, 0, 20, 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    cv2.putText(t, f"{f[:6]} {m[f]['type'][:10]} mx{max(b[5] for b in d[f]['boxes']):.2f}", (2, 314), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
    tiles.append(t)
for k in range(0, len(tiles), 20):
    ts = tiles[k:k + 20] + [np.full_like(tiles[0], 255)] * (-len(tiles[k:k + 20]) % 5)
    cv2.imwrite(f"{O}/cs_{k // 20:02d}.jpg", np.vstack([np.hstack(ts[r:r + 5]) for r in range(0, len(ts), 5)]), [cv2.IMWRITE_JPEG_QUALITY, 82])
print(len(tiles), "tiles", (len(tiles) + 19) // 20, "sheets")
