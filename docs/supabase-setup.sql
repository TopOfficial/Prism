-- Run this in your Supabase project: SQL Editor → New query → paste → Run

-- 1. Users table (extends Supabase auth.users)
create table if not exists public.users (
  id                uuid references auth.users(id) on delete cascade primary key,
  email             text,
  is_pro            boolean   default false,
  stripe_customer_id text,
  searches_today    integer   default 0,
  searches_reset_at timestamptz default now()
);

-- Enable Row Level Security
alter table public.users enable row level security;

-- Users can only read/update their own row
create policy "users: read own" on public.users
  for select using (auth.uid() = id);

create policy "users: update own" on public.users
  for update using (auth.uid() = id);

-- Service role can do anything (used by backend)
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
