#!/usr/bin/env python3
"""G8 full-absence check for holdout clips the user marked present_classes == "none" (6 sampled frames only).
Goal: turn "none" into a verified negative (prereg rule 4 / FA/min) by showing the reviewer EVERY distinct moment
where any detector claims produce.

Hit sources (per clip):
  * G3 per-frame detections from stage-1 (/workspace/work/cv/g7al/stage1/<clip>/frames.json, ~4.2 fps, raw score>=0.1),
    kept at the deployed new-track threshold G3_THR (0.25 = tuned ByteTrack pick nt0.25_mt0.8_mh1; the lowest score
    that can spawn a visible track).
  * OWLv2 boxes from the G3+OWLv2 merge proposals (ml/runs/G8/autolabel/proposals/<clip>.json, keyframes),
    kept at OWL score >= 0.3, 12 supported classes only.
Clustering: hits sorted by score; greedy pick, a new moment must be >= 1.0 s from every picked moment; top MAXK per clip,\nwith the best moment of each claimed class taken before a class repeats.
Tiles: crop-in-context (box expanded, min 35% of frame side), box drawn, header "#N clip t=..s claimed: X (src score)".
Clips with zero hits anywhere are listed as "no detector hits" (cheap negatives) in the CSV with tile blank.
Decoding: ffmpeg -ss <t> -frames:v 1, threads 1, one frame at a time (low memory).
Usage: g8_absence_check.py OUTDIR [OUTDIR2 ...]   (first dir gets the files, others get copies)"""
import csv, io, json, os, shutil, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

G8 = '/workspace/work/nutrisole/ml/runs/G8/'
REV = G8 + 'review/holdout/holdout_presence_review.csv'
PROP = G8 + 'autolabel/proposals/{}.json'
S1 = '/workspace/work/cv/g7al/stage1/{}/frames.json'
AL = '/workspace/work/cv/g8logs/al_order.txt'
NAMES = ['banana', 'apple', 'mango', 'citrus', 'guava', 'pomegranate', 'lemon_lime', 'tomato', 'potato', 'cucumber',
         'carrot', 'capsicum']
G3_THR, OWL_THR, GAP_S, MAXK = 0.25, 0.30, 1.0, 4
EXCLUDED = {'8': 'UNCERTAIN in presence review', '28': 'UNCERTAIN in presence review'}
TW, TH, HDR, COLS, PER = 400, 300, 40, 4, 12

outs = sys.argv[1:]
out = outs[0]
os.makedirs(out, exist_ok=True)
paths = {os.path.basename(p.strip()).split('.')[0]: p.strip() for p in open(AL) if p.strip()}
try:
    FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 14)
except Exception:
    FONT = ImageFont.load_default()


def hits_for(clip):
    H = []
    if os.path.exists(S1.format(clip)):
        for f in json.load(open(S1.format(clip)))['frames']:
            for d in f['dets']:
                if d['score'] >= G3_THR:
                    H.append(dict(t=f['t'], cls=NAMES[d['classId']], score=d['score'], box=d['box'], src='G3'))
    if os.path.exists(PROP.format(clip)):
        for k in json.load(open(PROP.format(clip)))['keyframes']:
            for b in k['boxes']:
                o = b.get('owl')
                if o and o[0] in NAMES and o[1] >= OWL_THR:
                    H.append(dict(t=k['t'], cls=o[0], score=o[1], box=b['box'], src='OWLv2'))
    return H


def cluster(H):
    """Distinct moments (>= GAP_S apart), score order. Returned order puts the best moment of each claimed class first
    (so the top MAXK tiles cover every claimed class before repeating one), then the remaining moments by score."""
    H = sorted(H, key=lambda h: -h['score']); pick = []
    for h in H:
        if all(abs(h['t'] - p['t']) >= GAP_S for p in pick):
            pick.append(h)
    first, seen = [], set()
    for h in pick:
        if h['cls'] not in seen:
            seen.add(h['cls']); first.append(h)
    return first + [h for h in pick if h not in first]


CACHE = '/workspace/work/cv/g8logs/absence_frame_cache'  # resumable: decoded frames cached (not committed)


def frame(path, t):
    os.makedirs(CACHE, exist_ok=True)
    cp = f"{CACHE}/{os.path.basename(path).split('.')[0]}_{t:.3f}.png"
    if os.path.exists(cp):
        return Image.open(cp).convert('RGB')
    r = subprocess.run(['ffmpeg', '-v', 'error', '-threads', '1', '-ss', f'{t:.3f}', '-i', path, '-frames:v', '1',
                        '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True)
    if not r.stdout:
        return None
    im = Image.open(io.BytesIO(r.stdout)).convert('RGB'); im.save(cp); return im


def tile(img, h, header):
    W, Hh = img.size
    x0, y0, x1, y1 = h['box'][0] * W, h['box'][1] * Hh, h['box'][2] * W, h['box'][3] * Hh
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    cw = max(3 * (x1 - x0), 0.35 * W); ch = max(3 * (y1 - y0), 0.35 * Hh)
    ar = TW / TH  # match tile aspect
    if cw / ch < ar: cw = ch * ar
    else: ch = cw / ar
    cw, ch = min(cw, W), min(ch, Hh)
    L = min(max(cx - cw / 2, 0), W - cw); T = min(max(cy - ch / 2, 0), Hh - ch)
    crop = img.crop((int(L), int(T), int(L + cw), int(T + ch)))
    s = min(TW / crop.width, TH / crop.height)
    crop = crop.resize((max(1, int(crop.width * s)), max(1, int(crop.height * s))))
    t = Image.new('RGB', (TW, TH + HDR), (20, 20, 20)); ox, oy = (TW - crop.width) // 2, HDR + (TH - crop.height) // 2
    t.paste(crop, (ox, oy)); d = ImageDraw.Draw(t)
    bx = [ox + (x0 - L) * s, oy + (y0 - T) * s, ox + (x1 - L) * s, oy + (y1 - T) * s]
    col = (255, 60, 60) if h['src'] == 'G3' else (60, 200, 255)
    d.rectangle(bx, outline=col, width=3)
    lab = f"{h['cls']} {h['score']:.2f}"
    ly = bx[1] - 18 if bx[1] - 18 > HDR else bx[3] + 2
    d.rectangle([bx[0], ly, bx[0] + 8 * len(lab) + 6, ly + 17], fill=col); d.text((bx[0] + 3, ly + 1), lab, fill=(0, 0, 0), font=FONT)
    a, _, b = header.partition(' claimed: ')
    d.text((5, 3), a, fill=(255, 255, 255), font=FONT); d.text((5, 21), 'claimed: ' + b, fill=(255, 220, 90), font=FONT)
    return t


rows = [r for r in csv.DictReader(open(REV)) if r['present_classes'].strip().lower() == 'none']
recs, tiles, nozero, withhits, excl = [], [], [], [], []
for r in csv.DictReader(open(REV)):
    if r['n'] in EXCLUDED:
        excl.append((r['n'], r['clip_id'], EXCLUDED[r['n']]))
for r in rows:
    n, clip = r['n'], r['clip_id']
    H = hits_for(clip)
    if not H:
        nozero.append(clip)
        recs.append(dict(n=n, clip_id=clip, t_s='', claimed_class='', score='', source='no detector hits', tile='', verdict='',
                         split=r['split'], n_raw_hits=0, n_moments=0))
        continue
    M = cluster(H); withhits.append(clip)
    for h in M[:MAXK]:
        img = frame(paths[clip], h['t'])
        hdr = f"#{n} {clip} t={h['t']:.1f}s claimed: {h['cls']} ({h['src']} {h['score']:.2f})"
        tid = f"{len(tiles) + 1:03d}"
        if img is not None:
            tiles.append((tid, tile(img, h, f"[{tid}] " + hdr)))
        recs.append(dict(n=n, clip_id=clip, t_s=round(h['t'], 2), claimed_class=h['cls'], score=round(h['score'], 4), source=h['src'],
                         tile=f"{tid}@absence_sheet_{(len(tiles) - 1) // PER + 1}.jpg" if img is not None else 'DECODE_FAIL', verdict='',
                         split=r['split'], n_raw_hits=len(H), n_moments=len(M)))
    print(clip, 'raw', len(H), 'moments', len(M), flush=True)

sheets = []
for si in range(0, len(tiles), PER):
    chunk = tiles[si:si + PER]; rws = (len(chunk) + COLS - 1) // COLS
    sh = Image.new('RGB', (COLS * TW + (COLS - 1) * 4, rws * (TH + HDR) + (rws - 1) * 4), (255, 255, 255))
    for i, (_, t) in enumerate(chunk):
        sh.paste(t, ((i % COLS) * (TW + 4), (i // COLS) * (TH + HDR + 4)))
    p = f"{out}/absence_sheet_{si // PER + 1}.jpg"; q = 85
    while True:
        sh.save(p, quality=q)
        if os.path.getsize(p) < 1.5e6 or q <= 50: break
        q -= 10
    sheets.append(p)
F = ['n', 'clip_id', 't_s', 'claimed_class', 'score', 'source', 'tile', 'verdict', 'split', 'n_raw_hits', 'n_moments']
with open(f"{out}/absence_check.csv", 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=F); w.writeheader(); w.writerows(recs)
    for n, c, why in excl:
        w.writerow(dict(n=n, clip_id=c, source=f'EXCLUDED: {why}'))
summ = dict(g3_thr=G3_THR, owl_thr=OWL_THR, gap_s=GAP_S, max_per_clip=MAXK, none_clips=len(rows), zero_hit_clips=nozero,
            clips_with_hits=withhits, tiles=len(tiles), sheets=[os.path.basename(s) for s in sheets], excluded=excl)
json.dump(summ, open(f"{out}/absence_summary.json", 'w'), indent=1)
for o in outs[1:]:
    os.makedirs(o, exist_ok=True)
    for fn in os.listdir(out):
        shutil.copy(f"{out}/{fn}", o)
print(json.dumps(summ))
