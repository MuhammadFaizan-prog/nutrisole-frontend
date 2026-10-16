// Build-time public config for the Android app. The QA APK workflow
// (.github/workflows/android-glucose-qa-apk.yml) regenerates this file from repository
// variables (NUTRISOLE_SUPABASE_URL / NUTRISOLE_SUPABASE_ANON_KEY, with the public defaults in
// the workflow) before bundling. Only the project URL and the public anon/publishable key may
// appear here: rows are protected by Postgres RLS. Never a service-role or secret key.
export const NATIVE_SUPABASE_URL: string | null = null;
export const NATIVE_SUPABASE_ANON_KEY: string | null = null;
/** Explicit build mode. The default saves real readings on Android without a server. */
export const NATIVE_GLUCOSE_STORAGE: 'phone' | 'account' = 'phone';
