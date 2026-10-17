// Web (Vite) configuration. Only the public project URL and the publishable/anon key
// may ever be supplied to the client; row access is enforced by Postgres RLS.
// A service-role or secret key must never be placed in a VITE_ variable.
import type { GlucoseConfig } from './types';
import { PROJECT_KEY, PROJECT_URL } from './publicProject';
import { accountSessionStorage } from './sessionStorage';

type ViteEnv = Record<string, string | undefined>;
function viteEnv(): ViteEnv {
  try { return ((import.meta as unknown as { env?: ViteEnv }).env) || {}; } catch { return {}; }
}
function demoFromUrl(): boolean {
  try { return typeof location !== 'undefined' && new URLSearchParams(location.search).has('glucoseDemo'); } catch { return false; }
}
function demoSeedFromUrl(): boolean {
  try { return typeof location !== 'undefined' && new URLSearchParams(location.search).get('glucoseDemo') === 'seed'; } catch { return false; }
}

export function readGlucoseConfig(): GlucoseConfig {
  const env = viteEnv();
  const url = (env.VITE_SUPABASE_URL || PROJECT_URL).trim();
  const key = (env.VITE_SUPABASE_ANON_KEY || PROJECT_KEY).trim();
  const demo = env.VITE_GLUCOSE_DEMO === '1' || demoFromUrl();
  return { supabaseUrl: /^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(url) || /^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(url) ? url : null, supabaseAnonKey: key || null, sessionStorage: accountSessionStorage(url), demo, demoSeed: demo && demoSeedFromUrl() };
}
