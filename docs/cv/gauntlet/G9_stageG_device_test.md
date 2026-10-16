# G9 Stage G: emulator / device test plan (for the user's PC)

**Nothing in this file has been run.** The sandbox has 2 vCPU, no GPU, no /dev/kvm, no adb, no Android SDK and no phone. **FPS, camera
latency, thermals and battery are not measured in Stage G.** An emulator run checks function only (it never gives phone FPS).

**Repo state that limits what can be tested today:** the camera / inference stack is still *planned, not installed*
(`Techspec.md` line 11: react-native-vision-camera 5.2.3 + vision-camera-resizer + worklets 0.12.2 + react-native-executorch 0.10.5,
fallback onnxruntime-react-native 1.24.3; procedure `docs/cv/android-spike.md`). `native/package.json` has none of these packages, so
there is no VisionCamera frame processor to wire yet. Stage G delivers the pure-TS pieces the frame processor will call
(`native/src/cv/pipeline/closeup.ts`, `native/src/cv/prices/display.ts`) with unit/parity tests, plus this plan.

## Wiring (what the frame processor must do, in order)
1. VisionCamera `useFrameProcessor` at the camera's full resolution (record `frame.width`, `frame.height`, `orientation`).
2. Resizer plugin: letterbox the frame to 480 x 480 RGB float32 (pad 114) -> G3 (`det_yolo11n_640_raw`, imgsz 480; .pte for
   executorch or .onnx for onnxruntime-react-native). Decode `decodeRawWithNms` (conf 0.35, NMS 0.7), then `sceneGuard` (1% area).
3. Map every box to frame pixels with `detectorToFrame(box, frame.width, frame.height)` (closeup.ts). Rotate for display with
   `rotateBoxNormalized` and draw with `srcToScreen` (preprocess.ts).
4. `IouTracker.update` -> `idPolicy(label, score, hits)` -> show name + `categoryPrice(...)` only when `identified`;
   otherwise "Unable to identify".
5. On tap: `roiFromTap(tap, W, H, trackedBoxes)`. If `source === 'tap_roi'` (tracking fragmented) take a full-resolution
   still (`camera.takePhoto()`), re-run detection on the still and use the ROI there (high-res still fallback).
6. Close-up: `cropRect(box, W, H)` on the **full-resolution** frame or still -> analysis copy at <= `ANALYSIS_MAX_SIDE` (256) ->
   condition (E224), ripeness chip, measurements, `grade()` (rules.ts) -> `qualityReasons(q, FROZEN_GATE)` (+ `blockiness` for stills)
   -> `GradeGate.push` (5 Hz, every 3rd frame at 15 fps) -> `gateMessage` + `gradedPrice(...)`.
7. Persist only through `toCvAssessment(...)` -> `validateCvAssessment` (contracts.ts). No Supabase table or CV API exists in the
   repo today; do not add one without a schema review.

## Tests on the PC
| # | Test | Where | How | Pass |
|---|---|---|---|---|
| D1 | Unit + parity tests | PC, no phone | `cd native && npm test` (node --test) and `python -m pytest ml/eval/test_closeup.py ml/prices/tests` | all pass (sandbox: 104/104 TS, see report) |
| D2 | Model loading | emulator (function only) or phone | dev build with the spike packages; load G3 480 + E224 + ripeness from assets; log load time and input/output shapes | shapes (1,3,480,480)->(1,16,4725); (1,3,224,224)->(1,2); no crash |
| D3 | Coordinate mapping | emulator camera = virtual scene or webcam; phone | point at a printed checkerboard with 4 corner markers; tap each marker; log `detectorToFrame` + `srcToScreen` boxes in portrait and landscape | overlay within 2% of frame width of the marker |
| D4 | High-res crop extraction | phone | tap an item; save the native crop PNG (debug flag) and log `cropRect.sidePx` vs the on-screen box | crop contains the item; sidePx matches box x frame scale |
| D5 | Move-closer gate | phone | apple on a table, start at 2 m, walk in; log first `identified`, first `graded` / `Not graded` reason | "Move closer" until >= 96 px; grade only after 3 agreeing assessments |
| D6 | ROI + still fallback | phone | pile of 10+ tomatoes (tracking fragments); tap one | still captured, ROI result shown or a clear refusal; no crash |
| D7 | Refusals | phone | printed fruit poster, persimmon or kiwi, cut fruit, dark room, item half out of frame | "Unable to identify" or "Not graded"; never a grade |
| D8 | Price line | phone, offline + online | identified apple with today's list loaded; then a list older than 2 days | source, date, Lahore, per kg shown; stale list -> no price |
| D9 | Latency / FPS (phone only) | phone | perf overlay or logcat timings for 3 min | report p50/p95 per stage; this is the first real FPS number |
| D10 | Protected features | phone | open nutrition, glucose, diet/exercise, footwear, assistant screens | unchanged behaviour |

Script: `native/scripts/g9g-device-check.ps1` runs D1, checks adb / device, captures logcat lines tagged `NSCV` for D2-D9 into a CSV.
