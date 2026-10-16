// Native configuration: the public Supabase project URL + anon/publishable key come from
// nativeEnv.ts (generated at build time by the QA APK workflow). Left null, the app shows the
// honest "Configure database" state. Never put a service-role/secret key in the app.
import type { GlucoseConfig } from './types';
import { NATIVE_SUPABASE_URL, NATIVE_SUPABASE_ANON_KEY } from './nativeEnv';

/** Explicit demo flag: in-memory session records, clearly labelled as not saved. */
const GLUCOSE_DEMO = false;
const isPublicKey = (k: string | null) => !!k && (k.startsWith('sb_publishable_') || /"role"\s*:\s*"anon"/.test(decodeJwtPayload(k)));
function decodeJwtPayload(k: string): string {
  const part = k.split('.')[1]; if (!part) return '';
  try { const b64 = part.replace(/-/g, '+').replace(/_/g, '/'); return typeof atob === 'function' ? atob(b64 + '='.repeat((4 - (b64.length % 4)) % 4)) : ''; } catch { return ''; }
}

export function readGlucoseConfig(): GlucoseConfig {
  const url = NATIVE_SUPABASE_URL && /^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(NATIVE_SUPABASE_URL) ? NATIVE_SUPABASE_URL : null;
  const key = isPublicKey(NATIVE_SUPABASE_ANON_KEY) ? NATIVE_SUPABASE_ANON_KEY : null; // refuses a service_role key
  return { supabaseUrl: url && key ? url : null, supabaseAnonKey: url && key ? key : null, demo: GLUCOSE_DEMO, demoSeed: false };
}
