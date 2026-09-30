"""Vendor selected, unmodified Tabler icons from a pinned official release."""
from pathlib import Path
import urllib.request
import json
import hashlib

root = Path(__file__).resolve().parents[1]
destination = root / 'assets' / 'icons'
destination.mkdir(parents=True, exist_ok=True)
base = 'https://raw.githubusercontent.com/tabler/tabler-icons/v3.48.0/'
icons = {
    'CameraFilled': 'filled/camera',
    'Running': 'outline/run',
    'Wheelchair': 'outline/wheelchair',
    'Allergen': 'outline/rosette-asterisk',
    'CalendarPlain': 'outline/calendar-event',
}
symbols, provenance = {}, []
for name, source in icons.items():
    url = base + 'icons/' + source + '.svg'
    data = urllib.request.urlopen(url).read()
    (destination / (name + '.svg')).write_bytes(data)
    symbols[name] = data.decode()
    provenance.append({'name': name, 'url': url, 'sha256': hashlib.sha256(data).hexdigest(), 'license': 'MIT', 'version': '3.48.0'})
(destination / 'LICENSE').write_bytes(urllib.request.urlopen(base + 'LICENSE').read())
(destination / 'provenance.json').write_text(json.dumps(provenance, indent=2))
(root / 'src' / 'nutrisole' / 'referenceIcons.ts').write_text('// Unmodified library SVG assets. Regenerate with scripts/vendor-reference-icons.py.\nexport const referenceIcons = ' + json.dumps(symbols, indent=2) + ' as const;\n')
print('Vendored five pinned Tabler icons with license and provenance.')
