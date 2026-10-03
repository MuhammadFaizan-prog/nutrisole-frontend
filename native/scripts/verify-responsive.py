"""Standalone APK layout matrix through Android's real window, font and input APIs."""
import hashlib
import json
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

native = Path(__file__).resolve().parents[1]
root = native.parent
adb = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
serial = sys.argv[1] if len(sys.argv) > 1 else 'emulator-5660'
package = 'com.muhammadfaizan.nutrisole'
out = root / ('artifacts/native/navigation-qa/v1.0.4/matrix' if '--journeys' in sys.argv else 'artifacts/native/responsive-qa/v1.0.3/matrix')
if '--quick' in sys.argv:
    out = out / 'final-reference'
out.mkdir(parents=True, exist_ok=True)
model = (root / 'src/nutrisole/extensions/model.ts').read_text(encoding='utf-8')
extras = re.findall(r"'([^']+)'", model.split('export const extensionRoutes = [', 1)[1].split('] as const', 1)[0])
routes = ['onboarding', 'home', 'scan', 'log-meal', 'weekly-plan', 'profile'] + extras
configs = [
    {'name': 'compact-320', 'width': 320, 'height': 568, 'density': 160, 'font': 1, 'navigation': 'gestural'},
    {'name': 'short-360-large-text', 'width': 360, 'height': 640, 'density': 160, 'font': 1.3, 'navigation': 'threebutton'},
    {'name': 'reference-393', 'width': 393, 'height': 852, 'density': 160, 'font': 1, 'navigation': 'gestural'},
    {'name': 'phone-390', 'width': 390, 'height': 844, 'density': 160, 'font': 1, 'navigation': 'gestural'},
    {'name': 'dense-412', 'width': 412, 'height': 914, 'density': 240, 'font': 1, 'navigation': 'threebutton'},
    {'name': 'large-430-large-text', 'width': 430, 'height': 932, 'density': 320, 'font': 1.5, 'navigation': 'gestural'},
]
if '--journeys' in sys.argv:
    configs = [configs[2], configs[5], {'name': 'compact-320-max-text', 'width': 320, 'height': 568, 'density': 160, 'font': 2, 'navigation': 'threebutton'}]
    routes = routes[:6] + ['glucose-overview', 'flow-directory', 'sign-in', 'create-account', 'catalog-queue', 'report-triage']
elif '--quick' in sys.argv:
    configs = [configs[2]]
    routes = routes[:6] + ['sign-in', 'create-account', 'food-selector', 'privacy-data-rights', 'assistant', 'flow-directory', 'verify-email', 'plan-generation', 'recover-account', 'capture-retry', 'glucose-overview']
elif '--stress' in sys.argv:
    configs = [{'name': 'compact-320-max-text', 'width': 320, 'height': 568, 'density': 160, 'font': 2, 'navigation': 'gestural'}]
    routes = routes[:6] + ['sign-in', 'create-account', 'food-selector', 'privacy-data-rights', 'assistant', 'flow-directory']
elif '--feedback' in sys.argv:
    # All 38 at both ends of the width/text range; all six main screens at
    # every other requested width. The report records the exact route matrix.
    configs.append({'name': 'compact-320-max-text', 'width': 320, 'height': 568, 'density': 160, 'font': 2, 'navigation': 'gestural'})
apk = native / 'android/app/build/outputs/apk/release/app-release.apk'
report = {'apkSha256': hashlib.sha256(apk.read_bytes()).hexdigest(), 'device': serial, 'iosRuntimeTested': False, 'physicalPhoneTested': False, 'configs': [], 'errors': [], 'routeMethod': 'deep links for layout inspection only'}
prior_report = None
if '--rerun-failed' in sys.argv:
    prior_report = json.loads((out / 'validation.json').read_text(encoding='utf-8'))
    assert prior_report['apkSha256'] == report['apkSha256'], 'Cannot combine evidence from different APKs'
    assert prior_report.get('crashFree'), 'A crashed run requires a complete rerun'
    (out / 'validation-before-rerun.json').write_text(json.dumps(prior_report, indent=2), encoding='utf-8')
    configs = [{key: value for key, value in config.items() if key not in ['screens', 'physicalPixels']}
               for config in prior_report['configs'] if any(screen['status'] == 'failed' for screen in config['screens'])]
    assert configs, 'No failed configurations to rerun'

def run(*args, binary=False):
    r = subprocess.run([str(adb), '-s', serial, *map(str, args)], capture_output=True, timeout=50)
    if r.returncode:
        raise RuntimeError(r.stderr.decode(errors='replace') + r.stdout.decode(errors='replace'))
    return r.stdout if binary else r.stdout.decode(errors='replace').strip()

def tree(directory, name):
    run('shell', 'uiautomator', 'dump', '/sdcard/nutri-responsive.xml')
    xml = run('shell', 'cat', '/sdcard/nutri-responsive.xml')
    (directory / f'{name}.xml').write_text(xml, encoding='utf-8')
    return ET.fromstring(xml)

def bounds(node):
    return list(map(int, re.findall(r'\d+', node.get('bounds', ''))))

def screenshot(directory, name):
    (directory / f'{name}.png').write_bytes(run('exec-out', 'screencap', '-p', binary=True))

def check(doc, route, px_width, px_height, factor=1, initial=True, font_scale=1):
    screen = next((n for n in doc.iter('node') if n.get('resource-id', '').endswith('screen-' + route)), None)
    assert screen is not None, 'Route did not render'
    assert not any(n.get('resource-id', '').endswith('reference-canvas') for n in doc.iter('node')), 'Legacy scaled canvas still mounted'
    x1, y1, x2, y2 = bounds(screen)
    assert x1 >= 0 and x2 <= px_width and y1 >= 0 and y2 <= px_height, 'Screen escapes window'
    assert x2 - x1 == px_width, 'Display resize has not reached the native viewport'
    for node in doc.iter('node'):
        if node.get('package') != package:
            continue
        rect = bounds(node)
        if len(rect) == 4 and rect[2] > rect[0]:
            assert rect[0] >= 0 and rect[2] <= px_width, 'Horizontal overflow: ' + (node.get('text') or node.get('content-desc', ''))
    footer = next((n for n in doc.iter('node') if n.get('resource-id', '').endswith('footer-' + route)), None)
    if footer is not None:
        fx1, fy1, fx2, fy2 = bounds(footer)
        assert fy1 >= y1 and fy2 <= y2, 'Fixed footer escapes safe viewport'
    if route == 'home':
        body = next((n for n in doc.iter('node') if n.get('resource-id', '').endswith('scroll-home')), None)
        if body is not None:
            _, body_top, _, body_bottom = bounds(body)
            padding = 14 if px_width / factor - 24 < 340 else 18
            for card in doc.iter('node'):
                if card.get('resource-id', '').split('/')[-1] in ['view-plan', 'open-health']:
                    cx1, cy1, cx2, cy2 = bounds(card)
                    if cy1 > body_top + factor and cy2 < body_bottom - factor:
                        # Android 14 scales sp sizes nonlinearly. Use the rendered
                        # title/description geometry instead of multiplying heights
                        # by Configuration.fontScale.
                        title = next((n for n in card.iter('node') if n.get('text') in ['View Plan', 'Health']), None)
                        description = next((n for n in card.iter('node') if n.get('text') in ['Meals for your goals', 'Trends & insights']), None)
                        assert title is not None and description is not None, 'Home card labels are missing'
                        _, ty1, _, ty2 = bounds(title)
                        _, dy1, _, dy2 = bounds(description)
                        assert dy1 >= ty2, 'Home title and description overlap'
                        assert dy2 - dy1 >= max(15 * factor, (ty2 - ty1) * .8) - 2 * factor, 'Home description is clipped'
                        assert dy2 <= cy2 - padding * factor + 2 * factor, 'Home description does not clear its card padding'
    if route == 'scan':
        capture = next((n for n in doc.iter('node') if n.get('content-desc') == 'Capture food'), None)
        assert capture is not None and bounds(capture)[3] - bounds(capture)[1] >= 60 * factor, 'Camera capture control is clipped'
    if route == 'weekly-plan' and initial:
        cells = [n for n in doc.iter('node') if n.get('resource-id', '').split('/')[-1] in ['select-' + d for d in ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']] and len(bounds(n)) == 4 and bounds(n)[3] > bounds(n)[1]]
        assert cells, 'Weekday controls are missing'
        assert len({bounds(n)[1] for n in cells}) == 1, 'Weekdays wrapped into multiple rows'
        if font_scale == 1:
            assert len(cells) == 7, 'All seven default-text weekdays must fit on one row'
    if route == 'capture-retry' and initial:
        photo = next((n for n in doc.iter('node') if n.get('content-desc') == 'Food photo'), None)
        assert photo is not None, 'Retry photo did not render'
        bx1, by1, bx2, by2 = bounds(photo)
        assert abs((by2 - by1) / (bx2 - bx1) - 234.65 / 349) < .08, 'Retry photo does not preserve its intended crop'
    back = next((n for n in doc.iter('node') if n.get('resource-id', '').endswith('action-back')), None)
    if back is not None:
        bx1, by1, bx2, by2 = bounds(back)
        assert bx2 - bx1 <= 64 * factor, 'Back control is stretched away from its header position'
    return [x1, y1, x2, y2]

try:
    report['api'] = int(run('shell', 'getprop', 'ro.build.version.sdk'))
    run('logcat', '-c')
    for config in configs:
        directory = out / config['name']
        directory.mkdir(exist_ok=True)
        factor = config['density'] / 160
        px_width, px_height = round(config['width'] * factor), round(config['height'] * factor)
        run('shell', 'am', 'force-stop', package)
        run('shell', 'wm', 'size', f'{px_width}x{px_height}')
        run('shell', 'wm', 'density', config['density'])
        run('shell', 'settings', 'put', 'system', 'font_scale', config['font'])
        run('shell', 'cmd', 'overlay', 'enable-exclusive', '--category', f"com.android.internal.systemui.navbar.{config['navigation']}")
        time.sleep(1)
        run('shell', 'pm', 'clear', package)
        entry = {**config, 'physicalPixels': [px_width, px_height], 'screens': []}
        report['configs'].append(entry)
        if prior_report:
            old_config = next(c for c in prior_report['configs'] if c['name'] == config['name'])
            config_routes = [screen['route'] for screen in old_config['screens'] if screen['status'] == 'failed']
        else:
            config_routes = routes if '--feedback' not in sys.argv or config['name'] in ['compact-320', 'large-430-large-text'] else routes[:6]
        for route in config_routes:
            try:
                run('shell', 'am', 'start', '-W', '-a', 'android.intent.action.VIEW', '-d', f'nutrisole://screens/{route}', '-n', package + '/.MainActivity')
                time.sleep(.25)
                for attempt in range(4):
                    doc = tree(directory, route)
                    try:
                        root_bounds = check(doc, route, px_width, px_height, factor, font_scale=config['font'])
                        break
                    except AssertionError:
                        if attempt == 3:
                            raise
                        time.sleep(.6)
                screenshot(directory, route)
                scrolling = next((n for n in doc.iter('node') if n.get('resource-id', '').endswith('scroll-' + route)), None)
                scrolled = False
                if scrolling is not None:
                    bx1, by1, bx2, by2 = bounds(scrolling)
                    if by2 - by1 > 100:
                        for _ in range(8 if config['font'] >= 2 else 3):
                            run('shell', 'input', 'swipe', (bx1+bx2)//2, by2-25, (bx1+bx2)//2, by1+25, '200')
                        bottom = tree(directory, route + '-bottom')
                        check(bottom, route, px_width, px_height, factor, initial=False, font_scale=config['font'])
                        screenshot(directory, route + '-bottom')
                        scrolled = True
                assert run('shell', 'pidof', package), 'Process crashed'
                entry['screens'].append({'route': route, 'status': 'passed', 'safeViewportBounds': root_bounds, 'scrollGestureExercised': scrolled})
                print(f"PASS {config['name']} {route}", flush=True)
            except Exception as error:
                entry['screens'].append({'route': route, 'status': 'failed', 'error': str(error)})
                report['errors'].append(f"{config['name']}/{route}: {error}")
                print(f"FAIL {config['name']} {route}: {error}", flush=True)
        report_name = 'quick-validation.json' if '--quick' in sys.argv else 'stress-validation.json' if '--stress' in sys.argv else 'validation.json'
        (out / report_name).write_text(json.dumps(report, indent=2), encoding='utf-8')
    report['status'] = 'passed' if not report['errors'] else 'failed'
    if prior_report:
        replacements = {(config['name'], screen['route']): screen for config in report['configs'] for screen in config['screens']}
        for config in prior_report['configs']:
            config['screens'] = [replacements.get((config['name'], screen['route']), screen) for screen in config['screens']]
        report['rerunCases'] = [{'configuration': name, 'route': route, 'status': screen['status']}
                                for (name, route), screen in replacements.items()]
        report['configs'] = prior_report['configs']
        report['errors'] = [f"{config['name']}/{screen['route']}: {screen['error']}"
                            for config in report['configs'] for screen in config['screens'] if screen['status'] == 'failed']
        report['status'] = 'passed' if not report['errors'] else 'failed'
finally:
    crash = run('logcat', '-d', '-b', 'crash')
    (out / 'crash-log.txt').write_text(crash, encoding='utf-8')
    report['crashFree'] = 'FATAL EXCEPTION' not in crash and 'Fatal signal' not in crash
    if not report['crashFree']:
        report['status'] = 'failed'
    run('shell', 'settings', 'put', 'system', 'font_scale', '1.0')
    run('shell', 'cmd', 'overlay', 'enable-exclusive', '--category', 'com.android.internal.systemui.navbar.gestural')
    run('shell', 'wm', 'size', '432x960')
    run('shell', 'wm', 'density', '160')
    report_name = 'quick-validation.json' if '--quick' in sys.argv else 'stress-validation.json' if '--stress' in sys.argv else 'validation.json'
    (out / report_name).write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({'status': report.get('status'), 'configs': len(report['configs']), 'screens': sum(len(c['screens']) for c in report['configs']), 'errors': report['errors']}), flush=True)
sys.exit(0 if report.get('status') == 'passed' else 1)
