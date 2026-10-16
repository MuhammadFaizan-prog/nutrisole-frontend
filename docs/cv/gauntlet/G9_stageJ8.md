# G9 Stage J8: real-time CV on the Android camera + report-only colour-variation diagnosis

Branch `cv-gauntlet-device`, draft PR #2 into `cv-gauntlet`. It is never merged to main and never deployed.

**Ground rules followed:**
- No training.
- G3 / H2 weights, every threshold, `DEFAULT_ID`, `FROZEN_VERIFY` and `FROZEN_GATE` are unchanged (asserted by
  `tests/cvLiveJ8.test.ts`).
- Per the 02:39 PKT override, no verification-policy change was made because of the apple/citrus report.

## 1. Design chosen

**Option (b): GPU resizer in the VisionCamera frame worklet, then ORT on the RN side, one inference in flight.**

**Why not (a), a Kotlin frame-processor plugin with the ORT Java API?**
- The Gradle build cannot run in the sandbox, so every Kotlin iteration would be a blind CI round trip.
- It would duplicate the preprocessing, NMS and decoding that are already parity-tested in TypeScript.
- It is not needed for smoothness, because:
  - onnxruntime-react-native 1.24.3 runs `session.run` on its own native thread (`AsyncWorker`, `cpp/InferenceSessionHostObject.cpp`),
    so the JS thread is never blocked by inference;
  - the camera preview is drawn natively, so it is never blocked by JS;
  - the per-update JS work is small: copying and rotating about 130 k pixels, padding the 480 tensor, and decoding 75 k floats.

**Data path:**
1. `useFrameOutput` (yuv) worklet:
   - counts frames;
   - `gateVerdict`: drop if busy or before the next slot, so frames are never queued;
   - calls `resizer.resize(frame)` (react-native-vision-camera-resizer). This does YUV→RGB uint8 on the GPU, at the
     **480-letterbox inner size** (for example 480×270 for a 1280×720 frame).
2. `scheduleOnRN` copies the buffer to the RN thread.
3. On the RN thread:
   - `unpackResized` (RGB / RGBX / row stride, refusing anything else);
   - `rotateRgb` by `Frame.orientation` / `isMirrored`;
   - **the same `detectorInput`** as the tap path. Because the buffer is already the inner size, it only pads with 114, so the
     tensor matches the Ultralytics letterbox;
   - G3 (ORT);
   - `decodeRawWithNms` (unchanged);
   - `mergeAgnostic`: one object per fruit, competing classes kept only for the log;
   - `LiveTracker` (IoU);
   - overlay through the existing `stillBoxToView` / `srcToScreen` mapping.

**Throttling:**
- The interval is `max(125 ms, latency EMA × 1.25)`, capped at 333 ms, giving about 3–8 updates/s.
- Thermal floors: 250 / 333 / 500 ms at moderate / severe / critical `PowerManager` status.
- Only one inference is in flight at a time.

**Identification (unchanged policy):**
- `trackWide()` is exactly `burstWide()` (J7's 3-still policy) applied to the last `idMinHits` = 3 live-frame observations of
  one track. A missed frame counts as null.
- A test proves the two give equal results on the same observations.
- Anti-flicker:
  - a label is held only through missed frames;
  - any observed contradicting class or score < 0.5 hides it at once;
  - new and lost tracks never inherit a label;
  - a label is never shown before the policy passes.

**Close-up:**
- Tap a tracked box. One high-res photo is taken (`capturePhoto` is used ONLY here and in the optional tap-3 fallback).
- `runCloseupFromTrack` then runs G3 on the still for the crop, H2 on the high-res crop, and `verifyIdentity(FROZEN_VERIFY)`.
- The result is "Name. Not graded" or "Unable to identify (— move closer)". Grades stay blocked; the REAL/PLACEHOLDER badge is
  kept.

**Lifecycle:**
- The camera runs only when permission is granted, the app is in the foreground and the screen is focused/mounted.
- The frame processor also needs the models ready and live mode selected.
- Going to the background resets the tracks.
- ORT sessions load once per process (module-level promise) and are reused across remounts.

**QA-only native additions (`ModelAssetsModule.kt`):**
- logcat tag `NutriSoleCV`;
- `runtimeStats` (thermal status, native heap, Java heap);
- `appendDiag` (JSONL);
- `saveRgbJpeg`.

All files go to `/sdcard/Android/data/com.muhammadfaizan.nutrisole/files/diag`.

**Bottleneck note:**
- If a phone shows detection updates/s < 3 with G3 p50 > 250 ms, the bottleneck is G3 on the CPU EP.
- The smallest next step is to enable the NNAPI/XNNPACK execution provider in `InferenceSession.create` options. That is one
  line, but it needs a phone A/B because NNAPI output parity must be checked.
- The step after that is the Kotlin ORT frame-processor plugin.
- Neither is done blind.

## 2. Host-side colour-variation probe (REPORT-ONLY)

**This is HOST-SIDE:**
- the sandbox CPU and onnxruntime-node, running the same TypeScript and the same ONNX files;
- a static image stands in for 3 identical live frames;
- the live buffer is a PIL bilinear resize, not the GPU resizer.

**About the probe set:**
- It is **AI-labelled by Hark** and is diagnostic only: non-evidential, never a gate or training input.
- It has 122 images from non-eval pools: J-train packs 1+2 and the J5/J6 Commons candidates. It never uses J-eval, M-TEST,
  CU-check or frozen eval images.
- 93 synthetic lighting variants (dark ×0.45, warm tint, over ×1.7) were added for apples, carrots and citrus.

Files:
- `ml/runs/G9/stageJ/out/j8/probe_manifest.json`
- `probe_report.json` (per-row G3 class/score, competing classes, H2 top-3, titles, hints, quality)
- scripts: `native/scripts/g9j8_probe.ts` and `ml/runs/G9/stageJ/scripts/j8_probe_report.py`

### Original images (n=122)

| | correct | wrong ID | unsupported accepted | abstain |
|---|---|---|---|---|
| **J8 live label** (G3, 3-frame wide policy) | 63 | 12 | 8 / 21 | 39 |
| **J8 close-up title** (G3 + H2, FROZEN_VERIFY) | 21 | 0 | 1 / 21 | 100 |
| J7 tap-3 title (before) | 23 | 0 | 1 / 21 | 98 |
| J7 overlay: a wrong class NAME drawn on the main item (before) | | **34 / 122** | | |
| J8 overlay: two names on one object | | 0 | | |

**Live per class (correct / wrong / abstain):**

| class | correct | wrong | abstain |
|---|---|---|---|
| apple | 31 | 2 | 3 |
| banana | 10 | 0 | 3 |
| citrus | 13 | 6 | 4 |
| tomato | 1 | 4 | 9 |
| carrot | 3 | 0 | 4 |
| multi | 5 | 0 | 2 |
| capsicum | 0 | 0 | 1 |
| unsupported | — | 8 accepted | 13 |

**Live confusions:**
- apple → pomegranate 2 (striped Gala)
- citrus → apple 2, lemon_lime 1, pomegranate 1, mango 1, tomato 1
- tomato → apple 2 (green), citrus 1, mango 1
- unsupported → citrus 3, apple 3, pomegranate 2 (persimmons, a printed still life, onion, strawberries, lulo)

### Synthetic lighting (n=93)

| | correct | wrong ID | abstain |
|---|---|---|---|
| Live | 62 | 15 | 16 |
| Close-up | 20 | 1 | 72 |

The close-up error was a dark citrus read as pomegranate. Live errors under lighting: apple → pomegranate 6, citrus →
pomegranate/apple/mango 8, carrot → citrus 1.

### Apple → citrus: not reproduced

Across 78 apple rows (original + lighting variants), there were 0 citrus outcomes on every measure:
- live label;
- close-up title;
- J7 raw overlay name;
- G3 competing class;
- H2 top-1.

**The most plausible mechanism for what you saw is the J7 overlay (inferred, not proven).** J7 drew *every* decoded G3 box
≥ 0.25 with its class name, before any policy, with class-wise NMS. That means a low-score second-class box could print a wrong
fruit name on a distant item. That happened on 34/122 probe images. J8 removes it. Small/distant items (< 96 px) are also where
5 of the 8 live unsupported acceptances occur, consistent with your "phone too far" observation. Phone diagnostics will tell.

### Implementation / integration checks

| Check | Result |
|---|---|
| Raw class-wise boxes named on screen (J7) | **Bug, fixed**: one object per fruit; name only after the policy passes |
| Live letterbox / pad / normalisation | Same `detectorInput` (pad 114, /255). Live buffer = inner size, so no resample (unit test) |
| RGB vs BGR | Code feeds RGB. Swapping R/B changes H2 top-1 on 75/122, so order matters and is right (as Stage I found) |
| YUV→RGB in the live path | Done by the GPU resizer. Not testable host-side. On-device `NSCV colourcheck` compares the live colour with the photo colour on every tap |
| H2 crop source | Preview-resolution crop vs high-res crop changes H2 top-1 on 19/122, so close-up always uses ONE high-res photo; live H2 is only logged |
| Crop padding / aspect | Unchanged `identityCrop` stageH (pad 0.08); Stage I's square-crop candidate is still not adopted |
| G3/H2 disagreement | Existing P-a → "Unable to identify" (`close_up_contradicts_wide` / `citrus_family_contradiction`). The close-up showed no confident wrong label on the original images. The one unsupported acceptance (onion → Apple) is G3 + H2 agreeing wrongly |

### Error attribution, model limitations (need H3, which is blocked; no training without your explicit permission)

- **G3 class confusion:**
  - striped/red-yellow apple → pomegranate
  - green tomato → apple
  - ponkan/tangerine → lemon_lime/pomegranate/apple/mango
  - persimmon/lulo → citrus
  - onion/printed fruit → apple
- **H2:** the close-up is correct on only 21/101 supported items, mostly through `unknown` / low confidence. This matches Stage
  H's 9/99 and Stage I's domain-mismatch finding.

**Does the app refuse uncertain predictions?**
- The close-up refuses everything uncertain or contradictory: 0 wrong IDs on the original images.
- The live label does not refuse confident G3 mistakes, because it is the unchanged wide policy. They are shown as "Apple"
  etc. with a hint, and the close-up tap is the check.
- Tightening live labels (for example requiring H2) was **not done**, per your override.

## 3. Tests (sandbox)

| Suite | Result |
|---|---|
| native | 199/199 (183 before + 16 new in `cvLiveJ8.test.ts`): throttler, tracker, consistency-from-frames ≡ burst, coordinate mapping in all orientations, lifecycle, fallback toggle, hints, quality metrics, diagnostics, close-up |
| ML (pytest) | 161/161 |
| web | 5/5 |
| expansion | 8/8 |
| runtime | 28 OK |
| tsc | No new errors in the changed files (pre-existing test-typing errors unchanged) |
| babel worklets transform | `onFrame` and `gateVerdict` workletized |

The Metro bundle and Gradle run in CI only; local Metro times out in the sandbox.

## 4. What is not proven yet

These need the phone (see the P1 guide):
- real frame rate, latency, thermal and memory;
- box alignment in each rotation;
- GPU resizer availability and its colour conversion;
- background/foreground behaviour.
