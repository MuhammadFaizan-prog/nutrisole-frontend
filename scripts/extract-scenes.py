from pathlib import Path
from PIL import Image
import json
import hashlib

root = Path(__file__).resolve().parents[1]
source = root.parent / 'NutriSole-UI-Concepts'
scenes = [('scan-photo-region', '01_21_18 AM-3', (41,37,822,1408)), ('onboarding-photo-region', '01_21_15 AM-1', (38,609,824,1591)), ('scan-time-background', '01_21_18 AM-3', (116,112,190,149)), ('scan-indicators-background', '01_21_18 AM-3', (620,112,780,152))]
manifest = []
for name, suffix, bounds in scenes:
    path = next(source.glob(f'*{suffix}.png'))
    cropped = Image.open(path).crop(bounds)
    for directory in [root / 'assets/source', root / 'public/nutrisole']:
        cropped.save(directory / f'{name}.png')
    manifest.append({'id': name, 'source': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'boundsLTRB': bounds, 'method': 'Lossless photographic region crop. Must be rendered ONLY by ScenePhoto: an SVG mask excludes every source UI pixel. Never render this asset directly.'})
(root / 'assets/source/scenes.provenance.json').write_text(json.dumps(manifest, indent=2))
print('Saved four source crops with rendering restrictions and provenance.')
