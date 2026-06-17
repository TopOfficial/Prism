-- Run this in your Supabase project: SQL Editor → New query → paste → Run
--
-- If you already deployed the old (is_pro subscription) schema, skip to
-- section 4 "MIGRATION" instead of re-running sections 1–3.

-- 1. Users table (extends Supabase auth.users)
create table if not exists public.users (
  id                     uuid references auth.users(id) on delete cascade primary key,
  email                  text,
  credits                integer     not null default 0,
  is_subscriber          boolean     not null default false,
  is_admin               boolean     not null default false,
  free_research_reset_at timestamptz,                       -- last time the weekly free run was used
  stripe_customer_id     text
);

alter table public.users enable row level security;

create policy "users: read own" on public.users
  for select using (auth.uid() = id);
create policy "users: update own" on public.users
  for update using (auth.uid() = id);
create policy "service role: all" on public.users
  using (true) with check (true);

-- 2. Auto-create a users row on signup
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.users (id, email)
  values (new.id, new.email)
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- 3. Per-user Deep Research history (one report per user per ticker)
create table if not exists public.research_history (
  user_id      uuid references auth.users(id) on delete cascade,
  ticker       text not null,
  company_name text,
  report       text not null,
  created_at   timestamptz not null default now(),
  primary key (user_id, ticker)
);

alter table public.research_history enable row level security;

create policy "history: read own" on public.research_history
  for select using (auth.uid() = user_id);
create policy "service role: all" on public.research_history
  using (true) with check (true);


-- ─────────────────────────────────────────────────────────────────────────────
-- 4. MIGRATION — run ONLY if upgrading an existing project from the old schema
-- ─────────────────────────────────────────────────────────────────────────────
--
-- alter table public.users add column if not exists credits integer not null default 0;
-- alter table public.users add column if not exists is_subscriber boolean not null default false;
-- alter table public.users add column if not exists is_admin boolean not null default false;
-- alter table public.users add column if not exists free_research_reset_at timestamptz;
-- alter table public.users drop column if exists is_pro;
-- alter table public.users drop column if exists searches_today;
-- alter table public.users drop column if exists searches_reset_at;
-- drop table if exists public.research_cache;
-- (then run section 3 above to create research_history)

-- 5. Make yourself admin (unlimited, no credit charge). Find your UID in
--    Supabase → Authentication → Users → click your email → User UID.
-- update public.users set is_admin = true where id = 'your-user-uuid-here';
