# NutriSole native user journeys

**Goal:** Connect all 38 native screens by task and replace Home's screen catalog with a menu/settings destination.

**Architecture:** Keep the protected six shared modules, source assets and web runtime intact. Native route metadata, a history reducer, task links and scene/action adapters own the new behavior. Keep the five existing primary destinations: Home, Plan, Scan, Health and Profile. Reuse `flow-directory` as Menu & Settings so old app links remain valid without adding another catalog screen.

**Design:** Home keeps its food/plan/health cards and recent scans. A header menu and Profile settings control lead to secondary tools and account/data settings. Capture opens assessment, food correction opens the selector, nutrition opens portion confirmation, and logging updates Home/history. Plan tools connect generation, rationale and weekly activity. Health connects manual readings, sources and foot support. Account screens follow sign-up/verification/sign-in and recovery/reset flows. Reports connect result/report/status; staff previews are grouped under a clearly separate workspace menu. Forms/detail pages use contextual back; switching primary tabs starts that section without stacking old tabs.

## Implementation and verification

- [x] Add failing native journey tests for 38-route reachability, task entry points, tab selection/back history, legacy aliases and context-bound destinations.
- [x] Implement native navigation metadata/reducer, a consistent tab bar and task link groups.
- [x] Replace the native screen directory with Menu & Settings; remove the Home catalog shortcut. Add discoverable menu/Profile settings controls and explicit staff preview choices.
- [x] Connect account, capture, assessment, nutrition, portions, readings, plans, history and reports. Keep selected food and saved meal data consistent between native routes.
- [x] Run native typecheck/lint/tests and root runtime/preservation/domain checks. Review the navigation implementation.
- [x] Increment Android/iOS source version to 1.0.4 and build with `native/android/gradlew.bat :app:assembleRelease`.
- [ ] Install the exact release without Metro; exercise actual task paths into all 38 screens, back behavior, primary tabs, forms and settings. Save screenshots/crash logs and review changed screens at compact/enlarged text configurations.
- [x] Deliver the APK and an evidence report. State the iOS runtime limitation.

Runtime verification is partial: an intermediate APK reached 31 screens with physical task controls and exposed a JSON-preview truncation that was fixed in the final build. The exact final APK was installed, its hash matched, and onboarding rendered without Metro. Repeated Android system/launcher ANRs and host memory pressure interrupted the final sweep. All 38 final task paths and the final phone/text layout matrix remain unverified; retained evidence is in `artifacts/native/navigation-qa/v1.0.4/README.md`. The owned QA emulator was stopped after recording this limit.

Regression commands: `npm --prefix native test`, `npm --prefix native run typecheck`, `npm --prefix native run lint`, `npm run check:runtime`, `npm run test:expansion`, `npm test`. The Android journey harness must count routes reached through physical task controls, separately from any deep-link render check. Do not reuse an old APK's results for the new artifact.
