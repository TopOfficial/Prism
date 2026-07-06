"""Catalyst calendar (v2.0, honest version): upcoming earnings (with estimates)
and dividend dates from FMP — the two catalyst types with a reliable free
source. FDA decisions / lockups / investor days need data we don't have."""
import time
from datetime import date

_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL_S = 6 * 3600


def _today() -> str:
    return date.today().isoformat()


def _earnings_calendar(ticker: str) -> list:
    import os
    import requests
    key = os.getenv("FMP_API_KEY")
    if not key:
        return []
    try:
        r = requests.get("https://financialmodelingprep.com/stable/earnings",
                         params={"symbol": ticker, "apikey": key}, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[CATALYSTS] earnings {ticker}: {type(e).__name__}: {e}")
        return []


def _dividends(ticker: str) -> list:
    import os
    import requests
    key = os.getenv("FMP_API_KEY")
    if not key:
        return []
    try:
        r = requests.get("https://financialmodelingprep.com/stable/dividends",
                         params={"symbol": ticker, "apikey": key}, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[CATALYSTS] dividends {ticker}: {type(e).__name__}: {e}")
        return []


def ticker_catalysts(ticker: str) -> dict:
    """{"ticker", "next_earnings": {date, eps_estimate, revenue_estimate}|None,
        "next_dividend": {ex_date, payment_date, amount}|None} (6h cache)."""
    now = time.time()
    cached = _CACHE.get(ticker)
    if cached and now - cached[0] < _CACHE_TTL_S:
        return cached[1]

    today = _today()

    upcoming_earnings = [
        e for e in _earnings_calendar(ticker)
        if str(e.get("date", "")) >= today and e.get("epsActual") is None
    ]
    upcoming_earnings.sort(key=lambda e: str(e.get("date", "")))
    next_earnings = None
    if upcoming_earnings:
        e = upcoming_earnings[0]
        next_earnings = {
            "date": str(e.get("date"))[:10],
            "eps_estimate": e.get("epsEstimated"),
            "revenue_estimate": e.get("revenueEstimated"),
        }

    upcoming_divs = [d for d in _dividends(ticker) if str(d.get("date", "")) >= today]
    upcoming_divs.sort(key=lambda d: str(d.get("date", "")))
    next_dividend = None
    if upcoming_divs:
        d = upcoming_divs[0]
        next_dividend = {
            "ex_date": str(d.get("date"))[:10],
            "payment_date": (str(d.get("paymentDate"))[:10] if d.get("paymentDate") else None),
            "amount": d.get("dividend") or d.get("adjDividend"),
        }

    result = {"ticker": ticker, "next_earnings": next_earnings, "next_dividend": next_dividend}
    _CACHE[ticker] = (now, result)
    return result


def watchlist_catalysts(tickers: list) -> list:
    """Catalysts for a set of tickers, soonest event first; tickers with no
    upcoming events are dropped."""
    out = []
    for t in tickers:
        try:
            c = ticker_catalysts(t)
        except Exception as e:
            print(f"[CATALYSTS] {t} failed: {e}")
            continue
        if c["next_earnings"] or c["next_dividend"]:
            out.append(c)

    def soonest(c):
        dates = [d for d in (
            (c["next_earnings"] or {}).get("date"),
            (c["next_dividend"] or {}).get("ex_date"),
        ) if d]
        return min(dates) if dates else "9999-99-99"

    out.sort(key=soonest)
    return out
