-- Permanent notice records (audit step 2). Applied to production Supabase as the admin account (postgres).
-- The app role echosphere_app is not the owner: it can read and add records and events, update only a record's
-- current-state columns (never the original title/content, creator or creation time), and never delete.

create table if not exists public.notice_records (
  id serial primary key,
  announcement_id integer not null,
  original_title varchar(255),
  original_content text,
  creator_id integer,
  creator_name varchar(255),
  creator_role varchar(50),
  creator_department varchar(100),
  created_at timestamp without time zone not null,
  title varchar(255),
  content text,
  category varchar(100),
  priority varchar(30),
  emergency_level varchar(30),
  target_audience varchar(255),
  channels varchar(100),
  status varchar(40),
  scheduled_at timestamp without time zone,
  published_at timestamp without time zone,
  first_delivered_at timestamp without time zone,
  last_delivered_at timestamp without time zone,
  speaker_play_count integer not null default 0,
  deleted_at timestamp without time zone,
  deleted_by_id integer,
  deleted_by_name varchar(255),
  deleted_by_role varchar(50),
  deleted_before_broadcast boolean,
  audio_deleted_at timestamp without time zone,
  partial boolean not null default false
);
create unique index if not exists ix_notice_records_announcement_id on public.notice_records (announcement_id);
create index if not exists ix_notice_records_created_at on public.notice_records (created_at);
create index if not exists ix_notice_records_creator_id on public.notice_records (creator_id);
create index if not exists ix_notice_records_title on public.notice_records (title);
create index if not exists ix_notice_records_last_delivered_at on public.notice_records (last_delivered_at);
create index if not exists ix_notice_records_deleted_at on public.notice_records (deleted_at);

create table if not exists public.notice_record_events (
  id serial primary key,
  announcement_id integer not null,
  created_at timestamp without time zone not null,
  event varchar(30) not null,
  actor_id integer,
  actor_name varchar(255),
  actor_role varchar(50),
  detail text
);
create index if not exists ix_notice_record_events_announcement_id on public.notice_record_events (announcement_id);

alter table public.notice_records enable row level security;
alter table public.notice_record_events enable row level security;
revoke all on public.notice_records, public.notice_record_events from public, anon, authenticated;

grant select, insert on public.notice_records to echosphere_app;
grant update (title, content, category, priority, emergency_level, target_audience, channels, status, scheduled_at,
              published_at, first_delivered_at, last_delivered_at, speaker_play_count, deleted_at, deleted_by_id,
              deleted_by_name, deleted_by_role, deleted_before_broadcast, audio_deleted_at, partial)
  on public.notice_records to echosphere_app;
grant select, insert on public.notice_record_events to echosphere_app;
grant usage, select on sequence public.notice_records_id_seq, public.notice_record_events_id_seq to echosphere_app;

create policy app_read on public.notice_records for select to echosphere_app using (true);
create policy app_add on public.notice_records for insert to echosphere_app with check (true);
create policy app_update on public.notice_records for update to echosphere_app using (true) with check (true);
create policy app_read on public.notice_record_events for select to echosphere_app using (true);
create policy app_add on public.notice_record_events for insert to echosphere_app with check (true);

-- ---------------------------------------------------------------- backfill: notices that exist today
insert into public.notice_records (
  announcement_id, original_title, original_content, creator_id, creator_name, creator_role, creator_department,
  created_at, title, content, category, priority, emergency_level, target_audience, channels, status, scheduled_at,
  published_at, first_delivered_at, last_delivered_at, speaker_play_count, partial)
select a.id, a.title, a.description, a.created_by, u.full_name, r.name, d.name,
       a.created_at, a.title, a.description, c.name,
       initcap(replace(a.priority::text, '_', ' ')), initcap(replace(a.emergency_level::text, '_', ' ')),
       a.target_audience,
       (select string_agg(dt.name, ',' order by dt.name) from announcement_deliveries ad
          join delivery_types dt on dt.id = ad.delivery_type_id where ad.announcement_id = a.id),
       initcap(replace(a.status::text, '_', ' ')), a.scheduled_at,
       case when a.status::text = 'PUBLISHED' then a.created_at end,
       (select min(q.played_at) from speaker_queue q where q.announcement_id = a.id),
       (select max(q.played_at) from speaker_queue q where q.announcement_id = a.id),
       (select count(*) from speaker_queue q where q.announcement_id = a.id and q.status = 'Completed'),
       false
from announcements a
left join users u on u.id = a.created_by
left join roles r on r.id = u.role_id
left join departments d on d.id = u.department_id
left join announcement_categories c on c.id = a.category_id
on conflict (announcement_id) do nothing;

insert into public.notice_record_events (announcement_id, created_at, event, actor_name, detail)
select a.id, now() at time zone 'utc', 'RECORD_STARTED', 'System',
       'Record started from the notice as it was on 2026-10-22. Earlier edits and deliveries were not recorded.'
from announcements a
where not exists (select 1 from public.notice_record_events e where e.announcement_id = a.id and e.event = 'RECORD_STARTED');

-- ---------------------------------------------------------------- backfill: notices deleted before today (partial)
with deleted as (
  select distinct on (l.entity_id) l.entity_id as nid, l.created_at as deleted_at, l.user_id as deleter,
         nullif(regexp_replace(coalesce(l.description, ''), '^Deleted announcement:\s*', ''), '') as title
  from audit_logs l
  where l.action = 'DELETE_ANNOUNCEMENT' and l.entity = 'ANNOUNCEMENT'
    and not exists (select 1 from announcements a where a.id = l.entity_id)
  order by l.entity_id, l.created_at desc
), created as (
  select distinct on (l.entity_id) l.entity_id as nid, l.created_at, l.user_id as creator
  from audit_logs l where l.action = 'CREATE_ANNOUNCEMENT' and l.entity = 'ANNOUNCEMENT'
  order by l.entity_id, l.created_at
)
insert into public.notice_records (
  announcement_id, original_title, creator_id, creator_name, creator_role, creator_department, created_at, title,
  deleted_at, deleted_by_id, deleted_by_name, deleted_by_role, partial)
select del.nid, del.title, cr.creator, cu.full_name, crr.name, cd.name, coalesce(cr.created_at, del.deleted_at),
       del.title, del.deleted_at, del.deleter, du.full_name, dr.name, true
from deleted del
left join created cr on cr.nid = del.nid
left join users cu on cu.id = cr.creator
left join roles crr on crr.id = cu.role_id
left join departments cd on cd.id = cu.department_id
left join users du on du.id = del.deleter
left join roles dr on dr.id = du.role_id
on conflict (announcement_id) do nothing;

insert into public.notice_record_events (announcement_id, created_at, event, actor_id, actor_name, actor_role, detail)
select r.announcement_id, r.created_at, 'CREATED', r.creator_id, r.creator_name, r.creator_role,
       'Partial record rebuilt from the earlier audit trail: content, channels and deliveries were not recorded.'
from public.notice_records r
where r.partial and not exists (select 1 from public.notice_record_events e where e.announcement_id = r.announcement_id);

insert into public.notice_record_events (announcement_id, created_at, event, actor_id, actor_name, actor_role, detail)
select r.announcement_id, r.deleted_at, 'DELETED', r.deleted_by_id, r.deleted_by_name, r.deleted_by_role,
       'Deleted (from the earlier audit trail).'
from public.notice_records r
where r.partial and not exists (select 1 from public.notice_record_events e
                                where e.announcement_id = r.announcement_id and e.event = 'DELETED');
