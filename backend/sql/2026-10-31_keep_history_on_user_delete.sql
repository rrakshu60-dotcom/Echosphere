-- Deleting a user keeps their history: audit entries, announcements and approvals keep the
-- user's id (no foreign key any more), and audit entries also keep their name, role and
-- department. The user's own notifications and password reset tokens go with the account.
-- Run once as postgres in the Supabase SQL editor. Safe to re-run.

alter table public.audit_logs
    add column if not exists user_name varchar(150),
    add column if not exists user_username varchar(50),
    add column if not exists user_email varchar(150),
    add column if not exists user_role varchar(50),
    add column if not exists user_department varchar(100),
    add column if not exists user_employee_id varchar(30),
    add column if not exists user_usn varchar(30),
    add column if not exists user_semester integer,
    add column if not exists user_section varchar(10);

update public.audit_logs a
set user_name = u.full_name,
    user_username = u.username,
    user_email = u.official_email,
    user_role = r.name,
    user_department = d.name,
    user_employee_id = u.employee_id,
    user_usn = u.usn,
    user_semester = u.semester,
    user_section = u.section
from public.users u
left join public.roles r on r.id = u.role_id
left join public.departments d on d.id = u.department_id
where u.id = a.user_id and a.user_name is null;

create index if not exists ix_audit_logs_user_id on public.audit_logs (user_id);

alter table public.audit_logs drop constraint if exists audit_logs_user_id_fkey;
alter table public.announcements drop constraint if exists announcements_created_by_fkey;
alter table public.announcement_approvals drop constraint if exists announcement_approvals_approver_id_fkey;
alter table public.announcement_archives drop constraint if exists announcement_archives_created_by_fkey;

alter table public.notifications drop constraint if exists notifications_user_id_fkey;
alter table public.notifications
    add constraint notifications_user_id_fkey foreign key (user_id) references public.users (id) on delete cascade;
alter table public.password_reset_tokens drop constraint if exists password_reset_tokens_user_id_fkey;
alter table public.password_reset_tokens
    add constraint password_reset_tokens_user_id_fkey foreign key (user_id) references public.users (id) on delete cascade;
