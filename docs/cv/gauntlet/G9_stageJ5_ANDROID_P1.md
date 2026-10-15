# G9 Stage J5: Android P0 / P1 on the isolated device branch `cv-gauntlet-device`

> **J6 (2026-10-16): the P1 steps are superseded by `G9_stageJ6_ANDROID_P1_ADDENDUM.md`** (versions, inference badge, memory/latency capture, what to send back). The J5 record below is kept unchanged.

Written 2026-10-15 (PKT). Branch `cv-gauntlet-device` was cut from `cv-gauntlet` after the J5 commit; it is never merged to `main` and
never deployed. Approval: the user's 22:53 PKT message ("APPROVED: isolated Android dev branch"). **No FPS, latency or accuracy claim
is made from anything below.** D6–D8 are functional observations, not accuracy.

## What the branch adds (everything else is unchanged)
| File | Change |
|---|---|
| `native/package.json` (+ lock) | Stage H/I pinned camera + runtime set: `react-native-vision-camera` 5.2.3, `react-native-nitro-modules` 0.37.1, `react-native-nitro-image` 0.15.2, `react-native-vision-camera-worklets` 5.2.3, `react-native-vision-camera-resizer` 5.2.3, `react-native-worklets` 0.12.2 (peer range RN 0.83–0.87), `onnxruntime-react-native` 1.24.3. ExecuTorch left out (optional; no H2 `.pte` export exists). Lockfile resolved with **no version change** to any existing package. Script `npm run cv:check`. |
| `native/babel.config.js` | `react-native-worklets/plugin` (required by the worklets package; listed last). |
| `AndroidManifest.xml` | `android.permission.CAMERA` + `uses-feature camera required=false`. Requested at run time **only** when the debug flag is on. |
| `native/src/cv/device/` | pure TS: `flags.ts` (`CV_DEBUG_PIPELINE = false`), `permissions.ts`, `pixels.ts` (nitro-image raw formats → RGB, crop, G3 letterbox input), `orientation.ts` (orientation / rotation / mirroring → existing `stillCropPlan`, still box → screen rect), `debugPipeline.ts`, `overlay.ts`, `models.ts` (device paths + sha256). |
| `native/responsive/CvDebugScan.tsx` | debug layer: VisionCamera preview, tap → 3-photo burst → G3 detector on each → frozen id policy (3 agreeing stills, score ≥ 0.5) → tap crop → H2 → `verifyIdentity(FROZEN_VERIFY)` → `stageHDecision(grades off)` → `fromStageH` → **title only** ("Apple. Not graded" / "Unable to identify"). Boxes show a class name only. NSCV log lines. |
| `native/responsive/ScanScreen.tsx` | 4 lines: imports the flag; `require('./CvDebugScan')` only when the flag is true; renders the layer over the preview area. Flag off = the existing Scan screen, unchanged. |
| `native/scripts/g9j5-push-models.ps1` | sha256-checks and pushes the three ONNX files to the phone. |
| `native/tests/cvDevice.test.ts` | 11 tests: flag default off + gating, permissions, pixel formats, letterbox, crop, orientation/rotation/mirroring, coordinate mapping, box rendering, burst id policy, end-to-end with fake models, wiring (pins, CAMERA, model files). |

Not in the debug path: the quality gate, occlusion cues and the condition model (`E_224…onnx`), so the best outcome is
"<name>. Not graded" with reason `quality_gate_not_run_in_debug`. Grades stay blocked everywhere.

## P0 (sandbox, 2026-10-15) — results
| Check | Result |
|---|---|
| `npm ci` in `native/` (network available) | **OK**, 723 packages |
| `check-cv-runtime.ts` | camera ready **yes**, inference runtime ready **yes** (onnxruntime), weights **NOT READY** (weights are pushed to the phone, not the repo) → `RESULT: NOT READY` as expected |
| `tsc -p native/tsconfig.json` (first time possible: native types now installed) | app code incl. `CvDebugScan.tsx` / `ScanScreen.tsx` **0 errors** against the real VisionCamera 5.2.3 / ORT 1.24.3 types; 45 pre-existing errors only in older `tests/*.test.ts` (`readFileSync(new URL…)` typing), not introduced here |
| `npm run export:check` (Metro Android release bundle) | **OK**, 3.3 MB bundle; the debug layer resolves and is compiled, flag inlined as `false` |
| ESLint on changed files | 0 errors (inline-style warnings only, same as existing screens) |
| `node --test` native | 166/166 |
| Gradle build / APK / device run | **not possible in the sandbox** (no Android SDK, no device) → P1 |

## P1 — on your Windows PC with your Android phone
Prerequisites: Node ≥ 22.11, JDK 17, Android Studio (SDK 35+, platform-tools on PATH), USB debugging on the phone. If the build fails
with long paths, run `native/scripts/prepare-windows-ninja.ps1` first (existing helper).

1. Get the branch: `git fetch origin` then `git switch cv-gauntlet-device` (remote branch `cv-gauntlet-device`).
2. `cd native` → `npm ci`.
3. **Locally only**, open `native/src/cv/device/flags.ts` and change `false as boolean` to `true as boolean`. Do not commit this.
4. Phone plugged in: `npx react-native run-android` (debug build). Keep the Metro window open.
5. Unzip `NutriSole_G9J5_device_models.zip` (handoff) into the repo root as `models_g9j5\` and run
   `powershell -ExecutionPolicy Bypass -File native/scripts/g9j5-push-models.ps1 -Dir models_g9j5`
   (checks sha256, pushes to `/sdcard/Android/data/com.muhammadfaizan.nutrisole/files/models/`). "Permission denied" → open the app once, retry.
6. In a second PowerShell: `adb logcat -c` then `adb logcat -v epoch -s ReactNativeJS:* > g9j5_device_log.txt` (stop with Ctrl+C at the end).
7. Open the app → Scan. Allow camera. Wait for "Tap an item" (models loaded). Then:

| # | Do | Expect |
|---|---|---|
| D1 | open Scan with the flag on | camera permission prompt; after allow, live preview; "Tap an item"; log has `NSCV model h2 …` and `NSCV model g3_det …`, no `model_load_failed` |
| D3 | tap an apple in the centre, then near each corner of the screen (portrait) | yellow crop box sits on the tapped spot; `NSCV map tap=…` lines |
| D3b | same in landscape (rotate the phone) | crop still on the tapped spot (`NSCV photo … orientation=…`) |
| D6 | one apple, banana, orange/kinnow, tomato, carrot on a plain table; tap each | "<name>. Not graded" or "Unable to identify"; **never a grade or %** |
| D7 | each item in a clear bag, mesh bag, half covered by a hand | "Not graded" or "Unable to identify" |
| D8 | a printed fruit photo, a cut apple, an unsupported fruit | "Unable to identify" expected |
| D10 | deny the camera permission once (Settings → Apps → NutriSole → Permissions) and reopen Scan | "Open Settings" button, no crash |

8. Set the flag back to `false` (or `git checkout native/src/cv/device/flags.ts`).

## What to send back
`g9j5_device_log.txt`; screenshots of D3, D6, D7, D8; phone model + Android version; output of `npx react-native info`; the full red-screen
or Gradle error text if anything fails (copy from the terminal). From these I can check mapping lines and pipeline errors; D6–D8 are
functional observations only and are not quoted as accuracy.

## Draft PR
A draft PR `cv-gauntlet-device → cv-gauntlet` is acceptable under the existing workflow; it is a review vehicle only (no merge without
your test and go).
