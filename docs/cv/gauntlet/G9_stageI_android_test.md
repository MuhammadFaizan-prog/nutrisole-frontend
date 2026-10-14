# G9 Stage I: Android camera-inference readiness and test instructions (I4)

**Status:** integration layer and tests are written and pass in the sandbox. **Nothing has run on a phone or emulator** (the sandbox
has no adb, Android SDK or KVM). **No FPS or phone-latency figure is claimed.** No dependency was added to `native/package.json`.

## 1. Runtime dependencies (unchanged from the Stage H review)
Use exactly the set reviewed in `G9_stageH_device_test.md` §1-2. In short:

| Role | Package (pinned) | Note |
|---|---|---|
| Camera + frame processors | react-native-vision-camera 5.2.3 + nitro-modules 0.37.1 + nitro-image 0.15.2 + vision-camera-worklets 5.2.3 | VC5 declares no RN range: the first Gradle build is the real test on RN 0.86.3 |
| GPU resize / letterbox | react-native-vision-camera-resizer 5.2.3 | **not** vision-camera-resize-plugin (VC4 + worklets-core) |
| Worklets | react-native-worklets **0.12.2** | executorch 0.10.5 needs `>=0.10.0 <0.13.0`; Babel plugin loaded once, last |
| Primary runtime | react-native-executorch 0.10.5 + react-native-blob-util **0.24.12** + @kesha-antonov/react-native-background-downloader 4.6.3 | `.pte` export of H2 **not done yet** |
| Fallback runtime | onnxruntime-react-native 1.24.3 | runs the same `.onnx` files as the sandbox, including `h2_mnv3s.onnx` |

Install commands are in `G9_stageH_device_test.md` §2. They are for a device branch only, after review; Stage I did not run them.

## 2. What Stage I adds (pure TypeScript, no deps): `native/src/cv/pipeline/camera.ts`
Mirror of `ml/eval/camera_io.py`; parity test `native/tests/cvCamera.test.ts` replays `ml/eval/fixtures/camera_parity.json`.

| Function | What it does | Tested by |
|---|---|---|
| `tapToFrame(tap, viewW, viewH, frameW, frameH, rotation, mirrored, mode)` | preview tap (points) → normalised analysis-frame point in sensor orientation. Undoes `cover` / `letterbox` scaling, front-camera mirroring and the clockwise sensor rotation (0/90/180/270). Returns `null` on a letterbox bar | 60 Python cases + inverse-rotation test |
| `frameToStillBox(box, frameW, frameH, stillW, stillH, sensorAspect?)` | analysis-frame box → full-resolution still box. Assumes both are centre crops of one sensor FOV (e.g. 16:9 video inside a 4:3 still) | fixed 16:9→4:3 case + 40 plans |
| `identityCrop(box, W, H, mode)` | `stageH` (default, frozen) = Stage G `cropRect` pad 0.08; `square` = Stage I candidate square-context crop (**not frozen**) | 80 cases; `stageH` checked equal to `cropRect` |
| `stillCropPlan(tap, view, frame, still, boxes, …)` | the whole chain: tap → frame → `roiFromTap` → still box → identity crop on the **still** (the high-res crop) | 40 Python cases |
| `h2Input(rgb, w, h, mode)` | RGB uint8 crop → float32 NCHW (1,3,224,224), ImageNet mean/std; `stageH` = short side 256 + centre 224 | 6 synthetic crops (sampled values + sum) |
| `checkModelIO(name, meta)` | compares tensor metadata read from ONNX Runtime / ExecuTorch with the contract | real metadata of H2, G3 detector, condition model |

**Model I/O contract** (`MODEL_IO`; verified against the real ONNX files):
- H2 `h2_mnv3s.onnx`: input `images` [n,3,224,224] float32 RGB, ImageNet mean/std → output `probs` [n,13], already softmaxed
  (index 12 = unknown).
- G3 detector `det_yolo11n_640_raw.onnx`: [1,3,480,480] float32, /255, letterbox 114 → [1,16,4725].
- Condition `E_224_e15_b64_sgd01.onnx`: [1,3,224,224] → [1,2] (grades not displayed).
- An ExecuTorch `.pte` export must keep the same shapes. `checkModelIO` is meant to run right after model load on the device.

**Device resize caveat (measured in the sandbox):** the pure-bilinear device path (`h2Input`, with integer box pre-reduction when
downscaling ≥ 2×) gives the same H2 decision as the Stage H cv2 path on **370/378** audit crops (max |Δp| 0.18,
`ml/runs/G9/stageI/out/camera_h2_agreement.json`). Training used PIL antialiased resize. So whatever resizer the phone uses
(VC5 resizer or the JS fallback) must pass parity test A3 before any identity number from a phone is trusted.

## 3. Close-up flow on the phone (unchanged decisions)
1. Scan stream (VC5 frame processor): G3 at 480 → tracker → wide id policy (Stage G).
2. User tap → `stillCropPlan(...)` with the analysis-frame boxes → `takePhoto()` still → crop the still at `plan.crop` (Stage H: 'stageH').
3. `h2Input` → H2 → `verifyIdentity(wide, null, probs, FROZEN_VERIFY)` → occlusion (`occlusionReasons(..., FROZEN_OCC)`; the mask cues need
   OpenCV and stay optional on the phone) → Stage G gate → `stageHDecision(..., gradeDisplayEnabled=false)` → `closeupDisplay`.
4. **No A/B/C and no grade-specific price.** Category reference price only for a verified or user-confirmed (labelled) identity.

## 4. Android tests (run on the user's PC with an emulator or phone)
Script: `native/scripts/g9i-device-check.ps1` (Windows) or `native/scripts/g9i-device-check.sh` (Linux/macOS). It runs A1, records
device facts, pushes the parity bundle and summarises the `NSCV` logcat lines.

| # | Test | Where | How | Pass |
|---|---|---|---|---|
| A1 | Unit + parity | PC | `cd native && npm test`; `python -m pytest ml/eval/test_camera_io.py ml/eval/test_verify.py ml/eval/test_closeup.py` | all pass (TS 122, py incl. 13 camera/audit tests) |
| A2 | Build + model load | emulator or phone | debug build with the §1 set; load H2 with onnxruntime-react-native; log `checkModelIO('h2', meta)` | build succeeds; `[]` (no mismatch); no crash |
| A3 | H2 input + output parity | emulator or phone | the in-app parity screen reads `/sdcard/Download/nscv_parity/p00-p11.png`, runs `h2Input` + H2, logs `NSCV parity file=pNN.png maxdiff=x` against `expected.json` `probs_device_path` | every maxdiff ≤ 0.02 |
| A4 | Tap mapping, back camera | phone | portrait and landscape; tap the centre and the 4 corners of a sheet of paper with 5 dots; log `NSCV map tap=... frame=... still=... crop=... rot=... mirror=...` and save the crops | every saved crop contains the tapped dot |
| A5 | Tap mapping, front camera | phone | same as A4 with the front camera | mirrored correctly (dot inside the crop) |
| A6 | Frame vs still FOV | phone | photograph a ruler; compare a box drawn on the 16:9 preview with the same region in the 4:3 still | offset ≤ 2% of the still side; otherwise set `sensorAspect` |
| A7 | Wrong-ID / unsupported | phone | persimmon, peach, kiwi, papaya; a printed fruit photo; a cut apple | "Unable to identify" or the user-confirm sheet; never a name + grade |
| A8 | Occlusion | phone | apple half covered by a hand, in a plastic bag, behind another fruit, 25% outside the tap box | "Not graded" with a reason, or unable; never a grade |
| A9 | Latency (phone only) | physical phone | logcat `NSCV stage=crop|h2|occl ms=` for 3 min | report p50/p95 as the first phone number; the emulator gives no latency claim |

Attach `g9i_device_log.txt` / `.csv` and the A4-A8 screenshots to a Stage I device note before any device claim is made.
