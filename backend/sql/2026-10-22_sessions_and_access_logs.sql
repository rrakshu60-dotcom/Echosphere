-- Sessions, sign-in log and app-access log (audit step 1). Applied to production Supabase on 2026-10-22 as the
-- admin account (postgres), migration "create_session_and_access_logs". The app role echosphere_app is not the
-- owner, so row-level security applies to it and it cannot alter or drop these tables.

create table if not exists public.user_sessions (
  id serial primary key,
  user_id integer not null,
  user_name varchar(255),
  refresh_hash varchar(64) not null,
  remember_me boolean not null default false,
  platform varchar(20),
  user_agent varchar(300),
  ip varchar(64),
  last_ip varchar(64),
  created_at timestamp without time zone not null,
  last_seen_at timestamp without time zone not null,
  expires_at timestamp without time zone not null,
  ended_at timestamp without time zone,
  end_reason varchar(30),
  ended_by_user_id integer
);
create unique index if not exists ix_user_sessions_refresh_hash on public.user_sessions (refresh_hash);
create index if not exists ix_user_sessions_user_id on public.user_sessions (user_id);
create index if not exists ix_user_sessions_last_seen_at on public.user_sessions (last_seen_at);

create table if not exists public.sign_in_logs (
  id serial primary key,
  created_at timestamp without time zone not null,
  identifier varchar(255),
  user_id integer,
  user_name varchar(255),
  role varchar(50),
  success boolean not null,
  reason varchar(40) not null,
  ip varchar(64),
  user_agent varchar(300),
  platform varchar(20),
  session_id integer
);
create index if not exists ix_sign_in_logs_created_at on public.sign_in_logs (created_at);
create index if not exists ix_sign_in_logs_identifier on public.sign_in_logs (identifier);
create index if not exists ix_sign_in_logs_user_id on public.sign_in_logs (user_id);
create index if not exists ix_sign_in_logs_ip on public.sign_in_logs (ip);

create table if not exists public.app_access_logs (
  id serial primary key,
  created_at timestamp without time zone not null,
  event varchar(20) not null,
  user_id integer,
  user_name varchar(255),
  session_id integer,
  platform varchar(20),
  app_version varchar(30),
  ip varchar(64),
  user_agent varchar(300)
);
create index if not exists ix_app_access_logs_created_at on public.app_access_logs (created_at);
create index if not exists ix_app_access_logs_user_id on public.app_access_logs (user_id);
create index if not exists ix_app_access_logs_ip on public.app_access_logs (ip);

alter table public.user_sessions enable row level security;
alter table public.sign_in_logs enable row level security;
alter table public.app_access_logs enable row level security;

revoke all on public.user_sessions, public.sign_in_logs, public.app_access_logs from public, anon, authenticated;

grant select, insert, update on public.user_sessions to echosphere_app;
grant select, insert on public.sign_in_logs to echosphere_app;
grant select, insert, delete on public.app_access_logs to echosphere_app;
grant usage, select on sequence public.user_sessions_id_seq, public.sign_in_logs_id_seq, public.app_access_logs_id_seq to echosphere_app;

create policy app_read on public.user_sessions for select to echosphere_app using (true);
create policy app_add on public.user_sessions for insert to echosphere_app with check (true);
create policy app_update on public.user_sessions for update to echosphere_app using (true) with check (true);

create policy app_read on public.sign_in_logs for select to echosphere_app using (true);
create policy app_add on public.sign_in_logs for insert to echosphere_app with check (true);

create policy app_read on public.app_access_logs for select to echosphere_app using (true);
create policy app_add on public.app_access_logs for insert to echosphere_app with check (true);
create policy app_purge_after_90_days on public.app_access_logs for delete to echosphere_app
  using (created_at < (now() at time zone 'utc') - interval '90 days');
