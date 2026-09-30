from pathlib import Path
import json
import shutil

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'assets/source/photo-patches/manifest.json').read_text())
patches = manifest['patches']
dest = root / 'public/nutrisole/photo-patches'
dest.mkdir(parents=True, exist_ok=True)
for p in patches:
    shutil.copyfile(p['path'], dest / (p['id'] + '.png'))
rows = [{'asset': p['id'], 'scene': p['sourceScreen'], 'x': p['sourceRectXYWHPx'][0], 'y': p['sourceRectXYWHPx'][1], 'w': p['sourceRectXYWHPx'][2], 'h': p['sourceRectXYWHPx'][3]} for p in patches]
(root / 'src/nutrisole/photoPatches.ts').write_text('export const photoPatches = ' + json.dumps(rows, indent=2) + ';\n')
web = '\n'.join(f"  '{p['id']}': {{ uri: '/nutrisole/photo-patches/{p['id']}.png' }}," for p in patches)
native = '\n'.join(f"  '{p['id']}': require('../../assets/source/photo-patches/{p['id']}.png')," for p in patches)
(root / 'src/nutrisole/photoAssets.ts').write_text('export const photoAssets = {\n' + web + '\n};\n')
(root / 'src/nutrisole/photoAssets.native.ts').write_text('export const photoAssets = {\n' + native + '\n};\n')
print(f'Registered {len(patches)} original photographic patches.')
