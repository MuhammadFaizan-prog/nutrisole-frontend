# Android glucose capture and responsive imports

The user requests a separate PR based on `feature/glucose-monitoring` at `39fa8b7`, leaving `main` and PR #3 unchanged. Android test-strip meters are the target; this is not continuous glucose monitoring. The supplied proposal supports manual readings and compatible health-data/device sources.

## Design

Keep the shared validated reading model and review screen. Use a bundled Android ML Kit reader for images and PdfRenderer for PDF pages, executing outside the React Native JavaScript thread. Preserve positions so results cannot be confused with reference ranges. Never manufacture a glucose result from an unrelated document or silently replace a decimal/unit. OCR needs user review and cannot be claimed medically accurate.

Provide real, encrypted, durable on-device storage as the default Android mode. Android Keystore AES-GCM protects a snapshot in app-private no-backup storage; writes use atomic replacement. This works without a network or a database migration. Explicitly label phone storage separately from a Supabase account and demo mode. Existing configured cloud mode remains available and isolated; no production database change is authorized by this PR request.

Batch confirmed local imports in one durable transaction. Publish successful readings to the subscribed store immediately. For cloud imports, limit concurrent requests and expose completed rows rather than waiting for a long serial import. Do not show success before persistence completes.

Discover standard Bluetooth Glucose Service meters incrementally, allow selection as soon as a meter appears, and show transferred records progressively. Keep the connection for the user-selected transfer and handle cancellation, optional context characteristics, timeouts, disconnects, malformed timestamps and unrelated RACP responses. Keep the meter clock and source identifiers. Health Connect reads foreground data with explicit read permission, pagination limits and visible errors; it cannot produce records absent from the source app.

## Verification

Add regressions before implementation for false OCR positives, multi-page collection dates, durable reload and import idempotency, failed writes, store races, progressive transfer and subscription cleanup. Run root and native typechecks/tests/lint, preservation checks, web build, and a standalone Android build. Exercise actual rendered routes and native import paths on an Android emulator if available. Measure capture, parsing and save durations without imposing unsupported millisecond OCR or hardware claims. Hardware compatibility requires the actual meter.
