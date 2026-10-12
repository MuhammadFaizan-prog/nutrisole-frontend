"""Synthetic 'handheld' regression clips built ONLY from locked TEST-split images.

This is a REGRESSION TEST, never a headline number (master prompt 4b(3), 8.10): it
exercises the temporal pipeline (tracking, hysteresis, throttling, reset) under
pan/zoom/rotation, exposure drift, blur bursts and noise, with EXACT per-frame ground
truth because the warp applied to each frame is also applied to the GT boxes.

Each segment = one test image, 4.0 s @ FPS:
  phase 'enter'  0.0-0.6 s  slides in from the side (object entering the frame)
  phase 'static' 0.6-2.6 s  hand-shake only (+-2 px jitter, tiny rotation) -> flicker is measured here
  phase 'motion' 2.6-4.0 s  pan/zoom/rotate + exposure drift + one blur burst + noise
followed by 0.8 s of an empty background (object has left) so trackers must reset.
Clips:
  det_clip.mp4      detector clip from det-v1 test images (LVIS domain)
  quality_clip.mp4  quality clip from quality2 test images (Sultana, single item, fresh/rotten)
  neg_clip.mp4      negatives: coco128 images with no COCO food classes + plain backgrounds
GT json per clip: {fps, w, h, n_frames, frames:[{t_ms, segment, phase, objects:[{cls, box_norm}]}],
                   segments:[{start, end, cls, quality, src}]}
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random

import cv2
import numpy as np

NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
COCO_FOOD = {46, 47, 48, 49, 50, 51, 52, 53, 54, 55}  # banana..cake in COCO-80 ids


def fit_canvas(img, W, H):
    """Place img on a WxH canvas (cover-crop to the canvas aspect, like a phone viewfinder)."""
    h, w = img.shape[:2]
    s = max(W / w, H / h)
    nw, nh = int(round(w * s)), int(round(h * s))
    r = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    x0, y0 = (nw - W) // 2, (nh - H) // 2
    return r[y0:y0 + H, x0:x0 + W], (s, x0, y0)


def warp_boxes(boxes_px, M, W, H):
    out = []
    for b in boxes_px:
        pts = np.array([[b[0], b[1]], [b[2], b[1]], [b[0], b[3]], [b[2], b[3]]], np.float32)
        p = cv2.transform(pts[None], M)[0]
        x1, y1 = p[:, 0].min(), p[:, 1].min()
        x2, y2 = p[:, 0].max(), p[:, 1].max()
        x1, y1, x2, y2 = max(0, x1), max(0, y1), min(W, x2), min(H, y2)
        out.append([x1, y1, x2, y2])
    return out


def render_segment(base, boxes_px, classes, quality, seg_idx, fps, W, H, rnd, frames, writer, bg):
    n = int(4.0 * fps)
    blur_at = rnd.randint(int(3.0 * fps), int(3.6 * fps))
    side = rnd.choice([-1, 1])
    for f in range(n):
        t = f / fps
        if t < 0.6:
            phase = "enter"
            k = t / 0.6
            tx, ty, ang, sc = side * (1 - k) * W * 0.9, 0.0, 0.0, 1.0
        elif t < 2.6:
            phase = "static"
            tx, ty, ang, sc = rnd.uniform(-2, 2), rnd.uniform(-2, 2), rnd.uniform(-0.5, 0.5), 1.0
        else:
            phase = "motion"
            k = (t - 2.6) / 1.4
            tx, ty = 40 * np.sin(2 * np.pi * k), 25 * np.sin(4 * np.pi * k)
            ang, sc = 12 * np.sin(2 * np.pi * k), 1.0 + 0.25 * np.sin(np.pi * k)
        M = cv2.getRotationMatrix2D((W / 2, H / 2), ang, sc)
        M[0, 2] += tx
        M[1, 2] += ty
        fr = cv2.warpAffine(base, M, (W, H), borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
        valid = cv2.warpAffine(np.full((H, W), 255, np.uint8), M, (W, H))
        fr[valid == 0] = bg[valid == 0]
        if phase == "motion":
            gain = 1.0 + 0.35 * np.sin(2 * np.pi * (t - 2.6) / 1.4)
            fr = np.clip(fr.astype(np.float32) * gain, 0, 255).astype(np.uint8)
            if abs(f - blur_at) <= 2:
                kk = 9
                kern = np.zeros((kk, kk), np.float32)
                kern[kk // 2, :] = 1.0 / kk
                fr = cv2.filter2D(fr, -1, kern)
            fr = np.clip(fr.astype(np.int16) + np.random.default_rng(f).normal(0, 6, fr.shape).astype(np.int16), 0, 255).astype(np.uint8)
        wb = warp_boxes(boxes_px, M, W, H)
        objs = []
        for b, c in zip(wb, classes):
            bw, bh = b[2] - b[0], b[3] - b[1]
            if bw > 4 and bh > 4:
                objs.append(dict(cls=int(c), box_norm=[float(b[0]) / W, float(b[1]) / H, float(b[2]) / W, float(b[3]) / H]))
        frames.append(dict(t_ms=round(1000 * len(frames) / fps, 3), segment=seg_idx, phase=phase, objects=objs))
        writer.write(fr)
    return n


def render_gap(bg, fps, frames, writer, seconds=0.8):
    for _ in range(int(seconds * fps)):
        frames.append(dict(t_ms=round(1000 * len(frames) / fps, 3), segment=-1, phase="gap", objects=[]))
        writer.write(bg)


def make_bg(W, H, rnd):
    base = np.full((H, W, 3), rnd.randint(150, 220), np.uint8)
    noise = cv2.GaussianBlur(np.random.default_rng(rnd.randint(0, 10 ** 6)).normal(0, 18, (H // 8, W // 8)).astype(np.float32), (0, 0), 2)
    noise = cv2.resize(noise, (W, H))
    tint = np.array([rnd.uniform(0.9, 1.05), rnd.uniform(0.9, 1.05), rnd.uniform(0.9, 1.05)], np.float32)
    return np.clip((base.astype(np.float32) + noise[..., None]) * tint, 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.environ.get("NUTRISOLE_DATA", "/workspace/work/cv/g1data"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=int, default=15)
    ap.add_argument("--w", type=int, default=480)
    ap.add_argument("--h", type=int, default=640)
    ap.add_argument("--n-det", type=int, default=24)
    ap.add_argument("--n-quality", type=int, default=16)
    ap.add_argument("--n-neg", type=int, default=12)
    a = ap.parse_args()
    rnd = random.Random(0)
    np.random.seed(0)
    os.makedirs(a.out, exist_ok=True)
    W, H, fps = a.w, a.h, a.fps
    four = cv2.VideoWriter_fourcc(*"mp4v")

    # ---- detector clip: single-dominant-object test images (largest box >= 15% of image)
    det_root = f"{a.data}/builds/v1/det"
    cands = []
    for lp in sorted(glob.glob(f"{det_root}/labels/test/*.txt")):
        rows = [l.split() for l in open(lp).read().strip().splitlines() if l.strip()]
        if not rows:
            continue
        areas = [float(r[3]) * float(r[4]) for r in rows]
        big = int(np.argmax(areas))
        if areas[big] >= 0.15:
            cands.append((lp, rows))
    by_cls = {}
    for lp, rows in cands:
        areas = [float(r[3]) * float(r[4]) for r in rows]
        by_cls.setdefault(int(rows[int(np.argmax(areas))][0]), []).append((lp, rows))
    picked = []
    while len(picked) < a.n_det and any(by_cls.values()):
        for c in sorted(by_cls):
            if by_cls[c] and len(picked) < a.n_det:
                picked.append(by_cls[c].pop(rnd.randrange(len(by_cls[c]))))
    frames, segs = [], []
    vw = cv2.VideoWriter(f"{a.out}/det_clip.mp4", four, fps, (W, H))
    bg = make_bg(W, H, rnd)
    render_gap(bg, fps, frames, vw, 0.6)
    for lp, rows in picked:
        ip = lp.replace("/labels/", "/images/").replace(".txt", ".jpg")
        img = cv2.imread(ip)
        canvas, (s, x0, y0) = fit_canvas(img, W, H)
        ih, iw = img.shape[:2]
        boxes, classes = [], []
        for r in rows:
            c, x, y, w, h = int(r[0]), *map(float, r[1:])
            b = [(x - w / 2) * iw * s - x0, (y - h / 2) * ih * s - y0, (x + w / 2) * iw * s - x0, (y + h / 2) * ih * s - y0]
            boxes.append(b)
            classes.append(c)
        areas = [(b[2] - b[0]) * (b[3] - b[1]) for b in boxes]
        prim = classes[int(np.argmax(areas))]
        start = len(frames)
        render_segment(canvas, boxes, classes, None, len(segs), fps, W, H, rnd, frames, vw, bg)
        segs.append(dict(start=start, end=len(frames) - 1, cls=int(prim), quality=None, src=os.path.basename(ip)))
        render_gap(bg, fps, frames, vw)
    vw.release()
    json.dump(dict(fps=fps, w=W, h=H, n_frames=len(frames), frames=frames, segments=segs, kind="det"), open(f"{a.out}/det_clip.json", "w"))

    # ---- quality clip: Sultana test split, one fruit per segment, box = whole item (approx)
    qroot = f"{a.data}/builds/v1/quality2/test"
    files = {lvl: sorted(glob.glob(f"{qroot}/{lvl}/*.jpg")) for lvl in ["fresh", "rotten"]}
    frames, segs = [], []
    vw = cv2.VideoWriter(f"{a.out}/quality_clip.mp4", four, fps, (W, H))
    bg = make_bg(W, H, rnd)
    render_gap(bg, fps, frames, vw, 0.6)
    produce_to_id = {n: i for i, n in enumerate(NAMES)}
    for k in range(a.n_quality):
        lvl = ["fresh", "rotten"][k % 2]
        f = files[lvl].pop(rnd.randrange(len(files[lvl])))
        produce = os.path.basename(f).split("__")[0]
        img = cv2.imread(f)
        # place the photo (white-paper background) at ~60% of the frame on the background
        ih, iw = img.shape[:2]
        s = 0.6 * min(W / iw, H / ih)
        r = cv2.resize(img, (int(iw * s), int(ih * s)), interpolation=cv2.INTER_AREA)
        canvas = bg.copy()
        ox, oy = (W - r.shape[1]) // 2, (H - r.shape[0]) // 2
        canvas[oy:oy + r.shape[0], ox:ox + r.shape[1]] = r
        # GT box = the item's tight box found by saturation threshold on the white paper
        hsv = cv2.cvtColor(r, cv2.COLOR_BGR2HSV)
        m = ((hsv[..., 1] > 60) | (hsv[..., 2] < 90)).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        ys, xs = np.where(m > 0)
        if len(xs) < 50:
            box = [ox, oy, ox + r.shape[1], oy + r.shape[0]]
        else:
            box = [ox + xs.min(), oy + ys.min(), ox + xs.max(), oy + ys.max()]
        start = len(frames)
        render_segment(canvas, [box], [produce_to_id[produce]], lvl, len(segs), fps, W, H, rnd, frames, vw, bg)
        segs.append(dict(start=start, end=len(frames) - 1, cls=produce_to_id[produce], quality=lvl, src=os.path.basename(f)))
        render_gap(bg, fps, frames, vw)
    vw.release()
    json.dump(dict(fps=fps, w=W, h=H, n_frames=len(frames), frames=frames, segments=segs, kind="quality",
                   note="GT box for quality clips is a saturation-threshold box on white paper (approximate)"), open(f"{a.out}/quality_clip.json", "w"))

    # ---- negative clip
    neg = []
    for lp in sorted(glob.glob(f"{a.data}/neg/coco128/labels/train2017/*.txt")):
        cl = {int(l.split()[0]) for l in open(lp).read().strip().splitlines() if l.strip()}
        if not (cl & COCO_FOOD) and 60 not in cl and 41 not in cl:  # no food, no dining table, no cup
            neg.append(lp.replace("/labels/", "/images/").replace(".txt", ".jpg"))
    rnd.shuffle(neg)
    frames, segs = [], []
    vw = cv2.VideoWriter(f"{a.out}/neg_clip.mp4", four, fps, (W, H))
    for k in range(a.n_neg):
        if k % 4 == 3:
            canvas, src = make_bg(W, H, rnd), "plain_background"
        else:
            canvas, _ = fit_canvas(cv2.imread(neg[k]), W, H)
            src = os.path.basename(neg[k])
        start = len(frames)
        render_segment(canvas, [], [], None, len(segs), fps, W, H, rnd, frames, vw, make_bg(W, H, rnd))
        segs.append(dict(start=start, end=len(frames) - 1, cls=None, quality=None, src=src))
    vw.release()
    json.dump(dict(fps=fps, w=W, h=H, n_frames=len(frames), frames=frames, segments=segs, kind="neg",
                   note="coco128 images without COCO food classes/dining table/cup + plain backgrounds"), open(f"{a.out}/neg_clip.json", "w"))
    print("clips written", a.out)


if __name__ == "__main__":
    main()
