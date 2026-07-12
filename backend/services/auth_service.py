import os
from datetime import datetime, timezone, timedelta

_client_cache = None

_FREE_RESEARCH_PERIOD = timedelta(days=7)  # 1 free Deep Research per week
SHARED_CACHE_MAX_AGE = timedelta(days=5)   # reuse another user's report if generated within this window


def _sb():
    global _client_cache
    if _client_cache is None:
        from supabase import create_client
        _client_cache = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_ROLE_KEY"],
        )
    return _client_cache


def _parse_ts(ts_str: str | None) -> datetime | None:
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except ValueError:
        return None


def verify_jwt(token: str):
    """Verify Supabase JWT; returns the User object or None if invalid."""
    try:
        res = _sb().auth.get_user(token)
        return res.user
    except Exception as e:
        print(f"[AUTH DEBUG] verify_jwt failed: {e}")
        return None


def get_user_record(user_id: str) -> dict | None:
    try:
        res = _sb().table("users").select("*").eq("id", user_id).single().execute()
        return res.data
    except Exception:
        return None


def get_account_status(user_id: str) -> dict:
    """Returns the user's entitlement summary for the frontend."""
    record = get_user_record(user_id)
    if not record:
        return {"is_admin": False, "is_subscriber": False, "credits": 0, "free_research_available": False, "next_free_research_at": None}

    now = datetime.now(timezone.utc)
    reset_at = _parse_ts(record.get("free_research_reset_at"))
    free_available = reset_at is None or (now - reset_at) >= _FREE_RESEARCH_PERIOD
    next_free_at = None if free_available else reset_at + _FREE_RESEARCH_PERIOD

    return {
        "is_admin": bool(record.get("is_admin")),
        "is_subscriber": bool(record.get("is_subscriber")),
        "credits": int(record.get("credits") or 0),
        "free_research_available": free_available,
        "next_free_research_at": next_free_at.isoformat() if next_free_at else None,
    }


def set_subscriber(user_id: str, is_subscriber: bool, stripe_customer_id: str | None = None) -> None:
    # Upsert so the grant lands even if no users row exists yet (e.g. account predates the signup trigger).
    payload: dict = {"id": user_id, "is_subscriber": is_subscriber}
    if stripe_customer_id:
        payload["stripe_customer_id"] = stripe_customer_id
    try:
        _sb().table("users").upsert(payload, on_conflict="id").execute()
        print(f"[AUTH] set_subscriber: {user_id} -> {is_subscriber}")
    except Exception as e:
        print(f"[AUTH] set_subscriber failed for {user_id}: {e}")


def add_credits(user_id: str, amount: int, stripe_customer_id: str | None = None) -> None:
    if amount <= 0:
        return
    try:
        record = get_user_record(user_id)
        current = int((record or {}).get("credits") or 0)
        # Upsert so the grant lands even if no users row exists yet.
        payload: dict = {"id": user_id, "credits": current + amount}
        if stripe_customer_id:
            payload["stripe_customer_id"] = stripe_customer_id
        _sb().table("users").upsert(payload, on_conflict="id").execute()
        print(f"[AUTH] add_credits: {user_id} +{amount} (was {current}, now {current + amount})")
    except Exception as e:
        print(f"[AUTH] add_credits failed for {user_id}: {e}")


def grant_from_stripe(
    event_id: str,
    user_id: str,
    kind: str,
    credits: int = 0,
    stripe_customer_id: str | None = None,
) -> None:
    """
    Atomic, idempotent entitlement grant via the `grant_from_stripe` Postgres function.

    The DB function dedupes by Stripe event id (a duplicate delivery is a no-op) and applies
    the grant in the same transaction. We deliberately DO NOT catch errors here: if the grant
    fails, the exception propagates out of the webhook handler so the endpoint returns 5xx and
    Stripe retries the delivery — safe because the event-id dedup makes a successful retry a no-op.
    """
    _sb().rpc("grant_from_stripe", {
        "p_event_id": event_id,
        "p_user_id": user_id,
        "p_kind": kind,
        "p_credits": int(credits or 0),
        "p_customer_id": stripe_customer_id,
    }).execute()
    print(f"[AUTH] grant_from_stripe ok: event={event_id} user={user_id} kind={kind} credits={credits}")


def consume_research(user_id: str) -> tuple[bool, str]:
    """
    Charge a user for one Deep Research run via the atomic `consume_research` Postgres
    function (row-locked, so concurrent requests can't double-spend a credit).
    Resolution order: admin/subscriber (unlimited) → weekly free → credits.
    Returns (allowed, charge_type) where charge_type is one of:
    'unlimited', 'free_weekly', 'credit', or the denial reason 'no_credits'.
    """
    try:
        res = _sb().rpc("consume_research", {"p_user_id": user_id}).execute()
        charge_type = res.data if isinstance(res.data, str) else "no_credits"
        return charge_type != "no_credits", charge_type
    except Exception as e:
        print(f"[AUTH] consume_research failed for {user_id}: {e}")
        # On infra error, deny so we never give away paid analysis for free by accident
        return False, "no_credits"


def refund_research(user_id: str, charge_type: str) -> None:
    """Reverse a consume_research charge when the analysis fails after charging.
    Atomic via the `refund_research` Postgres function. No-op for 'unlimited'/'no_credits'."""
    if charge_type not in ("credit", "free_weekly"):
        return
    try:
        _sb().rpc("refund_research", {"p_user_id": user_id, "p_charge_type": charge_type}).execute()
        print(f"[AUTH] refund_research: {user_id} refunded {charge_type}")
    except Exception as e:
        print(f"[AUTH] refund_research failed for {user_id}: {e}")


def acquire_research_lock(user_id: str, ticker: str) -> bool:
    """Try to claim the per-(user, ticker) run lock so two concurrent requests can't both
    run the expensive analysis. Returns True if acquired. Fails OPEN (returns True) on infra
    error — this is a best-effort dedup guard and must never block a paying user if the DB
    hiccups; the atomic charge still protects against double-spend."""
    try:
        res = _sb().rpc("acquire_research_lock", {"p_user_id": user_id, "p_ticker": ticker}).execute()
        return bool(res.data)
    except Exception as e:
        print(f"[AUTH] acquire_research_lock failed for {user_id}/{ticker}: {e}")
        return True


def release_research_lock(user_id: str, ticker: str) -> None:
    """Release the per-(user, ticker) run lock. Idempotent (no-op if not held)."""
    try:
        _sb().rpc("release_research_lock", {"p_user_id": user_id, "p_ticker": ticker}).execute()
    except Exception as e:
        print(f"[AUTH] release_research_lock failed for {user_id}/{ticker}: {e}")


# ── Feedback ─────────────────────────────────────────────────────────────────

def save_feedback(ticker: str, verdict: str, thumbs: str, comment: str) -> bool:
    try:
        _sb().table("feedback").insert({
            "ticker": ticker,
            "verdict": verdict or None,
            "thumbs": thumbs,
            "comment": comment or None,
        }).execute()
        return True
    except Exception as e:
        print(f"[AUTH] save_feedback failed for {ticker}: {e}")
        return False


def log_research_event(user_id: str, email: str | None, ticker: str,
                        charge_type: str, source: str) -> None:
    """Append one row to the admin usage log for a successful Deep Research run.
    Best-effort: logging must never break a run the user already paid for."""
    try:
        _sb().table("research_events").insert({
            "user_id": user_id,
            "email": email,
            "ticker": ticker,
            "charge_type": charge_type,
            "source": source,
        }).execute()
    except Exception as e:
        print(f"[AUTH] log_research_event failed for {user_id}/{ticker}: {e}")


def list_research_events(limit: int = 100) -> list:
    """Newest-first Deep Research runs for the admin dashboard."""
    try:
        res = (
            _sb().table("research_events")
            .select("email, ticker, charge_type, source, created_at")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[AUTH] list_research_events failed: {e}")
        return []


# ── Per-user research history ──────────────────────────────────────────────────

def save_history(user_id: str, ticker: str, company_name: str | None, report: str,
                  created_at: str | None = None, source: str = "fresh") -> None:
    """Upsert one report per (user, ticker). Re-analyze overwrites the prior entry.
    Pass `created_at` to preserve the original generation time when copying a shared
    report, so the freshness window doesn't reset every time it's reused."""
    try:
        _sb().table("research_history").upsert({
            "user_id": user_id,
            "ticker": ticker,
            "company_name": company_name,
            "report": report,
            "created_at": created_at or datetime.now(timezone.utc).isoformat(),
            "source": source,
        }, on_conflict="user_id,ticker").execute()
    except Exception as e:
        print(f"[AUTH] save_history failed for {user_id}/{ticker}: {e}")


def get_shared_report(ticker: str, exclude_user_id: str,
                       newer_than: str | None = None) -> dict | None:
    """Freshest *other* user's report for this ticker within SHARED_CACHE_MAX_AGE.
    Excludes exclude_user_id (the requester's own row never satisfies their own request).
    If newer_than is given (the requester's own existing report's created_at), only a
    peer report strictly more recent than that qualifies — so a first-time analysis
    reuses any fresh peer, while a Re-analyze only reuses a peer newer than what the
    user already has, otherwise it falls through to a genuinely fresh Claude run."""
    try:
        cutoff = (datetime.now(timezone.utc) - SHARED_CACHE_MAX_AGE).isoformat()
        q = (
            _sb().table("research_history")
            .select("ticker, company_name, report, created_at")
            .eq("ticker", ticker)
            .neq("user_id", exclude_user_id)
            .gte("created_at", cutoff)
        )
        if newer_than:
            q = q.gt("created_at", newer_than)
        res = q.order("created_at", desc=True).limit(1).execute()
        rows = res.data or []
        return rows[0] if rows else None
    except Exception as e:
        print(f"[AUTH] get_shared_report failed for {ticker}: {e}")
        return None


def list_history(user_id: str) -> list:
    """Return the user's saved tickers (newest first), without the full report body."""
    try:
        res = (
            _sb().table("research_history")
            .select("ticker, company_name, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def get_usage_stats() -> dict:
    """Aggregate usage numbers for the admin dashboard. Computed in Python — fine at low
    volume; move to a Postgres view/RPC if research_history grows past tens of thousands of rows."""
    from collections import Counter

    sb = _sb()
    now = datetime.now(timezone.utc)

    hist = (sb.table("research_history").select("ticker, user_id, created_at, source").execute().data) or []
    users = (sb.table("users").select("is_subscriber, is_admin, credits").execute().data) or []

    week_ago = now - timedelta(days=7)
    runs_7d = 0
    shared_reuses_7d = 0
    hour_counts: dict[int, int] = {}
    for h in hist:
        ts = _parse_ts(h.get("created_at"))
        if ts is None:
            continue
        if ts >= week_ago:
            runs_7d += 1
            if h.get("source") == "shared":
                shared_reuses_7d += 1
        bkk_hour = int((ts + timedelta(hours=7)).hour)  # UTC → Bangkok (UTC+7)
        hour_counts[bkk_hour] = hour_counts.get(bkk_hour, 0) + 1

    top_tickers = Counter(h["ticker"] for h in hist if h.get("ticker")).most_common(15)

    return {
        "recent_research": list_research_events(),
        "total_runs": len(hist),
        "runs_last_7_days": runs_7d,
        "shared_reuses_7d": shared_reuses_7d,
        "unique_users_run": len({h["user_id"] for h in hist if h.get("user_id")}),
        "registered_users": len(users),
        "subscribers": sum(1 for u in users if u.get("is_subscriber")),
        "admins": sum(1 for u in users if u.get("is_admin")),
        "credits_outstanding": sum(int(u.get("credits") or 0) for u in users),
        "top_tickers": [{"ticker": t, "runs": c} for t, c in top_tickers],
        "runs_by_bkk_hour": dict(sorted(hour_counts.items())),
        "generated_at": now.isoformat(),
    }


def delete_account(user_id: str) -> bool:
    """Permanently delete a user: cancel any active Stripe subscription, clean up the user's
    run locks, then delete the auth user (cascades to public.users + research_history via FK
    `on delete cascade`). Returns True on success."""
    try:
        record = get_user_record(user_id)
        customer_id = (record or {}).get("stripe_customer_id")
        if customer_id:
            # Imported lazily to avoid a circular import (stripe_service imports from this module).
            from services.stripe_service import cancel_customer_subscriptions
            cancel_customer_subscriptions(customer_id)

        # research_locks has no FK cascade — remove the user's locks explicitly.
        try:
            _sb().table("research_locks").delete().eq("user_id", user_id).execute()
        except Exception:
            pass

        _sb().auth.admin.delete_user(user_id)
        print(f"[AUTH] delete_account: {user_id} deleted")
        return True
    except Exception as e:
        print(f"[AUTH] delete_account failed for {user_id}: {e}")
        return False


def get_history_report(user_id: str, ticker: str) -> dict | None:
    """Return a single saved report for this user + ticker, or None."""
    try:
        res = (
            _sb().table("research_history")
            .select("ticker, company_name, report, created_at")
            .eq("user_id", user_id)
            .eq("ticker", ticker)
            .single()
            .execute()
        )
        return res.data
    except Exception:
        return None
