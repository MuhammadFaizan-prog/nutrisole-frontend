# NutriSole G9 Stage J4: first physical Android phone test (camera + close-up pipeline, proposal Figure 7.2)

Written 2026-10-15 (PKT). **Nothing here has run on a phone** (the sandbox has no adb, SDK or device). This runbook prepares the first
test on the user's Windows PC + Android phone. It measures **whether the pipeline runs and maps coordinates correctly**. It makes **no
accuracy claim**, enables **no grade**, and every result screen must say *Unable to identify* or *Not graded*.

Figure 7.2 flow being exercised: wide scan → tap an item → full-resolution close-up crop → identity check (H2, explicit unknown) →
occlusion / quality gate → result **without** a grade (`result.ts`: states `unknown`, `not_graded`, `poor_capture`; no graded state).

## 0. What exists now (cv-gauntlet)
| Piece | File | Tested in sandbox |
|---|---|---|
| tap → frame → still → crop geometry | `native/src/cv/pipeline/camera.ts`, `cropmap.ts` | parity + J4 crop-mapping tests |
| identity verify / occlusion / Stage H decision | `verify.ts`, `closeup.ts` | parity tests |
| explicit Unknown / Not graded result | `native/src/cv/pipeline/result.ts` | `cvResult.test.ts` |
| runtime presence check | `native/scripts/check-cv-runtime.ts` | `cvRuntimeCheck.test.ts` (today: **NOT READY**, no camera/inference package, no weights, no CAMERA permission) |
| debug flag + NSCV log lines | `native/src/cv/debug.ts` (`setCvDebug(true)`) | `cvDebug.test.ts` (lines match `g9i-device-check.ps1`) |
| phone-test script | `native/scripts/g9i-device-check.ps1` | not runnable in sandbox |

**Not done (needs the user's go, on a separate device branch, never main):** installing the camera/inference packages, adding the
CAMERA permission, copying model weights into the APK, and a debug-only camera test screen that calls the pipeline. The live Scan screen
stays the demo (labelled *Demo data*).

## P0. Today, no new dependency (about 30 minutes)
PowerShell, repo root, `cv-gauntlet` checked out, phone with **USB debugging** on (Settings → About phone → tap *Build number* 7× →
Developer options → USB debugging), Android platform-tools installed (`adb` on PATH):
```powershell
cd $HOME\nutrisole-frontend; git switch cv-gauntlet; git pull
cd native; npm ci; npm test                                   # expect 149 passing
node --experimental-strip-types scripts/check-cv-runtime.ts   # expect "RESULT: NOT READY" with the MISSING list
adb devices                                                   # phone listed as "device"
powershell -ExecutionPolicy Bypass -File scripts/prepare-windows-ninja.ps1   # first build only
cd android; .\gradlew.bat :app:assembleRelease --max-workers=2 --console=plain
adb install -r app\build\outputs\apk\release\app-release.apk
cd ..\..; powershell -ExecutionPolicy Bypass -File native/scripts/g9i-device-check.ps1 -Minutes 2
```
On the phone, open NutriSole → Scan. **Record** (screenshots): the scan banner shows *Demo data · not a model result* (no %), the
assessment screen shows *Not graded · Demo data* and no letter grade, the market screen shows *Not graded · Demo data*. Note the phone
model, Android version and ABI printed by the script.

## P1. After the user approves a device branch (first real camera run)
1. `git switch -c device/g9-camera cv-gauntlet` (never main; nothing merged or deployed).
2. Install the pinned set (`G9_stageH_device_test.md` §2): VisionCamera 5.2.3 family, worklets 0.12.2, `onnxruntime-react-native@1.24.3`
   (ExecuTorch optional; H2 `.pte` export not done). Add `<uses-permission android:name="android.permission.CAMERA" />`.
3. Copy `h2_mnv3s.onnx`, `det_yolo11n_640_raw.onnx`, `E_224_e15_b64_sgd01.onnx` into `native/android/app/src/main/assets/models/`
   (not committed). Re-run `check-cv-runtime.ts` until it prints `RESULT: runtime prerequisites present` (this is not an accuracy result).
4. Debug-only test screen (agent can write it on the device branch once approved): camera preview → tap → `stillCropPlan` →
   `takePhoto` → crop → `h2Input` → H2 → `verifyIdentity(..., FROZEN_VERIFY)` → `stageHDecision(..., gradeDisplayEnabled=false)` →
   `fromStageH` → screen shows `title` only. At start-up: `if (__DEV__) setCvDebug(true)`; log `nscvMapLine`, `nscvStageLine`,
   `nscvResultLine`, and `checkModelIO('h2', meta)` after model load.
5. Run `g9i-device-check.ps1 -Minutes 3` while doing the tests below.

| # | Test | Do | Record | Pass |
|---|---|---|---|---|
| D1 | Model load | open the test screen | `checkModelIO` output | `[]`, no crash |
| D2 | Parity | in-app parity screen (bundle pushed by the script) | `NSCV parity file=… maxdiff=…` | every maxdiff ≤ 0.02 |
| D3 | Tap mapping, back camera | sheet with 5 dots; tap centre + 4 corners, portrait and landscape | `NSCV map …` lines + saved crops | every crop contains its dot |
| D4 | Tap mapping, front camera | same | same | mirrored correctly |
| D5 | Frame vs still | ruler; compare preview box with the still region | screenshot pair | offset ≤ 2 % of the still side |
| D6 | Showcase items | one apple, banana, orange/kinnow, tomato, carrot on a plain table | screenshot + `NSCV event=result` | screen shows a name + *Not graded*, or *Unable to identify*; **never a grade or %** |
| D7 | Hard conditions | each item in a clear bag, a mesh bag, half covered by a hand, 30 % outside the frame | screenshots | *Not graded* with a reason, or *Unable to identify* |
| D8 | Unsupported | kiwi/peach/papaya, a printed fruit photo, a cut apple | screenshots | *Unable to identify* or the user-confirm sheet |
| D9 | Timing (phone only) | normal use for 3 min | `NSCV stage=… ms=` | report p50/p95 only as "first phone timing" |

Send `g9i_device_log.txt`, `g9i_device_log.csv` and the screenshots. D6–D8 are **functional observations**, not accuracy: they use a
handful of items, no human-verified ground truth, and M-TEST stays sealed. No identity percentage may be quoted from them.
