"""Contact sheets of teacher proposals for agent review. Usage: review_sheets.py MODE [ids...]
MODE overview: all images with >=3 proposals, 24 per sheet (400 px tiles). MODE detail: listed ids, 4 per sheet (900 px tiles) with a 10x10 grid."""
import json, sys, cv2, numpy as np
D = "/workspace/work/cv/g9d"; T = json.load(open(f"{D}/teacher.json"))
AB = ["BAN", "APL", "MNG", "CIT", "GUA", "POM", "LIM", "TOM", "POT", "CUC", "CAR", "CAP"]
COL = [(0, 230, 255), (0, 0, 255), (0, 140, 255), (0, 165, 255), (100, 255, 100), (128, 0, 200), (0, 255, 128), (60, 60, 255), (100, 160, 200), (0, 120, 0), (0, 100, 255), (255, 0, 255)]
EDIT = json.load(open(f"{D}/edits.json")) if __import__("os").path.exists(f"{D}/edits.json") else {}
def boxes(k):
    bs = [b for b in T[k]["boxes"]]; e = EDIT.get(k, {})
    bs = [b for i, b in enumerate(bs) if i not in set(e.get("drop", []))]
    for i, c in e.get("relabel", {}).items(): pass
    return bs
def tile(k, w, grid=False, show_idx=False):
    im = cv2.imread(f"{D}/commons/img/{k}"); H, W = im.shape[:2]; s = w / W; im = cv2.resize(im, (w, int(H * s))); h = im.shape[0]
    for i, b in enumerate(T[k]["boxes"]):
        p1, p2 = (int(b[0] * w), int(b[1] * h)), (int(b[2] * w), int(b[3] * h)); cv2.rectangle(im, p1, p2, COL[b[4]], 1 if w < 600 else 2)
        if show_idx: cv2.putText(im, f"{i}{AB[b[4]][:2]}", (p1[0] + 1, p1[1] + 11), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1)
    if grid:
        for g in range(1, 10):
            cv2.line(im, (int(g * w / 10), 0), (int(g * w / 10), h), (255, 255, 255), 1); cv2.line(im, (0, int(g * h / 10)), (w, int(g * h / 10)), (255, 255, 255), 1)
    cv2.rectangle(im, (0, 0), (200, 18), (0, 0, 0), -1); cv2.putText(im, f"{k[:-4]} n{len(T[k]['boxes'])}", (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
    return im
def sheet(ks, w, cols, out, **kw):
    ts = [tile(k, w, **kw) for k in ks]; th = max(t.shape[0] for t in ts)
    ts = [np.vstack([t, np.zeros((th - t.shape[0], w, 3), np.uint8)]) for t in ts]; ts += [np.zeros((th, w, 3), np.uint8)] * ((-len(ts)) % cols)
    cv2.imwrite(out, np.vstack([np.hstack(ts[r * cols:(r + 1) * cols]) for r in range(len(ts) // cols)]), [cv2.IMWRITE_JPEG_QUALITY, 85])
if sys.argv[1] == "overview":
    ks = sorted(k for k, v in T.items() if "boxes" in v and len(v["boxes"]) >= 3); print(len(ks))
    for i in range(0, len(ks), 32): sheet(ks[i:i + 32], 300, 8, f"{D}/ov_{i // 32:02d}.jpg")
else:
    ks = sys.argv[2:]
    for i in range(0, len(ks), 2): sheet(ks[i:i + 2], 900, 2, f"{D}/dt_{ks[i][:-4]}.jpg", grid=True, show_idx=True)
