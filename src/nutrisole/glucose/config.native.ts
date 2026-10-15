// Native configuration. Fill these two public values (project URL + publishable/anon
// key) to connect the app to the approved Supabase project. Leave them null to show
// the honest "Configure database" state. Never put a service-role/secret key here.
import type { GlucoseConfig } from './types';

const SUPABASE_URL: string | null = null; // e.g. 'https://zlxefqhzceiloplyszje.supabase.co' after the migration is approved
const SUPABASE_ANON_KEY: string | null = null; // publishable/anon key only
/** Explicit demo flag: in-memory session records, clearly labelled as not saved. */
const GLUCOSE_DEMO = false;

export function readGlucoseConfig(): GlucoseConfig {
  return { supabaseUrl: SUPABASE_URL, supabaseAnonKey: SUPABASE_ANON_KEY, demo: GLUCOSE_DEMO, demoSeed: false };
}
