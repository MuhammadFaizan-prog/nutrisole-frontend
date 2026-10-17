-- Report/photo readings are user-reviewed and may be corrected after saving.
-- Keep the original extraction metadata and source identity immutable, preserving
-- idempotent re-imports. Direct device/provider measurements remain read-only.
begin;

create or replace function public.glucose_readings_guard() returns trigger
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
       or new.source_record_id is distinct from old.source_record_id or new.created_at is distinct from old.created_at
       or new.source_meta is distinct from old.source_meta or new.import_batch_id is distinct from old.import_batch_id then
      raise exception 'ownership and provenance of a glucose reading cannot change' using errcode = 'P0001';
    end if;
    if old.source_type not in ('manual', 'file', 'ocr', 'vendor_import') and (new.value_original is distinct from old.value_original
       or new.unit_original is distinct from old.unit_original or new.measured_at is distinct from old.measured_at) then
      raise exception 'imported glucose values are read-only' using errcode = 'P0001';
    end if;
    if old.source_type <> 'manual' and (new.measured_at is distinct from old.measured_at
       or new.value_original is distinct from old.value_original or new.unit_original is distinct from old.unit_original) then
      new.dedupe_key := to_char(date_trunc('minute', new.measured_at at time zone 'UTC'), 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"') || '|' ||
        to_char(round(case when new.unit_original = 'mg/dL' then new.value_original else round(new.value_original * 18.0182, 2) end, 1), 'FM9999990.0');
    end if;
    new.updated_at := now();
  end if;
  return new;
end;
$$;

revoke all on function public.glucose_readings_guard() from public, anon, authenticated;

commit;
