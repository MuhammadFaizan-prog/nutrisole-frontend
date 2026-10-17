// Native configuration: the public Supabase project URL + anon/publishable key come from
// nativeEnv.ts (generated at build time by the QA APK workflow). Android defaults
// to encrypted phone storage. Never put a service-role/secret key in the app.
import type { GlucoseConfig } from './types';
import { NATIVE_SUPABASE_URL, NATIVE_SUPABASE_ANON_KEY, NATIVE_GLUCOSE_STORAGE } from './nativeEnv';
import { Platform } from 'react-native';
import { phoneGlucoseStorage } from './nativeCapture.native';
import { PROJECT_KEY, PROJECT_URL } from './publicProject';
import { accountSessionStorage } from './sessionStorage';

/** Explicit demo flag: in-memory session records, clearly labelled as not saved. */
const GLUCOSE_DEMO = false;
const isPublicKey = (k: string | null) => !!k && (k.startsWith('sb_publishable_') || /"role"\s*:\s*"anon"/.test(decodeJwtPayload(k)));
function decodeJwtPayload(k: string): string {
  const part = k.split('.')[1]; if (!part) return '';
  try { const b64 = part.replace(/-/g, '+').replace(/_/g, '/'); return typeof atob === 'function' ? atob(b64 + '='.repeat((4 - (b64.length % 4)) % 4)) : ''; } catch { return ''; }
}

export function readGlucoseConfig(): GlucoseConfig {
  const configuredUrl = NATIVE_SUPABASE_URL || PROJECT_URL;
  const configuredKey = NATIVE_SUPABASE_ANON_KEY || PROJECT_KEY;
  const url = /^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(configuredUrl) ? configuredUrl : null;
  const key = isPublicKey(configuredKey) ? configuredKey : null;
  // Android works without a cloud account. Phone readings stay separate from cloud
  // records; no production migration or hidden upload is performed.
  return { supabaseUrl: url && key ? url : null, supabaseAnonKey: url && key ? key : null, sessionStorage: url ? accountSessionStorage(url) : undefined, demo: GLUCOSE_DEMO, demoSeed: false, ...(Platform.OS === 'android' && NATIVE_GLUCOSE_STORAGE === 'phone' ? { localStorage: phoneGlucoseStorage } : {}) };
}
