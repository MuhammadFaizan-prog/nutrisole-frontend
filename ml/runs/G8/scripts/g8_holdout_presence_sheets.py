#!/usr/bin/env python3
"""G8: clip-level presence review sheets for the VB8 holdout (34 clips).
Clean frames only (no model boxes). 6 frames/clip evenly spread, 6 clips/sheet.
Portrait clips get taller cells so produce stays legible.
Writes sheets + holdout_presence_review.csv (blank columns for user verification).
Usage: g8_holdout_presence_sheets.py OUTDIR [start_sheet end_sheet]   (0-based, end exclusive)
Uses ffmpeg (decodes AV1), threads 1, one frame at a time (low memory)."""
import csv, os, subprocess, sys, io
from PIL import Image, ImageDraw, ImageFont
R = '/workspace/work/nutrisole/'
SPL = R + 'ml/runs/G7/video_v7/splits_v7.csv'
AL = '/workspace/work/cv/g8logs/al_order.txt'
SPLITS = ['holdout (LOCKED)', 'holdout_v7_pending', 'negatives_v7']
PRIO = ['c6e08132a', 'c61cbc2a6', 'c9030be18', 'c97bdc431', 'c19ae062b', 'c8b2d2f36']
W, H_LAND, H_PORT, NF, PER, HDR = 320, 180, 400, 6, 6, 28

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
rows = [r for r in csv.DictReader(open(SPL)) if r['split'] in SPLITS]
paths = {os.path.basename(p.strip()).split('.')[0]: p.strip() for p in open(AL) if p.strip()}
rows.sort(key=lambda r: (PRIO.index(r['clip_id']) if r['clip_id'] in PRIO else 99,
                         SPLITS.index(r['split']), r['clip_id']))


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, **kw)


def dur(p):
    o = run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p], text=True).stdout.strip()
    try:
        return float(o)
    except ValueError:
        return None


def dims(p):
    o = run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
             'stream=width,height:stream_side_data=rotation', '-of', 'csv=p=0', p], text=True).stdout.split()
    try:
        w, h = [int(x) for x in o[0].split(',')[:2]]
        rot = any(x.strip(',').lstrip('-') in ('90', '270') for x in o[1:])
        return (h, w) if rot else (w, h)
    except Exception:
        return (16, 9)


def frame(p, t):
    o = run(['ffmpeg', '-v', 'error', '-threads', '1', '-ss', f'{t:.2f}', '-i', p, '-frames:v', '1',
             '-vf', 'scale=640:-2', '-threads', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'], timeout=60).stdout
    if not o:
        return None
    im = Image.open(io.BytesIO(o)).convert('RGB')
    im.load()
    return im


try:
    F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 18)
    F2 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
except OSError:
    F = F2 = ImageFont.load_default()

sheets = [rows[i:i + PER] for i in range(0, len(rows), PER)]
a = int(sys.argv[2]) if len(sys.argv) > 2 else 0
b = int(sys.argv[3]) if len(sys.argv) > 3 else len(sheets)
csvrows = []
for si, grp in enumerate(sheets):
    name = f'holdout_presence_sheet_{si + 1}.jpg'
    for j, r in enumerate(grp):
        csvrows.append(dict(n=si * PER + j + 1, clip_id=r['clip_id'], uploader=r['uploader'], split=r['split'],
                            sheet=name, present_classes='', absent_confirmed='', notes=''))
    if not (a <= si < b):
        continue
    hs = []
    for r in grp:
        p = paths.get(r['clip_id'])
        w0, h0 = dims(p) if p else (16, 9)
        hs.append(H_LAND if w0 >= h0 else H_PORT)
    ys = [sum(HDR + h + 4 for h in hs[:j]) for j in range(len(grp))]
    sheet = Image.new('RGB', (W * NF + 5 * (NF - 1), sum(HDR + h + 4 for h in hs)), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for j, r in enumerate(grp):
        n = si * PER + j + 1
        p = paths.get(r['clip_id'])
        y, H = ys[j], hs[j]
        D = (dur(p) if p else None) or float(r['dur_s'])
        d.rectangle([0, y, sheet.width, y + HDR - 2], fill=(30, 30, 30))
        d.text((6, y + 4), f"#{n} {r['clip_id']}  ({r['uploader']}, {r['split']}, {D:.1f}s)", fill=(255, 255, 255), font=F)
        for k in range(NF):
            t = D * (k + 0.5) / NF
            x = k * (W + 5)
            im = frame(p, t) if p else None
            if im is None and p:
                im = frame(p, max(0, t - 1.0))
            if im is None:
                d.rectangle([x, y + HDR, x + W, y + HDR + H], fill=(200, 0, 0))
                d.text((x + 10, y + HDR + H // 2 - 10), 'NO FRAME', fill=(255, 255, 255), font=F)
                continue
            im.thumbnail((W, H))
            sheet.paste(im, (x + (W - im.width) // 2, y + HDR + (H - im.height) // 2))
            d.rectangle([x, y + HDR + H - 18, x + 62, y + HDR + H], fill=(0, 0, 0))
            d.text((x + 3, y + HDR + H - 17), f't={t:.1f}s', fill=(255, 255, 0), font=F2)
    q = 85
    fp = os.path.join(out, name)
    while True:
        sheet.save(fp, quality=q)
        if os.path.getsize(fp) < 1.5e6 or q < 50:
            break
        q -= 10
    print(name, [c['n'] for c in csvrows if c['sheet'] == name], os.path.getsize(fp), flush=True)

with open(os.path.join(out, 'holdout_presence_review.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(csvrows[0]))
    w.writeheader()
    w.writerows(csvrows)
missing = [r['clip_id'] for r in rows if r['clip_id'] not in paths]
print('clips', len(rows), 'uploaders', len({r['uploader'] for r in rows}), 'missing_paths', missing)
