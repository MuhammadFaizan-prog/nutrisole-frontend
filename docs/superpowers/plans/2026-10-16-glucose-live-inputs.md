# Android glucose capture implementation plan

**Goal:** Make Android manual, attached-report, camera and compatible strip-meter imports responsive and durable in a separate PR.

**Architecture:** Retain shared validation/review. Move photo/PDF recognition to a native worker, persist actual readings in a Keystore-encrypted phone repository, and stream device transfer progress into the review state.

**Stack:** React Native, TypeScript, Kotlin, bundled ML Kit, Android PdfRenderer and Keystore, existing BLE and Health Connect adapters.

- [x] Reproduce false-positive meter parsing and multi-page collection-date loss in `tests/glucose/live-inputs.test.ts`; run `npm run test:glucose` and confirm the regressions fail.
- [x] Add `localRepository.ts` with serialized atomic CRUD, validation, source-record idempotency and bulk writes; verify restart, conversion parity, failures and concurrent mutations.
- [x] Wire Android encrypted storage through native configuration and truthfully label phone persistence in shared actions and views. Keep cloud rows and phone rows separate.
- [x] Add `GlucoseCaptureModule.kt` and package registration. Recognize orientation-aware URI images (up to 2,400 px) and bounded PDF pages on an executor, preserve element coordinates, and return real timing and confidence metadata.
- [x] Route Android OCR/PDF through the module, keep cancellation/error states and remove JS image decoding from the Android capture path.
- [x] Harden the pure GLS session with progressive records, abort/cleanup, optional context, valid dates and relevant RACP completion. Wire incremental discovery and transfer to import review without advancing cursors for unsaved rows.
- [x] Correct parser safety and per-page dates. Keep unsupported inputs empty and retain original values, units and provenance.
- [ ] Run root/native test suites and typechecks, native lint, runtime and six-screen preservation, web build and standalone Android build. Exercise rendered/native journeys, capture timing and document remaining hardware limits.
- [x] Review final diff, commit on `fix/glucose-live-inputs`, push that branch and open a PR targeting `feature/glucose-monitoring`. Attach the PR and leave it unmerged.
