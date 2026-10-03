"""Report only evidence recorded against the current v1.0.3 release APK."""
import hashlib
import json
import re
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[2]
out = root / 'artifacts/native/responsive-qa/v1.0.3'
matrix = json.loads((out / 'matrix/validation.json').read_text(encoding='utf-8'))
interactions = json.loads((out / 'interactions/validation.json').read_text(encoding='utf-8'))
critical = json.loads((out / 'critical-taps/validation.json').read_text(encoding='utf-8'))
apk = root / 'artifacts/native/NutriSole-Responsive-v1.0.3.apk'
digest = hashlib.sha256(apk.read_bytes()).hexdigest()
assert matrix['apkSha256'] == interactions['apkSha256'] == interactions['installedApkSha256'] == digest
assert matrix['status'] == interactions['status'] == 'passed'
assert matrix['crashFree'] and interactions['crashFree']
assert critical['status'] == 'passed' and critical['crashFree']
assert critical['apkSha256'] == critical['installedApkSha256'] == digest
assert len(interactions['screens']) == len(interactions['directoryTaps']) == 38
font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 16)

for config in matrix['configs']:
    directory = out / 'matrix' / config['name']
    names = [screen['route'] for screen in config['screens']]
    for bottom in [False, True]:
        suffix = '-bottom' if bottom else ''
        for start in range(0, len(names), 9):
            canvas = Image.new('RGB', (1008, 1830), '#e9e7e1')
            draw = ImageDraw.Draw(canvas)
            for index, route in enumerate(names[start:start + 9]):
                image_path = directory / (route + suffix + '.png')
                if not image_path.exists():
                    continue
                shot = Image.open(image_path).convert('RGB')
                shot.thumbnail((320, 568), Image.Resampling.LANCZOS)
                x, y = 8 + index % 3 * 336, 8 + index // 3 * 610
                draw.text((x, y), route, font=font, fill='#123f2c')
                canvas.paste(shot, (x, y + 28))
            canvas.save(directory / f'contact{suffix}-{start // 9 + 1:02}.png')

with zipfile.ZipFile(apk) as archive:
    bundle = archive.read('assets/index.android.bundle')
    fonts = [name for name in archive.namelist() if name.startswith('assets/fonts/')]
    assert bundle[:8].hex() == 'c61fbc03c103191f', 'Expected compiled Hermes bundle'
    assert all(any(alias in name for name in fonts) for alias in ['NutriSans', 'NutriSansBold', 'NutriSerif', 'NutriSerifBold', 'NutriSerifText'])
    assert all(any(name.startswith(f'lib/{abi}/') for name in archive.namelist()) for abi in ['arm64-v8a', 'x86_64'])

rows = ['| Logical viewport | Text scale | Navigation | Screens |', '|---|---:|---|---:|']
for config in matrix['configs']:
    rows.append(f"| {config['width']} × {config['height']} | {config['font']} | {config['navigation']} | {len(config['screens'])} |")
checks = sum(len(config['screens']) for config in matrix['configs'])
report = f'''# NutriSole 1.0.3 responsiveness and navigation verification

Android release APK: `../../NutriSole-Responsive-v1.0.3.apk`, version 1.0.3 (4).
SHA-256: `{digest}`. The installed package matched this exact hash.
Built with `native/android/gradlew.bat :app:assembleRelease`; bundled Hermes, ARM64/x86_64 and all five native font aliases. No Metro server was listening during testing.

## Changes

Home's View Plan and Health cards use measured available width, retain two columns at the reference size, and stack before enlarged text becomes cramped. Weekly calendars use one horizontal row for all seven days; default text fits all seven on the requested phone widths, while enlarged text gets horizontal scrolling. A visible Home → All screens entry opens a native directory containing all 38 canonical destinations.

All additions remain real React Native components. The six protected shared modules/assets and the web runtime were preserved. The photo exclusion masks, safe areas, keyboard focus fix and Fabric touch adapter remain intact.

## Executed checks

- Native typecheck passed; lint had 0 errors (156 existing/inline-style warnings); 20 native tests passed.
- Root runtime check passed for 28 protected files; 8 expansion/preservation tests and 5 domain tests passed, including the 119-file original-screen baseline.
- Static code review found no actionable issues.
- Cold launch and all 38 rendered routes passed on Android API {interactions['api']} x86_64. All 38 directory destinations were exercised through actual taps. {len(interactions['interactions'])} interaction groups passed, covering preferences, keyboard focus, inputs, portions, planning, camera, navigation and back behavior.
- Three additional physical-input checks passed at 320 × 568 with 200% text: scrolling the weekday rail to Sunday and selecting it, scrolling to the complete View Plan card and opening Weekly Plan, and scrolling to the complete Health card and opening Glucose overview. Evidence is in `critical-taps/validation.json` and its screenshots/XML. The first rail gesture started in Android's back-gesture edge region and returned Home; that attempt is retained under `critical-taps-edge-gesture-attempt/`. The successful test starts within the calendar rail and preserves system back behavior.
- {checks} viewport/route checks passed. Initial and scrolled screenshots/XML are saved under `matrix/`. These checks verify viewport bounds, horizontal overflow, single-row weekdays, camera capture visibility, scrolling and absence of the legacy scaled canvas; they do not by themselves prove pixel identity or every text line's appearance.

The initial matrix's only app-layout flag was a Home minimum-height estimate at 150% text. The rendered description occupied a complete 50-pixel line and cleared the card's padding; the estimate assumed linear font scaling. Android 14 applies [nonlinear font scaling](https://developer.android.com/about/versions/14/features#non-linear-font-scaling). The assertion was changed to check actual title/description bounds, separation and padding. Replaying the corrected check against the earlier clipped Home XML still rejects it (`home-card-assertion-replay.txt`). The affected Home case was rerun against the unchanged final APK; `matrix/validation-before-rerun.json` preserves the original flag, and `rerunCases` identifies the replacement result. No app code, APK or integrity baseline was changed to resolve this test-model error.

{chr(10).join(rows)}

All 38 routes were tested at 320 × 568/default text and 430 × 932/150% text. The six main screens were additionally checked at the other listed configurations, including 200% text. Gesture and three-button navigation were exercised.

## Manual screenshot review

Visually inspected all 38 reference captures, the initial and scrolled contact sheets for all 38 routes at 320 × 568/default text and 430 × 932/150% text, and the six main screens at 320 × 568/200% text. Also inspected all six supplied-PNG comparison images and the Sunday, View Plan and Health targeted tap screenshots.

The Home card descriptions are complete and readable; narrow or enlarged-text layouts stack the cards. The weekday controls stay on one horizontal row, with Sunday reachable by horizontal scrolling when needed. Long content and enlarged labels wrap and scroll; fixed navigation and submission controls remain reachable. Content partially visible at a scroll viewport boundary was checked using the scrolled captures. This is snapshot review, not certification of every possible UI state. Typography metrics, spacing and native system chrome differ from the supplied phone mockups; exact pixel identity is not claimed.

## Runtime environment and limitations

The earlier build's first attempt was blocked by Android system-process/System UI ANR dialogs. That failure and screenshot are retained under `../v1.0.3-before-card-height/interactions/attempt1-validation.json` and `attempt1-system-anr.png`. System UI was recovered before the final interaction run. The first matrix launch lost its emulator connection; its traceback is retained in `../v1.0.3-layout-final.log`. After restarting the owned QA emulator, a Bluetooth system-service crash dialog blocked route inspection; the failed XML, Bluetooth crash log and recovery screenshot are retained under `matrix-system-dialog-attempt/`. Bluetooth was disabled only on this test emulator, the system dialog was closed, and the complete matrix was rerun. No app crash occurred in the successful test intervals. An intermediate Home description-height issue was corrected and rebuilt before these final checks. Crash logs and reports retain the actual APK hash and Android API.

This was emulator testing. No physical Android phone or iOS simulator/device was available. iOS safe-area calculations have unit coverage, but iOS runtime behavior is unverified. The manual review coverage is recorded above; contact sheets alone do not prove visual correctness.

Detailed results: `matrix/validation.json` and `interactions/validation.json`.

Original PNG comparisons and the 38-screen reference inspection sheets are saved under `visual-review/`. The reference crops remove the outer phone frame but retain the pictured status bar and island; the APK uses its actual native system chrome. These are qualitative comparisons, not hardware-excluded pixel-difference measurements.
'''
(out / 'README.md').write_text(report, encoding='utf-8')
print(json.dumps({'status': 'passed', 'apkSha256': digest, 'layoutChecks': checks, 'directoryTaps': len(interactions['directoryTaps'])}))
