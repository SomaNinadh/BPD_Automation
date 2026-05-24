create extension if not exists pgcrypto;

create table if not exists public.draft_projects (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    owner_user_id uuid not null,
    last_modified_by_user_id uuid not null,
    project_json jsonb not null,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = timezone('utc', now());
    return new;
end;
$$;

drop trigger if exists draft_projects_set_updated_at on public.draft_projects;

create trigger draft_projects_set_updated_at
before update on public.draft_projects
for each row
execute function public.set_updated_at();
