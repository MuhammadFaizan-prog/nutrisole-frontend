"""G5.1a video hard-negative mining (Jin et al., ECCV 2018 'Unsupervised hard example mining from videos'), app-side variant.

Run a detector over UNLABELLED, licence-clear produce/market video (never a gauntlet clip). For every detection
(score >= --conf) at frame t, count the neighbouring frames t-K..t+K (K=5, excluding t) that contain a detection with
IoU >= 0.2 to it (class-agnostic):
  * 0 neighbours        -> ISOLATED: a flash detection with no temporal support = presumed false positive.
                           Its context crop (box expanded x2, min 96 px) becomes a hard-negative BACKGROUND image
                           (no labels), unless the crop touches a temporally consistent box.
  * >= 3 neighbours     -> CONSISTENT: probably a real object; listed for human review only, NEVER auto-labelled.
  * 1-2 neighbours      -> ambiguous, ignored.
Outputs: OUT/crops/*.jpg, OUT/mining.json (per-video counts, every isolated/consistent det, licence per video).
"""
import argparse, glob, json, os, sys
import cv2, numpy as np, onnxruntime as ort
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), "eval"))
from geometry import letterbox, dst_to_src, decode  # noqa: E402
from tracker import iou  # noqa: E402
NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--det", required=True); ap.add_argument("--imgsz", type=int, default=480)
    ap.add_argument("--frames", required=True, help="dir with one sub-dir of frames per video")
    ap.add_argument("--sources", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--conf", type=float, default=0.35); ap.add_argument("--k", type=int, default=5)
    a = ap.parse_args()
    so = ort.SessionOptions(); so.intra_op_num_threads = 2
    s = ort.InferenceSession(a.det, so, providers=["CPUExecutionProvider"]); inp = s.get_inputs()[0].name
    os.makedirs(f"{a.out}/crops", exist_ok=True)
    src = {v["vid"]: v for v in json.load(open(a.sources))}
    rep = dict(det=a.det, imgsz=a.imgsz, conf=a.conf, k=a.k, iou_link=0.2, device="sandbox CPU, onnxruntime", videos={}, isolated=[], consistent=[])
    for vd in sorted(glob.glob(f"{a.frames}/*")):
        vid = os.path.basename(vd); fs = sorted(glob.glob(f"{vd}/*.jpg")); dets = []
        for f in fs:
            im = cv2.imread(f); H, W = im.shape[:2]; x, tf = letterbox(im, a.imgsz)
            dd = []
            for d in decode(s.run(None, {inp: x})[0], "raw", a.conf):
                b = dst_to_src(d["box"], tf); dd.append(dict(box=[b[0] / W, b[1] / H, b[2] / W, b[3] / H], classId=d["classId"], score=d["score"]))
            dets.append(dd)
        n_iso = n_con = n_crop = 0
        for t, dd in enumerate(dets):
            cons = []
            info = []
            for d in dd:
                nb = sum(1 for u in range(max(0, t - a.k), min(len(dets), t + a.k + 1)) if u != t and any(iou(d["box"], e["box"]) >= 0.2 for e in dets[u]))
                info.append(nb)
                if nb >= 3: cons.append(d)
            for d, nb in zip(dd, info):
                row = dict(vid=vid, frame=os.path.basename(fs[t]), cls=NAMES[d["classId"]], score=round(d["score"], 3), box=[round(v, 4) for v in d["box"]], neighbours=nb)
                if nb >= 3:
                    n_con += 1; rep["consistent"].append(row)
                elif nb == 0:
                    n_iso += 1
                    im = cv2.imread(fs[t]); H, W = im.shape[:2]
                    bx = d["box"]; cx, cy = (bx[0] + bx[2]) / 2 * W, (bx[1] + bx[3]) / 2 * H
                    side = max(96, 2 * max((bx[2] - bx[0]) * W, (bx[3] - bx[1]) * H))
                    x1, y1, x2, y2 = max(0, cx - side / 2), max(0, cy - side / 2), min(W, cx + side / 2), min(H, cy + side / 2)
                    cn = [x1 / W, y1 / H, x2 / W, y2 / H]
                    touch = any(min(cn[2], c["box"][2]) > max(cn[0], c["box"][0]) and min(cn[3], c["box"][3]) > max(cn[1], c["box"][1]) for c in cons)
                    row["crop"] = None
                    if not touch and x2 - x1 >= 64 and y2 - y1 >= 64:
                        name = f"{vid}_{t:05d}_{n_crop:03d}.jpg"; cv2.imwrite(f"{a.out}/crops/{name}", im[int(y1):int(y2), int(x1):int(x2)]); row["crop"] = name; n_crop += 1
                    rep["isolated"].append(row)
        rep["videos"][vid] = dict(title=src[vid]["title"], page=src[vid]["page"], licence=src[vid]["licence"], frames_5fps=len(fs),
                                  dets=sum(len(d) for d in dets), isolated=n_iso, consistent=n_con, crops=n_crop)
        print(vid, rep["videos"][vid], flush=True)
    json.dump(rep, open(f"{a.out}/mining.json", "w"), indent=1)

if __name__ == "__main__":
    main()
