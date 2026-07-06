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
  source       text not null default 'fresh',  -- 'fresh' (own Claude run) | 'shared' (reused another user's report)
  primary key (user_id, ticker)
);

alter table public.research_history enable row level security;

create policy "history: read own" on public.research_history
  for select using (auth.uid() = user_id);
create policy "service role: all" on public.research_history
  using (true) with check (true);

-- 3a. Supports the shared-cache lookup in get_shared_report() — finds the freshest
--     *other* user's report for a ticker within the reuse window.
create index if not exists research_history_ticker_created_at_idx
  on public.research_history (ticker, created_at desc);

-- 3b. Stripe webhook idempotency + atomic entitlement grant
--     Stripe delivers webhooks at-least-once and retries on 5xx, so the grant must be
--     exactly-once and atomic. We dedupe by Stripe event id and apply the grant in one tx.
create table if not exists public.stripe_events (
  id         text primary key,          -- Stripe event id (evt_...)
  created_at timestamptz not null default now()
);

alter table public.stripe_events enable row level security;
create policy "service role: all" on public.stripe_events
  using (true) with check (true);

create or replace function public.grant_from_stripe(
  p_event_id    text,
  p_user_id     uuid,
  p_kind        text,
  p_credits     integer default 0,
  p_customer_id text default null
)
returns void
language plpgsql
security definer set search_path = public
as $$
declare
  v_inserted integer;
begin
  -- Claim the event. If it already exists, this is a duplicate/retry → no-op.
  insert into public.stripe_events (id) values (p_event_id)
  on conflict (id) do nothing;
  get diagnostics v_inserted = row_count;
  if v_inserted = 0 then
    return;
  end if;

  if p_kind = 'subscription' then
    insert into public.users (id, is_subscriber, stripe_customer_id)
    values (p_user_id, true, p_customer_id)
    on conflict (id) do update
      set is_subscriber      = true,
          stripe_customer_id = coalesce(excluded.stripe_customer_id, public.users.stripe_customer_id);
  elsif p_kind = 'credits' then
    insert into public.users (id, credits, stripe_customer_id)
    values (p_user_id, p_credits, p_customer_id)
    on conflict (id) do update
      set credits            = public.users.credits + p_credits,   -- atomic increment, no read-modify-write
          stripe_customer_id = coalesce(excluded.stripe_customer_id, public.users.stripe_customer_id);
  end if;
end;
$$;


-- 3c. Thumbs up/down feedback on a brief (anonymous — no auth required to submit)
create table if not exists public.feedback (
  id         bigint generated always as identity primary key,
  ticker     text not null,
  verdict    text,
  thumbs     text not null,            -- 'up' | 'down'
  comment    text,
  created_at timestamptz not null default now()
);

alter table public.feedback enable row level security;
create policy "service role: all" on public.feedback
  using (true) with check (true);


-- 3d. Atomic Deep Research charge + refund.
--     The old Python read-modify-write (read credits, then update credits-1) could
--     double-spend under concurrent requests. These functions resolve and mutate in a
--     single transaction with a row lock (`for update`), so concurrent calls serialize.
--     Resolution order matches the old logic: admin/subscriber → weekly free → credits.
create or replace function public.consume_research(p_user_id uuid)
returns text
language plpgsql
security definer set search_path = public
as $$
declare
  v_rec    public.users%rowtype;
  v_now    timestamptz := now();
  v_period interval := interval '7 days';
begin
  select * into v_rec from public.users where id = p_user_id for update;
  if not found then
    return 'no_credits';
  end if;

  if v_rec.is_admin or v_rec.is_subscriber then
    return 'unlimited';
  end if;

  if v_rec.free_research_reset_at is null
     or (v_now - v_rec.free_research_reset_at) >= v_period then
    update public.users set free_research_reset_at = v_now where id = p_user_id;
    return 'free_weekly';
  end if;

  if coalesce(v_rec.credits, 0) > 0 then
    update public.users set credits = credits - 1 where id = p_user_id;
    return 'credit';
  end if;

  return 'no_credits';
end;
$$;

-- Reverses exactly one consume_research charge when the analysis fails after charging.
-- 'free_weekly' refund clears the weekly timer (user becomes eligible again now).
create or replace function public.refund_research(p_user_id uuid, p_charge_type text)
returns void
language plpgsql
security definer set search_path = public
as $$
begin
  if p_charge_type = 'credit' then
    update public.users set credits = coalesce(credits, 0) + 1 where id = p_user_id;
  elsif p_charge_type = 'free_weekly' then
    update public.users set free_research_reset_at = null where id = p_user_id;
  end if;
end;
$$;


-- 3e. Per-(user, ticker) lock so two concurrent /research requests can't both run the
--     expensive Claude analysis (the atomic charge in 3d prevents double-CHARGE, this
--     prevents double-RUN). A row = an in-flight run. TTL reclaim means a crashed request
--     that never released its lock can't block the ticker forever.
create table if not exists public.research_locks (
  user_id    uuid not null,
  ticker     text not null,
  created_at timestamptz not null default now(),
  primary key (user_id, ticker)
);

alter table public.research_locks enable row level security;
create policy "service role: all" on public.research_locks
  using (true) with check (true);

-- Atomically claim the lock. Returns true if acquired (no live lock existed, or the
-- existing one was older than p_ttl_seconds and got reclaimed), false if another run holds it.
create or replace function public.acquire_research_lock(
  p_user_id uuid, p_ticker text, p_ttl_seconds int default 300
)
returns boolean
language plpgsql
security definer set search_path = public
as $$
declare
  v_now timestamptz := clock_timestamp();
begin
  insert into public.research_locks (user_id, ticker, created_at)
  values (p_user_id, p_ticker, v_now)
  on conflict (user_id, ticker) do update
    set created_at = v_now
    where public.research_locks.created_at < v_now - make_interval(secs => p_ttl_seconds);
  -- We hold the lock iff the stored timestamp is the one we just wrote.
  return exists (
    select 1 from public.research_locks
    where user_id = p_user_id and ticker = p_ticker and created_at = v_now
  );
end;
$$;

create or replace function public.release_research_lock(p_user_id uuid, p_ticker text)
returns void
language plpgsql
security definer set search_path = public
as $$
begin
  delete from public.research_locks where user_id = p_user_id and ticker = p_ticker;
end;
$$;


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
-- (and run section 3b above to create stripe_events + the grant_from_stripe function)
-- alter table public.research_history add column if not exists source text not null default 'fresh';
-- (then run section 3a above to add the ticker/created_at index, if not already present)

-- 5. Make yourself admin (unlimited, no credit charge). Find your UID in
--    Supabase → Authentication → Users → click your email → User UID.
-- update public.users set is_admin = true where id = 'your-user-uuid-here';


-- ─────────────────────────────────────────────────────────────────────────────
-- 6. v1.1 (Acquisition) — run this whole section once when deploying v1.1
-- ─────────────────────────────────────────────────────────────────────────────

-- 6a. Public shareable report pages (/r/{ticker}). One row per ticker — the
--     latest publish wins. Only the backend (service role) reads/writes.
create table if not exists public.public_reports (
  ticker       text primary key,
  company_name text,
  report       text not null,
  created_at   timestamptz,                         -- when the underlying analysis was generated
  published_at timestamptz not null default now(),  -- when it was (re)published
  published_by uuid references auth.users(id) on delete set null
);

alter table public.public_reports enable row level security;
create policy "service role: all" on public.public_reports
  using (true) with check (true);

-- 6b. Daily market news briefing shown on the homepage. One row per date
--     (US/Eastern); the first request of the day generates and caches it.
create table if not exists public.market_news (
  date       date primary key,
  content    jsonb not null,       -- {indexes, headlines, briefing}
  created_at timestamptz not null default now()
);

alter table public.market_news enable row level security;
create policy "service role: all" on public.market_news
  using (true) with check (true);


-- ─────────────────────────────────────────────────────────────────────────────
-- 7. v1.2 (Retention) — run this whole section once when deploying v1.2
-- ─────────────────────────────────────────────────────────────────────────────

-- 7a. Watchlists: one row per (user, ticker). `baseline` is what the daily
--     alert job diffs against (last seen price + earnings quarter); it is
--     seeded on the first run so a fresh watch never alerts immediately.
create table if not exists public.watchlists (
  user_id      uuid not null references auth.users(id) on delete cascade,
  ticker       text not null,
  company_name text,
  added_at     timestamptz not null default now(),
  baseline     jsonb not null default '{"price": null, "earnings_quarter": null}',
  primary key (user_id, ticker)
);

alter table public.watchlists enable row level security;
create policy "watchlists: read own" on public.watchlists
  for select using (auth.uid() = user_id);
create policy "service role: all" on public.watchlists
  using (true) with check (true);

-- Supports the alert job's group-by-ticker pass.
create index if not exists watchlists_ticker_idx on public.watchlists (ticker);

-- 7b. Alert email opt-out (one-click unsubscribe link in every alert email).
alter table public.users add column if not exists alerts_enabled boolean not null default true;
