"""Contact sheets of G3 boxes on mining-pool clips for agent visual review. Each tile: context crop (box expanded to a square
of side max(2.5 x box side, 160 px)), red box drawn, caption id / class / score. Writes cand_video.json with crop geometry."""
import os, sys, json, glob
import cv2, numpy as np
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
M = "/workspace/work/cv/g9b/mine"; O = "/workspace/work/cv/g9b/vsheets"; os.makedirs(O, exist_ok=True)
CL = sys.argv[1].split(","); tag = sys.argv[2]; cap_per = int(sys.argv[3]) if len(sys.argv) > 3 else 999
def vpath(c):
    for d in ("g6src", "g7src"):
        for e in ("webm", "ogv"):
            p = f"/workspace/work/cv/{d}/raw/{c}.{e}"
            if os.path.exists(p): return p
cands = []
for c in CL:
    d = json.load(open(f"{M}/{c}.json")); seen = {}
    for f in d["frames"]:
        for b in f["boxes"]:
            k = (b[4], int(f["t"] // 2), round(b[0] * 4), round(b[1] * 4))  # dedupe: class, 2-s bucket, coarse position
            if k in seen: continue
            seen[k] = 1; cands.append(dict(clip=c, role=d["role"], fi=f["fi"], t=f["t"], box=b[:4], cls=N[b[4]], score=b[5], W=f["w"], H=f["h"]))
    cc = [x for x in cands if x["clip"] == c]
    if len(cc) > cap_per:
        keep = sorted(cc, key=lambda x: -x["score"])[:cap_per]; cands = [x for x in cands if x["clip"] != c] + keep
tiles = []
for i, x in enumerate(cands):
    x["id"] = f"{tag}{i:03d}"
    cap = cv2.VideoCapture(vpath(x["clip"])); cap.set(cv2.CAP_PROP_POS_FRAMES, x["fi"]); ok, fr = cap.read()
    if not ok: continue
    H, W = fr.shape[:2]; x0, y0, x1, y1 = x["box"][0] * W, x["box"][1] * H, x["box"][2] * W, x["box"][3] * H
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; side = max(2.5 * max(x1 - x0, y1 - y0), 160); side = min(side, W, H)
    a = int(max(0, min(W - side, cx - side / 2))); b_ = int(max(0, min(H - side, cy - side / 2))); s = int(side)
    x["crop"] = [a, b_, s]
    t = fr[b_:b_ + s, a:a + s].copy(); cv2.rectangle(t, (int(x0 - a), int(y0 - b_)), (int(x1 - a), int(y1 - b_)), (0, 0, 255), max(1, s // 120))
    t = cv2.resize(t, (200, 200)); t = cv2.copyMakeBorder(t, 0, 22, 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    cv2.putText(t, f"{x['id']} {x['cls'][:7]} {x['score']:.2f}", (2, 216), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
    tiles.append(t)
for k in range(0, len(tiles), 30):
    ts = tiles[k:k + 30] + [np.full_like(tiles[0], 255)] * (-len(tiles[k:k + 30]) % 6)
    rows = [np.hstack(ts[r:r + 6]) for r in range(0, len(ts), 6)]
    cv2.imwrite(f"{O}/{tag}_{k // 30}.jpg", np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])
json.dump(cands, open(f"{O}/{tag}_cands.json", "w")); print(len(cands), "tiles", (len(tiles) + 29) // 30, "sheets")
