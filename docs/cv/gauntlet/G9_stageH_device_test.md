# G9 Stage H: dependency review and Android device test plan (P5)

**Nothing in this file has been run on a device.** The sandbox has no adb, Android SDK, KVM or phone. **No FPS, camera latency, thermal
or battery number is claimed.** An emulator run only checks that things work; it never gives a phone FPS number. This file extends
`G9_stageG_device_test.md` (D1-D10) with the Stage H steps.

## 1. Dependency review (npm registry metadata, checked 2026-10-14; nothing installed, `native/package.json` unchanged)

The app is on **react-native 0.86.3 / react 19.2.3**. None of the camera or runtime packages are in `native/package.json`. The Stage H
TS modules (`verify.ts`, `closeup.ts`, `display.ts`) are pure TS and need none of them for tests.

| Package | Latest | Declared peers | RN 0.86.3 | Use |
|---|---|---|---|---|
| react-native-vision-camera | 5.2.3 (2026-08-20) | react-native-nitro-modules, react-native-nitro-image (both `*`) | No declared RN range (Nitro-based v5); **unverified until a build** | camera + frame processors |
| react-native-vision-camera-worklets | 5.2.3 | react-native-worklets `*`, nitro-modules, vision-camera | as above | frame-processor worklets for VC5 |
| react-native-vision-camera-resizer | 5.2.3 | nitro-modules, vision-camera | as above | GPU resize / letterbox to 480 and 224 |
| vision-camera-resize-plugin | 3.2.0 | vision-camera **>=4.0.1**, **react-native-worklets-core** >=1.2.0 | | **Do not use with VC5**: built for VC4 + worklets-core, a second worklet runtime |
| react-native-nitro-modules | 0.37.1 | none | `*` | required by VC5 |
| react-native-nitro-image | 0.15.2 | nitro-modules | `*` | required by VC5 |
| react-native-worklets | 0.13.0 needs RN **0.86-0.88**; **0.12.2 needs RN 0.83-0.87** | @babel/core, @react-native/metro-config | both cover 0.86.3 | **Pin 0.12.2**: executorch 0.10.5 requires `>=0.10.0 <0.13.0` |
| react-native-executorch | 0.10.5 | react-native-worklets `>=0.10.0 <0.13.0`, react-native-blob-util `^0.24.0`, @kesha-antonov/react-native-background-downloader `>=4.4.0` | no RN range | primary runtime (.pte models) |
| react-native-blob-util | 0.25.1 latest; **0.24.12** latest 0.24.x | none | `*` | **pin 0.24.12** (0.25 is outside executorch's `^0.24.0`) |
| @kesha-antonov/react-native-background-downloader | 4.6.3 | react-native >=0.57.0 | ok | executorch model download |
| onnxruntime-react-native | 1.24.3 | none | no RN range | fallback runtime; runs the same .onnx files as the sandbox, including H2 `h2_mnv3s.onnx` |
| react-native-fast-tflite | 3.0.1 | nitro-modules | `*` | alternative fallback (needs .tflite exports, not produced yet) |
| react-native-fast-opencv | 1.0.1 | none | `*` | **only needed if the occlusion cues run on the phone** (GrabCut, contours, convex hull). Stage H's accepted occlusion evidence uses H2 half-crops instead, so this is optional |

**Install steps (on the PC, in a spike branch, never on `main`).** Follow `docs/cv/android-spike.md` sections 1-3, with these Stage H pins:
```bash
cd native
npm i react-native-vision-camera@5.2.3 react-native-nitro-modules@0.37.1 react-native-nitro-image@0.15.2 \
      react-native-vision-camera-worklets@5.2.3 react-native-vision-camera-resizer@5.2.3 react-native-worklets@0.12.2
# runtime A (primary)
npm i react-native-executorch@0.10.5 react-native-blob-util@0.24.12 @kesha-antonov/react-native-background-downloader@4.6.3
# runtime B (fallback, same ONNX files as the sandbox)
npm i onnxruntime-react-native@1.24.3
# babel.config.js: add 'react-native-worklets/plugin' LAST; android/gradle.properties: minSdkVersion 26 (to be confirmed by the build)
cd android && ./gradlew clean assembleDebug
```
Risks to check in that build:
- VC5 and executorch both declare `react-native: *`, so the first Gradle / CMake build is the real compatibility test on RN 0.86.3.
- The worklets Babel plugin must be loaded only once (reanimated is not in the app today).
- The New Architecture must stay enabled (Nitro requires it).

## 2. Models the phone must load
| Model | File | Input -> output | Status |
|---|---|---|---|
| G3 detector (unchanged) | `det_yolo11n_640_raw.onnx` (imgsz 480) | (1,3,480,480) -> (1,16,4725) | Stage G |
| E224 condition | `E_224_e15_b64_sgd01.onnx` | (1,3,224,224) -> (1,2) | Stage G (grades not displayed) |
| **H2 close-up identity** | `h2_mnv3s.onnx` (MobileNetV3-S, 13 classes) | (N,3,224,224) RGB, ImageNet mean/std, softmax -> (N,13) | **new in Stage H**; ONNX FP32; .pte export not done |

## 3. Wiring changes vs Stage G (order in the frame processor / on tap)
1. Wide scan as Stage G (G3 -> tracker -> `idPolicy`). Show the name + `categoryPrice` only when identified, as before.
2. **On tap (close-up):** `cropRect` on the full-resolution frame (or a `takePhoto` still) -> resize short side 256, centre 224 -> **H2** ->
   `verifyIdentity(wide, h1, h2Probs, FROZEN_VERIFY)` (`verify.ts`). H1 (G3 on the crop) is only needed if the frozen policy is P-b.
3. If `unable`: show **"Unable to identify"**, plus the user-confirm sheet with `suggestions` ("Is this an apple / a tomato / something
   else?"). `userConfirm` -> category price only, labelled "Category confirmed by you". Never a grade.
4. If `verified`: H2 on the 4 half-crops -> `partAgreement` -> `occlusionReasons({...cues, partAgree}, FROZEN_OCC)`. The mask cues are
   optional on the phone (they need OpenCV). Then the Stage G `qualityReasons` + `GradeGate`, then `stageHDecision(..., gradeDisplayEnabled=false)`.
5. Display only through `closeupDisplay` (`display.ts`): **no A/B/C and no grade-specific price**; category line only for a verified (or
   user-confirmed, labelled) identity with a current official list.

## 4. New device tests (in addition to D1-D10)
| # | Test | Where | How | Pass |
|---|---|---|---|---|
| H1 | Unit + parity | PC | `cd native && npm test` (includes `cvVerify.test.ts`), `python -m pytest ml/eval/test_closeup.py ml/eval/test_verify.py` | all pass |
| H2 | H2 model load | emulator or phone | load `h2_mnv3s.onnx` with onnxruntime-react-native; log input/output shapes and load ms | (1,3,224,224) -> (1,13); no crash |
| H3 | H2 parity on device | phone | run H2 on the 10 fixture crops in `ml/runs/G9/stageH/out/device_parity/` (PNG + expected probs) | max abs prob diff <= 0.02 |
| H4 | Wrong-ID block | phone | point at a persimmon / plum / peach / papaya / kiwi / avocado; at a printed fruit poster; at a cut apple | "Unable to identify" or user-confirm sheet; never a name + grade |
| H5 | Occlusion | phone | apple half covered by a hand, by a plastic bag, by a second fruit; apple 40% out of frame | "Not graded" with a reason; never a grade |
| H6 | User-confirm fallback | phone | tap an item that gives "Unable to identify"; choose a suggestion; then choose "something else" | category line labelled "confirmed by you"; no grade; "something else" -> no price |
| H7 | Close-up latency (phone only) | phone | logcat `NSCV stage=h2|parts|occl ms=` over 3 min | report p50/p95; first real number for H2 on a phone |

Script: `native/scripts/g9h-device-check.ps1` (runs H1, checks adb, records the NSCV lines for D2-D9 + H2-H7, and summarises
p50/p95 per stage and the event counts, including `unable`, `user_confirmed` and `not_graded`).
