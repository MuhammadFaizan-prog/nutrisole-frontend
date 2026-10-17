// Explicit live QA. Uses dedicated test users and removes only the records it creates.
import { readFile, writeFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
import { createGlucoseStore } from '../../src/nutrisole/glucose/store.ts';
import { PROJECT_URL, PROJECT_KEY } from '../../src/nutrisole/glucose/publicProject.ts';
import { validateGlucoseInput } from '../../src/nutrisole/glucose/validation.ts';
import { nowDisplay } from '../../src/nutrisole/glucose/time.ts';
import { RealtimeClient } from '@supabase/realtime-js';

const env = Object.fromEntries((await readFile('.env.glucose-test-users.local', 'utf8')).trim().split(/\r?\n/).map(line => [line.slice(0,line.indexOf('=')),line.slice(line.indexOf('=')+1)]));
const results = [];
const check = (name, detail = true) => { results.push({ name, detail }); console.log('PASS', name, typeof detail === 'number' ? `${detail} ms` : ''); };
const until = async test => { const deadline = Date.now()+15000; while (!test()) { if (Date.now()>deadline) throw new Error('Timed out waiting for live account state'); await new Promise(r=>setTimeout(r,50)); } };
let persisted = null;
const config = { supabaseUrl: PROJECT_URL, supabaseAnonKey: PROJECT_KEY, demo: false };
const first = createGlucoseStore({ ...config, sessionStorage: { read: async()=>persisted, write: async v=>{persisted=v;} } });
const second = createGlucoseStore(config); const outsider = createGlucoseStore(config);
const created = []; let restarted; let unauthorized;
try {
  await Promise.all([first.start(),second.start(),outsider.start()]);
  for (const [store, tag] of [[first,'A'],[second,'A'],[outsider,'B']]) { const result = await store.signIn(env[`GLUCOSE_TEST_USER_${tag}_EMAIL`],env[`GLUCOSE_TEST_USER_${tag}_PASSWORD`]); assert.equal(result.ok,true); }
  await new Promise(r=>setTimeout(r,1500));
  const now = nowDisplay();
  const validated = validateGlucoseInput({ value:'113',unit:'mg/dL',date:now.date,time:now.time,mealContext:'unspecified',note:'isolated readings repair QA' }); assert.equal(validated.ok,true);
  const start = performance.now(); const saved = await first.save(validated.draft); assert.equal(saved.ok,true); created.push(saved.reading.id); check('Live account create',Math.round(performance.now()-start));
  await until(()=>second.getSnapshot().readings.some(r=>r.id===saved.reading.id)); check('Second client receives insert automatically',Math.round(performance.now()-start));
  assert.equal((await outsider.repository.list()).some(r=>r.id===saved.reading.id),false); check('Other account cannot read the record');
  await assert.rejects(outsider.repository.update(saved.reading.id,{ ...validated.draft,valueOriginal:'999',valueMgDl:999 }));
  await assert.rejects(outsider.repository.remove(saved.reading.id)); check('Other account cannot update or delete the record');
  let denied = false;
  unauthorized = new RealtimeClient(PROJECT_URL+'/realtime/v1',{params:{apikey:PROJECT_KEY},accessToken:async()=>outsider.client.currentSession().accessToken});
  unauthorized.channel('glucose:'+first.client.currentSession().userId,{config:{private:true}}).on('broadcast',{event:'changed'},()=>{throw new Error('Cross-account broadcast received');}).subscribe(status=>{if(status==='CHANNEL_ERROR')denied=true;});
  await until(()=>denied); check('Other account cannot subscribe to private account changes');
  const update = await first.save({...validated.draft,valueOriginal:'116',valueMgDl:116},saved.reading.id); assert.equal(update.ok,true);
  await until(()=>second.getSnapshot().readings.find(r=>r.id===saved.reading.id)?.valueOriginal==='116'); check('Second client receives update automatically');
  const importedDraft = { ...validated.draft, source: { type: 'ocr', provider: 'isolated-readings-qa', device: null, recordId: 'report-'+Date.now(), meta: {originalValue: '113', originalUnit: 'mg/dL', rawText: 'Glucose 113 mg/dL'}, batchId: 'qa-report', dedupeKey: 'old-key' } };
  const imported = await first.repository.create(importedDraft); created.push(imported.id);
  const corrected = await first.repository.update(imported.id, { ...importedDraft, valueOriginal: '117', valueMgDl: 117 });
  assert.equal(corrected.valueOriginal, '117'); assert.deepEqual(corrected.source.meta, importedDraft.source.meta);
  assert.equal(corrected.source.recordId, importedDraft.source.recordId); assert.match(corrected.source.dedupeKey, /\|117\.0$/);
  await assert.rejects(first.repository.create(importedDraft)); check('Saved OCR reading can be corrected without changing its source or duplicating a re-import');
  await first.client.flushSession(); first.dispose();
  restarted = createGlucoseStore({...config,sessionStorage:{read:async()=>persisted,write:async v=>{persisted=v;}}}); await restarted.start();
  assert.equal(restarted.getSnapshot().readings.find(r=>r.id===saved.reading.id)?.valueOriginal,'116'); check('New app instance restores sign-in and account history');
  assert.equal((await restarted.remove(saved.reading.id)).ok,true);
  await until(()=>!second.getSnapshot().readings.some(r=>r.id===saved.reading.id)); check('Second client receives deletion automatically');
  await restarted.signOut(); assert.equal(persisted,''); assert.equal(restarted.getSnapshot().readings.length,0); check('Sign-out clears persisted tokens and visible health data');
  await writeFile('artifacts/native/glucose-live-qa/live-account-results.json',JSON.stringify({at:new Date().toISOString(),project:PROJECT_URL,results},null,2));
} finally {
  for (const id of created) { try { await second.repository.remove(id); } catch { /* already deleted */ } }
  first.dispose(); second.dispose(); outsider.dispose(); restarted?.dispose(); await unauthorized?.removeAllChannels(); await unauthorized?.disconnect();
}
