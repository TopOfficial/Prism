import os
from datetime import datetime, timezone, timedelta

_client_cache = None


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


def set_user_pro(user_id: str, is_pro: bool, stripe_customer_id: str | None = None) -> None:
    payload: dict = {"is_pro": is_pro}
    if stripe_customer_id:
        payload["stripe_customer_id"] = stripe_customer_id
    try:
        _sb().table("users").update(payload).eq("id", user_id).execute()
    except Exception:
        pass


def check_and_increment_search(user_id: str) -> tuple[bool, str]:
    """
    Returns (allowed, reason).
    Pro users are always allowed.
    Free users get 5 searches/day; counter resets after 24h.
    """
    try:
        record = get_user_record(user_id)
        if not record:
            return True, "ok"

        if record.get("is_pro"):
            return True, "ok"

        now = datetime.now(timezone.utc)
        searches = record.get("searches_today", 0)
        reset_at = _parse_ts(record.get("searches_reset_at"))

        # Reset counter if it's been more than 24 hours
        if reset_at and (now - reset_at) > timedelta(hours=24):
            _sb().table("users").update({
                "searches_today": 1,
                "searches_reset_at": now.isoformat(),
            }).eq("id", user_id).execute()
            return True, "ok"

        if searches >= 5:
            return False, "daily_limit_reached"

        _sb().table("users").update({
            "searches_today": searches + 1,
        }).eq("id", user_id).execute()
        return True, "ok"

    except Exception:
        # On error, allow the request — don't punish users for backend issues
        return True, "ok"
