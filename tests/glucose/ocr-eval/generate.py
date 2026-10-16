#!/usr/bin/env python3
"""Synthetic glucose report / meter-screen images for OCR evaluation. NO real patient data:
every name, id, lab name and value is generated. Two disjoint splits:
  dev      - seed 1001, fonts DEV_FONTS, used while building the parser/layout code
  heldout  - seed 777123, fonts HELDOUT_FONTS (none shared with dev), different label
             spellings/columns mixes; never used for tuning, only for the final score.
Each image gets a ground-truth JSON: readings [{type, value, unit}], date (sample day: collection date,
else registration date), nonGlucose (HbA1c etc., must NOT be imported) and kind.
Usage: python3 generate.py <dev|heldout> <outdir> [count]"""
import json, math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import cv2

FD = '/usr/share/fonts/opentype/urw-base35/'
DJ = '/usr/share/fonts/truetype/dejavu/'
DEV_FONTS = [(DJ + 'DejaVuSans.ttf', DJ + 'DejaVuSans-Bold.ttf'), (FD + 'NimbusRoman-Regular.otf', FD + 'NimbusRoman-Bold.otf')]
HELDOUT_FONTS = [(FD + 'NimbusSans-Regular.otf', FD + 'NimbusSans-Bold.otf'), (FD + 'C059-Roman.otf', FD + 'C059-Bold.otf'),
                 (FD + 'URWBookman-Light.otf', FD + 'URWBookman-Demi.otf'), (DJ + 'DejaVuSerif.ttf', DJ + 'DejaVuSerif-Bold.ttf'),
                 (FD + 'NimbusMonoPS-Regular.otf', FD + 'NimbusMonoPS-Bold.otf'), (FD + 'P052-Roman.otf', FD + 'P052-Bold.otf'),
                 (FD + 'NimbusSansNarrow-Regular.otf', FD + 'NimbusSansNarrow-Bold.otf'), (FD + 'URWGothic-Book.otf', FD + 'URWGothic-Demi.otf')]

# Label vocab per meal type. Dev sees a subset; held-out samples from the full list.
LABELS = {
    'fasting': ['Glucose Fasting', 'Blood Sugar Fasting', 'FBS', 'Sugar (F)', 'Fasting Blood Glucose', 'Glucose (Fasting)', 'Fasting Plasma Glucose', 'Blood Glucose Fasting', 'F.B.S', 'Glucose - Fasting'],
    'random': ['Blood Sugar Random', 'Glucose Random', 'RBS', 'Sugar (R)', 'Random Blood Sugar', 'Random Plasma Glucose', 'R.B.S', 'Glucose (Random)'],
    'after_meal': ['2 hr PP', 'Blood Sugar 2 hrs PP', 'Post Prandial Glucose', 'Glucose 2 hrs after meal', 'P.P.B.S', 'Sugar 2 hr P.P', 'Glucose PP (2 Hours)'],
}
DEV_LABELS = {k: v[:4] for k, v in LABELS.items()}
RANGES = {'fasting': ['70 - 110', '70-100', '74 - 106', '60 - 110', '< 100', '70 – 99'], 'random': ['< 200', '80 - 160', '70 - 140', 'Upto 140', '< 140'], 'after_meal': ['< 140', '80 - 140', '< 160', 'Upto 140']}
MMOL_RANGES = {'fasting': ['3.9 - 6.1', '3.9-5.5', '< 5.6'], 'random': ['< 11.1', '3.9 - 7.8'], 'after_meal': ['< 7.8', '3.9 - 7.8']}
OTHER_ROWS = [('Haemoglobin', lambda r: f'{r.uniform(10.5, 16.5):.1f}', 'g/dL', ['13.0 - 17.0', '12.0 - 15.5']),
              ('Total Cholesterol', lambda r: str(r.randint(140, 260)), 'mg/dL', ['< 200']),
              ('Triglycerides', lambda r: str(r.randint(90, 280)), 'mg/dL', ['< 150']),
              ('Serum Creatinine', lambda r: f'{r.uniform(0.6, 1.4):.2f}', 'mg/dL', ['0.6 - 1.2', '0.7 - 1.3']),
              ('Urea', lambda r: str(r.randint(15, 45)), 'mg/dL', ['10 - 50']),
              ('ALT (SGPT)', lambda r: str(r.randint(12, 60)), 'U/L', ['< 40']),
              ('TSH', lambda r: f'{r.uniform(0.6, 4.5):.2f}', 'uIU/mL', ['0.4 - 4.0'])]
LAB_NAMES = ['Model Town Diagnostic Lab (synthetic)', 'CITY PATH LABORATORIES - SAMPLE', 'Green Valley Clinical Lab', 'National Reference Lab (demo)',
             'Crescent Diagnostics', 'Ravi Medical Laboratory', 'Metro Pathology Centre', 'Indus Health Labs (test)']
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def fmt_date(r, y, m, d, style):
    if style == 0: return f'{d:02d}-{MONTHS[m-1]}-{y}'
    if style == 1: return f'{d:02d}/{m:02d}/{y}'
    if style == 2: return f'{d} {MONTHS[m-1]} {y}'
    if style == 3: return f'{d:02d}-{m:02d}-{y}'
    return f'{d:02d}.{m:02d}.{y}'


def fmt_time(r, hh, mm):
    if r.random() < 0.6: return f'{(hh % 12) or 12:02d}:{mm:02d} {"AM" if hh < 12 else "PM"}'
    return f'{hh:02d}:{mm:02d}'


def font(path, size): return ImageFont.truetype(path, size)


def gen_report(r, split, idx):
    fonts = DEV_FONTS if split.startswith('dev') else HELDOUT_FONTS
    reg, bold = r.choice(fonts) if split.startswith('dev') else fonts[(idx + (3 if split == 'heldout2' else 0)) % len(fonts)]
    labels = DEV_LABELS if split.startswith('dev') else LABELS
    W, H = 1240, 1754  # A4 @150dpi
    img = Image.new('RGB', (W, H), (252, 252, 250)); dr = ImageDraw.Draw(img)
    s = r.randint(22, 28); f = font(reg, s); fb = font(bold, s); fh = font(bold, s + 14); fs = font(reg, s - 4)
    y = 60
    dr.text((80, y), r.choice(LAB_NAMES), font=fh, fill=(20, 40, 90)); y += s + 30
    dr.text((80, y), f'Ph: 042-{r.randint(3000000, 3999999)}  |  www.example-lab.test', font=fs, fill=(60, 60, 60)); y += s + 10
    dr.line((60, y, W - 60, y), fill=(30, 30, 30), width=2); y += 20
    yy, mo, dd = 2026, r.randint(1, 10), r.randint(1, 28)
    if mo == 10: dd = min(dd, 15)
    ch, cm = r.randint(7, 11), r.randint(0, 59)
    dstyle = r.randint(0, 4)
    coll = f'{fmt_date(r, yy, mo, dd, dstyle)} {fmt_time(r, ch, cm)}'
    rd = min(28, dd + r.choice([0, 0, 1]))
    rep = f'{fmt_date(r, yy, mo, rd, dstyle)} {fmt_time(r, r.randint(12, 18), r.randint(0, 59))}'
    reg_d = f'{fmt_date(r, yy, mo, dd, dstyle)} {fmt_time(r, max(6, ch - 1), r.randint(0, 59))}'
    has_coll = r.random() < 0.8
    pid = f'MR-{r.randint(100000, 999999)}'
    left = [('Patient Name', f'TEST PATIENT {chr(65 + idx % 26)}{r.randint(1, 99)}'), ('Age / Sex', f'{r.randint(18, 80)} Y / {r.choice(["M", "F"])}'), ('MR No.', pid)]
    coll_label = r.choice(['Collected On', 'Sample Collected', 'Collection Date', 'Specimen Collected', 'Sample Taken'])
    right = [('Registered', reg_d)] + ([(coll_label, coll)] if has_coll else []) + [(r.choice(['Reported On', 'Report Date', 'Reported']), rep)]
    for i in range(max(len(left), len(right))):
        if i < len(left): dr.text((80, y), f'{left[i][0]}: {left[i][1]}', font=f, fill=(0, 0, 0))
        if i < len(right): dr.text((650, y), f'{right[i][0]}: {right[i][1]}', font=f, fill=(0, 0, 0))
        y += s + 14
    y += 10; dr.line((60, y, W - 60, y), fill=(30, 30, 30), width=1); y += 18
    dr.text((80, y), r.choice(['CLINICAL CHEMISTRY', 'BIOCHEMISTRY', 'DIABETIC PROFILE', 'BLOOD GLUCOSE']), font=fh, fill=(0, 0, 0)); y += s + 30
    # Column order varies: unit before or after range.
    unit_last = r.random() < 0.4
    cols = ['Test', 'Result', 'Range', 'Unit'] if unit_last else ['Test', 'Result', 'Unit', 'Range']
    heads = {'Test': r.choice(['Test Name', 'Test', 'Investigation', 'Parameter']), 'Result': r.choice(['Result', 'Results', 'Observed Value', 'Value']),
             'Unit': r.choice(['Unit', 'Units']), 'Range': r.choice(['Reference Range', 'Normal Range', 'Normal Value', 'Biological Ref. Interval'])}
    xs = {'Test': 80}
    xr = r.randint(470, 560); xs['Result'] = xr
    if unit_last: xs['Range'] = xr + r.randint(170, 220); xs['Unit'] = xs['Range'] + r.randint(240, 300)
    else: xs['Unit'] = xr + r.randint(150, 200); xs['Range'] = xs['Unit'] + r.randint(150, 200)
    for c in cols: dr.text((xs[c], y), heads[c], font=fb, fill=(0, 0, 0))
    y += s + 12; dr.line((60, y, W - 60, y), fill=(120, 120, 120), width=1); y += 14
    mmol = r.random() < 0.2
    unit = 'mmol/L' if mmol else 'mg/dL'
    types = r.sample(['fasting', 'random', 'after_meal'], k=r.choice([1, 1, 2, 2, 3]))
    rows = []
    gt = []
    for t in types:
        if mmol:
            v = {'fasting': r.uniform(4.2, 9.5), 'random': r.uniform(5.0, 15.0), 'after_meal': r.uniform(5.5, 14.0)}[t]; val = f'{v:.1f}'
            rng = r.choice(MMOL_RANGES[t])
        else:
            v = {'fasting': r.randint(72, 190), 'random': r.randint(85, 320), 'after_meal': r.randint(95, 290)}[t]; val = str(v)
            rng = r.choice(RANGES[t])
        lab = r.choice(labels[t]); flag = ''
        if not mmol and ((t == 'fasting' and v > 110) or v > 200) and r.random() < 0.5: flag = r.choice([' H', ' (H)', ' High'])
        rows.append((lab, val + flag, unit, rng, True)); gt.append({'type': t, 'value': val, 'unit': unit})
    for o in r.sample(OTHER_ROWS, k=r.randint(1, 3)):
        rows.append((o[0], o[1](r), o[2], r.choice(o[3]), False))
    non = []
    if r.random() < 0.45:
        a1c = f'{r.uniform(5.0, 10.5):.1f}'
        rows.append((r.choice(['HbA1c', 'Glycated Haemoglobin (HbA1c)', 'HbA1c (Glycosylated Hb)']), a1c, '%', r.choice(['4.0 - 5.6', '< 5.7', '4 - 6']), False)); non.append({'kind': 'hba1c', 'value': a1c})
    if r.random() < 0.25: rows.append(('Urine Sugar', r.choice(['Nil', 'Negative', 'Trace']), '', 'Nil', False))
    r.shuffle(rows)
    for (lab, val, u, rng, _) in rows:
        dr.text((xs['Test'], y), lab, font=f, fill=(0, 0, 0))
        dr.text((xs['Result'], y), val, font=fb if r.random() < 0.6 else f, fill=(0, 0, 0))
        if u: dr.text((xs['Unit'], y), u, font=f, fill=(0, 0, 0))
        dr.text((xs['Range'], y), rng, font=f, fill=(0, 0, 0))
        y += s + r.randint(18, 30)
    y += 20
    for line in r.sample(['Method: Hexokinase / GOD-POD', 'Fasting: 70 - 100 mg/dL normal, 100 - 125 impaired, >= 126 diabetic (ADA).',
                          'Note: Results relate only to the sample received.', 'This is a computer generated report. Not valid for court.',
                          'Random glucose >= 200 mg/dL with symptoms suggests diabetes.'], k=2):
        dr.text((80, y), line, font=fs, fill=(70, 70, 70)); y += s + 8
    dr.text((80, H - 120), 'Dr. Sample Pathologist (synthetic)  MBBS, FCPS', font=fs, fill=(40, 40, 40))
    # Expected date = the day the sample was drawn: collection date, else registration (same day).
    gd = {'y': yy, 'm': mo, 'd': dd}
    return img, {'kind': 'lab-report', 'readings': gt, 'date': gd, 'nonGlucose': non, 'font': os.path.basename(reg), 'template': 'unit-last' if unit_last else 'unit-before-range'}


SEG = {'0': 'abcfed', '1': 'bc', '2': 'abged', '3': 'abgcd', '4': 'fgbc', '5': 'afgcd', '6': 'afgedc', '7': 'abc', '8': 'abcdefg', '9': 'abfgcd'}


def seg_digit(dr, x, y, w, h, t, ch, col):
    pts = {'a': [(x + t, y), (x + w - t, y), (x + w - 2 * t, y + t), (x + 2 * t, y + t)],
           'd': [(x + 2 * t, y + h - t), (x + w - 2 * t, y + h - t), (x + w - t, y + h), (x + t, y + h)],
           'g': [(x + t, y + h / 2), (x + 2 * t, y + h / 2 - t / 2), (x + w - 2 * t, y + h / 2 - t / 2), (x + w - t, y + h / 2), (x + w - 2 * t, y + h / 2 + t / 2), (x + 2 * t, y + h / 2 + t / 2)],
           'f': [(x, y + t), (x + t, y + 2 * t), (x + t, y + h / 2 - t), (x, y + h / 2 - t / 2)],
           'b': [(x + w, y + t), (x + w, y + h / 2 - t / 2), (x + w - t, y + h / 2 - t), (x + w - t, y + 2 * t)],
           'e': [(x, y + h / 2 + t / 2), (x + t, y + h / 2 + t), (x + t, y + h - 2 * t), (x, y + h - t)],
           'c': [(x + w, y + h / 2 + t / 2), (x + w, y + h - t), (x + w - t, y + h - 2 * t), (x + w - t, y + h / 2 + t)]}
    for sname in SEG[ch]: dr.polygon(pts[sname], fill=col)


def gen_meter(r, split, idx):
    fonts = DEV_FONTS if split.startswith('dev') else HELDOUT_FONTS
    reg, bold = r.choice(fonts) if split.startswith('dev') else fonts[(idx + (3 if split == 'heldout2' else 0)) % len(fonts)]
    W, H = 900, 640
    bg = tuple(int(c) for c in r.choice([(176, 190, 170), (200, 205, 190), (160, 178, 165), (215, 218, 205)]))
    img = Image.new('RGB', (W, H), (40, 40, 45)); dr = ImageDraw.Draw(img)
    dr.rounded_rectangle((60, 50, W - 60, H - 50), radius=30, fill=bg)
    mmol = r.random() < 0.3
    val = f'{r.uniform(3.8, 16.0):.1f}' if mmol else str(r.randint(65, 320))
    unit = 'mmol/L' if mmol else 'mg/dL'
    col = (25, 30, 25)
    dw, dh, t = 110, 200, 20; x = 160 if len(val.replace('.', '')) == 3 else 230; y0 = 200
    for ch in val:
        if ch == '.': dr.ellipse((x - 8, y0 + dh - 26, x + 18, y0 + dh), fill=col); x += 40; continue
        seg_digit(dr, x, y0, dw, dh, t, ch, col); x += dw + 34
    fu = font(bold, 46); dr.text((x + 10, y0 + dh - 50), unit, font=fu, fill=col)
    mo, dd = r.randint(1, 10), r.randint(1, 28)
    if mo == 10: dd = min(dd, 15)
    hh, mm = r.randint(6, 22), r.randint(0, 59)
    fdt = font(bold, 44)
    dstr = f'{dd:02d}-{mo:02d}' if r.random() < 0.5 else f'{dd:02d}/{mo:02d}'
    dr.text((120, 90), f'{hh:02d}:{mm:02d}', font=fdt, fill=col); dr.text((W - 290, 90), dstr, font=fdt, fill=col)
    if r.random() < 0.5: dr.text((120, H - 120), r.choice(['MEM', 'AC', 'PC', 'GLU']), font=font(reg, 36), fill=col)
    return img, {'kind': 'meter-screen', 'readings': [{'type': 'unspecified', 'value': val, 'unit': unit}], 'date': {'y': 2026, 'm': mo, 'd': dd}, 'time': f'{hh:02d}:{mm:02d}', 'nonGlucose': [], 'font': os.path.basename(bold), 'template': 'lcd'}


def degrade(r, img, kind):
    a = np.array(img).astype(np.float32)
    h, w = a.shape[:2]
    pad = int(0.08 * max(h, w))
    table = np.array(r.choice([(120, 100, 80), (90, 90, 95), (160, 150, 130), (60, 70, 60)]), np.float32)
    canvas = np.ones((h + 2 * pad, w + 2 * pad, 3), np.float32) * table
    canvas += np.random.default_rng(r.randint(0, 1 << 30)).normal(0, 6, canvas.shape)
    canvas[pad:pad + h, pad:pad + w] = a
    H2, W2 = canvas.shape[:2]
    j = 0.05 if kind == 'lab-report' else 0.07
    src = np.float32([[pad, pad], [pad + w, pad], [pad + w, pad + h], [pad, pad + h]])
    dst = src + np.float32([[r.uniform(-j, j) * w, r.uniform(-j, j) * h] for _ in range(4)])
    ang = math.radians(r.uniform(-4, 4)); c = np.float32([W2 / 2, H2 / 2])
    R = np.float32([[math.cos(ang), -math.sin(ang)], [math.sin(ang), math.cos(ang)]])
    dst = (dst - c) @ R.T + c
    M = cv2.getPerspectiveTransform(src, dst.astype(np.float32))
    out = cv2.warpPerspective(canvas, M, (W2, H2), borderMode=cv2.BORDER_REPLICATE)
    # Lighting: gradient + soft shadow blob.
    yy, xx = np.mgrid[0:H2, 0:W2].astype(np.float32)
    g = 1 - r.uniform(0.05, 0.3) * ((xx / W2) if r.random() < 0.5 else (yy / H2))
    cx, cy, rad = r.uniform(0, W2), r.uniform(0, H2), r.uniform(0.2, 0.5) * max(W2, H2)
    g *= 1 - r.uniform(0.1, 0.35) * np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * rad ** 2)))
    out *= g[..., None]
    out += np.random.default_rng(r.randint(0, 1 << 30)).normal(0, r.uniform(2, 7), out.shape)
    out = np.clip(out, 0, 255).astype(np.uint8)
    im = Image.fromarray(out).filter(ImageFilter.GaussianBlur(r.uniform(0.5, 1.5)))
    long = r.randint(1300, 1900) if kind == 'lab-report' else r.randint(800, 1200)
    sc = long / max(im.size); im = im.resize((int(im.size[0] * sc), int(im.size[1] * sc)), Image.BILINEAR)
    return im, r.randint(40, 75)


def main():
    split, out = sys.argv[1], sys.argv[2]; n = int(sys.argv[3]) if len(sys.argv) > 3 else (36 if split.startswith('heldout') else 16)
    seeds = {'heldout': 777123, 'dev': 1001, 'devmeter': 4242, 'heldout2': 990017}
    r = random.Random(seeds[split]); np.random.seed(len(split))
    os.makedirs(out, exist_ok=True); manifest = []
    for i in range(n):
        meter = (i % 4 == 3) or split == 'devmeter'
        img, gt = (gen_meter if meter else gen_report)(r, split, i)
        clean_too = (i % 6 == 0) and not meter
        variants = [('photo', True)] + ([('clean', False)] if clean_too else [])
        for vname, deg in variants:
            name = f'{split}-{i:02d}-{gt["kind"]}-{vname}.jpg'
            if deg: im, q = degrade(r, img, gt['kind'])
            else: im, q = img, 90
            im.save(os.path.join(out, name), quality=q)
            manifest.append({'file': name, 'variant': vname, 'jpegQuality': q, **gt})
    json.dump({'split': split, 'note': 'Synthetic only; no real patient data.', 'images': manifest}, open(os.path.join(out, 'ground-truth.json'), 'w'), indent=1)
    print(len(manifest), 'images ->', out)


if __name__ == '__main__': main()
