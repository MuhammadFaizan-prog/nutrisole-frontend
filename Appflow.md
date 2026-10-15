# NutriSole app flow

Onboarding Skip/Next → Home. Home Scan/camera → Scan → shutter → Log Meal. Log Meal Log saves consumed nutrition then returns Home; Save for later preserves a draft without consumption. Back/close use the stack. Home Plan → Weekly Plan. Home avatar/Profile → Profile. Home Health → inferred local Health; See all → local history.

Portion amount, weight, and size modes validate positive values. Weekly date/day tabs, acceptance, substitutes, details, and feedback use local seeded data. Preference/account/privacy/connection sheets use Save/Cancel. Connection status and scan confidence are demo fixtures. History includes two seeded scans plus new local records; Health has an explicit no-readings state. Invalid input has local error messages. Reference states preserve the original March dates and Pacific Time label.


## Glucose monitoring (feature/glucose-monitoring, draft)

Health → Glucose history (range control, trend chart or state card, readings list) → Add reading (value, unit, measured on, time, context, notes, time zone) → Review sheet (warnings need explicit confirmation) → Reading details (original value/unit, ≈ other unit, provenance) → Edit / Delete (confirmation). States: not configured, sign in, loading, ready/empty, empty range, offline (retry, last-loaded readings marked stale), setup pending (table missing), error. Health connections lists research-only sources; no connect buttons. Web returns from details to the (cleared) form on Back; native replaces the form with details.
