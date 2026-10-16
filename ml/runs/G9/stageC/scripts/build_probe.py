"""G9 Stage C SYNTHETIC small-object probe (DEV-only sources). Each segment = one DEV val still (det_v3 val, single-class GT)
downscaled by s in {1/2, 1/3, 1/4} of its contain-fit size and pasted onto a DEV negative background (g3data/devneg, cover-fit to
480x640) with a slow linear drift (3 px/frame, random direction, clamped), 18 frames at 15 fps; 6 background-only gap frames
before each segment. Up to 6 images per class (random.Random(0)). Writes probe_clip.mp4 + probe_clip.json (video_gauntlet format).
NOT real footage: a ranking proxy for small produce, never a confirmation."""
import os, sys, json, glob, random, math
import cv2, numpy as np
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
W, H, FPS, SEGF, GAP = 480, 640, 15, 18, 6; SCALES = [1 / 2, 1 / 3, 1 / 4]; PER = 6
rnd = random.Random(0)
bys = {}
for l in open("/workspace/work/cv/g3data/det_v3/val.txt"):
    p = l.strip(); lp = p.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"
    if not os.path.exists(lp): continue
    g = [list(map(float, x.split()[:5])) for x in open(lp) if len(x.split()) >= 5]
    cs = {int(x[0]) for x in g}
    if len(cs) == 1: bys.setdefault(cs.pop(), []).append((p, g))
pick = []
for c in sorted(bys):
    L = sorted(bys[c]); rnd.shuffle(L); pick += [(c, p, g) for p, g in L[:PER]]
bgs = sorted(glob.glob("/workspace/work/cv/g3data/devneg/*.jpg"))
def cover(im):
    h, w = im.shape[:2]; s = max(W / w, H / h); r = cv2.resize(im, (math.ceil(w * s), math.ceil(h * s)), interpolation=cv2.INTER_AREA)
    y, x = (r.shape[0] - H) // 2, (r.shape[1] - W) // 2; return r[y:y + H, x:x + W].copy()
vw = cv2.VideoWriter(f"{OUT}/probe_clip.mp4", cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
frames, segs, k = [], [], 0
def t(): return round(1000 * len(frames) / FPS, 3)
for si, (s, (c, p, g)) in enumerate([(s, x) for x in pick for s in SCALES]):
    bg = cover(cv2.imread(bgs[si % len(bgs)])); im = cv2.imread(p); h, w = im.shape[:2]
    f0 = min(W / w, H / h) * s; nw, nh = max(8, round(w * f0)), max(8, round(h * f0)); sm = cv2.resize(im, (nw, nh), interpolation=cv2.INTER_AREA)
    x0, y0 = rnd.uniform(0, W - nw), rnd.uniform(0, H - nh); a = rnd.uniform(0, 2 * math.pi); vx, vy = 3 * math.cos(a), 3 * math.sin(a)
    for _ in range(GAP): vw.write(bg); frames.append(dict(t_ms=t(), segment=-1, phase="gap", objects=[]))
    st = len(frames)
    for f in range(SEGF):
        x, y = min(max(0, x0 + vx * f), W - nw), min(max(0, y0 + vy * f), H - nh); xi, yi = int(round(x)), int(round(y))
        fr = bg.copy(); fr[yi:yi + nh, xi:xi + nw] = sm; vw.write(fr)
        objs = [dict(cls=c, box_norm=[(xi + (b[1] - b[3] / 2) * nw) / W, (yi + (b[2] - b[4] / 2) * nh) / H, (xi + (b[1] + b[3] / 2) * nw) / W, (yi + (b[2] + b[4] / 2) * nh) / H]) for b in g]
        frames.append(dict(t_ms=t(), segment=len(segs), phase="enter" if f < 3 else "static", objects=objs))
    segs.append(dict(start=st, end=len(frames) - 1, cls=c, quality=None, src=os.path.basename(p), scale=round(s, 4)))
for _ in range(GAP): vw.write(bg); frames.append(dict(t_ms=t(), segment=-1, phase="gap", objects=[]))
vw.release()
json.dump(dict(fps=FPS, w=W, h=H, n_frames=len(frames), frames=frames, segments=segs, kind="det", split="SYNTHETIC_DEV_PROBE",
               note=build_doc if (build_doc := __doc__) else ""), open(f"{OUT}/probe_clip.json", "w"))
print(len(segs), "segments", len(frames), "frames", {c: len(bys[c]) for c in sorted(bys)})
