# NutriSole Native Responsive Implementation Plan

**Goal:** Deliver all 38 frontend screens with adaptive native layouts and a verified standalone Android APK.

**Architecture:** Keep the web/reference sources intact. Add native flow components using shared stores/actions, six responsive screen implementations, and a card/row compiler for the existing extension model. Real safe-area insets and keyboard handling replace scaled canvases.

**Tech Stack:** React Native 0.86.3, TypeScript, react-native-safe-area-context, existing RN SVG/artwork, Gradle and ADB.

## Tasks

- [x] Add failing tests for safe viewport dimensions, height-independent typography, row/card membership, retained actions and fields, then implement pure helpers in native/responsive/metrics.ts and sceneFlow.ts. Run `npm test` from native.
- [x] Add responsive primitives in native/responsive/components.tsx: natural-height text, textured cards, measured scroll screens, semantic pressables, source art and image masks. No full-screen transforms or fixed-height text.
- [x] Implement the six screens in native/responsive/CoreScreens.tsx, ScanScreen.tsx and WeeklyScreen.tsx; reuse demo store, portion arithmetic and all existing actions.
- [x] Render all extension scenes through native/responsive/ExpandedScreen.tsx using sceneFlow card hierarchy and Flexbox bands/columns, natural-height inputs and wrapping tabs. Reuse useExpansion without changing the model.
- [x] Connect native/responsive/NutriSole.tsx from native/App.tsx. Add safe-area-context to native dependencies/Metro resolution and adjust modal inset/keyboard consumption. Increment the native app version.
- [x] Run `npm run typecheck`, `npm run lint`, `npm test` in native; run `npm run check:runtime` and `npm run test:expansion` in the root. Resolve failures without modifying baselines.
- [x] Build with `gradlew.bat :app:assembleRelease` in native/android. The final 1.0.3 APK was installed on emulator-5582 and its installed SHA-256 matched the artifact, without Metro.
- [x] Run the Android interaction regression suite and a 38-screen layout matrix. All 38 routes, 38 directory taps, 17 functional groups, 106 configuration/route checks and three 200%-text physical-input checks passed on the final APK. Retain the system-dialog attempts and the corrected nonlinear font-height assertion's original flag; do not mix earlier APK hashes into current results.
- [x] Save the versioned APK, screenshots, PNG comparisons and report in artifacts/native/responsive-qa/v1.0.3. Document the seven tested configurations and iOS/physical-phone limitations. The handoff uses NutriSole-Responsive-v1.0.3.apk.
