# NutriSole 1.0.4 native journeys

The frontend implementation and Android release build are complete. Final runtime verification is partial, as detailed below. This record does not certify all 38 routes on the delivered APK or pixel identity.

This source repository includes verification summaries and validation JSON. APK files, raw logs, PNG/XML captures and intermediate contact sheets referenced below remain in the local workspace and are excluded from Git.

## Deliverable

- APK: `C:/Users/DELL/Downloads/fvp deliverable 1/nutrisole-frontend/artifacts/native/NutriSole-Journeys-v1.0.4.apk`
- Latest alias: `artifacts/native/NutriSole-Responsive.apk`
- Version: 1.0.4 / Android versionCode 5.
- Size: 41,910,972 bytes.
- SHA256: `61905ab51c02bf69fe768afe8c15da3a3095f17d88c2e79a1ef6265df961999e`.
- Plain React Native 0.86.3 / TypeScript, ARM64 and x86_64, bundled Hermes JavaScript and five font resources; no Expo archive entries.
- Built through `native/android/gradlew.bat :app:assembleRelease`; final log: `../../build-release-v1.0.4-final-verified-source.log`.
- This evaluation build uses the existing development signing key. No backend, real authentication, live vision service, provider integration or server-side staff functionality was added.

## Behavior implemented

Home retains Scan Food, View Plan, Health and recent scans. Its header gear opens Menu & Settings; Profile provides another entrance. The five primary tabs are Home, Plan, Scan, Health and Profile. Secondary tools, account/data preferences, reports and synthetic staff roles are grouped in settings. There is no 38-screen catalog button on native Home.

All 38 registered native screens have task entrances. Account creation connects verification and sign-in; recovery connects reset and sign-in. Capture connects assessment, correction, nutrition, portions and history. Food, measured portion and record identity survive child screens, draft reopening and saved-record editing. Health connects manual readings, detail/edit and simulated provider fallback. Plan connects generation, rationale and activity; profile mobility edits affect the foot questionnaire and activity preview. Reports connect their originating result, review, status and staff triage preview. Back returns to task parents; primary tabs reset their section history.

Native-only responsive layouts retain Home card reflow, the single horizontal weekday strip, safe areas, content scrolling and system text scaling. Android keyboard avoidance now resizes screen and sheet content above the IME without adding the top safe-area inset twice. Input focus transfer and the existing Fabric touch adapter remain in place. The export sheet displays full selectable local JSON rather than a truncated editable field.

## Checks that passed on final source

| Check | Result | Evidence |
| --- | --- | --- |
| Native TypeScript | Passed | `typecheck.log` |
| Native lint | 0 errors, 165 warnings | `lint.json` |
| Native tests | 34 passed | `tests.log` |
| Root runtime preservation | 28 protected files passed | `runtime.log` |
| Expansion / six-screen preservation | 8 tests passed; 119 files preserved | `preservation.log` |
| Root domain tests | 5 passed | `root-tests.log` |
| Gradle release | Passed, 182 tasks | Final build log above |
| APK installation and identity | Installed SHA256 matches build and deliverable | `journeys/validation.json` |
| Standalone cold launch | Coded onboarding rendered without Metro | `journeys/onboarding.png` |

The original six shared source modules/assets, integrity baselines and protected web runtime were preserved. Lint warnings concern inline styles; they were not concealed by disabling rules. Native journey tests cover route graph reachability and navigation/data regressions, which is distinct from physical runtime coverage.

## Android runtime evidence and refinements

The owned API 34 x86_64 AVD was `NutriSole_Responsive_QA`, serial `emulator-5582`. The actual interaction configuration was **393 × 852 logical units**, density 160, default system text, gesture navigation. No Metro listener was present on port 8081. No physical phone was tested.

An intermediate APK, SHA256 `51ae1ec5bd937d80b652c647f0c9f8428ed1f1940d803ffff535cb827d3d2621`, reached **31 different screens through physical taps and Android Back**, with 16 recorded interaction assertions. It covered the original six, account creation/verification/sign-in, food correction, portions/drafts/history, retry/report flows, readings/provider fallback, foot/plan/activity state, Assistant, privacy and reminders. It failed the export assertion because the sheet truncated JSON to 300 characters. That real frontend issue was fixed and rebuilt into the final APK. Earlier retained attempts also exposed and helped refine keyboard coverage and input-focus handling.

Evidence for that intermediate run is in `journeys-attempt-4/validation.json`, its per-screen PNG/XML files and crash log. Four `intermediate-visual-review-*.jpg` contact sheets were reviewed for the 31 first-visit captures. Home's cards and the seven-day row were readable at that configuration, task roots showed consistent navigation, and the account/weight-sheet keyboard captures showed reachable focused inputs. Those screenshots belong to the intermediate APK; they are not final-release certification or proof of all scrolled content.

The exact final APK was installed, and its device hash matched `61905ab5…`. Final cold launch rendered onboarding. The final sweep was interrupted by **Process system**, **Pixel Launcher** and **System UI** nonresponsive alerts. A later tap/route expectation also failed while the Android system was unstable. Windows reported about 270 MB free physical memory, and restarting the owned emulator with a smaller allocation did not remove the system interruptions. The harness records known OS interruptions, never dismisses a NutriSole ANR as an OS event, and retains all failures. Its app crash-buffer check found no NutriSole crash in those attempts; that does not prove long-running stability.

Final attempts are retained in `journeys-attempt-5/` and `journeys/`; the latter includes `harnessInterruptions`, an incomplete route list and the failed create-account expectation. The QA emulator was stopped after collecting evidence. Other user applications/devices were not stopped.

## Limits and reproducible remaining verification

The **final** 38-screen physical journey sweep and final enlarged-text/compact-phone matrix were not completed. A 36-case layout harness is prepared for 393 × 852/default text/gestures, 430 × 932/150% text/gestures, and 320 × 568/200% text/three-button navigation, inspecting the six main screens plus six changed task roots. These are planned configurations, not claimed passes. Prior version 1.0.3 layout results are preserved separately and are not reused as final evidence.

When an Android device or stable emulator is available, install the exact APK and run from the repository root:

```powershell
python native/scripts/verify-journeys.py emulator-5582
python native/scripts/verify-responsive.py emulator-5582 --journeys
```

The first script checks the installed APK identity and uses physical task controls for reachability; the second uses validated deep links only for layout inspection. Keep their evidence separate. Recovery/reset and the five staff screens still need final physical interaction verification. Export after the final JSON fix also needs its runtime assertion rerun.

iOS source/version remains in the project, but no macOS, iOS simulator or iOS device was available. iOS compilation and runtime verification were not performed. No claim of 100% visual identity or universal phone compatibility is made.
