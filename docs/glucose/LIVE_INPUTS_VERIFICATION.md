# Android glucose verification

Branch: `fix/glucose-live-inputs`, based on `feature/glucose-monitoring` / draft PR #3 at `39fa8b7`. The separate draft PR targets the feature branch; neither main nor the base feature branch is modified or merged by this work.

## Completed code checks (2026-10-17)

- Root typecheck and production web build: passed.
- Shared glucose tests: 94 passed, including real PP-OCR fixture inference for the retained web/iOS fallback.
- Native typecheck: passed; native tests: 34 passed. Native lint: 0 errors, 166 existing inline-style warnings.
- Protected mobile runtime: all 28 protected files unchanged. The six-screen / 119-file expansion baseline and 8 expansion tests passed. Domain tests: 5 passed. Sites packaging: 4 passed after building.
- Read-only code review findings were reproduced and fixed: exact imported timestamps through edits, previously unseen rows during reload races, source dedupe across meters/pages, scan start/stop promises, transfer discard cleanup, repeated transfer snapshots, account-switch token races, saved-history loading after clock correction, lipid results misread as glucose, and inaccessible rows beyond the first import page.
- The 5,000-packet simulated meter burst completed in 162–470 ms on this Windows host, with throttled progress snapshots. This is a pure transport/parser test, not physical Bluetooth timing.

## Runtime checks in progress

The standalone Android APK and instrumentation APK build successfully for arm64-v8a and x86_64. On CI run [38960923261](https://github.com/MuhammadFaizan-prog/nutrisole-frontend/actions/runs/38960923261), the actual native ML Kit/PdfRenderer reader processed all 56 synthetic files and the Keystore test passed. Ten encrypted writes took 2–9 ms. OCR took 2.595–25.335 s (median 6.072 s, p95 9.868 s) on this emulator; it is not a millisecond OCR claim.

The fixed synthetic set contained 57 lab results and 9 segmented meter displays: 55/57 lab values and units were correct, 54/57 also had the expected context; no wrong value or extra glucose result was returned. The meter-display samples were not recovered (0/9); use manual/device input when display digits are unreadable. These are synthetic transcription scores, not clinical accuracy.

The first rendered UI smoke exposed an off-screen control selector: Android returned an inverted clipped rectangle for the below-fold Add reading button. The harness now scrolls to a real on-screen control. Full CRUD, DocumentsUI photo review/save, camera cancellation and all 40 route checks are being rerun. The native instrumentation invokes ML Kit/PdfRenderer and Keystore directly; a successful TypeScript test does not replace that run.

The automatic browser approval policy rejected access to the local preview after earlier attachment failures. The web build is verified; rendered web behavior remains unverified. No alternate browser or user Chrome session was used to bypass the rejection.

## External limits

No physical Bluetooth strip meter or Android phone is attached. Pairing, PIN/bonding, actual meter transfer and a meter-app-to-Health-Connect chain remain unverified. No universal compatibility or millisecond hardware/OCR latency is claimed. Health Connect imports records already stored by the source app on user request. OCR always requires review and is not a medically validated glucose measurement.

No live Supabase requests/migrations, deployments, purchases or main-branch merges were performed. The default Android store is encrypted on this phone; account mode remains separate and explicit.
