# Android runtime spike (week-1 P0-Camera) — steps for the user's PC

Status: **NOT RUN** (the G1 sandbox has no Android SDK, JDK, emulator, KVM, webcam or phone).
Everything below is a written procedure; nothing in it is verified yet. When you run it,
record the results in `docs/cv/gauntlet/G2.md` and tick the proof levels in
`docs/cv/DASHBOARD.md` (2 = camera operational, 3 = inference operational; an emulator run is
"emulator-verified", never "real-time validated").

## 0. Versions checked on npm (2026-10-12, registry metadata only)

| package | latest | peer deps that matter |
|---|---|---|
| react-native-vision-camera | 5.2.3 | react-native-nitro-modules, react-native-nitro-image |
| react-native-vision-camera-resizer | 5.2.3 | vision-camera, nitro-modules |
| react-native-nitro-modules | 0.37.1 | |
| react-native-nitro-image | 0.15.2 | |
| react-native-worklets | 0.13.0 (RN 0.86-0.88); **0.12.2 (RN 0.83-0.87)** | |
| react-native-executorch | 0.10.5 | **react-native-worklets >=0.10.0 <0.13.0**, react-native-blob-util ^0.24.0, @kesha-antonov/react-native-background-downloader >=4.4.0 |
| react-native-fast-tflite | 3.0.1 | nitro-modules |
| onnxruntime-react-native | 1.24.3 | |

Consequence: pin **react-native-worklets@0.12.2** (the only line that satisfies both RN 0.86.3
and react-native-executorch 0.10.5). Re-check before installing; versions move weekly.

## 1. Branch and baseline

```bash
cd nutrisole-frontend
git checkout -b cv/g2-android-spike
npm ci && (cd native && npm ci)
npm test && npm run test:expansion && npm run check:runtime && npm run build
(cd native && npm test && npm run typecheck && npm run lint)
cd native/android && ./gradlew :app:assembleRelease   # Windows: gradlew.bat; run scripts/prepare-windows-ninja.ps1 first
```
All must be green before adding anything.

## 2. Install the camera + runtime (primary stack: ExecuTorch)

```bash
cd native
npm i react-native-vision-camera@5.2.3 react-native-nitro-modules@0.37.1 react-native-nitro-image@0.15.2 \
      react-native-vision-camera-resizer@5.2.3 react-native-worklets@0.12.2 \
      react-native-executorch@0.10.5 react-native-blob-util@^0.24.0 @kesha-antonov/react-native-background-downloader@^4.4.0
```
- `native/babel.config.js`: add `'react-native-worklets/plugin'` as the LAST plugin.
- `native/android/build.gradle`: raise `minSdkVersion` from 24 to **26** (ExecuTorch states Android 13+/minSdk 26+; confirm in its README). Document the excluded devices (Android 7.0–7.1 phones) in Techspec.md.
- `native/android/app/src/main/AndroidManifest.xml`: `<uses-permission android:name="android.permission.CAMERA" />`.
- iOS (macOS only, later): `NSCameraUsageDescription` in Info.plist.
- Do NOT add Expo packages (native/AGENTS.md).

Fallback stack if a custom .pte will not load within ~2 days: `react-native-fast-tflite@3.0.1` with the
LiteRT export (`model.export(format="litert")` — G1 export status in `ml/models/G1/model_manifest.json`),
or `onnxruntime-react-native@1.24.3` with the ONNX export.

## 3. Models to bundle

From `ml/models/G1/model_manifest.json` (sha256, IO contract, class order). Copy the chosen files to
`native/android/app/src/main/assets/models/` (and the iOS bundle later); verify sha256 at app start
(`native/src/cv/models/` manifest) and refuse to run on mismatch or unknown class order.
- detector: YOLO26n 320 end-to-end export → output `(1, 300, 6)` = x1,y1,x2,y2,score,class in
  model-input pixels (letterbox). Decode with `native/src/cv/pipeline/postprocess.ts:decodeEndToEnd`.
- quality classifier: yolo26n-cls 192 → softmax probs `(1, 2)` [fresh, rotten]; apply the
  temperature from the manifest: `p_i ∝ p_i^(1/T)`.

## 4. Minimal frame loop (worklet)

```ts
const frameOutput = useFrameOutput({ pixelFormat: 'yuv', dropFramesWhileBusy: true, onFrame(frame) {
  'worklet';
  const rgb = resize(frame, { width: 320, height: 320, scaleMode: 'contain' /* = letterbox */, pixelFormat: 'rgb', dataType: 'uint8' });
  try {
    const out = detector.forward(toChwFloat(rgb, 320, 320));           // Float32Array (1*300*6)
    const dets = decodeEndToEnd(out, 300, 0.35).map(d => mapToFrame(d)); // dstToSrc with the SAME transform
    scheduleOnRN(onDetections, dets, frame.timestamp);
  } finally { rgb.dispose?.(); frame.dispose?.(); }
}});
```
- The G1 model was trained/evaluated with **letterbox** at 320, not cover at 384. If the resizer only
  offers cover, map boxes back with `computeTransform(..., 'cover')` and expect lost edges; rerun the
  gauntlet with cover before trusting it.
- Use `IouTracker` (`native/src/cv/pipeline/tracker.ts`) on the RN side; grade a track only when
  `stable === true`, max 3 per frame, re-grade at most once per second (same as the gauntlet).
- Map boxes to the preview with `srcToScreen(box, frameW, frameH, viewW, viewH, 'cover')` after
  `rotateBoxNormalized` for the sensor orientation. Unit tests already cover portrait/landscape and
  20:9 / tablet sizes.

## 5. Emulator camera with a video / webcam (emulator-verified only)

1. Android Studio → Device Manager → create a Pixel (API 34, x86_64) AVD.
2. AVD → Edit → Advanced → Camera Back: **VirtualScene** (lets you load an image into the scene) or
   **Webcam0** (your PC webcam). Command-line equivalent:
   `emulator -avd Pixel_API_34 -camera-back webcam0` (list cams: `emulator -webcam-list`).
3. To feed the G1 regression clips: play `ml/runs/G1/clips/*_clip.mp4` full-screen on the PC and point
   a webcam at it, or use a virtual-webcam tool (e.g. OBS Virtual Camera → appears as a webcam) and
   pick it with `-camera-back webcam1`.
4. Build and install the release APK (`./gradlew :app:assembleRelease`, `adb install -r app-release.apk`),
   open Scan, grant camera permission, and record the screen: `adb shell screenrecord /sdcard/g2.mp4`.
5. Log per-frame timing from the worklet (`frame.timestamp`, inference ms) with
   `adb logcat -s ReactNativeJS` and save it to `ml/runs/G2/emulator/`.

## 6. Physical phone (real-time validation, proof level 5)

`adb devices`, install the same APK, run 10-minute continuous scans, record `adb shell dumpsys gfxinfo`,
thermal state (`adb shell dumpsys thermalservice`), and the JS-side latency log. Target section 4 of
the master prompt (detector p50 ≤ 40 ms / p90 ≤ 70 ms, ≥ 15 det FPS, preview ≥ 24 FPS).
