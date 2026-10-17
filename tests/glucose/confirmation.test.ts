import test from 'node:test';
import assert from 'node:assert/strict';
import { importAction } from '../../src/nutrisole/glucose/importActions.ts';
import { fileToBatch } from '../../src/nutrisole/glucose/import/fileImport.ts';
import { initialExpansionState } from '../../src/nutrisole/extensions/model.ts';
import { initialImportState } from '../../src/nutrisole/glucose/import/view.ts';
import { createGlucoseStore } from '../../src/nutrisole/glucose/store.ts';
import type { Sheet } from '../../src/nutrisole/types.ts';

test('Confirm opens missing fields, validates corrections, and saves the corrected report reading once', async () => {
  const batch = await fileToBatch({name:'lab.csv',mime:'text/csv',bytes:new TextEncoder().encode('Date,Glucose,Unit\n16/10/2026,112,mg/dL')},{});
  assert.equal(batch.candidates[0].time,'');
  const store = createGlucoseStore({supabaseUrl:null,supabaseAnonKey:null,demo:true}); await store.start();
  let s = {...initialExpansionState(),glucoseImport:{...initialImportState(),batch}};
  const sheets: Sheet[] = []; const routes: string[] = [];
  const ctx = () => ({s,setState:(fn:(value:typeof s)=>typeof s)=>{s=fn(s);},store,go:(r:string)=>routes.push(r),back:()=>{},open:(sheet:Sheet)=>sheets.push(sheet)}) as never;
  importAction('import-bulk:confirm-clean',ctx());
  const sheet = sheets.at(-1)!; assert.equal(sheet.saveLabel,'Confirm reading'); assert.ok(sheet.save);
  const values = Object.fromEntries(sheet.fields!.map(f=>[f.key,f.value]));
  assert.match(String(await sheet.save(values)),/measurement time/);
  assert.equal(store.getSnapshot().readings.length,0);
  assert.equal(await sheet.save({...values,value:'114',date:'2026-10-16',time:'09:25'}),undefined);
  assert.equal(s.glucoseImport.batch!.candidates[0].decision,'confirmed');
  importAction('import-save',ctx()); importAction('import-save',ctx());
  for(let i=0;i<50&&!routes.includes('glucose-overview');i++)await new Promise(r=>setTimeout(r,5));
  assert.equal(store.getSnapshot().readings.length,1);
  const reading = store.getSnapshot().readings[0];
  assert.equal(reading.valueOriginal,'114'); assert.equal(reading.unitOriginal,'mg/dL');
  assert.equal(reading.source.type,'file');
  assert.equal(reading.source.meta?.originalValue,'112');
  assert.equal(s.glucoseImport.batch,null);
});


test('saving confirmed rows keeps unfinished report rows available for correction', async () => {
  const batch = await fileToBatch({name:'mixed.csv',mime:'text/csv',bytes:new TextEncoder().encode('Date,Time,Glucose,Unit\n16/10/2026,08:20,112,mg/dL\n16/10/2026,,120,mg/dL')},{});
  const store=createGlucoseStore({supabaseUrl:null,supabaseAnonKey:null,demo:true}); await store.start();
  let s={...initialExpansionState(),glucoseImport:{...initialImportState(),batch}};
  const sheets:Sheet[]=[]; const routes:string[]=[];
  const ctx=()=>({s,setState:(fn:(value:typeof s)=>typeof s)=>{s=fn(s);},store,go:(r:string)=>routes.push(r),back:()=>{},open:(sheet:Sheet)=>sheets.push(sheet)}) as never;
  importAction('import-bulk:confirm-clean',ctx());
  importAction('import-save',ctx());
  for(let i=0;i<50&&s.glucoseImport.saving;i++)await new Promise(r=>setTimeout(r,5));
  assert.equal(store.getSnapshot().readings.length,1);
  assert.equal(s.glucoseImport.batch?.candidates.length,1);
  assert.equal(s.glucoseImport.batch?.candidates[0].value,'120');
  assert.equal(routes.includes('glucose-overview'),false);
  importAction('import-bulk:confirm-clean',ctx());
  const sheet=sheets.at(-1)!; const values=Object.fromEntries(sheet.fields!.map(f=>[f.key,f.value]));
  assert.equal(await sheet.save!({...values,time:'09:25'}),undefined);
  importAction('import-save',ctx());
  for(let i=0;i<50&&s.glucoseImport.saving;i++)await new Promise(r=>setTimeout(r,5));
  assert.equal(store.getSnapshot().readings.length,2); assert.equal(s.glucoseImport.batch,null);
});
