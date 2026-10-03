"""Make inspection sheets from recorded APK renders and the original PNGs."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[2]
evidence = root / 'artifacts/native/responsive-qa/v1.0.3'
shots = evidence / 'interactions/reference-screens'
out = evidence / 'visual-review'
out.mkdir(parents=True, exist_ok=True)
font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 16)
validation = json.loads((evidence / 'interactions/validation.json').read_text(encoding='utf-8'))
names = [screen['route'] for screen in validation['screens']]
for start in range(0, len(names), 9):
    canvas = Image.new('RGB', (1008, 1830), '#e9e7e1')
    draw = ImageDraw.Draw(canvas)
    for index, route in enumerate(names[start:start + 9]):
        shot = Image.open(shots / (route + '.png')).convert('RGB')
        shot.thumbnail((320, 568), Image.Resampling.LANCZOS)
        x, y = 8 + index % 3 * 336, 8 + index // 3 * 610
        draw.text((x, y), route, font=font, fill='#123f2c')
        canvas.paste(shot, (x, y + 28))
    canvas.save(out / f'all-screens-{start // 9 + 1:02}.png')

# Crop coordinates remove pictured phone hardware. They are source-image units.
references = [
    ('onboarding', '01_21_15 AM-1', (38, 38, 786, 1748)),
    ('home', '01_21_16 AM-2', (42, 38, 777, 1737)),
    ('scan', '01_21_18 AM-3', (41, 37, 781, 1739)),
    ('log-meal', '01_21_19 AM-4', (55, 120, 750, 1604)),
    ('weekly-plan', '01_21_21 AM-5', (57, 149, 749, 1537)),
    ('profile', '01_21_23 AM-6', (50, 166, 760, 1564)),
]
reference_shots = evidence / 'matrix/reference-393'
for route, suffix, (x, y, width, height) in references:
    source = next((root.parent / 'NutriSole-UI-Concepts').glob('*' + suffix + '.png'))
    png = Image.open(source).convert('RGB').crop((x, y, x + width, y + height))
    rendered = reference_shots / (route + '.png')
    if not rendered.exists():
        rendered = shots / (route + '.png')
    apk = Image.open(rendered).convert('RGB')
    png.thumbnail((393, 852), Image.Resampling.LANCZOS)
    apk.thumbnail((393, 852), Image.Resampling.LANCZOS)
    canvas = Image.new('RGB', (810, 890), '#e9e7e1')
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 8), 'Original PNG: phone hardware cropped', font=font, fill='#123f2c')
    draw.text((409, 8), 'APK: native status/navigation bars', font=font, fill='#123f2c')
    canvas.paste(png, (8, 32))
    canvas.paste(apk, (409, 32))
    canvas.save(out / f'compare-{route}.png')

matrix_file = evidence / 'matrix/validation.json'
if matrix_file.exists():
    matrix = json.loads(matrix_file.read_text(encoding='utf-8'))
    for config in matrix['configs']:
        directory = evidence / 'matrix' / config['name']
        routes = [item['route'] for item in config['screens'] if item['status'] == 'passed']
        for bottom in [False, True]:
            suffix = '-bottom' if bottom else ''
            for start in range(0, len(routes), 9):
                canvas = Image.new('RGB', (1008, 1830), '#e9e7e1')
                draw = ImageDraw.Draw(canvas)
                for index, route in enumerate(routes[start:start + 9]):
                    shot_path = directory / (route + suffix + '.png')
                    if not shot_path.exists():
                        continue
                    shot = Image.open(shot_path).convert('RGB')
                    shot.thumbnail((320, 568), Image.Resampling.LANCZOS)
                    x, y = 8 + index % 3 * 336, 8 + index // 3 * 610
                    draw.text((x, y), route, font=font, fill='#123f2c')
                    canvas.paste(shot, (x, y + 28))
                canvas.save(directory / f'contact{suffix}-{start // 9 + 1:02}.png')
print(json.dumps({'screens': len(names), 'comparisons': len(references), 'directory': str(out)}))
