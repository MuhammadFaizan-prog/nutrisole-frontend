"""Make inspection sheets and a report from the APK verification evidence."""
import hashlib
import json
import re
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

native = Path(__file__).resolve().parents[1]
root = native.parent
out = root / 'artifacts/native/responsive-qa'
matrix = out / 'matrix'
model = (root / 'src/nutrisole/extensions/model.ts').read_text(encoding='utf-8')
extras = re.findall(r"'([^']+)'", model.split('export const extensionRoutes = [', 1)[1].split('] as const', 1)[0])
routes = ['onboarding', 'home', 'scan', 'log-meal', 'weekly-plan', 'profile'] + extras
font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 16)


def contacts(directory, bottom=False):
    names = [r for r in routes if (directory / (r + ('-bottom' if bottom else '') + '.png')).exists()]
    for page in range(0, len(names), 9):
        chunk = names[page:page + 9]
        canvas = Image.new('RGB', (1008, 1830), '#e9e7e1')
        draw = ImageDraw.Draw(canvas)
        for i, route in enumerate(chunk):
            im = Image.open(directory / (route + ('-bottom' if bottom else '') + '.png')).convert('RGB')
            im.thumbnail((320, 568), Image.Resampling.LANCZOS)
            x, y = 8 + i % 3 * 336, 8 + i // 3 * 610
            draw.text((x, y), route, font=font, fill='#123f2c')
            canvas.paste(im, (x, y + 28))
        canvas.save(directory / f"contact-{'bottom-' if bottom else ''}{page // 9 + 1:02}.png")


if '--contacts-only' in sys.argv:
    directory = matrix / sys.argv[-1]
    contacts(directory)
    contacts(directory, bottom=True)
    print('Inspection sheets saved: ' + str(directory))
    sys.exit(0)

data = json.loads((matrix / 'validation.json').read_text(encoding='utf-8'))
reference = json.loads((matrix / 'final-reference/quick-validation.json').read_text(encoding='utf-8'))
stress = json.loads((matrix / 'stress-validation.json').read_text(encoding='utf-8'))
interactions = json.loads((out / 'interactions/validation.json').read_text(encoding='utf-8'))
apk = root / 'artifacts/native/NutriSole-Responsive.apk'
digest = hashlib.sha256(apk.read_bytes()).hexdigest()
assert data['status'] == reference['status'] == stress['status'] == interactions['status'] == 'passed'
assert reference['apkSha256'] == stress['apkSha256'] == interactions['apkSha256'] == digest
assert len(interactions['screens']) == 38
for config in data['configs'] + reference['configs'] + stress['configs']:
    assert all(s['safeViewportBounds'][2] - s['safeViewportBounds'][0] == config['physicalPixels'][0] for s in config['screens']), 'Recorded viewport differs from requested display size'
for config in data['configs'] + stress['configs']:
    contacts(matrix / config['name'])
    contacts(matrix / config['name'], bottom=True)

for config in reference['configs']:
    contacts(matrix / 'final-reference' / config['name'])
    contacts(matrix / 'final-reference' / config['name'], bottom=True)

sources = {
    'onboarding': ('01_21_15 AM-1', (38, 38, 786, 1748)),
    'home': ('01_21_16 AM-2', (42, 38, 777, 1737)),
    'scan': ('01_21_18 AM-3', (41, 37, 781, 1739)),
    'log-meal': ('01_21_19 AM-4', (55, 120, 750, 1604)),
    'weekly-plan': ('01_21_21 AM-5', (57, 149, 749, 1537)),
    'profile': ('01_21_23 AM-6', (50, 166, 760, 1564)),
}
comparison = out / 'comparisons'
comparison.mkdir(exist_ok=True)
for route, (suffix, (x, y, w, h)) in sources.items():
    path = root.parent / 'NutriSole-UI-Concepts' / f'ChatGPT Image Sep 29, 2026, {suffix}.png'
    original = Image.open(path).convert('RGB').crop((x, y, x + w, y + h))
    original = original.resize((393, round(h * 393 / w)), Image.Resampling.LANCZOS)
    shot = Image.open(matrix / 'final-reference/reference-393' / f'{route}.png').convert('RGB')
    bottom_path = matrix / 'final-reference/reference-393' / f'{route}-bottom.png'
    bottom = Image.open(bottom_path).convert('RGB') if bottom_path.exists() else shot
    panel = Image.new('RGB', (1231, max(original.height, shot.height) + 50), '#eeece6')
    draw = ImageDraw.Draw(panel)
    for i, (label, image) in enumerate([('PNG content crop', original), ('Android initial position', shot), ('Android after scrolling', bottom)]):
        px = 8 + i * 409
        draw.text((px, 8), label, font=font, fill='#123f2c')
        panel.paste(image, (px, 38))
    panel.save(comparison / f'{route}.png')

total = sum(len(c['screens']) for c in data['configs'])
stress_total = sum(len(c['screens']) for c in stress['configs'])
reference_total = sum(len(c['screens']) for c in reference['configs'])
table = '\n'.join(f"| {c['name']} | {c['width']} × {c['height']} | {c['density']} | {c['font']} | {c['navigation']} | {len(c['screens'])} |" for c in data['configs'] + stress['configs'])
flows = '\n'.join('- ' + value for value in interactions['interactions'])
report = f"""# NutriSole responsive native verification

Android release **1.0.2 (3)**, plain React Native **0.86.3**, frontend only. The standalone APK is `../NutriSole-Responsive.apk`.

SHA-256: `{digest}`

## What changed

The native entry now uses measured Flexbox layouts in `native/responsive/`. The original six use dedicated flowing layouts; the 32 additional routes reuse their scene content, fields, actions and stores through a native card/row adapter. Text is naturally sized and system-scalable. SafeAreaProvider/SafeAreaView consume system insets once. Headers and footers sit outside bounded scroll bodies. Keyboard avoidance and input focus are retained, and expanded destinations start at the top.

Texture images have explicit dimensions and clipped decorative wrappers. Photos retain aspect ratio. Camera information scrolls when the available preview is too short, while capture controls stay visible. The existing clean camera photo is used consistently beneath its exclusion mask to avoid seams from photographed controls. The onboarding mask also excludes text fragments at the source photo edge. Source files and assets have not been rewritten.

At 200% system text, Home navigation wraps into two rows, the onboarding brand and Skip control use separate rows, health-source values stack, portion tabs wrap, and adjacent extension buttons reflow vertically. This preserves complete words and accessible controls on the narrowest phone without suppressing system font scaling. Scroll containers explicitly clip their moving contents so card backgrounds cannot paint over fixed headers.

## Runtime configurations actually tested

All six main screens and all 32 additional routes passed on an Android API 36 x86_64 emulator in each of the first six configurations. Twelve critical routes also passed with 200% system text on the short 320-wide phone.

The full six-configuration matrix was collected before the final large-text and scroll-clipping refinements, using APK `{data['apkSha256']}`. Those captures and their recorded hash remain unchanged. The delivered APK was separately retested on all 38 routes at 360 × 640 / 130% text, plus {reference_total} reference-viewport checks at 393 × 852 / default text and {stress_total} checks at 320 × 568 / 200% text. `matrix/final-reference/`, the stress captures and `interactions/` identify the delivered APK's hash.

| Configuration | Logical window | Density dpi | System font scale | Navigation | Routes |
| --- | --- | --- | --- | --- | --- |
{table}

There were **{total} full-matrix layout checks**, followed by **{reference_total} final reference checks** and **{stress_total} final stress checks**. The final installed APK was the exact artifact identified by the hash above. It launched without a Metro server. Layout QA checked each route's native root, safe viewport and horizontal bounds. Scrolling gestures were exercised and initial/after-scroll PNG screenshots plus UI hierarchies were saved. Camera capture/footer bounds were additionally checked. These automated bounds checks complement visual inspection; they are not a pixel-difference certification.

## Interaction checks

Cold launch opened onboarding. All 38 routes were opened separately, then these groups were exercised through Android physical input events:

Interaction QA used a 360 × 640 logical window, 160 dpi, 130% system text and Android three-button navigation. The raw measured display, text and navigation settings are recorded in `interactions/validation.json`.

{flows}

Crash buffers contained no FATAL EXCEPTION or Fatal signal. The APK contains its Hermes bundle, ARM64/x86_64 native libraries, local assets and all five verified font aliases. It uses the existing NutriSole leaf launcher artwork and internal evaluation signing configuration.

## Source verification and preservation

- Native TypeScript: passed.
- Native ESLint: zero errors; existing inline-style warnings remain.
- Native Node tests: 17 passed.
- Root runtime integrity: 28 protected files passed.
- Original screen/artwork preservation and expansion tests: 8 passed, including 119 protected files.
- Integrity baseline values were not changed.

## Visual review and limits

The `comparisons/` images place the PNG's content crop alongside the 393 × 852 Android screen, with the pictured device frame excluded. The OS status/navigation areas and the PNGs' different height ratios are visible for context. Colors, fonts, copy, source icons, card shapes, photos and component hierarchy are retained. Native content now wraps and scrolls; the Home and Onboarding content need scrolling at some shorter heights. Large text deliberately changes row and column arrangements. Exact pixel identity is not certified.

The screenshots in `matrix/` and its contact sheets record the tested layouts; `interactions/` contains input, sheet and flow evidence. All capture files refer to emulator output, not screen images mounted in the application.

Manual screenshot review covered all 38 compact and large-phone layouts, the six reference-viewport comparisons, and the twelve 200% text stress layouts. Review led to refinements of image crops, card textures, header/back alignment, preference values, navigation labels and large-text button rows.

**iOS:** common native layouts, font aliases, safe-area consumption and keyboard avoidance were updated/typechecked. Asymmetric iPhone insets are covered by unit tests. No iOS simulator/device was available on this Windows host, so iOS runtime/build verification remains unperformed. A physical Android phone was also not tested here.

## Reproduce

Build from `native/android` using `gradlew.bat :app:assembleRelease`. Install `app/build/outputs/apk/release/app-release.apk`, then run `native/scripts/verify-responsive.py SERIAL`, its `--stress` variant and `native/scripts/verify-android.py SERIAL --responsive`. The QA scripts clear only the configured emulator app's synthetic data and temporarily override its display/text settings. Matrix QA restores the emulator to 432 × 960, 160 dpi, default text and gesture navigation afterward.
"""
(out / 'README.md').write_text(report, encoding='utf-8')
summary = {'apkPath': str(apk), 'apkSha256': digest, 'version': '1.0.2', 'versionCode': 3, 'routes': 38, 'layoutChecks': total, 'stressChecks': stress_total, 'interactionGroups': len(interactions['interactions']), 'crashFree': data['crashFree'] and stress['crashFree'] and interactions['crashFree'], 'iosRuntimeTested': False, 'physicalPhoneTested': False, 'checks': {'nativeTypecheck': 'passed', 'nativeLint': '0 errors; inline-style warnings', 'nativeTests': 17, 'rootRuntimeProtectedFiles': 28, 'rootExpansionTests': 8, 'protectedDesignFiles': 119}, 'configurations': [{k: v for k, v in c.items() if k != 'screens'} for c in data['configs'] + stress['configs']], 'interactionConfiguration': interactions['configuration']}
(out / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps(summary, indent=2))
