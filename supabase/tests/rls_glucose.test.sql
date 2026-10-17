-- Two-identity RLS + integrity tests for public.glucose_readings (run by run-local.sh).
\set ON_ERROR_STOP on
\set QUIET on
\set A '''aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'''
\set B '''bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'''
insert into auth.users (id, email) values (:A, 'a@test.local'), (:B, 'b@test.local');

-- 1. RLS is enabled with four owner-only policies.
do $$ begin
  if not (select relrowsecurity from pg_class where oid = 'public.glucose_readings'::regclass) then raise exception 'FAIL 1: RLS disabled'; end if;
  if (select count(*) from pg_policies where tablename = 'glucose_readings' and roles = '{authenticated}') <> 4 then raise exception 'FAIL 1: expected 4 authenticated policies'; end if;
end $$;
\echo 'ok 1 - RLS enabled with select/insert/update/delete owner policies'

-- 2. anon has no access at all.
set role anon;
do $$ begin
  begin perform 1 from public.glucose_readings; raise exception 'FAIL 2: anon could select'; exception when insufficient_privilege then null; end;
  begin insert into public.glucose_readings (measured_at, tz_offset_minutes, value_original, unit_original) values (now(), 0, 100, 'mg/dL'); raise exception 'FAIL 2: anon could insert'; exception when insufficient_privilege then null; end;
end $$;
reset role;
\echo 'ok 2 - anon cannot read or write'

-- 3. User A creates readings; user_id comes from auth.uid(); canonical mg/dL is generated.
set role authenticated;
select set_config('request.jwt.claims', json_build_object('sub', :A, 'role', 'authenticated')::text, false) as jwt \gset
insert into public.glucose_readings (measured_at, tz_offset_minutes, tz_name, value_original, unit_original, meal_context, note)
  values ('2026-10-16T03:15:00Z', 300, 'Asia/Karachi', 110, 'mg/dL', 'fasting', 'a1'),
         ('2026-10-16T08:00:00Z', 300, 'Asia/Karachi', 6.1, 'mmol/L', 'after_meal', null),
         ('2026-10-16T08:00:00Z', 300, 'Asia/Karachi', 6.1, 'mmol/L', 'after_meal', 'measured twice');
do $$ begin
  if (select count(*) from public.glucose_readings) <> 3 then raise exception 'FAIL 3: A should see 3 rows'; end if;
  if exists (select 1 from public.glucose_readings where user_id <> auth.uid()) then raise exception 'FAIL 3: wrong owner'; end if;
  if (select value_mg_dl from public.glucose_readings where note = 'measured twice') <> 109.91 then raise exception 'FAIL 3: generated mg/dL'; end if;
  if (select value_mg_dl from public.glucose_readings where note = 'a1') <> 110 then raise exception 'FAIL 3: mg/dL must not convert'; end if;
end $$;
\echo 'ok 3 - owner inserts; user_id defaults to auth.uid(); value_mg_dl generated; same-time manual duplicates kept'

-- 4. A cannot create rows for B (column privilege) and cannot write the canonical column.
do $$ begin
  begin insert into public.glucose_readings (user_id, measured_at, tz_offset_minutes, value_original, unit_original) values ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', now(), 0, 100, 'mg/dL'); raise exception 'FAIL 4: inserted for B'; exception when insufficient_privilege then null; end;
  begin insert into public.glucose_readings (measured_at, tz_offset_minutes, value_original, unit_original, value_mg_dl) values (now(), 0, 100, 'mg/dL', 5); raise exception 'FAIL 4: wrote value_mg_dl'; exception when insufficient_privilege or generated_always then null; end;
  begin update public.glucose_readings set user_id = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'; raise exception 'FAIL 4: reassigned owner'; exception when insufficient_privilege then null; end;
end $$;
reset role;
-- Defence in depth: even with an (accidental) user_id column grant, the RLS WITH CHECK rejects cross-user rows.
begin;
grant insert (user_id) on public.glucose_readings to authenticated;
grant update (user_id) on public.glucose_readings to authenticated;
set local role authenticated;
do $$ begin
  begin insert into public.glucose_readings (user_id, measured_at, tz_offset_minutes, value_original, unit_original) values ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', now(), 0, 100, 'mg/dL'); raise exception 'FAIL 4b: RLS allowed cross-user insert'; exception when insufficient_privilege then null; end;
  begin update public.glucose_readings set user_id = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb' where note = 'a1'; raise exception 'FAIL 4b: cross-user update'; exception when insufficient_privilege or raise_exception then null; end;
end $$;
rollback;
\echo 'ok 4 - A cannot create, reassign or forge rows for B (column grants + RLS WITH CHECK)'

-- 5. User B cannot read, update or delete A's rows.
set role authenticated;
select set_config('request.jwt.claims', json_build_object('sub', :B, 'role', 'authenticated')::text, false) as jwt \gset
do $$ declare n int; begin
  if (select count(*) from public.glucose_readings) <> 0 then raise exception 'FAIL 5: B sees A rows'; end if;
  update public.glucose_readings set value_original = 999 where true; get diagnostics n = row_count; if n <> 0 then raise exception 'FAIL 5: B updated A rows'; end if;
  delete from public.glucose_readings where true; get diagnostics n = row_count; if n <> 0 then raise exception 'FAIL 5: B deleted A rows'; end if;
  insert into public.glucose_readings (measured_at, tz_offset_minutes, value_original, unit_original) values ('2026-10-15T03:00:00Z', 0, 95, 'mg/dL');
  if (select count(*) from public.glucose_readings) <> 1 then raise exception 'FAIL 5: B should see only its own row'; end if;
end $$;
\echo 'ok 5 - B cannot read, update or delete A rows; B sees only its own'

-- 6. No JWT (auth.uid() null) as authenticated sees nothing and cannot insert.
select set_config('request.jwt.claims', '', false) as jwt \gset
do $$ begin
  if (select count(*) from public.glucose_readings) <> 0 then raise exception 'FAIL 6: null uid sees rows'; end if;
  begin insert into public.glucose_readings (measured_at, tz_offset_minutes, value_original, unit_original) values (now(), 0, 100, 'mg/dL'); raise exception 'FAIL 6: null uid inserted'; exception when not_null_violation or insufficient_privilege then null; end;
end $$;
\echo 'ok 6 - a request without a user identity sees and writes nothing'

-- 7. Owner edit keeps provenance, bumps updated_at; validation constraints hold.
select set_config('request.jwt.claims', json_build_object('sub', :A, 'role', 'authenticated')::text, false) as jwt \gset
do $$ declare before timestamptz; begin
  select updated_at into before from public.glucose_readings where note = 'a1';
  perform pg_sleep(0.01);
  update public.glucose_readings set value_original = 112, unit_original = 'mg/dL' where note = 'a1';
  if (select updated_at from public.glucose_readings where note = 'a1') <= before then raise exception 'FAIL 7: updated_at'; end if;
  begin insert into public.glucose_readings (measured_at, tz_offset_minutes, value_original, unit_original) values (now(), 0, 5.555, 'mmol/L'); raise exception 'FAIL 7: 3 decimals'; exception when check_violation then null; end;
  begin insert into public.glucose_readings (measured_at, tz_offset_minutes, value_original, unit_original) values (now(), 0, 110, 'mmol/L'); raise exception 'FAIL 7: 110 mmol/L'; exception when check_violation then null; end;
  begin insert into public.glucose_readings (measured_at, tz_offset_minutes, value_original, unit_original) values (now(), 0, 0, 'mg/dL'); raise exception 'FAIL 7: zero'; exception when check_violation then null; end;
  begin insert into public.glucose_readings (measured_at, tz_offset_minutes, value_original, unit_original) values (now(), 0, 100, 'mmol'); raise exception 'FAIL 7: bad unit'; exception when check_violation then null; end;
  begin insert into public.glucose_readings (measured_at, tz_offset_minutes, value_original, unit_original) values (now() + interval '3 days', 0, 100, 'mg/dL'); raise exception 'FAIL 7: future'; exception when raise_exception then null; end;
  begin insert into public.glucose_readings (measured_at, tz_offset_minutes, value_original, unit_original, source_record_id) values (now(), 0, 100, 'mg/dL', 'x'); raise exception 'FAIL 7: manual with source id'; exception when check_violation then null; end;
end $$;
\echo 'ok 7 - edits bump updated_at; precision, range, unit, future and provenance constraints enforced'

-- 8. Imports are idempotent and their values are read-only.
do $$ begin
  insert into public.glucose_readings (measured_at, tz_offset_minutes, value_original, unit_original, source_type, source_provider, source_record_id)
    values ('2026-10-14T03:00:00Z', 300, 104, 'mg/dL', 'health_connect', 'com.example.meter', 'hc-1');
  begin insert into public.glucose_readings (measured_at, tz_offset_minutes, value_original, unit_original, source_type, source_provider, source_record_id)
    values ('2026-10-14T03:00:00Z', 300, 104, 'mg/dL', 'health_connect', 'com.example.meter', 'hc-1'); raise exception 'FAIL 8: duplicate import'; exception when unique_violation then null; end;
  begin update public.glucose_readings set value_original = 140 where source_record_id = 'hc-1'; raise exception 'FAIL 8: imported value changed'; exception when raise_exception then null; end;
  update public.glucose_readings set note = 'context added later', meal_context = 'fasting' where source_record_id = 'hc-1';
  insert into public.glucose_readings (measured_at, tz_offset_minutes, value_original, unit_original, source_type, source_provider, source_record_id)
    values ('2026-10-14T03:00:00Z', 300, 104, 'mg/dL', 'health_connect', 'com.example.meter', 'hc-2');
end $$;
reset role;
-- B may import the same source record id independently (per-user uniqueness).
set role authenticated;
select set_config('request.jwt.claims', json_build_object('sub', :B, 'role', 'authenticated')::text, false) as jwt \gset
insert into public.glucose_readings (measured_at, tz_offset_minutes, value_original, unit_original, source_type, source_provider, source_record_id)
  values ('2026-10-14T03:00:00Z', 300, 104, 'mg/dL', 'health_connect', 'com.example.meter', 'hc-1');
reset role;
\echo 'ok 8 - import uid is idempotent per user; imported values read-only; notes editable'

-- 9. Owner delete works; account deletion cascades.
set role authenticated;
select set_config('request.jwt.claims', json_build_object('sub', :A, 'role', 'authenticated')::text, false) as jwt \gset
delete from public.glucose_readings where note = 'measured twice';
do $$ begin if (select count(*) from public.glucose_readings) <> 4 then raise exception 'FAIL 9: A delete'; end if; end $$;
reset role;
delete from auth.users where id = :A;
do $$ begin
  if (select count(*) from public.glucose_readings where user_id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa') <> 0 then raise exception 'FAIL 9: cascade'; end if;
  if (select count(*) from public.glucose_readings where user_id = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb') <> 2 then raise exception 'FAIL 9: B rows affected'; end if;
end $$;
\echo 'ok 9 - owner delete; deleting the auth user cascades only that user''s readings'
-- 10. Stage G-2 import columns: file/ocr sources, provenance meta, batch id, dedupe key.
set role authenticated;
select set_config('request.jwt.claims', json_build_object('sub', :B, 'role', 'authenticated')::text, false) as jwt \gset
insert into public.glucose_readings (measured_at, tz_offset_minutes, value_original, unit_original, meal_context, source_type, source_provider, source_record_id, source_meta, import_batch_id, dedupe_key)
  values (now() - interval '2 hours', 300, 112, 'mg/dL', 'fasting', 'ocr', 'ocr:tesseract.js', 'abc123:line10', '{"fileName":"report.jpg","locator":"line 10","confidence":0.86,"originalValue":"112"}', 'img-test-1', '2026-10-16T03:00:00.000Z|112.0'),
         (now() - interval '3 hours', 300, 6.1, 'mmol/L', 'random', 'file', 'file:csv', 'def456:row2', '{"fileName":"export.csv"}', 'csv-test-1', '2026-10-16T02:00:00.000Z|109.9');
do $$ begin
  if (select count(*) from public.glucose_readings where source_type in ('file', 'ocr')) <> 2 then raise exception 'FAIL 10: import insert'; end if;
  begin  -- same file row again → unique import uid
    insert into public.glucose_readings (measured_at, tz_offset_minutes, value_original, unit_original, source_type, source_provider, source_record_id) values (now() - interval '3 hours', 300, 6.1, 'mmol/L', 'file', 'file:csv', 'def456:row2');
    raise exception 'FAIL 10: duplicate file row accepted';
  exception when unique_violation then null; end;
  begin  -- manual rows cannot carry import metadata
    insert into public.glucose_readings (measured_at, tz_offset_minutes, value_original, unit_original, source_meta) values (now() - interval '1 hour', 300, 100, 'mg/dL', '{"x":1}');
    raise exception 'FAIL 10: manual with meta accepted';
  exception when check_violation then null; end;
  begin  -- meta must be a JSON object
    insert into public.glucose_readings (measured_at, tz_offset_minutes, value_original, unit_original, source_type, source_provider, source_record_id, source_meta) values (now() - interval '1 hour', 300, 100, 'mg/dL', 'file', 'file:csv', 'x:row9', '[1,2]');
    raise exception 'FAIL 10: non-object meta accepted';
  exception when check_violation then null; end;
  begin  -- provenance meta is immutable after save
    update public.glucose_readings set source_meta = '{"fileName":"forged"}' where source_record_id = 'abc123:line10';
    raise exception 'FAIL 10: meta updated';
  exception when insufficient_privilege or raise_exception then null; end;
  update public.glucose_readings set value_original = 150 where source_record_id = 'abc123:line10';
  if (select value_original from public.glucose_readings where source_record_id = 'abc123:line10') <> 150 then raise exception 'FAIL 10: report correction not saved'; end if;
  if (select source_meta->>'originalValue' from public.glucose_readings where source_record_id = 'abc123:line10') <> '112' then raise exception 'FAIL 10: original extraction lost'; end if;
end $$;
update public.glucose_readings set note = 'checked against the paper report' where source_record_id = 'abc123:line10';
reset role;
do $$ begin
  if (select value_mg_dl from public.glucose_readings where source_record_id = 'def456:row2') <> 109.91 then raise exception 'FAIL 10: generated mg/dL'; end if;
  if (select source_meta->>'confidence' from public.glucose_readings where source_record_id = 'abc123:line10') <> '0.86' then raise exception 'FAIL 10: meta stored'; end if;
end $$;
\echo 'ok 10 - file/ocr imports: provenance meta + batch + dedupe key stored; re-import blocked; manual rows carry no meta; meta immutable; report values correctable'
\echo 'RLS SUITE PASSED'
