-- NutriSole glucose monitoring: finger-prick (SMBG) readings, one canonical table.
-- STATUS: DRAFT. Validated only on a local PostgreSQL 17 with a Supabase-compatible
-- auth stub (supabase/tests/). NOT applied to the live project `nutrisole`
-- (zlxefqhzceiloplyszje). Apply only after explicit owner approval.
-- Rollback: supabase/rollback/20261016000000_create_glucose_readings.down.sql

begin;

create table public.glucose_readings (
  id                uuid primary key default gen_random_uuid(),
  user_id           uuid not null default auth.uid() references auth.users (id) on delete cascade,
  measured_at       timestamptz not null,
  tz_offset_minutes smallint not null check (tz_offset_minutes between -840 and 840),
  tz_name           text check (tz_name is null or char_length(tz_name) between 1 and 64),
  -- Exactly what was entered; unconstrained numeric so extra decimals are rejected, never silently rounded.
  value_original    numeric not null,
  unit_original     text not null check (unit_original in ('mg/dL', 'mmol/L')),
  -- Canonical mg/dL derived once from the original (18.0182 mg/dL per mmol/L); cannot be written by clients.
  value_mg_dl       numeric(8,2) generated always as (
                      case when unit_original = 'mg/dL' then value_original
                           else round(value_original * 18.0182, 2) end) stored,
  meal_context      text not null default 'unspecified'
                      check (meal_context in ('fasting', 'before_meal', 'after_meal', 'bedtime', 'random', 'other', 'unspecified')),
  note              text check (note is null or char_length(note) <= 500),
  source_type       text not null default 'manual'
                      check (source_type in ('manual', 'health_connect', 'healthkit', 'ble_meter', 'vendor_import')),
  source_provider   text check (source_provider is null or char_length(source_provider) <= 200),
  source_device     text check (source_device is null or char_length(source_device) <= 200),
  source_record_id  text check (source_record_id is null or char_length(source_record_id) <= 200),
  import_version    smallint,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  constraint glucose_value_positive check (value_original > 0),
  constraint glucose_value_precision check (
    (unit_original = 'mg/dL'  and value_original = round(value_original, 1) and value_original between 10 and 1000) or
    (unit_original = 'mmol/L' and value_original = round(value_original, 2) and value_original between 0.6 and 55.5)),
  constraint glucose_measured_after_2000 check (measured_at >= '2000-01-01T00:00:00Z'),
  -- Manual rows carry no source identity; imported rows must carry provider + immutable source id.
  constraint glucose_source_identity check (
    (source_type = 'manual' and source_provider is null and source_record_id is null) or
    (source_type <> 'manual' and source_provider is not null and source_record_id is not null))
);

comment on table public.glucose_readings is 'Self-recorded finger-prick glucose readings (manual or authorized import). Informational only; no clinical interpretation.';
comment on column public.glucose_readings.measured_at is 'Instant shown on the meter (distinct from created_at).';
comment on column public.glucose_readings.value_mg_dl is 'Generated canonical mg/dL = value_original (mg/dL) or round(value_original * 18.0182, 2) (mmol/L).';

-- History pagination per user, newest first.
create index glucose_readings_user_measured_idx on public.glucose_readings (user_id, measured_at desc, id desc);
-- Import idempotency: one row per (user, source, provider, device, source record). Manual rows are excluded,
-- so two genuine manual readings at the same time are never collapsed.
create unique index glucose_readings_import_uid on public.glucose_readings
  (user_id, source_type, source_provider, coalesce(source_device, ''), source_record_id)
  where source_record_id is not null;

-- Integrity trigger: updated_at, no future readings, immutable ownership/provenance, imported values read-only.
create function public.glucose_readings_guard() returns trigger
  language plpgsql
  set search_path = ''
as $$
begin
  if new.measured_at > now() + interval '1 day' then
    raise exception 'measured_at is in the future' using errcode = 'P0001';
  end if;
  if tg_op = 'UPDATE' then
    if new.user_id is distinct from old.user_id or new.source_type is distinct from old.source_type
       or new.source_provider is distinct from old.source_provider or new.source_device is distinct from old.source_device
       or new.source_record_id is distinct from old.source_record_id or new.created_at is distinct from old.created_at then
      raise exception 'ownership and provenance of a glucose reading cannot change' using errcode = 'P0001';
    end if;
    if old.source_type <> 'manual' and (new.value_original is distinct from old.value_original
       or new.unit_original is distinct from old.unit_original or new.measured_at is distinct from old.measured_at) then
      raise exception 'imported glucose values are read-only' using errcode = 'P0001';
    end if;
    new.updated_at := now();
  end if;
  return new;
end;
$$;

create trigger glucose_readings_guard
  before insert or update on public.glucose_readings
  for each row execute function public.glucose_readings_guard();

-- Row Level Security: every operation is limited to the signed-in owner.
alter table public.glucose_readings enable row level security;

create policy glucose_select_own on public.glucose_readings
  for select to authenticated using ((select auth.uid()) = user_id);
create policy glucose_insert_own on public.glucose_readings
  for insert to authenticated with check ((select auth.uid()) = user_id);
create policy glucose_update_own on public.glucose_readings
  for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy glucose_delete_own on public.glucose_readings
  for delete to authenticated using ((select auth.uid()) = user_id);

-- Least privilege: anonymous clients get nothing; signed-in users get row-filtered CRUD.
revoke all on public.glucose_readings from anon, authenticated, public;
grant select, delete on public.glucose_readings to authenticated;
grant insert (measured_at, tz_offset_minutes, tz_name, value_original, unit_original, meal_context, note,
              source_type, source_provider, source_device, source_record_id, import_version)
  on public.glucose_readings to authenticated;
grant update (measured_at, tz_offset_minutes, tz_name, value_original, unit_original, meal_context, note)
  on public.glucose_readings to authenticated;
revoke all on function public.glucose_readings_guard() from public, anon, authenticated;

commit;
