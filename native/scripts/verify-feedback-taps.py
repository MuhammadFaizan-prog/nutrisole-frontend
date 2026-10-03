"""Physical input checks for the reported Home/calendar issues at 200% text."""
import hashlib
import json
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parents[2]
adb = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
serial = sys.argv[1] if len(sys.argv) > 1 else 'emulator-5582'
package = 'com.muhammadfaizan.nutrisole'
out = root / 'artifacts/native/responsive-qa/v1.0.3/critical-taps'
out.mkdir(parents=True, exist_ok=True)
apk = root / 'artifacts/native/NutriSole-Responsive-v1.0.3.apk'
report = {'apkSha256': hashlib.sha256(apk.read_bytes()).hexdigest(), 'device': serial,
          'configuration': {'width': 320, 'height': 568, 'density': 160, 'fontScale': 2},
          'checks': [], 'errors': []}

def run(*args, binary=False):
    result = subprocess.run([str(adb), '-s', serial, *map(str, args)], capture_output=True, timeout=50)
    assert result.returncode == 0, result.stderr.decode(errors='replace')
    return result.stdout if binary else result.stdout.decode(errors='replace').strip()

def bounds(node):
    return list(map(int, re.findall(r'\d+', node.get('bounds', ''))))

def tree(name):
    run('shell', 'uiautomator', 'dump', '/sdcard/nutri-feedback.xml')
    xml = run('shell', 'cat', '/sdcard/nutri-feedback.xml')
    (out / (name + '.xml')).write_text(xml, encoding='utf-8')
    return ET.fromstring(xml)

def shot(name):
    path = out / (name + '.png')
    path.write_bytes(run('exec-out', 'screencap', '-p', binary=True))
    return path

def find(doc, identifier):
    return next((node for node in doc.iter('node') if node.get('resource-id', '').split('/')[-1] == identifier), None)

def has_screen(doc, route):
    return find(doc, 'screen-' + route) is not None

def tap(node):
    x1, y1, x2, y2 = bounds(node)
    assert x2 > x1 and y2 > y1, 'Tap target has no visible bounds'
    run('shell', 'input', 'tap', (x1 + x2) // 2, (y1 + y2) // 2)

def go(route):
    run('shell', 'am', 'start', '-W', '-a', 'android.intent.action.VIEW', '-d',
        'nutrisole://screens/' + route, '-n', package + '/.MainActivity')
    time.sleep(.4)
    doc = tree(route + '-entry')
    assert has_screen(doc, route), 'Destination did not render: ' + route
    return doc

def seek_card(identifier):
    for attempt in range(18):
        doc = tree(identifier + '-seek-' + str(attempt))
        scroll = find(doc, 'scroll-home')
        card = find(doc, identifier)
        assert scroll is not None
        sx1, sy1, sx2, sy2 = bounds(scroll)
        if card is not None:
            x1, y1, x2, y2 = bounds(card)
            if y1 > sy1 + 4 and y2 < sy2 - 4 and y2 - y1 > 100:
                shot(identifier + '-visible')
                return card
        distance = round((sy2 - sy1) * .35)
        run('shell', 'input', 'swipe', (sx1 + sx2) // 2, sy2 - 20,
            (sx1 + sx2) // 2, sy2 - 20 - distance, '500')
    raise AssertionError('Could not scroll the complete card into view: ' + identifier)

try:
    installed_path = run('shell', 'pm', 'path', package).split('package:', 1)[1].splitlines()[0]
    report['installedApkSha256'] = run('shell', 'sha256sum', installed_path).split()[0]
    assert report['installedApkSha256'] == report['apkSha256']
    run('shell', 'am', 'force-stop', package)
    run('shell', 'wm', 'size', '320x568')
    run('shell', 'wm', 'density', '160')
    run('shell', 'settings', 'put', 'system', 'font_scale', '2.0')
    run('logcat', '-c')
    doc = go('weekly-plan')
    strip = find(doc, 'week-strip')
    assert strip is not None
    x1, y1, x2, y2 = bounds(strip)
    # Start inside the rail, clear of Android's back-gesture edge region.
    run('shell', 'input', 'swipe', x2 - 44, (y1 + y2) // 2, x1 + 44, (y1 + y2) // 2, '500')
    doc = tree('sunday-visible')
    sunday = find(doc, 'select-sun')
    assert sunday is not None, 'Sunday is missing after the horizontal rail gesture'
    sx1, sy1, sx2, sy2 = bounds(sunday)
    assert sx2 - sx1 >= 60 and sy2 - sy1 >= 70, 'Sunday is not reachable after the horizontal scroll'
    cells = [node for node in doc.iter('node') if node.get('resource-id', '').split('/')[-1] in
             ['select-' + day for day in ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']]
             and bounds(node)[2] > bounds(node)[0]]
    assert len({bounds(node)[1] for node in cells}) == 1, 'Calendar wrapped'
    tap(sunday)
    doc = tree('sunday-selected')
    selected = find(doc, 'select-sun')
    sx1, sy1, sx2, sy2 = bounds(selected)
    image = Image.open(shot('sunday-selected')).convert('RGB')
    red, green, blue = image.getpixel((sx1 + 5, (sy1 + sy2) // 2))
    assert green > red * 1.3 and green > blue * 1.15, 'The physical Sunday tap did not select its green card'
    report['checks'].append('200% text: horizontal calendar scroll reaches Sunday; physical tap selects it')

    go('home')
    tap(seek_card('view-plan'))
    assert has_screen(tree('view-plan-destination'), 'weekly-plan')
    report['checks'].append('200% text: stacked View Plan card scrolls fully into view and opens Weekly Plan')
    go('home')
    tap(seek_card('open-health'))
    assert has_screen(tree('health-destination'), 'glucose-overview')
    report['checks'].append('200% text: stacked Health card scrolls fully into view and opens Glucose overview')
    assert run('shell', 'pidof', package)
    report['status'] = 'passed'
except Exception as error:
    report['status'] = 'failed'
    report['errors'].append(str(error))
finally:
    try:
        crash = run('logcat', '-d', '-b', 'crash')
        (out / 'crash-log.txt').write_text(crash, encoding='utf-8')
        report['crashFree'] = 'FATAL EXCEPTION' not in crash and 'Fatal signal' not in crash
        if not report['crashFree']:
            report['status'] = 'failed'
        run('shell', 'settings', 'put', 'system', 'font_scale', '1.0')
        run('shell', 'wm', 'size', '432x960')
        run('shell', 'wm', 'density', '160')
    except Exception as error:
        report['errors'].append(str(error))
        report['status'] = 'failed'
    (out / 'validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
sys.exit(0 if report['status'] == 'passed' else 1)
