// Writes src/nutrisole/glucose/nativeEnv.ts from NUTRISOLE_SUPABASE_URL / NUTRISOLE_SUPABASE_ANON_KEY
// (CI build-time env). Refuses anything but a public anon/publishable key.
import { writeFileSync } from 'node:fs';
const storage = process.env.NUTRISOLE_GLUCOSE_STORAGE || 'phone';
if (!['phone', 'account'].includes(storage)) throw new Error('NUTRISOLE_GLUCOSE_STORAGE must be phone or account');
const url = (process.env.NUTRISOLE_SUPABASE_URL || '').trim(); const key = (process.env.NUTRISOLE_SUPABASE_ANON_KEY || '').trim();
const write = (url, key) => writeFileSync(new URL('../src/nutrisole/glucose/nativeEnv.ts', import.meta.url), `// GENERATED at build time. Public values only; phone and account records remain separate.\nexport const NATIVE_SUPABASE_URL: string | null = ${JSON.stringify(url)};\nexport const NATIVE_SUPABASE_ANON_KEY: string | null = ${JSON.stringify(key)};\nexport const NATIVE_GLUCOSE_STORAGE: 'phone' | 'account' = ${JSON.stringify(storage)};\n`);
if (!url && !key) { write(null, null); console.log(`No cloud config; glucose storage mode: ${storage}.`); process.exit(0); }
if (!/^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(url)) { console.error('NUTRISOLE_SUPABASE_URL is not a https://<ref>.supabase.co URL'); process.exit(1); }
let role = null;
if (key.startsWith('sb_publishable_')) role = 'anon';
else { try { role = JSON.parse(Buffer.from(key.split('.')[1], 'base64url').toString()).role; } catch { role = null; } }
if (role !== 'anon') { console.error(`Refusing key with role ${role}: only the public anon/publishable key may ship in the app.`); process.exit(1); }
write(url, key);
console.log(`nativeEnv.ts written for ${url} (key role: ${role})`);
