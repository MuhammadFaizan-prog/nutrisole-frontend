"""Side-by-side DEV video from cached G3 detections (no extra inference): left = G3 (guard 1%), right = guard 0.25% (arm C2, REJECTED by the
prereg FA rules; shown for illustration). Excerpts: SYNTHETIC probe segments where the arms differ most, then DEV neg clip windows where the
lower guard shows extra false tracks. Same pipeline as stagec_eval.py (floor 0.35, IouTracker defaults). Usage: render_guard.py OUT.mp4"""
import json, sys, subprocess, os, cv2, numpy as np
sys.path.insert(0, "/workspace/work/nutrisole/ml/eval")
from tracker import IouTracker, iou
from scene_guard import scene_guard
import video_gauntlet as vg
OUT = sys.argv[1]; A, B = 0.01, 0.0025
def run(gt, D, maf):
    t = IouTracker(); out = []
    for fi, fr in enumerate(gt["frames"][:len(D)]):
        out.append(t.update(scene_guard([dict(box=d[:4], classId=d[4], score=d[5]) for d in D[fi] if d[5] >= .35], maxSameClass=0, minAreaFrac=maf), fr["t_ms"]))
    return out
def draw(im, tr, lab, gt):
    im = im.copy(); H, W = im.shape[:2]
    for o in gt:
        b = o["box_norm"]; cv2.rectangle(im, (int(b[0] * W), int(b[1] * H)), (int(b[2] * W), int(b[3] * H)), (255, 255, 255), 1)
    for x in tr:
        b = x["box"]; p1, p2 = (int(b[0] * W), int(b[1] * H)), (int(b[2] * W), int(b[3] * H)); cv2.rectangle(im, p1, p2, (0, 255, 0), 2)
        cv2.putText(im, f"{vg.NAMES[x['label']]} #{x['id']}", (p1[0], max(12, p1[1] - 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
    cv2.rectangle(im, (0, 0), (W, 24), (0, 0, 0), -1); cv2.putText(im, f"{lab}  shown: {len(tr)}", (4, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return im
tmp = OUT + ".avi"; vw = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*"MJPG"), 15, (960, 680))
def emit(mp4, gt, D, frames, caption):
    LA, LB = run(gt, D, A), run(gt, D, B); cap = cv2.VideoCapture(mp4); fi = -1; want = set(frames)
    while True:
        ok, fr = cap.read(); fi += 1
        if not ok or fi > max(frames): break
        if fi not in want: continue
        g = gt["frames"][fi]["objects"]
        im = np.hstack([draw(fr, LA[fi], "G3 guard 1% (champion)", g), draw(fr, LB[fi], "guard 0.25% (C2, rejected)", g)])
        bar = np.zeros((40, 960, 3), np.uint8); cv2.putText(bar, caption, (6, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1); vw.write(np.vstack([im, bar]))
G = json.load(open("/workspace/work/cv/g9c/probe/probe_clip.json")); D = json.load(open("/workspace/work/cv/g9c/probe/probe_dets.json"))
LA, LB = run(G, D, A), run(G, D, B); score = []
for si, sg in enumerate(G["segments"]):
    def hits(L): return sum(1 for fi in range(sg["start"], sg["end"] + 1) for x in L[fi] for o in G["frames"][fi]["objects"] if x["label"] == o["cls"] and iou(x["box"], o["box_norm"]) >= .5)
    score.append((hits(LB) - hits(LA), si))
pick = sorted([s for s in sorted(score, reverse=True)[:8] if s[0] > 0], key=lambda s: s[1])
fr = [f for _, si in pick for f in range(G["segments"][si]["start"] - 6, G["segments"][si]["end"] + 1)]
emit("/workspace/work/cv/g9c/probe/probe_clip.mp4", G, D, fr, "SYNTHETIC DEV probe (val stills shrunk onto DEV negatives). White = GT.")
N = json.load(open("/workspace/work/cv/g3clips_dev/neg_clip.json")); DN = json.load(open("/workspace/work/cv/g9fp/devclip_neg_dets.json"))
NA, NB = run(N, DN, A), run(N, DN, B); ex = [fi for fi in range(len(DN)) if NB[fi] and not NA[fi]]
fr = sorted({f for e in ex for f in range(max(0, e - 15), min(len(DN), e + 15))})
emit("/workspace/work/cv/g3clips_dev/neg_clip.mp4", N, DN, fr, "DEV negative clip (no produce): extra false tracks the lower guard shows")
vw.release(); subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-c:v", "libx264", "-crf", "28", "-preset", "veryfast", "-pix_fmt", "yuv420p", OUT], check=True); os.remove(tmp)
print("wrote", OUT, "probe segs", pick, "neg extra frames", len(ex))
