"""Watchlist storage: one row per (user, ticker) with a per-ticker baseline the
alert job diffs against. Free users watch up to FREE_TICKER_LIMIT tickers;
subscribers/admins are unlimited (enforced here, server-side)."""
from datetime import datetime, timezone

FREE_TICKER_LIMIT = 3


class WatchlistError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _sb():
    from services.auth_service import _sb as sb
    return sb()


# ── Thin DB accessors (monkeypatchable in tests) ─────────────────────────────

def _count_watchlist(user_id: str) -> int:
    res = _sb().table("watchlists").select("ticker", count="exact").eq("user_id", user_id).execute()
    return res.count or 0


def _is_watched(user_id: str, ticker: str) -> bool:
    try:
        res = _sb().table("watchlists").select("ticker").eq("user_id", user_id).eq("ticker", ticker).execute()
        return bool(res.data)
    except Exception:
        return False


def _upsert_watch(row: dict) -> None:
    _sb().table("watchlists").upsert(row, on_conflict="user_id,ticker").execute()


# ── Public API ───────────────────────────────────────────────────────────────

def add_to_watchlist(user_id: str, ticker: str, company_name: str | None,
                     is_unlimited: bool) -> dict:
    """Add (or re-add) a ticker. Raises WatchlistError('limit_reached') when a
    free user already watches FREE_TICKER_LIMIT other tickers."""
    if not is_unlimited and not _is_watched(user_id, ticker):
        if _count_watchlist(user_id) >= FREE_TICKER_LIMIT:
            raise WatchlistError("limit_reached")
    _upsert_watch({
        "user_id": user_id,
        "ticker": ticker,
        "company_name": company_name,
        "added_at": datetime.now(timezone.utc).isoformat(),
        "baseline": {"price": None, "earnings_quarter": None},
    })
    return {"ticker": ticker, "watching": True}


def remove_from_watchlist(user_id: str, ticker: str) -> None:
    try:
        _sb().table("watchlists").delete().eq("user_id", user_id).eq("ticker", ticker).execute()
    except Exception as e:
        print(f"[WATCH] remove failed for {user_id}/{ticker}: {e}")


def list_watchlist(user_id: str) -> list:
    try:
        res = (
            _sb().table("watchlists")
            .select("ticker, company_name, added_at")
            .eq("user_id", user_id)
            .order("added_at", desc=True)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def all_watch_rows() -> list:
    """Every watchlist row (all users) — used by the daily alert job."""
    try:
        res = (
            _sb().table("watchlists")
            .select("user_id, ticker, company_name, baseline")
            .limit(10000)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[WATCH] all_watch_rows failed: {e}")
        return []


def update_baseline(ticker: str, baseline: dict) -> None:
    """Set the fresh baseline on every user's row for this ticker."""
    try:
        _sb().table("watchlists").update({"baseline": baseline}).eq("ticker", ticker).execute()
    except Exception as e:
        print(f"[WATCH] update_baseline failed for {ticker}: {e}")
