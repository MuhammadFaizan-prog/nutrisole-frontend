# NutriSole responsive APK handoff

The current release is [NutriSole 1.0.3](../NutriSole-Responsive-v1.0.3.apk). All 38 screens can be opened through **Home → All screens · 38**. Its final APK passed 38 route renders, 38 directory taps, 17 interaction groups, 106 phone/text configuration checks and three additional physical-input checks at 200% text. See [the current report](v1.0.3/README.md).

## Historical 1.0.2 handoff

The record below describes the earlier 1.0.2 APK and its limitations. The unversioned NutriSole-Responsive.apk alias now points to 1.0.3; the historical SHA-256 below does not describe that current alias.

The user requested stopping emulator work on October 3, 2026 and receiving the built APK.

## Delivered artifact

- APK: `../NutriSole-Responsive.apk`
- Absolute path: `C:/Users/DELL/Downloads/fvp deliverable 1/nutrisole-frontend/artifacts/native/NutriSole-Responsive.apk`
- Version: 1.0.2 (3), plain React Native 0.86.3, frontend only.
- SHA-256: `f321d7eed0da21b1d4567e16452442d64f30bbe7d0fa3b59a2ca11cf405bb64d`
- Built successfully with `native/android/gradlew.bat :app:assembleRelease`.
- Bundled Hermes JS, ARM64/x86_64 libraries, local artwork and five verified font aliases. No Metro or Expo is needed.

## Implementation

All 38 screens have native responsive layouts: six dedicated screen counterparts and 32 flow adapters. Measured content space, Flexbox, growing text, native safe areas, scrolling bodies and fixed footers replace the old scaled canvases. Keyboard focus handling, stores, actions, input validation and the Fabric touch fix remain in place. Camera framing responds to preview space and source-photo exclusion masks remain active. At 200% text, navigation, brand/Skip, health-source values, portion tabs and adjacent buttons reflow to preserve readable labels. Scroll content is clipped below fixed headers.

## Checks completed

- Native TypeScript: passed.
- Native lint: zero errors, 150 inline-style warnings.
- Native tests: 17 passed.
- Root runtime: 28 protected files passed.
- Expansion/preservation tests: 8 passed, including 119 original design files.
- No integrity baseline values were changed.
- An earlier responsive build (`09301daa043fde27e23c96bfcf3c7c72abd8d05843c140a274d8506855dc874e`) passed all 38 routes on six Android configurations: 320x568/font1, 360x640/font1.3, 393x852/font1, 390x844/font1, 412x914/font1 and 430x932/font1.5. Gesture and three-button navigation were covered. The 228 layout checks and captures are recorded in `matrix/validation.json`.
- An intermediate refined build (`45fb37e66666440e98c71ace07b4ed695bfea6f333fabdaf5e30dbbcdab8b196`) passed 12 critical routes at 320x568 with 200% text. The captures and their actual hash are recorded in `matrix/stress-validation.json`.
- The delivered APK additionally includes wrapping portion tabs and explicit scroll clipping. It was installed on the Android emulator; pulling the installed APK confirmed an exact hash match, with no Metro listener. Onboarding rendered, but repeated emulator System UI timeout dialogs blocked the final interaction harness. These failures are preserved in `interactions/validation.json`; they are not reported as passed app checks.

## Remaining verification

The final APK's all-route interaction regression, final reference captures and final 200% text rerun were stopped at the user's request. The prior matrices describe their recorded builds, not the delivered APK. No physical Android phone or iOS simulator/device was tested here. iOS code is included and typechecked, but iOS runtime/build verification requires macOS/Xcode. Exact pixel identity and flawless behavior on every phone are not certified.
