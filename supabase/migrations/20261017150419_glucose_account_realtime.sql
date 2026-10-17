-- Private invalidations contain no reading, value, date, note or source metadata.
create or replace function public.notify_glucose_account()
returns trigger language plpgsql security definer set search_path = ''
as $$
begin
  perform realtime.send(jsonb_build_object('changed', true), 'changed',
    'glucose:' || coalesce(NEW.user_id, OLD.user_id)::text, true);
  return null;
end;
$$;
revoke all on function public.notify_glucose_account() from public, anon, authenticated;
create trigger glucose_account_changed after insert or update or delete
on public.glucose_readings for each row execute function public.notify_glucose_account();
create policy glucose_account_receive on realtime.messages for select to authenticated
using (realtime.topic() = 'glucose:' || (select auth.uid())::text);
