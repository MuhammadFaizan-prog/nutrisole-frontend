"""Inspect native Figma PNG exports downloaded through the desktop plugin UI."""
from pathlib import Path
import hashlib
import json
import zipfile
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
bundle = Path('C:/Users/DELL/Downloads/NutriSole-live-Figma-QA-v2.zip')
out = root / 'artifacts/figma-expansion/live-render'
out.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(bundle) as archive:
    report = json.loads(archive.read('live-figma-report.json'))
    expected = {'live-figma-report.json', *(f['route'] + '.png' for f in report['frames'])}
    assert set(archive.namelist()) == expected
    for name in expected:
        assert '/' not in name and '\\' not in name
        (out / name).write_bytes(archive.read(name))
frames = report['frames']
evidence = []
for batch in range((len(frames) + 5) // 6):
    sheet = Image.new('RGB', (1242, 942), '#e8e8e5')
    draw = ImageDraw.Draw(sheet)
    for k, frame in enumerate(frames[batch * 6:batch * 6 + 6]):
        route = frame['route']
        x, y = (k % 3) * 414, (k // 3) * 471
        draw.text((x + 5, y + 5), route, fill='black')
        draw.text((x + 5, y + 23), 'Live Figma', fill='black')
        draw.text((x + 209, y + 23), 'Frontend / concept', fill='black')
        native = out / (route + '.png')
        other = root / 'artifacts/expansion/browser' / (route + '-app.png')
        if not other.exists():
            other = root / 'artifacts/screen-coverage/images' / (route + '.png')
        for j, path in enumerate([native, other]):
            if path.exists():
                img = Image.open(path).convert('RGB')
                if j == 0:
                    assert img.size == (393, 852)
                    evidence.append({'route': route, 'frameId': frame['id'], 'pixels': list(img.size), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
                sheet.paste(img.resize((196, 425)), (x + 5 + j * 204, y + 42))
    sheet.save(out / f'comparison-{batch + 1}.jpg', quality=95)
(out / 'capture-evidence.json').write_text(json.dumps({'source': 'Live native Figma exportAsync, saved through plugin UI', 'pageId': report['pageId'], 'frames': evidence, 'pixelIdentityCertified': False}, indent=2), encoding='utf-8')
print(json.dumps({'exportedFrames': len(evidence), 'comparisonSheets': batch + 1, 'allOriginalsUnchanged': all(report['originalScreensUnchanged'].values())}))
