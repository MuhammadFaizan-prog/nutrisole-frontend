// Writes src/nutrisole/glucose/nativeEnv.ts from NUTRISOLE_SUPABASE_URL / NUTRISOLE_SUPABASE_ANON_KEY
// (CI build-time env). Refuses anything but a public anon/publishable key.
import { writeFileSync } from 'node:fs';
const url = (process.env.NUTRISOLE_SUPABASE_URL || '').trim(); const key = (process.env.NUTRISOLE_SUPABASE_ANON_KEY || '').trim();
if (!url && !key) { console.log('No Supabase config given; the app will show "Configure database".'); process.exit(0); }
if (!/^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(url)) { console.error('NUTRISOLE_SUPABASE_URL is not a https://<ref>.supabase.co URL'); process.exit(1); }
let role = null;
if (key.startsWith('sb_publishable_')) role = 'anon';
else { try { role = JSON.parse(Buffer.from(key.split('.')[1], 'base64url').toString()).role; } catch { role = null; } }
if (role !== 'anon') { console.error(`Refusing key with role ${role}: only the public anon/publishable key may ship in the app.`); process.exit(1); }
writeFileSync(new URL('../src/nutrisole/glucose/nativeEnv.ts', import.meta.url), `// GENERATED at build time by scripts/write-native-env.mjs. Public values only (RLS protects rows).\nexport const NATIVE_SUPABASE_URL: string | null = ${JSON.stringify(url)};\nexport const NATIVE_SUPABASE_ANON_KEY: string | null = ${JSON.stringify(key)};\n`);
console.log(`nativeEnv.ts written for ${url} (key role: ${role})`);
