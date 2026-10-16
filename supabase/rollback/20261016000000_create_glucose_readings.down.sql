-- Rollback for 20261016000000_create_glucose_readings.sql.
-- WARNING: drops every stored glucose reading. Export first if any real data exists:
--   copy (select * from public.glucose_readings) to stdout with csv header;
begin;
drop table if exists public.glucose_readings cascade;   -- also drops its policies, indexes and trigger
drop function if exists public.glucose_readings_guard();
commit;
