# G9 Stage J9: frozen 1 % scene guard restored in the J8 live CV (QA APK)

This document is in-branch as `docs/cv/gauntlet/G9_stageJ9.md` (doc-only commit `[skip ci]` after the build, so it does not change the APK).

Branch `cv-gauntlet-device`, draft PR #2 only. Not merged. Physical-device **performance and accuracy are UNVERIFIED** until you test the APK on your phone.

## 1. Build

| | |
|---|---|
| Actions run | [38880462397](https://github.com/MuhammadFaizan-prog/nutrisole-frontend/actions/runs/38880462397) (push, success on the first attempt, about 12 min) |
| Artifact | `nutrisole-qa-apk-4566215`, id **12038091384**, expires 2026-11-15: https://github.com/MuhammadFaizan-prog/nutrisole-frontend/actions/runs/38880462397/artifacts/12038091384 |
| Source commit | `456621534d98bf2edaecd6e190663f6d59670e6d` (local `55b1d1d`; remote = J8 `fd64b24` + 7 single-file commits, 7/7 blobs verified) |
| APK | `nutrisole-qa-4566215.apk`, 91,338,578 bytes |
| APK SHA-256 | `084bda826ce317a91349fae5060123303820e5d55ad6b19c0709efac80c0fe3a` (matches the `.sha256` file in the artifact: yes) |

Verified after downloading the artifact:
- the SHA-256 matches the `.sha256` file (`sha256sum -c`: OK);
- `aapt2` badging: minSdk 26, targetSdk 36; permissions CAMERA, INTERNET, ACCESS_NETWORK_STATE;
- **both models bundled**: `assets/models/det_yolo11n_640_raw.onnx` (10,600,677 B, `c6fcb32a…d340c1`) and `assets/models/h2_mnv3s.onnx` (6,133,032 B, `20898d7c…89a22e`), SHA-256 equal to `models.ts` and byte-identical to the J8 APK's models;
- the JS bundle `assets/index.android.bundle` is embedded as Hermes bytecode (magic `c6 1f bc 03`, 3,061,108 B), so it runs without Metro;
- **the guard code is in the bundle**: `guardFrame`, `closerCandidates`, `minAreaFrac`, `maxSameClass`, `droppedBySuppression`, `tooSmallAtTap`, `suppressedSinceLast`, `NSCV suppressed `, `scene_guard_suppressed`, `NSCV event=tap_on_suppressed`, `below_min_area`, `too_small_at_tap`, `cv-move-closer`, `Move closer` (all found). The CI hard checks for the J9 markers passed as well;
- the J8 strings are still present (`held_through_missed_frame`, `NSCV perf window_s=`, `NUTRISOLE_QA_FLAGS_ON`);
- arm64-v8a libs present: onnxruntime (+jsi), VisionCamera, VisionCameraResizer, VisionCameraWorklets, worklets, NitroModules;
- the PR-event run [38880464345](https://github.com/MuhammadFaizan-prog/nutrisole-frontend/actions/runs/38880464345) on the same commit is also green.

## 2. What changed (7 files)

- **`native/src/cv/device/guard.ts` (new).** `guardFrame(dets, w, h)` calls the frozen `sceneGuard()` with `DEFAULT_SCENE_GUARD` from `pipeline/postprocess.ts`. Nothing is re-implemented or tuned: `minAreaFrac` stays 0.01 and `maxSameClass` stays 0 (rule 2 has been off since G4).
  - **Coordinate space.** The detector box is mapped back with `detectorToFrame` (undoes the 480 letterbox, clipped). Boxes are then in pixels of the upright original frame or photo (after rotation), and are divided by that image's width and height. This is the same order and space as `ml/eval/video_gauntlet.py` (`dst_to_src` with clipping, then `/W,/H`, then `scene_guard`).
  - **Live buffer.** The live buffer is a uniform scale of the camera frame (480-letterbox inner size), so its normalisation equals the full camera frame's (tested).
  - **Preview crop.** The on-screen "cover" crop of the preview is **not** used. As in the eval, the guard is relative to the full camera frame.
- **Live path (`responsive/CvDebugScan.tsx`, `live.ts`).** Order: decode, then guard, then `mergeAgnostic(kept)`, then `LiveTracker.update(kept, t, suppressedBoxes)`.
  - Suppressed boxes never become a track, a hit, a box, a label or a confirmation.
  - **Stale boxes.** An unmatched track overlapped by a suppressed box (same `iouMatch` 0.3) is dropped in that frame. Under J8 it would have kept its held box and label for up to `maxMissed` = 4 frames. With nothing suppressed, the tracker behaves exactly like J8 (tested).
  - **Taps.** A tap on a below-guard box is refused: no close-up, `Move closer`, and the log line `NSCV event=tap_on_suppressed`.
- **Close-up photo and tap-3 burst (`debugPipeline.ts`).** Both paths are guarded on the photo's or still's own pixels. Only kept boxes are drawn, tapped or used for the crop plan. A tap that lands only on a suppressed box sets `guard.tooSmallAtTap`, and the screen shows "Unable to identify — move closer". The display contract is unchanged.
- **"Move closer" hint.** It is one small chip for the whole screen, never one per box, and is rate-limited:
  - it shows after 2 processed frames in a row;
  - it shows only when **nothing** guarded is on screen;
  - it shows only for suppressed items scoring ≥ the existing `idMinScore` 0.5, so faint noise from the 0.25 floor cannot trigger it;
  - it is held ≥ 1.5 s, then has a 2 s cooldown;
  - a guarded item appearing hides it at once.
  This is UI only and changes no score.
- **Diagnostics (`diag.ts`).** Suppressed detections are logged **separately** from decisions:
  - logcat prefix `NSCV suppressed` (tag `NutriSoleCV`);
  - a JSONL record of kind `scene_guard_suppressed` in `nscv_diag.jsonl`, carrying `n_in`, `n_kept`, `n_suppressed`, per-item class, score, `area_frac`, reason and box, `dropped_tracks`, `move_closer_hint`, the guard params and `decode_floor`;
  - live logging is limited to 1 record/s, with counts accumulated between records so none are lost; the close-up and tap-3 paths log one record per still that had suppressions.
- **Workflow.** New hard checks that the J9 guard strings (`NSCV suppressed `, `scene_guard_suppressed`, `NSCV event=tap_on_suppressed`, `cv-move-closer`) are in the embedded JS bundle.

**Unchanged:**
- G3 and H2 weights and models (the same pinned `qa-models-j7` commit and SHA-256), preprocessing, `DEFAULT_ID` (0.5 / 3), `FROZEN_VERIFY` P-a, `FROZEN_GATE` (96 px), the H2 high-res close-up and the refusal behaviour;
- the class-wise NMS and the 3-consistent-frame confirmation;
- throttling, worklet, resizer and lifecycle;
- cv-gauntlet / PR #1, the G10 files, M-TEST, main and the glucose PR #3: not touched;
- no training.

**Decode floor (reported, not changed).** All three device paths still decode G3 at **0.25** (`DET_DECODE_FLOOR`). The guard runs after that floor, exactly as the eval does (decode at `dec_thr`, then guard). Naming still needs `idMinScore` 0.5 over 3 frames.

**Small eval/app difference.** The eval also drops boxes under 2 px per side before the guard. With a 1 % guard such boxes are always below 1 % anyway, so the result is identical.

## 3. Tests (sandbox)

| Suite | J8 (fd64b24) | J9 |
|---|---|---|
| native | 199/199 | **216/216** (+17 in `tests/cvSceneGuardJ9.test.ts`) |
| ML (pytest) | 161/161 | 161/161 |
| web | 5/5 | 5/5 |
| expansion | 8/8 | 8/8 |
| runtime integrity | 28 OK | 28 OK |
| tsc / eslint on changed files | — | 0 new errors / clean |
| CI native tests (flag off) | green | green (216/216 in the CI log) |

What the 17 new tests cover:
- the frozen-policy constants, checked against the Python `DEFAULT_GUARD`;
- **parity:** all 60 cases of `ml/eval/fixtures/scene_guard_parity.json`, in normalised space and in pixel space (1024×512, 2048×1024);
- equality with `sceneGuard(DEFAULT_SCENE_GUARD)` and the exact 1 % boundary;
- the coordinate space: the letterbox is undone (a box that is 1.23 % of the frame but only 0.69 % of the 480 square is kept), and the result is rotation-invariant on the upright buffer;
- the live tracker: tiny boxes never make a track; an apple identified close up and then moved away keeps its label while ≥ 1 %, and is dropped the first frame it falls below (J8 coasted for 4 frames); unrelated tiny boxes have no effect;
- the hint timing, the score ≥ 0.5 candidates rule, the separate rate-limited diagnostics, the close-up and tap-3 `tooSmallAtTap` behaviour, the 96 px hint still firing, and source wiring (every device decode is followed by the guard).

## 4. Comparison vs J8

| | J8 (`fd64b24`) | J9 (`4566215`) |
|---|---|---|
| Scene guard on device | **Not applied** (decode 0.25 → boxes; `sceneGuard()` never called) | Frozen `sceneGuard` (1 %, rule 2 off) on live, close-up and tap-3 |
| Area space | n/a | Upright original frame/photo, letterbox undone (= Python eval) |
| Below-1 % detections | Boxed, tracked, could be labelled after 3 frames, tappable | No box, no label, not tappable, never confirmed, no tracker hit |
| Item shrinking below 1 % | Track coasts up to 4 missed frames with its held box/label | Track dropped that frame; one `Move closer` chip |
| Guidance | Per-track hints (96 px / 224 px / blur / light / edge) | Same, plus the rate-limited global `Move closer` for suppressed items |
| Diagnostics | `NSCV diag` decisions | + separate `NSCV suppressed` / `scene_guard_suppressed` |
| Decode floor | 0.25 | 0.25 (unchanged) |
| G3 / H2 / DEFAULT_ID / FROZEN_VERIFY / 96 px gate | frozen | unchanged |
| native tests | 199 | 216 |
| APK bytes | 91,330,102 | 91,338,578 |
| JS bundle bytes | 3,052,632 | 3,061,108 |
| APK SHA-256 | `ed935a93…0243f` | `084bda82…c0fe3a` |
| Artifact | `nutrisole-qa-apk-fd64b24` (id 12011100216, run 38814693298) | `nutrisole-qa-apk-4566215` (id 12038091384, run 38880462397) |

**Expected effect, from G10b offline evidence only.** G3 with the 1 % guard: 593 correct / 243 false-positive boxes. G3 without it: 825 / 433. Tap identity was the same either way (30 / 1 / 4). Those eval labels are exploratory and not independently human-verified, so this is **not** a proven accuracy improvement. On-phone accuracy and performance are **unverified**.

## 5. Phone test (about 2 minutes)

1. Uninstall the J8 build (the same debug signature lets you install over it, but a clean install is simpler). Then install the APK from the artifact.
2. Open Scan in LIVE mode. Hold **an apple close** (filling roughly a quarter of the screen). After about 3 frames it should get a green box and the label "Apple".
3. **Move the phone away slowly.** The box and label should stay while the apple is reasonably large. Once it is below about 1 % of the camera frame (about one tenth of the frame’s width and height), the box and label should disappear at once, with no frozen box left behind. A small yellow **"Move closer"** chip should then appear in the centre, without flickering.
4. Tap where the small apple is. Nothing should be identified; you should see "Move closer" only. Move back in, tap the apple, and the close-up check should run as in J8.
5. Optional logs: `adb logcat -s NutriSoleCV | grep -E "NSCV (suppressed|event=tap_on_suppressed)"`.

Report what you see. Nothing is merged; further changes wait for your approval.
