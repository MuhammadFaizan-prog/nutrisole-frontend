# NutriSole frontend requirements

Build onboarding, Home, Scan, Log Meal, Weekly Plan, and Profile exactly from the supplied individual images. Users can navigate, confirm portions, save or log meals, accept/substitute plan meals, and edit local preferences. The six PNGs override the poster and preliminary JSON. Default values and copy remain fixed until an interaction changes them.

Acceptance: real text and controls, original separable photos, useful actions, coherent local changes, reset restores fixtures, no hidden screenshot-hotspot implementation, browser comparison evidence for each screen. Exact missing typefaces and photographic originals must be disclosed. Health/history/edit states are inferred and subordinate.

Non-goals: authentication, backend, Supabase, AI inference, real camera/health access, produce prices/grades, clinical advice, deployment. Success is a runnable frontend and an honest visual/functional verification record.


## Glucose monitoring (feature/glucose-monitoring, draft)

Finger-prick (strip-meter) glucose only. Users record a reading in mg/dL or mmol/L with measurement date/time (separate from entry time), optional context and notes; view, filter (7/30/90 days/all) and chart history; edit; delete with confirmation. Device import (Health Connect, HealthKit, BLE 0x1808, vendor export) is research-gated and disabled. Non-goals: CGM, diagnosis, insulin/treatment advice, alerts posing as medical advice. Acceptance: exact conversion (18.0182) with original value/unit preserved; honest loading/empty/error/offline/signed-out/not-configured states; no sample readings outside an explicit demo flag; owner-only data via RLS. Details: `docs/glucose/README.md`.
