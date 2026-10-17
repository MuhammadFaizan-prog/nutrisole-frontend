# Android glucose verification

Branch: `fix/glucose-live-inputs`, based on `feature/glucose-monitoring` / draft PR #3 at `39fa8b7`. [Separate draft PR #4](https://github.com/MuhammadFaizan-prog/nutrisole-frontend/pull/4) targets that feature branch. Main and the original feature branch remain unchanged and unmerged.

## Delivered QA APK (2026-10-17)

- App source: `5d731731dfd6d8c904fbd4bfae9b7030e9188896`. Later commits change verification scripts, workflows and evidence only.
- Build: [38966139455](https://github.com/MuhammadFaizan-prog/nutrisole-frontend/actions/runs/38966139455), artifact `nutrisole-glucose-qa-apk-5d73173` / `12075336752`.
- APK: `NutriSole-Glucose-v1.0.5-QA.apk`, 82,341,793 bytes.
- SHA-256: `fa84a6ee752f749b1de59f260f74b5a6e512f6cf57be3d7c35fe16d8fed13999`.
- Android 8+ (API 26), arm64-v8a and x86_64, version 1.0.5 / code 6. Standalone bundled JavaScript; no Metro or account needed for phone history. Existing debug signing key: QA build, not a store release.
- The APK ZIP and APK checksums were independently verified after download. Adjacent `.sha256` names the delivered APK.

## Completed code checks

- Root typecheck and production web build: passed.
- Shared glucose tests: 99 passed, including real PP-OCR fixture inference for the retained web/iOS fallback.
- Native typecheck: passed; native tests: 34 passed. Native lint: 0 errors, 166 existing inline-style warnings.
- Protected mobile runtime: all 28 protected files unchanged. The six-screen / 119-file expansion baseline and 8 expansion tests passed. Domain tests: 5 passed. Sites packaging: 4 passed after building.
- Read-only review findings were reproduced and fixed: exact imported timestamps through edits, unseen rows during reload races, source dedupe across meters/pages, scan start/stop promises, transfer discard cleanup, repeated transfer snapshots, account-switch token races, saved-history loading after clock correction, lipid results misread as glucose, inaccessible rows beyond the first import page, and collection clocks confused with printing times after OCR added colon spacing.
- A 5,000-packet simulated meter burst completed in 162–470 ms on this Windows host with throttled progress snapshots. This is a pure transport/parser test, not physical Bluetooth timing.

## Actual Android runtime evidence

The native instrumentation invokes bundled ML Kit/PdfRenderer and Android Keystore directly. On [run 38964137185](https://github.com/MuhammadFaizan-prog/nutrisole-frontend/actions/runs/38964137185), app source `37dfbca`, both instrumentation tests passed and the reader processed 56 synthetic files. Ten encrypted snapshot writes took 1–6 ms. OCR took 2.303–8.646 s (median 4.704 s, p95 6.784 s) on the emulator. These are worker/storage timings, not complete interaction or physical-phone latency. Native Android source is unchanged between that APK and the delivered `5d73173` APK.

The first native run [38960923261](https://github.com/MuhammadFaizan-prog/nutrisole-frontend/actions/runs/38960923261) also passed both instrumentation tests: writes 2–9 ms, OCR 2.595–25.335 s (median 6.072 s, p95 9.868 s). Neither run supports a millisecond OCR claim.

Re-scoring retained native output with the final parser passes all 14 standard report/photo/PDF fixtures (16 readings) for value, unit, context, collection date and clock. In the separate challenge set, 55/57 lab values and units were correct, 54/57 also retained the expected context; no wrong value or extra glucose result was returned. Segmented LCD meter-display challenge samples were unrecovered (0/9). The UI provides manual entry when no reading is recovered. All OCR results require review. Synthetic transcription scores do not establish clinical accuracy.

The standalone UI run [38966955659](https://github.com/MuhammadFaizan-prog/nutrisole-frontend/actions/runs/38966955659) passed using APK source `37dfbca` and smoke source `e02946a`. It exercised actual UI manual create, force-stop/restart, edit and delete; Android DocumentsUI photo selection, native OCR, review, confirm/save and restart; camera launch/cancel; and route-specific assertions for all 40 screens without Metro. App-UID crash/ANR logs were empty. One stock Pixel Launcher ANR was captured and dismissed by an exact system-dialog handler; it was not treated as an app success. Any application ANR or crash dialog fails the final harness. Saved UI XML, screenshot evidence and results were downloaded and inspected.

Final delivered-APK UI run [39022429267](https://github.com/MuhammadFaizan-prog/nutrisole-frontend/actions/runs/39022429267) **passed**, using the exact delivered APK source `5d73173` and reviewed smoke source `c6cdebf`. The downloaded results confirm manual create/restart/edit/delete, DocumentsUI photo OCR/review/save/restart, camera launch/cancel, standalone operation and all 40 route assertions. App-UID crash/ANR error logs are empty. One stock Pixel Launcher ANR was captured and closed by the exact system-dialog handler; an application crash/ANR would stop the run immediately. Final screenshots and UI XML were downloaded and inspected. Evidence artifact: `12097740300`, ZIP SHA-256 `6aa4a11ece24fef457f311015c6eb36dd6a149caa309ac376ad724b11905a096`.

Earlier attempts confirmed restart persistence but exposed test assertions about which screen holds the source label and separate value/unit text nodes. Those assertions and fatal ANR propagation were corrected; independent read-only review found no remaining concrete issue. [Machine-readable verification](validation.json) records source commits, checksums, measured results and run provenance.

The final APK build run's instrumentation stage stopped before emulator startup because the SDK system-image download returned an invalid ZIP. It did not execute or fail an application test. The separate fresh-emulator UI workflow verifies the delivered APK independently of that environment failure.

## Remaining verification limits

No physical Bluetooth strip meter or Android phone is attached. Pairing, PIN/bonding, actual meter transfer and the source-app-to-Health-Connect chain remain unverified. Bluetooth support requires the standard Glucose Service (0x1808); a price range or Bluetooth label is insufficient to establish compatibility. Health Connect imports available records on user request. No universal device compatibility, immediate health-platform push or millisecond hardware/OCR latency is claimed. Camera launch/cancel and real photo-URI import were exercised; a physical camera capture remains unverified.

Automatic browser approval rejected access to the local preview. The web build is verified; rendered web checks remain unverified. No alternative browser session was used to bypass the rejection. iOS compilation and HealthKit are outside this Android change.

No live Supabase requests/migrations, deployments, purchases or main-branch merges were performed. Default Android history is encrypted on this phone; cloud-account mode is separate and explicit. Existing computer-vision work and the user's proposal document were preserved.
