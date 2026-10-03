# NutriSole 1.0.3 responsiveness and navigation verification

Android release APK: `../../NutriSole-Responsive-v1.0.3.apk`, version 1.0.3 (4).
SHA-256: `09955085ecf5d07bde39c3499f66b28291fef38f07ac5293cd36ece831fccb2b`. The installed package matched this exact hash.
Built with `native/android/gradlew.bat :app:assembleRelease`; bundled Hermes, ARM64/x86_64 and all five native font aliases. No Metro server was listening during testing.

## Changes

Home's View Plan and Health cards use measured available width, retain two columns at the reference size, and stack before enlarged text becomes cramped. Weekly calendars use one horizontal row for all seven days; default text fits all seven on the requested phone widths, while enlarged text gets horizontal scrolling. A visible Home → All screens entry opens a native directory containing all 38 canonical destinations.

All additions remain real React Native components. The six protected shared modules/assets and the web runtime were preserved. The photo exclusion masks, safe areas, keyboard focus fix and Fabric touch adapter remain intact.

## Executed checks

- Native typecheck passed; lint had 0 errors (156 existing/inline-style warnings); 20 native tests passed.
- Root runtime check passed for 28 protected files; 8 expansion/preservation tests and 5 domain tests passed, including the 119-file original-screen baseline.
- Static code review found no actionable issues.
- Cold launch and all 38 rendered routes passed on Android API 34 x86_64. All 38 directory destinations were exercised through actual taps. 17 interaction groups passed, covering preferences, keyboard focus, inputs, portions, planning, camera, navigation and back behavior.
- Three additional physical-input checks passed at 320 × 568 with 200% text: scrolling the weekday rail to Sunday and selecting it, scrolling to the complete View Plan card and opening Weekly Plan, and scrolling to the complete Health card and opening Glucose overview. Evidence is in `critical-taps/validation.json` and its screenshots/XML. The first rail gesture started in Android's back-gesture edge region and returned Home; that attempt is retained under `critical-taps-edge-gesture-attempt/`. The successful test starts within the calendar rail and preserves system back behavior.
- 106 viewport/route checks passed. Initial and scrolled screenshots/XML are saved under `matrix/`. These checks verify viewport bounds, horizontal overflow, single-row weekdays, camera capture visibility, scrolling and absence of the legacy scaled canvas; they do not by themselves prove pixel identity or every text line's appearance.

The initial matrix's only app-layout flag was a Home minimum-height estimate at 150% text. The rendered description occupied a complete 50-pixel line and cleared the card's padding; the estimate assumed linear font scaling. Android 14 applies [nonlinear font scaling](https://developer.android.com/about/versions/14/features#non-linear-font-scaling). The assertion was changed to check actual title/description bounds, separation and padding. Replaying the corrected check against the earlier clipped Home XML still rejects it (`home-card-assertion-replay.txt`). The affected Home case was rerun against the unchanged final APK; `matrix/validation-before-rerun.json` preserves the original flag, and `rerunCases` identifies the replacement result. No app code, APK or integrity baseline was changed to resolve this test-model error.

| Logical viewport | Text scale | Navigation | Screens |
|---|---:|---|---:|
| 320 × 568 | 1 | gestural | 38 |
| 360 × 640 | 1.3 | threebutton | 6 |
| 393 × 852 | 1 | gestural | 6 |
| 390 × 844 | 1 | gestural | 6 |
| 412 × 914 | 1 | threebutton | 6 |
| 430 × 932 | 1.5 | gestural | 38 |
| 320 × 568 | 2 | gestural | 6 |

All 38 routes were tested at 320 × 568/default text and 430 × 932/150% text. The six main screens were additionally checked at the other listed configurations, including 200% text. Gesture and three-button navigation were exercised.

## Manual screenshot review

Visually inspected all 38 reference captures, the initial and scrolled contact sheets for all 38 routes at 320 × 568/default text and 430 × 932/150% text, and the six main screens at 320 × 568/200% text. Also inspected all six supplied-PNG comparison images and the Sunday, View Plan and Health targeted tap screenshots.

The Home card descriptions are complete and readable; narrow or enlarged-text layouts stack the cards. The weekday controls stay on one horizontal row, with Sunday reachable by horizontal scrolling when needed. Long content and enlarged labels wrap and scroll; fixed navigation and submission controls remain reachable. Content partially visible at a scroll viewport boundary was checked using the scrolled captures. This is snapshot review, not certification of every possible UI state. Typography metrics, spacing and native system chrome differ from the supplied phone mockups; exact pixel identity is not claimed.

## Runtime environment and limitations

The earlier build's first attempt was blocked by Android system-process/System UI ANR dialogs. That failure and screenshot are retained under `../v1.0.3-before-card-height/interactions/attempt1-validation.json` and `attempt1-system-anr.png`. System UI was recovered before the final interaction run. The first matrix launch lost its emulator connection; its traceback is retained in `../v1.0.3-layout-final.log`. After restarting the owned QA emulator, a Bluetooth system-service crash dialog blocked route inspection; the failed XML, Bluetooth crash log and recovery screenshot are retained under `matrix-system-dialog-attempt/`. Bluetooth was disabled only on this test emulator, the system dialog was closed, and the complete matrix was rerun. No app crash occurred in the successful test intervals. An intermediate Home description-height issue was corrected and rebuilt before these final checks. Crash logs and reports retain the actual APK hash and Android API.

This was emulator testing. No physical Android phone or iOS simulator/device was available. iOS safe-area calculations have unit coverage, but iOS runtime behavior is unverified. The manual review coverage is recorded above; contact sheets alone do not prove visual correctness.

Detailed results: `matrix/validation.json` and `interactions/validation.json`.

Original PNG comparisons and the 38-screen reference inspection sheets are saved under `visual-review/`. The reference crops remove the outer phone frame but retain the pictured status bar and island; the APK uses its actual native system chrome. These are qualitative comparisons, not hardware-excluded pixel-difference measurements.
