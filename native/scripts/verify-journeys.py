"""Verify task navigation in the installed release using physical Android taps."""
import hashlib
import json
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

root = Path(__file__).resolve().parents[2]
adb = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
serial = sys.argv[1] if len(sys.argv) > 1 else 'emulator-5582'
package = 'com.muhammadfaizan.nutrisole'
out = root / ('artifacts/native/navigation-qa/v1.0.4/intermediate-tail' if '--tail' in sys.argv else 'artifacts/native/navigation-qa/v1.0.4/intermediate-smoke' if '--smoke' in sys.argv else 'artifacts/native/navigation-qa/v1.0.4/journeys')
out.mkdir(parents=True, exist_ok=True)
apk = root / 'native/android/app/build/outputs/apk/release/app-release.apk'
model = (root / 'src/nutrisole/extensions/model.ts').read_text(encoding='utf-8')
extra = re.findall(r"'([^']+)'", model.split('export const extensionRoutes = [', 1)[1].split('] as const', 1)[0])
expected = ['onboarding', 'home', 'scan', 'log-meal', 'weekly-plan', 'profile'] + extra
report = {'serial': serial, 'apkSha256': hashlib.sha256(apk.read_bytes()).hexdigest(), 'routes': [], 'checks': [], 'errors': [], 'navigationMethod': 'physical taps and Android Back; no route deep links', 'iosRuntimeTested': False, 'physicalPhoneTested': False}
cached_doc = None

def run(*args, binary=False):
    global cached_doc
    if args[:2] in [('shell', 'input'), ('shell', 'am'), ('shell', 'pm')]:
        cached_doc = None
    value = subprocess.run([str(adb), '-s', serial, *args], capture_output=True, timeout=50)
    if value.returncode:
        raise RuntimeError(value.stderr.decode(errors='replace') + value.stdout.decode(errors='replace'))
    return value.stdout if binary else value.stdout.decode(errors='replace').strip()

def save_report():
    (out / 'validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

def tree(name='current'):
    global cached_doc
    if cached_doc is not None:
        (out / f'{name}.xml').write_text(ET.tostring(cached_doc, encoding='unicode'), encoding='utf-8')
        return cached_doc
    for attempt in range(3):
        run('shell', 'uiautomator', 'dump', '/sdcard/nutri-journeys.xml')
        xml = run('shell', 'cat', '/sdcard/nutri-journeys.xml')
        doc = ET.fromstring(xml)
        alert = next((n.get('text', '') for n in doc.iter('node') if n.get('resource-id') == 'android:id/alertTitle'), '')
        if alert.startswith('Pixel Launcher') or alert.startswith('System UI') or alert.startswith("Process system isn't responding"):
            report.setdefault('harnessInterruptions', []).append(alert)
            (out / f'os-interruption-{len(report["harnessInterruptions"])}.xml').write_text(xml, encoding='utf-8')
            # Wait on a system-server interruption; only close known launcher/UI dialogs.
            # NutriSole ANRs are never dismissed by this harness.
            control_id = 'android:id/aerr_wait' if alert.startswith('Process system') else 'android:id/aerr_close'
            close = next(n for n in doc.iter('node') if n.get('resource-id') == control_id)
            x1, y1, x2, y2 = bounds(close)
            run('shell', 'input', 'tap', str((x1+x2)//2), str((y1+y2)//2))
            time.sleep(.5)
        else:
            (out / f'{name}.xml').write_text(xml, encoding='utf-8')
            cached_doc = doc
            return doc
    raise AssertionError('Android OS repeatedly interrupted QA')

def capture(name):
    (out / f'{name}.png').write_bytes(run('exec-out', 'screencap', '-p', binary=True))

def bounds(node):
    return tuple(map(int, re.findall(r'\d+', node.get('bounds', ''))))

def contains(doc, text):
    return any(text in n.get('text', '') or text in n.get('content-desc', '') for n in doc.iter('node'))

def expect(route):
    doc = tree(route)
    assert run('shell', 'pidof', package), 'App process ended'
    assert any(n.get('resource-id', '').endswith('screen-' + route) for n in doc.iter('node')), f'Expected {route}'
    if route not in report['routes']:
        report['routes'].append(route)
        capture(route)
        save_report()
        print('PASS task route: ' + route, flush=True)
    return doc

def scroll(doc, up=False):
    region = next((n for n in doc.iter('node') if n.get('scrollable') == 'true' and 'week-strip' not in n.get('resource-id', '')), None)
    if region is None:
        return False
    x1, y1, x2, y2 = bounds(region)
    start, end = (.3, .75) if up else (.76, .3)
    run('shell', 'input', 'swipe', str((x1+x2)//2), str(y1+int((y2-y1)*start)), str((x1+x2)//2), str(y1+int((y2-y1)*end)), '400')
    time.sleep(.15)
    return True

def tap(resource=None, label=None, text=None):
    for attempt in range(12):
        doc = tree()
        for node in doc.iter('node'):
            if resource and node.get('resource-id', '').endswith(resource) or label and node.get('content-desc', '') == label or text and text in (node.get('text', ''), node.get('content-desc', '')):
                box = bounds(node)
                minimum_height = 38 if node.get('class') == 'android.widget.EditText' else 12
                if len(box) == 4 and box[2] > box[0] and box[3] - box[1] >= minimum_height:
                    run('shell', 'input', 'tap', str((box[0]+box[2])//2), str((box[1]+box[3])//2))
                    time.sleep(.25)
                    return
        if not scroll(doc, up=8 <= attempt < 12):
            break
    capture('missing-control')
    raise AssertionError(f'Unreachable control: {resource or label or text}')

def field(resource, value):
    if resource.startswith('sheet-'):
        tap(label={'sheet-grams': 'Weight in grams', 'sheet-dietary': 'Preference', 'sheet-mobility': 'Mobility Constraints'}[resource])
    else:
        tap(resource=resource)
    focused = tree('focus-' + resource)
    assert any(n.get('class') == 'android.widget.EditText' and n.get('focused') == 'true' and (n.get('resource-id', '').endswith(resource) or resource.startswith('sheet-')) for n in focused.iter('node')), 'Requested input did not receive focus: ' + resource
    run('shell', 'input', 'keyevent', 'KEYCODE_MOVE_END')
    # Existing values are short; repeat DEL without changing keyboard focus.
    run('shell', 'input', 'keyevent', *(['KEYCODE_DEL'] * 50))
    run('shell', 'input', 'text', value.replace(' ', '%s'))
    time.sleep(.2)

def back():
    run('shell', 'input', 'keyevent', '4')
    time.sleep(.25)

def hide_keyboard():
    if 'mInputShown=true' in run('shell', 'dumpsys', 'input_method'):
        back()

def check(name, condition=True):
    assert condition, name
    report['checks'].append(name)
    save_report()
    print('PASS interaction: ' + name, flush=True)

def tab(route):
    tap(resource='tab-' + route)
    return expect(route)

def menu():
    # Return through the current task stack, then use a root tab.
    for _ in range(12):
        doc = tree()
        if any(n.get('resource-id', '').endswith('tab-home') for n in doc.iter('node')):
            tab('home')
            tap(resource='open-menu')
            return expect('flow-directory')
        back()
    raise AssertionError('Could not return to the main navigation')

def open_menu(route):
    menu()
    tap(resource='menu-' + route)
    return expect(route)

def capture_food():
    menu(); tab('scan'); tap(resource='capture-food'); expect('analysis-result')

def select_food(food):
    tap(resource='action-evidence'); tap(text='Correct food label'); expect('food-selector')
    tap(label='Select ' + food); tap(label='Confirm ' + food); expect('nutrition-details')
    tap(label='Confirm portion'); expect('portion-confirmation' if food != 'Apple' else 'log-meal')

def staff(role, route):
    menu(); tap(resource='menu-staff-workspace'); tap(text=role); expect(route)

try:
    report['installedApkSha256'] = run('shell', 'sha256sum', run('shell', 'pm', 'path', package).splitlines()[0].removeprefix('package:')).split()[0]
    assert report['installedApkSha256'] == report['apkSha256'], 'Installed APK differs from build artifact'
    report['configuration'] = {'size': run('shell', 'wm', 'size'), 'density': run('shell', 'wm', 'density'), 'fontScale': run('shell', 'settings', 'get', 'system', 'font_scale'), 'api': run('shell', 'getprop', 'ro.build.version.sdk')}
    if '--tail' not in sys.argv:
        run('logcat', '-c'); run('shell', 'pm', 'clear', package)
        run('shell', 'am', 'start', '-W', '-n', package + '/.MainActivity'); time.sleep(2)
        expect('onboarding'); tap(resource='get-started'); expect('create-account')
        field('field-name', 'Journey Tester'); field('field-email', 'journey@example.com'); field('field-password', 'NutriSole42'); capture('keyboard-create-account')
        hide_keyboard(); tap(resource='action-toggle-terms'); tap(resource='action-create-account'); expect('verify-email')
        tap(resource='action-verify-demo'); tap(text='Valid link · Continue'); expect('sign-in')
        field('field-password', 'NutriSole42'); hide_keyboard(); tap(resource='action-sign-in'); expect('home')
        check('signup, verification and sign-in land on Home')

        tap(resource='review-apple-scan'); expect('log-meal')
        tap(resource='portion-by-weight'); field('sheet-grams', '500'); capture('keyboard-weight-sheet'); hide_keyboard(); tap(text='Save')
        tap(resource='nutrition-information'); tap(text='View nutrition details'); expect('nutrition-details'); back()
        check('Apple portion survives the nutrition child screen', contains(expect('log-meal'), '500'))
        tap(resource='confirm-log-meal'); expect('home'); tap(resource='review-latest-logged-food'); expect('personal-history')
        check('saved recent food enters history with its measured portion', contains(tree(), '500 g'))
        if '--smoke' in sys.argv:
            raise SystemExit(0)

        capture_food(); tap(resource='action-go-market-reference'); expect('market-reference'); back()
        select_food('Tomato'); tap(resource='action-choose-portion-By weight'); field('field-grams', '500'); hide_keyboard()
        tap(resource='action-draft-meal'); tap(text='Save draft'); expect('personal-history')
        tap(label='Open Saved draft · This session'); expect('portion-confirmation')
        check('reopened draft keeps its food and 500 g quantity', contains(tree(), 'Tomato') and contains(tree(), '500'))
        tap(resource='action-save-meal'); tap(text='Log confirmed meal'); expect('personal-history')
        check('consuming a draft removes the unconsumed duplicate', not contains(tree(), 'Saved draft · This session'))

        capture_food(); select_food('Banana'); tap(resource='action-save-meal'); tap(text='Log confirmed meal'); expect('personal-history')
        menu(); tab('scan'); tap(resource='choose-gallery-image'); tap(text='Blurred apple · Retake'); expect('capture-retry')
        tap(resource='action-choose-photo'); tap(text='Clear single apple · Review'); expect('analysis-result')
        tap(label='Confirm food'); expect('nutrition-details'); check('retry sample resets a previous Banana correction', contains(tree(), 'Apple · Raw'))
        tap(label='Confirm portion'); expect('log-meal'); back(); back(); back(); expect('capture-retry')
        tap(resource='action-go-scan'); expect('scan'); back(); expect('flow-directory')
        check('retake and Android Back restore the task parent')

        capture_food(); tap(resource='action-evidence'); tap(text='Report assessment'); expect('report-output')
        tap(resource='action-review-report'); tap(text='Submit demo report'); expect('report-status')
        tap(resource='action-go-analysis-result'); expect('analysis-result'); check('report and result are connected')

        menu(); tab('glucose-overview'); tap(resource='action-new-reading'); expect('add-reading'); field('field-reading', '110'); hide_keyboard()
        tap(resource='action-review-reading'); tap(text='Confirm & save reading'); expect('reading-detail')
        tap(resource='action-edit-reading'); expect('add-reading'); field('field-reading', '125'); hide_keyboard()
        tap(resource='action-review-reading'); tap(text='Confirm & save reading'); expect('reading-detail'); back(); expect('reading-detail'); back(); expect('glucose-overview')
        tap(resource='action-go-health-connections'); expect('health-connections'); tap(resource='action-permissions'); tap(text='Preview provider unavailable'); tap(text='Add reading manually'); expect('add-reading')
        check('provider fallback starts a new reading form', not contains(tree(), '125'))
        field('field-reading', '130'); hide_keyboard(); tap(resource='action-review-reading'); tap(text='Confirm & save reading'); expect('reading-detail')
        menu(); tab('glucose-overview'); check('new provider fallback preserves the prior reading', contains(tree(), '2 manual readings'))
        tap(resource='task-foot-questionnaire'); expect('foot-questionnaire'); tap(resource='action-choose-mobility-Limited'); tap(resource='action-review-foot')
        check('foot review agrees with the selected mobility', contains(tree(), 'Mobility: Limited'))
        tap(text='See general guidance'); expect('foot-guidance'); check('foot guidance is connected')

        menu(); tab('weekly-plan'); tap(resource='task-plan-generation'); expect('plan-generation')
        tap(resource='action-profile-diet'); field('sheet-dietary', 'Vegan'); hide_keyboard(); tap(text='Save')
        tap(resource='action-create-plan'); tap(text='Review sample meal plan'); expect('plan-rationale')
        check('plan rationale uses the edited profile', contains(tree(), 'Vegan'))
        tap(resource='action-go-weekly-plan'); expect('weekly-plan'); tap(resource='task-activity-plan'); expect('activity-plan')
        check('activity respects the recorded mobility concern', contains(tree(), 'Activity deferred'))
        menu(); tab('profile'); expect('profile'); tap(resource='edit-mobility-constraints'); field('sheet-mobility', 'None'); hide_keyboard(); tap(text='Save')
        tap(resource='open-settings'); expect('flow-directory')
        tap(resource='menu-foot-questionnaire'); expect('foot-questionnaire'); tap(resource='action-review-foot')
        check('profile mobility edits also update questionnaire review', contains(tree(), 'Mobility: Unrestricted')); tap(text='See general guidance')

        open_menu('assistant'); tap(resource='action-assistant-food'); check('assistant prompt produces a response', contains(tree(), 'Try adding a mix'))
        tap(label='Report a concern'); expect('report-output'); back(); expect('assistant')
        open_menu('privacy-data-rights'); tap(resource='action-toggle-retainPhotos'); tap(resource='action-save-preferences'); tap(text='Review reminders'); expect('reminders')
        tap(resource='action-toggle-mealReminder'); tap(resource='action-save-reminders'); tap(text='Close'); back(); expect('privacy-data-rights')
        tap(resource='action-export'); check('export includes shared meal records', contains(tree(), 'Tomato')); tap(text='Close')
    else:
        run('logcat', '-c'); tap(text='Close')
    open_menu('report-status'); check('settings opens the submitted report', contains(tree(), 'DEMO-104'))

    menu(); tap(resource='menu-sign-out'); tap(text='Sign out'); expect('sign-in'); tap(resource='action-go-recover-account'); expect('recover-account')
    tap(resource='action-recover'); tap(text='Preview recovery link'); expect('reset-password')
    field('field-newPassword', 'UpdatedNutri42'); field('field-confirmPassword', 'UpdatedNutri42'); capture('keyboard-reset-password'); hide_keyboard()
    tap(resource='action-reset-password'); expect('sign-in'); field('field-password', 'UpdatedNutri42'); hide_keyboard(); tap(resource='action-sign-in'); expect('home')
    check('recovery fields, keyboard focus and sign-in work')

    staff('Catalog curator', 'catalog-queue'); tap(resource='action-go-catalog-review'); expect('catalog-review'); tap(resource='action-catalog-save'); tap(text='Close')
    staff('Model administrator', 'model-release'); tap(resource='action-release-evidence'); tap(text='Close')
    staff('Operations administrator', 'operations-audit'); tap(resource='action-filter-audit'); tap(text='Close')
    staff('Support curator', 'report-triage'); tap(resource='action-choose-triage-Resolved'); tap(resource='action-triage-save'); tap(text='View report status'); expect('report-status')
    check('all four staff previews have explicit workspace entrances')
    menu(); tap(resource='menu-onboarding'); expect('onboarding'); back(); expect('flow-directory')
    check('Android Back from Getting started returns to settings')
    tab('home'); tap(resource='view-plan'); expect('weekly-plan'); tap(label='Select Sun'); capture('weekly-sunday-selected')
    tap(resource='accept-breakfast'); check('meal acceptance works on the selected day', contains(tree(), 'Accepted'))
    tab('home'); tap(resource='open-health'); expect('glucose-overview')
    check('Home View Plan and Health cards open their task sections')
    if '--tail' not in sys.argv:
        assert set(report['routes']) == set(expected), 'Missing task routes: ' + str(set(expected)-set(report['routes']))
        check('all 38 routes are reached through task controls')
except Exception as error:
    report['errors'].append(str(error)); capture('failure'); print('FAIL: ' + str(error), flush=True)
finally:
    logs = run('logcat', '-d', '-b', 'crash'); (out / 'crash-log.txt').write_text(logs, encoding='utf-8')
    report['appCrashDetected'] = package in logs
    save_report()
sys.exit(1 if report['errors'] or report['appCrashDetected'] else 0)
