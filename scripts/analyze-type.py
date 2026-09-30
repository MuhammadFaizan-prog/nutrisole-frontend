"""Identify close font shapes from source text; diagnostic only, never UI text assets."""
from pathlib import Path
from PIL import Image, ImageFont, ImageDraw
import numpy as np
import json

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'NutriSole-UI-Concepts'
QA = ROOT / 'artifacts/qa'
regions = [
 ('headline', '01_21_15 AM-1', (102, 288, 688, 370), 'Healthy choices,'),
 ('headline-second', '01_21_15 AM-1', (102, 374, 585, 455), 'made simple.'),
 ('brand', '01_21_15 AM-1', (163, 193, 393, 254), 'NutriSole'),
 ('body', '01_21_15 AM-1', (105, 478, 739, 523), 'Scan your food, get instant insights,'),
 ('profile-title', '01_21_23 AM-6', (251, 293, 680, 333), 'Profile & Preferences'),
 ('profile-name', '01_21_23 AM-6', (279, 412, 465, 457), 'Alex Chen'),
 ('home-greeting', '01_21_16 AM-2', (94, 175, 430, 225), 'Good morning,'),
]
fonts = list(Path('C:/Windows/Fonts').glob('*.ttf'))
fonts += list((ROOT / 'native/node_modules/@expo-google-fonts').rglob('*.ttf'))
fonts += list((ROOT / 'assets/fonts').glob('*.ttf'))
def trim(im):
    return im.crop(im.getbbox()) if im.getbbox() else im
results = {}
for name, suffix, bounds, text in regions:
    source = Image.open(next(SOURCE.glob(f'*{suffix}.png'))).convert('L').crop(bounds)
    mask = trim(source.point(lambda p: 255 if p < 100 else 0))
    target = np.asarray(mask, dtype=float) / 255
    scores = []
    for path in fonts:
        if 'Italic' in str(path) or path.stem.endswith('i'): continue
        try:
            f = ImageFont.truetype(str(path), 100)
            for spacing in [-2, -1, 0, 1, 2]:
                render = Image.new('L', (1800, 180))
                draw = ImageDraw.Draw(render)
                x = 10
                for char in text:
                    draw.text((x, 0), char, font=f, fill=255)
                    x += draw.textlength(char, font=f) + spacing
                glyph = trim(render)
                ratio = (glyph.width/glyph.height) / (mask.width/mask.height)
                if ratio < 0.75 or ratio > 1.25: continue
                normalized = glyph.resize(mask.size, Image.Resampling.LANCZOS)
                pred = np.asarray(normalized, dtype=float) / 255
                score = float(np.minimum(target,pred).sum()/np.maximum(target,pred).sum())
                scores.append((score, path, spacing, ratio, glyph))
        except (OSError, ValueError): pass
    scores.sort(key=lambda item: item[0], reverse=True)
    winners = scores[:10]
    results[name] = [{'iou': round(s,4), 'font':str(p), 'letterSpacingAt100':sp,'shapeRatio':round(r,4)} for s,p,sp,r,_ in winners]
    canvas = Image.new('RGB', (max(750,mask.width+20), (mask.height+45)*11), 'white')
    d = ImageDraw.Draw(canvas)
    canvas.paste(Image.eval(mask,lambda p:255-p),(10,30))
    d.text((10,5), f'{name} / source',fill='black')
    for i,(score,path,spacing,ratio,glyph) in enumerate(winners):
        y=(mask.height+45)*(i+1)
        d.text((10,y), f'{score:.3f} {path.stem} spacing={spacing} ratio={ratio:.2f}', fill='black')
        canvas.paste(Image.eval(glyph.resize(mask.size,Image.Resampling.LANCZOS),lambda p:255-p),(10,y+25))
    canvas.save(QA / f'type-{name}.png')
(QA/'font-diagnostics.json').write_text(json.dumps(results,indent=2))
for key,value in results.items(): print(key, json.dumps(value[:3]))
