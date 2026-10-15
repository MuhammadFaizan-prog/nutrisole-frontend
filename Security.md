# NutriSole prototype boundaries

Only synthetic fixture data. No sign-in, real health import, real AI, clinical advice, camera permission, keys, API requests, telemetry, or uploaded user content. Connected Apple Health and 97% Apple are demonstration labels.

Validate portions and edit fields. Recoverable storage errors fall back to clean fixtures; no deletion of external user files. Reset is scoped to synthetic app state. Local preview is a development service, not a production deployment. Dependencies are installed from npm; preserve both lockfiles. Future health/auth/inference integrations need separate server and privacy design.


## Glucose monitoring (feature/glucose-monitoring, draft)

Glucose data is health data. Owner-only RLS on all four operations (verified locally with two identities); anon has no grants; `user_id` and `value_mg_dl` are not client-writable; imported values are immutable. Tokens are memory-only; errors never echo values; nothing is logged. Client holds only the publishable key; service-role keys stay out of the repo, CI and apps. Account deletion cascades readings server-side; in-app account deletion is not implemented yet. Consent for imports is opt-in and currently moot (all adapters disabled). Approval handoff: `docs/glucose/supabase-approval.md`.
