# G9 Stage J6 addendum: Android P1 on `cv-gauntlet-device` (supersedes the P1 steps in G9_stageJ5_ANDROID_P1.md)

Written 2026-10-16 (PKT). Branch `cv-gauntlet-device` only (draft PR #2 into `cv-gauntlet`; never `main`, never deployed).
**Everything measured in the sandbox is host-side.** No phone latency, FPS, memory or accuracy claim is made. A/B/C grades stay disabled.

## 1. What J6 adds on the device branch
| File | Change |
|---|---|
| `native/src/cv/domainMap.ts` (mirrored from `cv-gauntlet`) | canonical CV class ↔ nutrition/price domain map (`citrus` → `citrus_orange`) |
| `native/src/cv/device/instrument.ts` | `inferenceBadge` (REAL INFERENCE vs PLACEHOLDER), `domainOf` (CV → domain via the map), latency recorder (p50/p95/max), JS event-loop lag sampler, host-side model-memory estimate |
| `native/src/cv/device/debugPipeline.ts` | outcome now carries `inference: 'real'` and `domain {cvClass, domainId}` |
| `native/responsive/CvDebugScan.tsx` | visible badge under the DEBUG pill: green **"REAL INFERENCE · G3 + H2 ONNX on this device"** only when both sessions loaded AND the shown title came from the pipeline; otherwise orange **"PLACEHOLDER · no model output (reason)"**. Logs `NSCV stage=init model=… ms=`, `NSCV latency …`, `NSCV ui_lag …`, `NSCV domain …`. Shows `domain=… · nutrition USDA FDC per 100 g · price: no verified source loaded`. |
| `native/scripts/g9j6_host_pipeline.ts` | host harness: the same TS pipeline + same ONNX files through onnxruntime-node on the sandbox CPU |
| `ml/runs/G9/stageJ/scripts/j6_host_parity.py` | Python ONNX init/IO check + Python reference tensors (Ultralytics LetterBox; `camera_io.h2_input`) |
| `native/tests/cvDeviceJ6.test.ts` (6), `native/tests/fixtures/g9j6_preproc_parity.json` | regressions (below) |

## 2. Host-side checks (sandbox, 2026-10-16) — results
| Check | How | Result |
|---|---|---|
| Real RN env | `native/node_modules` | react-native 0.86.3, react-native-vision-camera 5.2.3, react-native-worklets 0.12.2, onnxruntime-react-native 1.24.3 installed (from J5 `npm ci`) |
| Permission handling | `permissions.ts` unit tests | off → nothing requested; not-determined → request / settings; denied → settings; restricted → unavailable (pass) |
| Preview / frame capture interfaces | `pixels.ts` raw formats, size-mismatch refusal; CvDebugScan uses `capturePhoto → toImageAsync → resizeAsync → toRawPixelDataAsync` against the real VC5 / nitro-image types | pass (types: app code 0 tsc errors) |
| G3 + H2 ONNX init | onnxruntime Python 1.31 and onnxruntime-node 1.24.3 load both files (sha256 = `device/models.ts`) | I/O matches `MODEL_IO` exactly: H2 `images [n,3,224,224]` → `probs [n,13]`; G3 `images [1,3,480,480]` → `output0 [1,16,4725]`; 0 errors in `checkModelIO` with real runtime metadata |
| RGB preprocessing parity | TS `detectorInput` / `h2Input` vs Python reference on 16 real stills (J5 unverified training candidates, ≤1280 px) + 3 committed synthetic images | detector tensor max abs diff **0.0051** (tolerance 2/255 = 0.0078; Ultralytics uses cv2 fixed-point bilinear); H2 tensor max abs diff **0** (tol 1e-3); H2 probabilities identical, top-1 16/16; detector class sets at the 0.25 decode floor 13/16 identical (3 differ by 1–2 borderline boxes) |
| Box coordinate mapping, rotation / mirroring, high-res crop | existing `cvDevice.test.ts` + `cvCropMap` / `cvCamera` | pass |
| End-to-end debug pipeline | harness, 16 stills, simulated burst (same still ×3), tap at view centre and at the top G3 box (26 runs) | 2 × "<name>. Not graded" (Citrus, Apple), 24 × "Unable to identify"; 0 display-contract errors; 0 grades/percentages. Functional only: images are unverified, no accuracy claim (consistent with H2's known heavy abstention) |
| Model init + memory | **host-side** | init h2 71 ms / g3 29 ms (onnxruntime-node); RSS +36 MB after init, 168 MB after 26 runs; static estimate weights + I/O buffers ≈ 20 MB |
| Latency hooks | **host-side, 2 vCPU** | G3 per still p50 45 ms (p95 135), H2 per crop p50 4.5 ms (p95 12), pipeline (3 stills + crop) p50 158 ms (p95 355). Phones will differ: measure on the phone |
| Gradle debug build | — | **not feasible in the sandbox**: no JDK/Android SDK/NDK installed, background processes do not survive between commands (checked), every command is capped at 120 s, 2 vCPU / 7 GB RAM; RN 0.86 New Architecture compiles VisionCamera/Nitro/worklets/ORT C++ with NDK 27 (tens of minutes). Build on your PC (below). |
| Metro Android bundle | `react-native bundle` | J5: OK (3.3 MB). J6 re-run timed out twice at the 120 s cap (cold cache); not re-verified this run. Only new pure-TS modules were added. |

## 3. P1 on your Windows PC + Android phone (exact steps)
**Versions:** Node **22.11 or newer** (LTS 22.x), **JDK 17** (Temurin 17; Gradle 9.3.1 + AGP 8.12 need JDK 17+), Android Studio with
**SDK Platform 36**, **Build-Tools 36.0.0**, **NDK 27.1.12297006**, **CMake 3.22.1**, Platform-Tools (adb). App id `com.muhammadfaizan.nutrisole`, minSdk 24.

1. **Phone:** Settings → About phone → tap *Build number* 7× → Developer options → **USB debugging ON** (Xiaomi: also *Install via USB* and
   *USB debugging (Security settings)*). Plug in by USB, accept the "Allow USB debugging?" prompt. `adb devices` must show `device`.
2. **PC env (PowerShell):**
   ```
   node -v ; java -version ; adb version
   $env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-17<...>"   # your JDK 17 path
   $env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
   ```
3. **Code:** `git fetch origin` → `git switch cv-gauntlet-device` → `git pull` → `cd native` → `npm ci`.
   Long-path errors: run `powershell -ExecutionPolicy Bypass -File scripts/prepare-windows-ninja.ps1` once.
4. **Flip the debug flag (locally only):** in `native/src/cv/device/flags.ts` change `false as boolean` → `true as boolean`. Never commit it.
5. **Build + install:** `npx react-native run-android` (debug). Keep Metro open. Then `adb shell dumpsys meminfo com.muhammadfaizan.nutrisole > mem_0_launch.txt`.
6. **Push models (hash-checked):** unzip `NutriSole_G9J5_device_models.zip` into the repo root as `models_g9j5\`, then from the repo root
   `powershell -ExecutionPolicy Bypass -File native/scripts/g9j5-push-models.ps1 -Dir models_g9j5`. It refuses any sha256 mismatch.
   "Permission denied": open the app once, close it, run again.
7. **Log:** second PowerShell: `adb logcat -c` then `adb logcat -v epoch -s ReactNativeJS:* > g9j6_device_log.txt`.
8. **Run:** open the app → Scan → allow camera. Badge must read **PLACEHOLDER · no model output (loading models)** until
   "Tap an item", then `adb shell dumpsys meminfo com.muhammadfaizan.nutrisole > mem_1_models_loaded.txt`.
9. **Test table** (start a screen recording first: `adb shell screenrecord --time-limit 170 /sdcard/g9j6.mp4`, repeat if needed):

| # | Do | Expect |
|---|---|---|
| D1 | open Scan | permission prompt → preview → "Tap an item"; log `NSCV stage=init model=h2 ms=…`, `model=g3_det`, no `model_load_failed` |
| D2 | tap an apple | badge turns green **REAL INFERENCE** only after a result; title "<name>. Not graded" or "Unable to identify"; `NSCV latency tap_to_result_ms=…` |
| D3 | tap centre + near each corner (portrait), then landscape | yellow crop box on the tapped spot; `NSCV map …`, `NSCV photo … orientation=…` |
| D6 | apple, banana, orange/kinnow, tomato, carrot on a plain table, 2 taps each | never a grade or %; orange shows `domain=citrus_orange · nutrition USDA FDC per 100 g · price: no verified source loaded` |
| D7 | each item in a clear bag, mesh bag, half hidden by a hand | "Not graded" or "Unable to identify" |
| D8 | printed fruit photo, cut apple, persimmon / unsupported fruit | "Unable to identify" expected |
| D9 | 10 more taps in a row | then `adb shell dumpsys meminfo com.muhammadfaizan.nutrisole > mem_2_after_taps.txt` |
| D10 | deny camera in Settings → reopen Scan | "Open Settings", badge PLACEHOLDER, no crash |

10. `adb pull /sdcard/g9j6.mp4` ; Ctrl+C the logcat; set the flag back (`git checkout native/src/cv/device/flags.ts`).

**What to measure (from the log, not by eye):** init ms per model (`NSCV stage=init`), per-still detector and per-crop H2 ms
(`NSCV stage=det|h2 ms=`, `NSCV latency span=infer_* p50/p95`), tap-to-result ms, UI lag (`NSCV ui_lag p95`), memory (TOTAL PSS / Native Heap
in the three `mem_*.txt`).

**Send back:** `g9j6_device_log.txt`, `mem_0_launch.txt`, `mem_1_models_loaded.txt`, `mem_2_after_taps.txt`, `g9j6.mp4` (or your own screen
recording), screenshots of D2, D3, D6, D7, D8, D10, phone model + Android version, `npx react-native info`, and the full Gradle/red-screen
text if anything fails. Results become phone numbers only after I parse these; D6–D8 stay functional observations, not accuracy.
