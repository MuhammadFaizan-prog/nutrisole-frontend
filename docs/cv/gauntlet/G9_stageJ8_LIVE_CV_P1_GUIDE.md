# G9 Stage J8: live camera CV, phone test P1 (guide for Faizi)

Branch `cv-gauntlet-device`, draft PR #2. This branch is never merged to main and never deployed.

**What changed since J7:** the Scan screen's QA camera layer now analyses the live video by itself. You no longer tap to take
3 photos.
- G3, H2, every threshold and the verification policy are **unchanged**. No training was done.
- The old tap-to-analyze 3-photo mode is still there as a toggle. It is not the default.

## 1. Install (no Metro, no PC needed after install)

1. Download the APK artifact `nutrisole-qa-apk-<sha7>` from the GitHub Actions run linked in the PR #2 comment, then unzip it.
2. Check its SHA-256 against the `.sha256` file:
   - Windows: `certutil -hashfile nutrisole-qa-*.apk SHA256`
   - macOS / Linux: `sha256sum`
3. Install it:
   - over USB: `adb install -r nutrisole-qa-*.apk`
   - or copy the APK to the phone and open it (allow "install unknown apps").
   - Uninstall the J7 QA APK first if Android reports a signature conflict.
4. Requirements:
   - Android 8.0+ (minSdk 26), arm64 phone.
   - Live mode needs the GPU resizer (Vulkan, in practice Android 9+). If it is missing, the screen says so and uses tap-to-analyze.
5. The APK is a release build: the JS bundle and the two ONNX models are inside it, so **Metro is not needed**. Unplug the USB
   cable and turn Wi-Fi off once: the app should still start and run live detection.

## 2. Target flow

Open NutriSole → **Scan** → allow the camera → point at an apple.

1. A **dashed box** appears around the apple straight away. It means "tracking, confirming".
2. After **3 matching live frames** (the unchanged `DEFAULT_ID` policy: same class, score ≥ 0.5), the box turns solid green and
   shows **"Apple"**. You do not tap anything. This takes about 0.4–1 s, depending on the phone.
3. Then do either of these:
   - **Move closer.** If a yellow **"Move closer"** chip shows, the apple is under 96 px (the Stage G quality-gate size) in the
     camera frame.
   - **Tap the apple's box.** The app takes ONE high-resolution photo, crops the apple, runs the **H2 close-up check** with the
     unchanged `FROZEN_VERIFY` policy, and shows `Apple. Not graded` or `Unable to identify`.
     - It shows `Unable to identify — move closer` if the crop was smaller than H2's 224 px input.
     - It never shows an A/B/C grade or a percentage.
4. The bottom panel explains the two kinds of label:
   - The **live label** comes from the detector and needs 3 matching frames.
   - The **close-up result** is the stricter G3 + H2 agreement. If the two models disagree, it says "Unable to identify" rather
     than a wrong fruit.

**Badge:**
- `REAL INFERENCE · G3 + H2 ONNX on this device` means the box and label come from the models on the phone.
- `PLACEHOLDER` means nothing ran (for example, models not loaded).

**Mode toggle (top right):**
- `LIVE · switch to tap-3` selects the old J7 tap → 3-photo burst.
- Switch back to LIVE afterwards.

### Guidance chips (UI hints only; they never change a label or a score)

| Chip | Shown when (existing constants, nothing new) |
|---|---|
| Move closer | Box side √(w·h) < 96 px in camera-frame pixels (`FROZEN_GATE.minSidePx`). On close-up: crop < 224 px (H2 input) |
| Hold steady | Laplacian variance of the box < 15 (`FROZEN_GATE.minBlurVar`), or box IoU between consecutive frames < 0.8 (`DEFAULT_TRACKER_PARAMS.stableIou`) |
| Improve lighting | Mean HSV V of the box < 80 or > 245 (`FROZEN_GATE.minMeanV` / `maxMeanV`) |
| Keep the whole item in view | Box touches the frame edge (`FROZEN_GATE.edgeMarginFrac` 1%) |

The live blur value is measured on the 480 px live buffer, which is sharper than full resolution. "Hold steady" is therefore
conservative in live mode and comes mostly from box jitter.

## 3. Reading the QA perf overlay (live mode, below the badge)

Every number is measured on your phone over the last 5 s. A "-" means the value is not available; nothing is estimated.

| Field | Meaning |
|---|---|
| camera frames/s | Frames delivered to the frame processor. This is not the preview render rate: the preview is drawn natively and is not slowed by inference |
| detection updates/s | Completed G3 runs per second. The target is about 3–8; it adapts to latency |
| G3 inference p50/p95 | ORT run time of G3 at 480 |
| frame→overlay p50/p95 | From the frame worklet taking the frame to the boxes being set on screen (resize + copy + rotate + G3 + decode + tracker) |
| skipped busy / interval | Frames dropped because one inference was already running, or because they came before the next slot. Dropped by design; never queued |
| dropped | Live steps that errored |
| interval | Current target gap between inferences: 125–333 ms; 250/333/500 ms under moderate/severe/critical thermal status |
| thermal | Android `PowerManager` thermal status (n/a below Android 10) |
| JS heap / native heap | Hermes JS heap if exposed; `Debug.getNativeHeapAllocatedSize` |

Do not read the camera frame rate as "30 FPS detection". Detection runs at the "detection updates/s" figure, which is bounded by
design.

## 4. Live test matrix (record the screen for each row)

| # | Scene | What to look for |
|---|---|---|
| 1-5 | One item at a time: apple, banana, orange/kinnow, tomato, carrot | Box appears at once; label after about 3 updates; label sits on the item; tap → close-up result |
| 6 | Bagged item (in a polythene bag) | Label or no label; hints |
| 7 | Partly covered (hand over half) | No wrong label; "Keep the whole item in view" / abstain |
| 8 | Unsupported (onion, persimmon, guava…) | Ideally no label. Note any label it does show |
| 9 | Printed fruit (photo or packaging) | Note any label |
| 10 | Several items (apple + orange side by side) | One box per item, the right name per box, no label jumping between boxes |
| 11 | Rotation: portrait, landscape left/right | Boxes still line up with the items |
| 12 | Background → foreground (home button, reopen) | Camera pauses, tracks reset, live detection resumes, no stale label |
| 13 | Far → near | "Move closer" at a distance disappears when close; label appears |
| 14 | Dim room / torch | "Improve lighting" |
| 15 | Shake the phone | "Hold steady" |

### The apple / citrus script

1. Start a screen recording.
2. Hold the phone about 30–40 cm away. Test one at a time, about 10 s each:
   1. red apple
   2. red-yellow apple
   3. orange
3. For each item, tap it once for the close-up check, then move a bit further away for about 5 s.
4. Put the apple and the orange together, about 10 s, then tap each.
5. Stop the recording.
6. Pull the logs and saved frames (section 5).

No accuracy claim can be made from a few clips. They are diagnostic.

## 5. Logs and diagnostic files (adb)

```bat
:: live logcat (both tags: native NutriSoleCV and the JS console copy)
adb logcat -c
adb logcat -v time NutriSoleCV:I ReactNativeJS:I *:S > nscv_j8.txt

:: only the per-decision diagnostics / perf summaries
adb logcat -v time -s NutriSoleCV | findstr /C:"NSCV diag" /C:"NSCV perf" /C:"NSCV colourcheck"

:: diagnostic JSONL + saved frames/crops of contested or refused decisions (app-specific external storage, no root needed)
adb shell ls /sdcard/Android/data/com.muhammadfaizan.nutrisole/files/diag
adb pull /sdcard/Android/data/com.muhammadfaizan.nutrisole/files/diag .\nscv_diag
```

### What the diagnostic lines mean

- **`NSCV diag {...}`** (also written to `diag/nscv_diag.jsonl`), one per decision change. Fields:
  - path (`live` / `closeup`) and track id
  - G3 class and score, and any competing G3 class on the same fruit
  - wide-policy state
  - H2 top-3. In live mode this is report-only, from the preview crop. In close-up mode it comes from the high-res crop.
  - whether G3 and H2 agree, and the verify result
  - box, crop size, and the quality numbers (side px, area fraction, mean V, luma, blur variance, edge)
  - hints, shown label, reason code, and `contested`
- **Saved images.** `diag/*_frame.jpg` + `*_crop.jpg` are saved only for contested decisions or close-ups that ended
  "Unable to identify", at most 6 per minute.
- **`NSCV colourcheck`** runs on every close-up tap. It compares the live-path colour of the item with the photo colour.
  - `rb_swapped` would mean a red/blue channel bug in the live GPU YUV→RGB path.
  - `ok` / `inconclusive` are expected.
- **`NSCV perf`** is the 5 s perf summary.
- **`NSCV live frame=...`** gives the camera frame size, orientation, pixel format and resize size.

## 6. What to send back

1. Screen recordings of the matrix rows you ran, plus the apple/citrus script.
2. `nscv_j8.txt` (logcat) and the pulled `nscv_diag` folder.
3. The phone model, Android version, and whether Live mode started or fell back to tap-3 (the note at the bottom says so).
4. Any row where a box was misaligned (rotation), a label stayed on the wrong item, or the app needed Metro or crashed.

## 7. Known limits

- **The live label is the detector's label.** It uses the unchanged wide policy and is not H2-verified.
  - On the host-side probe set (AI-labelled, not evidence; see `G9_stageJ8.md`) it was wrong on some items: striped apple →
    pomegranate, green tomato → apple, persimmon → citrus/apple.
  - The tap close-up check refused all of those except one onion close-up (→ "Apple").
- **The close-up check refuses most items** ("Unable to identify"). This is H2's known domain mismatch (Stage H/I). Fixing it
  needs H3, which is blocked: no human labels yet, and no training without your explicit go.
- **Alignment is not proven on a phone yet.** It assumes the live frame and the preview cover the same field of view (same
  aspect). Rotation handling follows VisionCamera's `Frame.orientation` convention. Row 11 checks both.
