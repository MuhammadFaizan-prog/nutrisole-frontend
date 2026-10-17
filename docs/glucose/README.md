# Glucose readings on Android

NutriSole records finger-prick/test-strip readings. It supports manual entry, attached CSV/Excel/PDF/images, camera photos, standard Bluetooth Glucose Service meters and Android Health Connect. It does not generate a measurement from the camera, provide continuous monitoring, diagnose a condition or control treatment. Photos are transcriptions of a printed report or meter display.

This change is on `fix/glucose-live-inputs`, based on draft PR #3 / `feature/glucose-monitoring` at `39fa8b7`. See [verification and limitations](LIVE_INPUTS_VERIFICATION.md) for what has actually been exercised.

## Android storage and capture

The default Android build uses real encrypted phone storage, works without an account or network, and starts with empty history. Android Keystore holds a non-exportable AES-GCM key; an atomic snapshot is stored in private no-backup app storage. Saved readings survive process restarts. Clearing app data, uninstalling, losing the key or losing the phone can lose this history. The UI labels this storage explicitly. Phone readings and cloud-account readings are separate; there is no automatic upload or sync.

Manual input is validated before saving. Imported rows first enter a review screen: confirm, edit or reject, then save the confirmed rows in one durable transaction. Large batches use pages of 40 rows; edits and confirmations survive page changes and progressive meter updates. Original values, units, source IDs and measurement timestamps are retained. Duplicate source records are skipped; manual duplicates produce a warning. Save failures preserve the previous history and do not show an unsaved row as saved. The phone store accepts up to 20,000 readings.

Android photos and PDF pages run through bundled ML Kit Latin recognition / PdfRenderer on a native worker. There is no model download or cloud OCR. The reader retains text positions, applies image orientation, bounds image sizes and accepts PDFs with 1–10 pages. Longer PDFs fail visibly before importing; they are not silently truncated. Searchable PDF text is used where Android exposes safe line geometry; other pages are rendered and read. File hashes and source locations provide provenance. OCR confidence is a reader score, not a clinical accuracy claim; compare every value and unit with the original. An unrelated lab result must not become glucose merely because it contains mg/dL.

The iOS reader retains the existing PP-OCR fallback. iOS compilation and HealthKit are not verified or implemented by this Android change.

## Bluetooth and Health Connect

Bluetooth discovery shows each meter immediately instead of waiting for the entire scan period. Select a compatible meter in its pairing/transfer mode. The adapter requests the standard Glucose Service (0x1808), subscribes to measurements and RACP, treats the context characteristic as optional, and displays received records progressively. A transfer can be stopped; nothing is automatically saved. The record cursor is not advanced merely because packets arrived.

This requires a meter that actually exposes the standard service. A Bluetooth label, price range or vendor companion app does not establish compatibility. Pairing, PIN entry, firmware behavior and interoperability still require testing with the exact physical meter and Android phone. No meter purchase is required or made by this PR.

Health Connect requests read access to BloodGlucose only. The user selects a period; available records are paginated into review. More than 5,000 records produces an explicit shorter-period message. Health Connect cannot supply readings that the source app has not written. It provides no immediate push notification for every new reading; this app reads on the user's import action. Hardware measurement time and Bluetooth/health-platform latency cannot be promised in milliseconds. [Android synchronization guidance](https://developer.android.com/health-and-fitness/health-connect/sync-data).

## Configuration

Run `node scripts/write-native-env.mjs` before building. `NUTRISOLE_GLUCOSE_STORAGE=phone` is the default. To build the separate account mode, explicitly set `NUTRISOLE_GLUCOSE_STORAGE=account` with `NUTRISOLE_SUPABASE_URL` and `NUTRISOLE_SUPABASE_ANON_KEY` (public anon/publishable only). Account mode requires the existing schema and a sign-in. Sessions are memory-only. No live Supabase migration is applied by this change; see [the existing migration approval record](supabase-approval.md).

The web uses its existing public environment configuration. `?glucoseDemo` / `VITE_GLUCOSE_DEMO=1` explicitly enables ephemeral demo data; it is never a fallback for real phone storage or an unavailable account.

## Validation

`npm run test:glucose` covers the shared parser, repository, import and session logic. Run root typecheck/build, runtime preservation and expansion checks, plus native typecheck/lint/tests. Android instrumentation in `GlucoseCaptureTest.kt` invokes the actual bundled reader on synthetic report fixtures and checks encrypted write/restart behavior. Synthetic fixture scores are not clinical accuracy or physical-device validation.

Android standalone build: run the Windows Ninja preparation script on Windows, then Gradle `:app:assembleRelease`. The QA workflow produces a standalone APK for arm64 phones and x86_64 emulators, plus a synthetic instrumentation APK, on this glucose branch; it is signed with the existing debug key and is not a store release. The emulator build must also be installed and launched without Metro.

Historical OCR experiments and meter research remain in [IMPORT_REPORT.md](IMPORT_REPORT.md) and [meter-research.md](meter-research.md). Their dates and older reader results must not be presented as results for this implementation.
