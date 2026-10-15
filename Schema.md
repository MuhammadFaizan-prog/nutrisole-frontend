# Synthetic local data schema

No database. DemoState version 1 includes profile, connection/image-retention preferences, consumed meals, drafts, accepted day/meal keys, substitutes, and feedback. The current meal type represents Apple implicitly and includes id, submission key, edible grams, calories, and created timestamp. Duplicate submission keys cannot increase totals twice. Drafts do not contribute to consumed totals; converting a draft removes its matching saved record.

Storage key `nutrisole.demo.v1` contains synthetic data only. Version and shape checks reject corrupt storage. Reset clears this app's synthetic namespace only. On web use localStorage; on native use AsyncStorage. Screen history and transient sheet state remain in memory. Original Home/Plan initial meal summaries intentionally describe separate fixtures.


## Glucose monitoring (feature/glucose-monitoring, draft)

Glucose uses Postgres, not local storage: `public.glucose_readings` (id, user_id → auth.users on delete cascade, measured_at, tz_offset_minutes, tz_name, value_original numeric, unit_original mg/dL|mmol/L, generated value_mg_dl = round(v × 18.0182, 2) for mmol/L, meal_context, note ≤500, source_type/provider/device/record_id, import_version, created_at, updated_at). Index (user_id, measured_at desc, id desc); partial unique import key per user. Manual same-time duplicates are allowed (warned in the app). Migration and rollback in `supabase/`; not applied to the live project. No glucose data is written to localStorage/AsyncStorage.
