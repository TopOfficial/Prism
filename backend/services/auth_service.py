import os
from datetime import datetime, timezone, timedelta

_client_cache = None

_FREE_RESEARCH_PERIOD = timedelta(days=7)  # 1 free Deep Research per week


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
        return {"is_admin": False, "is_subscriber": False, "credits": 0, "free_research_available": False}

    now = datetime.now(timezone.utc)
    reset_at = _parse_ts(record.get("free_research_reset_at"))
    free_available = reset_at is None or (now - reset_at) >= _FREE_RESEARCH_PERIOD

    return {
        "is_admin": bool(record.get("is_admin")),
        "is_subscriber": bool(record.get("is_subscriber")),
        "credits": int(record.get("credits") or 0),
        "free_research_available": free_available,
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
    Charge a user for one Deep Research run.
    Resolution order: admin/subscriber (free, unlimited) → weekly free → credits.
    Returns (allowed, charge_type) where charge_type is one of:
    'unlimited', 'free_weekly', 'credit', or a denial reason 'no_credits'.
    """
    try:
        record = get_user_record(user_id)
        if not record:
            return False, "no_credits"

        if record.get("is_admin") or record.get("is_subscriber"):
            return True, "unlimited"

        now = datetime.now(timezone.utc)
        reset_at = _parse_ts(record.get("free_research_reset_at"))

        # Weekly free research takes priority so credits are never wasted
        if reset_at is None or (now - reset_at) >= _FREE_RESEARCH_PERIOD:
            _sb().table("users").update({
                "free_research_reset_at": now.isoformat(),
            }).eq("id", user_id).execute()
            return True, "free_weekly"

        credits = int(record.get("credits") or 0)
        if credits > 0:
            _sb().table("users").update({
                "credits": credits - 1,
            }).eq("id", user_id).execute()
            return True, "credit"

        return False, "no_credits"

    except Exception as e:
        print(f"[AUTH] consume_research failed for {user_id}: {e}")
        # On infra error, deny so we never give away paid analysis for free by accident
        return False, "no_credits"


# ── Per-user research history ──────────────────────────────────────────────────

def save_history(user_id: str, ticker: str, company_name: str | None, report: str) -> None:
    """Upsert one report per (user, ticker). Re-analyze overwrites the prior entry."""
    try:
        _sb().table("research_history").upsert({
            "user_id": user_id,
            "ticker": ticker,
            "company_name": company_name,
            "report": report,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="user_id,ticker").execute()
    except Exception as e:
        print(f"[AUTH] save_history failed for {user_id}/{ticker}: {e}")


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
