# G9 Stage J7: install the NutriSole QA APK on your Android phone (P1, Windows)

Branch `cv-gauntlet-device` only (draft PR #2 into `cv-gauntlet`; never `main`, never deployed). This replaces the
"build it yourself with Android Studio" steps of the J5/J6 P1 guides: GitHub Actions now builds a **standalone** QA APK.

**What the QA APK is**
- A release-type build with the JavaScript bundle **embedded** (no Metro, no PC needed to run it), signed with the repo's
  **debug keystore** (not a store build). App id `com.muhammadfaizan.nutrisole`, **minSdk 24 (Android 7.0+)**, arm64-v8a only
  (every phone from roughly 2017 onwards; a 32-bit-only phone will refuse it as "App not installed").
- **QA flavour:** built with `NUTRISOLE_QA=1`, which turns `CV_DEBUG_PIPELINE` on for this APK only (Metro swaps in
  `native/src/cv/device/flags.qa.ts`). You do **not** edit any code. The committed source and any normal build stay unchanged (flag off).
- **Models bundled:** G3 detector `det_yolo11n_640_raw.onnx` (sha256 `c6fcb32a…`) and H2 verifier `h2_mnv3s.onnx` (sha256 `20898d7c…`)
  are inside the APK. On opening Scan the app copies them to its private storage and checks size + SHA-256 against
  `models.ts` before loading. If a file is missing or the hash differs it shows **"Models not loaded: …"** with the orange
  **PLACEHOLDER** badge and never shows a made-up prediction. Fallback: the old hash-checked adb push (J5 guide, step 6) still works.
- Grades A/B/C stay disabled. The result is only "<name>. Not graded" or "Unable to identify".
- The exact artifact name, source commit, APK SHA-256, size and minSdk for each build are in the latest bot comment on PR #2.

## 1. Download the APK (needs your GitHub login)
1. Open PR #2 → the latest J7 comment → click the **Actions run** link (or repo → **Actions** → *Android QA APK (cv-gauntlet-device)* → newest green run).
2. Scroll to **Artifacts** → click **`nutrisole-qa-apk-<sha7>`**. You must be signed in to GitHub; it downloads as a **.zip**.
3. Right-click the zip → *Extract All…*. Inside: `nutrisole-qa-<sha7>.apk`, `nutrisole-qa-<sha7>.apk.sha256`, `build-info.txt`
   (badging, permissions, file list, model hashes).

## 2. Verify the SHA-256 (PowerShell, on the PC)
```powershell
cd $HOME\Downloads\nutrisole-qa-apk-<sha7>
(Get-FileHash .\nutrisole-qa-<sha7>.apk -Algorithm SHA256).Hash.ToLower()
Get-Content .\nutrisole-qa-<sha7>.apk.sha256
```
The two hex strings must be identical **and** equal the APK SHA-256 in the PR #2 comment. If not, do not install; re-download.

## 3. Install on the phone
Either way works.

**A. Without a cable:** copy the `.apk` to the phone (USB file transfer, Google Drive, or WhatsApp "Document" to yourself), open it in
*Files*. Android asks to allow installs from that app: **Settings → "Install unknown apps" → (Files / Drive / Chrome) → Allow from this source**.
Go back → **Install**. Play Protect may warn "unknown developer" (debug-signed): tap *More details → Install anyway*.
Xiaomi/Redmi/POCO: also turn off *MIUI optimisation* prompts if it blocks the install; Samsung: *Auto Blocker* must be off.

**B. With adb (also needed for logs, §6):**
```powershell
adb devices                                   # must list your phone as "device" (USB debugging ON, see J6 addendum step 1)
adb install -r .\nutrisole-qa-<sha7>.apk
```
If you already have a NutriSole build from your own PC (different signature) and install fails with `INSTALL_FAILED_UPDATE_INCOMPATIBLE`:
`adb uninstall com.muhammadfaizan.nutrisole` first (this removes that app's local data on the phone only).

## 4. Open Scan, allow the camera, check the badge
1. Open **NutriSole** → finish/skip onboarding → Home → **Scan Food** (or with adb: `adb shell am start -a android.intent.action.VIEW -d nutrisole://scan`).
2. The QA build shows the debug camera layer straight away: yellow **"DEBUG · phone test"** pill top right.
3. Camera permission prompt → **Allow** (*While using the app*). Denied by mistake: the screen shows **Open Settings** → Permissions → Camera → Allow.
4. Badge under the pill:
   - orange **PLACEHOLDER · no model output (loading models)** while the models load (a second or two), then **(models loaded, tap an item)**;
   - after you tap an item and a result appears: green **REAL INFERENCE · G3 + H2 ONNX on this device**;
   - orange **PLACEHOLDER … (models not loaded)** plus a "Models not loaded: …" line at the bottom = bundled models failed their check.
     Screenshot it and send it (it names the file and the reason); do not continue the matrix.
5. Tap an item on screen → hold still for the 3-photo burst → title appears at the bottom.

## 5. Test matrix (2 taps each, phone in portrait, normal indoor light unless stated)
| # | Item / condition | Expected (functional only, not accuracy) | Record |
|---|---|---|---|
| T1 | apple, plain table | "Apple. Not graded" or "Unable to identify"; green REAL INFERENCE after the result | title, badge colour, screenshot |
| T2 | banana | same pattern | title, badge |
| T3 | orange / kinnow | if identified: "Citrus … Not graded" and `domain=citrus_orange · nutrition USDA FDC per 100 g · price: no verified source loaded` | title, domain line |
| T4 | tomato | same pattern | title, badge |
| T5 | carrot | same pattern | title, badge |
| T6 | each of T1–T5 inside a clear plastic bag | "Not graded" or "Unable to identify"; never a grade or % | title per item |
| T7 | each of T1–T5 half covered by your hand | same | title per item |
| T8 | unsupported produce: persimmon, potato (and any other non-listed item) | "Unable to identify" expected; a confident wrong fruit name is a finding | title |
| T9 | a fruit photo shown on another phone/PC screen, and printed on paper | "Unable to identify" expected | title |
| T10 | Settings → deny camera → reopen Scan | "Open Settings", PLACEHOLDER badge, no crash | screenshot |

For **every** tap write one line: `T#, item, condition, title shown, badge colour, yellow crop box on the tapped item? (y/n), seconds from tap to result (rough), anything odd`.
Never expected anywhere: "Grade A/B/C", "97%", any percentage or confidence number. If you see one, screenshot it: that is a bug.

## 6. Logs
There is no in-app log export. Logs come from `adb logcat` (Android **platform-tools**: https://developer.android.com/tools/releases/platform-tools,
unzip, e.g. to `C:\platform-tools`, run the commands from that folder or add it to PATH). Phone: USB debugging ON, cable connected.
```powershell
adb devices
adb logcat -c
adb logcat -v epoch -s ReactNativeJS:* > g9j7_device_log.txt        # NSCV lines (model_source, init, det/h2 ms, results, latency, ui_lag)
# run the whole matrix, then Ctrl+C
adb logcat -d -v epoch AndroidRuntime:E ReactNative:* ReactNativeJS:* onnxruntime:* *:S > g9j7_crash_log.txt   # only if it crashed / red screen
adb shell dumpsys meminfo com.muhammadfaizan.nutrisole > mem_after_matrix.txt
adb shell getprop ro.product.model ; adb shell getprop ro.build.version.release
```
The first lines you should see after opening Scan: `NSCV model_source model=h2 source=bundled sha256=ok` and the same for `g3_det`,
then `NSCV stage=init model=h2 ms=…`. `source=none reason=…` means the models were not loaded.

## 7. Screen recording
Use Android's built-in recorder: swipe down twice → **Screen record** tile (Samsung: *Screen recorder*; Xiaomi: *Screen recorder* app) →
start → run T1–T10 → stop. It saves to *Movies / DCIM / Screen recordings*. (Alternative with adb:
`adb shell screenrecord --time-limit 170 /sdcard/g9j7.mp4` then `adb pull /sdcard/g9j7.mp4`, repeat for longer runs.)

## 8. Send back
1. `build-info.txt` from the artifact zip + the line `Get-FileHash` printed (proves which APK you installed).
2. Phone model + Android version.
3. The per-tap lines from §5 (a simple text or Excel file is fine).
4. Screenshots: badge while loading, the first green REAL INFERENCE result, T3 domain line, one T6, one T8, T10.
5. The screen recording(s).
6. `g9j7_device_log.txt` (and `g9j7_crash_log.txt`, `mem_after_matrix.txt` if you made them).
7. If install or launch fails: the exact error text / screenshot.

Everything you send is a phone observation; I parse the NSCV log into latency and behaviour numbers. T1–T9 stay functional
observations, not an accuracy figure.

## Licence note (read before sharing the APK)
The G3 detector is a fine-tuned Ultralytics **YOLO11n**, licensed **AGPL-3.0**. Keeping the APK for your own testing is fine; giving the
APK (or the weights) to other people is distribution under AGPL-3.0 (offer the corresponding source under AGPL-3.0) unless an Ultralytics
Enterprise licence is obtained. The repo is public and has no LICENSE file yet. The weights sit on the separate orphan branch
`qa-models-j7`, never in `cv-gauntlet-device` history.
