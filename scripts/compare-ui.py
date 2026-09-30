"""Arrange actual browser captures beside normalized source references.

No image similarity percentage is claimed: platform chrome, recovered assets,
font rendering and JPEG capture make an aggregate pixel score misleading.
"""
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageEnhance

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / (sys.argv[1] if len(sys.argv) > 1 else 'artifacts/qa')
SOURCES = ROOT.parent / 'NutriSole-UI-Concepts'
CROPS = {
    'onboarding': ('01_21_15 AM-1', (38, 38, 786, 1748)),
    'home': ('01_21_16 AM-2', (42, 38, 777, 1737)),
    'scan': ('01_21_18 AM-3', (41, 37, 781, 1739)),
    'log-meal': ('01_21_19 AM-4', (55, 120, 750, 1604)),
    'weekly-plan': ('01_21_21 AM-5', (57, 149, 749, 1537)),
    'profile': ('01_21_23 AM-6', (50, 166, 760, 1564)),
}
rect = json.loads((QA / 'viewport.json').read_text())
left, top = round(rect['x']), round(rect['y'])
width, height = round(rect['width']), round(rect['height'])
font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 17)
overview = Image.new('RGB', (width * 3 + 80, height * 2 + 120), '#f2f3ef')
for i, (route, (suffix, crop)) in enumerate(CROPS.items()):
    capture = Image.open(QA / f'{route}-full.jpg')
    if left + width > capture.width or top + height > capture.height:
        raise ValueError(f'{route}: full-page screenshot is smaller than the observed screen rectangle. Recapture with fullPage=True.')
    actual = capture.crop((left, top, left + width, top + height))
    actual.save(QA / f'{route}.png')
    source_path = next(SOURCES.glob(f'*{suffix}.png'))
    x, y, w, h = crop
    source = Image.open(source_path).convert('RGB').crop((x, y, x + w, y + h))
    scale = min(width / w, height / h)
    resized = source.resize((round(w * scale), round(h * scale)), Image.Resampling.LANCZOS)
    reference = Image.new('RGB', (width, height), '#faf8f1' if route != 'scan' else '#111111')
    reference.paste(resized, ((width - resized.width) // 2, 0))
    reference.save(QA / f'{route}-reference.png')
    pair = Image.new('RGB', (width * 2 + 30, height + 45), '#f2f3ef')
    pair.paste(reference, (10, 35))
    pair.paste(actual, (width + 20, 35))
    draw = ImageDraw.Draw(pair)
    draw.text((10, 8), f'{route} / reference', fill='#203c2c', font=font)
    draw.text((width + 20, 8), 'rendered frontend', fill='#203c2c', font=font)
    pair.save(QA / f'{route}-comparison.png')
    Image.blend(reference, actual.convert('RGB'), 0.5).save(QA / f'{route}-overlay.png')
    difference = ImageChops.difference(reference, actual.convert('RGB'))
    ImageEnhance.Contrast(difference).enhance(2).save(QA / f'{route}-difference.png')
    ox = 20 + (i % 3) * (width + 20)
    oy = 40 + (i // 3) * (height + 45)
    overview.paste(actual, (ox, oy))
    ImageDraw.Draw(overview).text((ox, oy - 25), route.replace('-', ' ').title(), fill='#203c2c', font=font)
overview.save(QA / 'six-screen-preview.png')
print('Saved six reference/capture pairs, overlays, diagnostic differences, and the contact sheet.')
