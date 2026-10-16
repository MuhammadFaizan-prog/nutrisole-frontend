# NutriSole glucose import: Stage G-2 report (2026-10-16)

Branch `feature/glucose-monitoring`, draft PR #3 (MuhammadFaizan-prog/nutrisole-frontend). **Do not merge.** Nothing was changed on `main`, the CV branches, PR #1 and #2, or the live Supabase project `nutrisole`.

## Build identity
| | |
|---|---|
| App commit (APK built from it) | `3593252ac5fa36f941bd3191487d844c8c16e91c` |
| Tree | `d2cc22453e00cc75232518acdf92b1948b6e59fa`, identical to local `cc16640` (all 956 blobs and modes match) |
| QA APK run | https://github.com/MuhammadFaizan-prog/nutrisole-frontend/actions/runs/38884562373 (`success`) |
| Artifact | `nutrisole-glucose-qa-apk-3593252` (id `12039292884`), https://github.com/MuhammadFaizan-prog/nutrisole-frontend/actions/runs/38884562373/artifacts/12039292884 (45,806,909-byte zip, sha256 `80084674c805c3cf9107a90302d64353389c4b2e378f67ef0c2152f947b74c98`, kept 30 days) |
| APK | `nutrisole-glucose-qa-3593252.apk`, 45,797,697 (≈43.7 MiB) bytes |
| APK SHA-256 | `5874419d8f7331e166ceb1a123cc73e11e983c967d89d1fae3670018e9433fb6` (checked against the `.sha256` file and `build-info.txt`) |
| JS bundle | `assets/index.android.bundle` (3,055,384 bytes, Hermes bytecode) is in the APK, so no Metro is needed. Import markers: import-review 1, ble:gls 1, Health Connect 4, ML Kit (on this phone) 1, Confirm all unflagged 2. Package `com.muhammadfaizan.nutrisole` 1.0.4 (versionCode 5), targetSdk 36, arm64-v8a. CAMERA, BLUETOOTH_SCAN, BLUETOOTH_CONNECT and health.READ_BLOOD_GLUCOSE are present. |

This report is committed separately as `docs/glucose/IMPORT_REPORT.md`. The commit touches docs only, so the workflow's `paths-ignore` skips it and the APK above remains the build of the app code.

### Remote and local tree mismatch (fixed)
Remote `947497b` (tree `5cd8f37`) and local `cc16640` (tree `d2cc224`) had the same 956 files with byte-identical blobs. The only difference was the file mode of `supabase/tests/run-local.sh`: `100755` locally and `100644` on the remote. The file first reached the remote through the earlier contents-API sync (`gh_sync_glucose.py`). That API always writes `100644` and cannot set the executable bit, and later blob-based syncs saw an unchanged blob. Commit `3593252` sets the mode to `100755`, and the resulting remote tree is exactly `d2cc224`.

Intentional inclusions and exclusions:
- `public/tesseract/eng.traineddata.gz` (2.95 MB) **stays in Git**. It is an app runtime asset: web OCR loads it from `langPath: <base>tesseract` so it works offline and without a third-party CDN.
- `tests/glucose/fixtures/*` (synthetic CSV, XLSX, PDF, PNG and JPG, each under 62 KB) **stay**. The glucose test suite needs them.
- Review videos (`glucose_import_flow.mp4`, `glucose_manual_flow.mp4`) and screenshots **are not in Git**. They live only in the project files. APKs are git-ignored (`artifacts/native/*.apk`) and come from CI artifacts.

## What works, and how well it is verified
| Route | Status |
|---|---|
| CSV / XLSX (meter and app exports: Accu-Chek 360-style, Contour, mySugr, generic) | **Works.** Columns map automatically, with manual mapping as a fallback. Covered by tests. |
| PDF with a text layer (pdf.js) | **Works on web.** |
| Image OCR (tesseract.js, self-hosted language data) | **Works on web.** It read 12/12 synthetic fixtures (lab reports in Chughtai, IDC, Excel Labs and Shaukat Khanum styles, plus mg/dL and mmol/L meter screens, as clean images and "photo" variants). **This result is optimistic:** the parser was tuned on these same images, there is no held-out set, and no real photos were tested. Expect lower accuracy on real phone photos. |
| ML Kit OCR on device (`@react-native-ml-kit/text-recognition`) | **Code only (beta). Not verified on a device.** |
| Health Connect (`react-native-health-connect`, minSdk 26) | **Code only (beta). Not verified on a device.** No Pakistan-available meter app is known to write glucose to it. |
| Bluetooth meter (BLE Glucose Profile 0x1808: 0x2A18/0x2A34/0x2A52 + RACP, `react-native-ble-plx`) | **Code only (beta).** Tested only against a simulated meter. Needs a real meter (Accu-Chek Instant, Bluetooth model). |
| Apple HealthKit | **Typed mapper only.** No native module. |

HbA1c, eAG and urine values in lab reports are kept separate and are never saved as blood-glucose readings.

### Review before save, and dedupe
- Every imported reading appears on a **Review import** screen first. Nothing is saved until the user confirms. Each row can be confirmed, edited or rejected, and **Confirm all unflagged** handles the rest in bulk.
- Unit detection (mg/dL vs mmol/L) runs on each import. Values outside 10–600 mg/dL and likely unit mix-ups are flagged, and flagged rows need an explicit decision.
- Dedupe runs at review time, within the batch and against existing history, using `dedupe_key` ("minute instant|mg/dL"). The database index on `dedupe_key` is deliberately **not unique**, because two genuine readings in the same minute are allowed; the review screen asks the user instead. Re-importing the same source record is blocked by the unique import index `(user_id, source_type, source_provider, source_device, source_record_id)`.

## Tests
| Suite | Result |
|---|---|
| `npm run test:glucose` (domain, parsers, OCR text, review and dedupe, adapters) | **48/48** |
| `npm run test:glucose:db` (local PostgreSQL + `auth.uid()` stub, two users, RLS) | **10/10** |
| `npm --prefix native test` | **34/34** |
| CI (`android-glucose-qa-apk`) on `3593252` | glucose and native tests pass, then the release APK build: success |

The database tests ran against a **local** database only. Nothing ran against live Supabase.

## Database: draft, NOT applied
`supabase/migrations/20261016000000_create_glucose_readings.sql` (with rollback in `supabase/rollback/`) now also adds:
- `source_type` values `file` and `ocr`
- `source_meta` (jsonb: file name, parser and OCR engine, confidence)
- `import_batch_id`
- `dedupe_key` (lookup index, not unique) and a unique import-idempotency index on the source record

**This waits for you to say "apply it".** Until then, the live `nutrisole` project has no glucose table and the app shows "Setup pending". The full SQL, risk and rollback are in `docs/glucose/supabase-approval.md`.

## Phone test steps (Android, arm64)
1. Download the artifact `nutrisole-glucose-qa-apk-3593252` from the run above, unzip it, and check the APK: `sha256sum nutrisole-glucose-qa-3593252.apk` must print `5874419d8f7331e166ceb1a123cc73e11e983c967d89d1fae3670018e9433fb6`.
2. Install it: `adb install -r nutrisole-glucose-qa-3593252.apk`, or copy it to the phone and allow "install unknown apps". It is signed with the debug keystore, so uninstall any differently signed NutriSole build first.
3. Open NutriSole → Glucose. **This QA APK has no Supabase URL or key and demo is off** (`src/nutrisole/glucose/config.native.ts`), so it shows **Database not configured**. Parsing, Review import, flags, edit, reject and in-batch dedupe all work. Pressing save shows "imported readings cannot be saved", and nothing is stored. Testing save, history dedupe and re-import needs either the migration applied plus the URL and key filled in, or a rebuild with `GLUCOSE_DEMO = true` (in-memory, labelled "Demo mode · not saved").
4. **File import:** Import → File. Pick a meter CSV or XLSX (or one of `tests/glucose/fixtures/*.csv`/`.xlsx` copied to the phone). Check the column mapping, units and flags on Review import. Confirm a few rows and reject one. A file that repeats a reading should flag it as a duplicate within the batch. Save should show the honest "cannot be saved in this build" notice. With a database or demo build, re-importing the same file should add nothing.
5. **Photo / OCR (ML Kit):** Import → Photo. Take a photo of a real lab report or meter screen, then one from the gallery. Note which values were read correctly, missed, or misread (value, unit, date/time). This is the first real-photo test.
6. **PDF:** import a lab PDF that has a text layer. A scanned PDF without text is expected to need the photo/OCR route.
7. **Health Connect** (Android 9+ with the Health Connect app): Connections → Health Connect. Grant "Read blood glucose". Readings appear only if some app has written glucose to Health Connect.
8. **Bluetooth meter** (only with a BLE GLS meter such as the Accu-Chek Instant BT model): Connections → Bluetooth meter. Grant Nearby devices / Bluetooth scan and connect. Pair (passkey on the meter), sync, then review.
9. After each step, check that nothing reaches History before you confirm, and that units and times match the source.
10. Send notes or screenshots of any misread value, crash or permission problem.

## Still open
- Approve the migration ("apply it"), then set the public URL and publishable key and re-run the two-user check on the live project.
- Real-device verification for ML Kit OCR, Health Connect and BLE. Real-photo OCR accuracy is unknown.
- HealthKit and an iOS build have not been started beyond types.
- Local commit history (`cc16640`) and remote history (`3593252`) differ in commit SHAs because of the API-based sync. The trees are identical.
