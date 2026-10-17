# Glucose readings repair

User scope: manual entry, report/photo extraction, editable confirmation, persistent Supabase readings. Device work is explicitly deferred. Keep PR #4 on fix/glucose-live-inputs, preserve main, PR #3, the six original screens and their artwork.

## Intended behavior

Use NutriSole's existing warm panels, typography and green actions. Review shows editable value, unit, date/time and meal context, with an actionable error when a required field is absent. A checked reading is saved with one action; no warning/confirmation chain or confidence badges. Original extracted text remains available as source detail. Report extraction must never turn reference ranges, lipid values, HbA1c or identifiers into measured blood glucose. Digital PDFs use their text before OCR; scans use image recognition and keep uncertain output editable.

Account storage is the configured default, with encrypted native session persistence, secure account boundaries, immediate local state updates after writes and authenticated realtime refresh across clients. Existing live schema/data must be preserved. No service key in the app. Explicit demo/phone modes remain test/legacy options, never silently substitute for cloud saving.

## Work

- [ ] Repair extraction: inspect native PDF/image pipeline and parser, improve native text extraction/layout and missing-field behavior, add regression fixtures and accuracy tests. Files: native Android GlucoseCaptureModule.kt and focused helpers, glucose/import/fileImport.ts, labText.ts, OCR normalization, tests/glucose extraction tests. Delegate only this scope; do not alter auth, review actions or UI.
- [ ] Repair account configuration/session/realtime: config/nativeEnv generator/workflow, SupabaseRest/store, secure native session bridge, Supabase publication migration. Test session restart, refresh, account races and remote CRUD events. Verify live RLS/grants without exposing health records or credentials.
- [ ] Replace review interaction with clear editable forms, fix Confirm no-op, simplify glucose UI copy to existing app conventions. Files: importActions/review/view, extensions glucose scenes and native sheet/adapters. Regression tests for incomplete time/unit, edits, confirmation, keyboard and save failures.
- [ ] Verify actual live account create/read/update/delete and isolation with dedicated test data, then build standalone APK and run Android UI tests including missing-time report editing and restart persistence. Inspect screenshots. Run root/native checks and preservation guards.
- [ ] Perform spec review, then quality review, fix findings, update PR #4 with measured evidence and deliver corrected APK. Device integration remains outside this correction by user instruction.

No assumptions of millisecond OCR or network writes; measure feedback and write latency separately. Do not label the feature complete from synthetic parser tests alone.
