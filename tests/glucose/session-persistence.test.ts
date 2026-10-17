import test from 'node:test';
import assert from 'node:assert/strict';
import { SupabaseRest, type Session, type FetchLike } from '../../src/nutrisole/glucose/supabaseRest.ts';

const session: Session = {accessToken:'test-token',refreshToken:'test-refresh',userId:'user-a',email:'qa@example.invalid',expiresAt:Date.now()+3600000};
const response = (status:number,body:unknown):Awaited<ReturnType<FetchLike>> => ({ok:status<300,status,json:async()=>body,text:async()=>JSON.stringify(body)});
test('restored sign-in survives a new client and sign-out durably clears it',async()=>{
  let value:string|null=JSON.stringify(session);
  const storage={read:async()=>value,write:async(v:string)=>{value=v;}};
  const client=new SupabaseRest('https://test.supabase.co','public',async()=>response(204,null),storage);
  await client.initialize(); assert.equal(client.currentSession()?.userId,'user-a');
  await client.signOut(); assert.equal(value,'');
  const next=new SupabaseRest('https://test.supabase.co','public',undefined,storage); await next.initialize(); assert.equal(next.currentSession(),null);
});
test('slow restore cannot overwrite a newer sign-in or sign-out',async()=>{
  let finish!:(v:string)=>void;
  const client=new SupabaseRest('https://test.supabase.co','public',async()=>response(204,null),{read:()=>new Promise(r=>{finish=r;}),write:async()=>{}});
  const start=client.initialize(); await client.signOut(); finish(JSON.stringify(session)); await start;
  assert.equal(client.currentSession(),null);
});
test('temporary refresh failure keeps the session for retry; revoked tokens clear it',async()=>{
  const codes=[503,400];let value='';
  const client=new SupabaseRest('https://test.supabase.co','public',async()=>response(codes.shift()!,{}),{read:async()=>null,write:async(v:string)=>{value=v;}});
  client.adoptSession({...session,expiresAt:0}); await assert.rejects(client.refresh());
  assert.equal(client.currentSession()?.userId,'user-a');
  assert.equal(await client.refresh(),false); assert.equal(value,'');
});
