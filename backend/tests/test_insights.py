import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.catalysts_service as cats
import services.macro_service as macro
from services.catalysts_service import ticker_catalysts, watchlist_catalysts


def test_ticker_catalysts_future_only(monkeypatch):
    cats._CACHE.clear()
    monkeypatch.setattr(cats, "_earnings_calendar", lambda t: [
        {"date": "2026-07-30", "epsEstimated": 1.88, "revenueEstimated": 1.0e11, "epsActual": None},
        {"date": "2026-04-30", "epsEstimated": 1.6, "epsActual": 1.65},  # past, reported
    ])
    monkeypatch.setattr(cats, "_dividends", lambda t: [
        {"date": "2026-08-11", "paymentDate": "2026-08-14", "dividend": 0.27},
        {"date": "2026-05-11", "paymentDate": "2026-05-14", "dividend": 0.27},
    ])
    monkeypatch.setattr(cats, "_today", lambda: "2026-07-07")
    out = ticker_catalysts("AAPL")
    assert out["next_earnings"]["date"] == "2026-07-30"
    assert out["next_earnings"]["eps_estimate"] == 1.88
    assert out["next_dividend"]["ex_date"] == "2026-08-11"


def test_ticker_catalysts_none_upcoming(monkeypatch):
    cats._CACHE.clear()
    monkeypatch.setattr(cats, "_earnings_calendar", lambda t: [])
    monkeypatch.setattr(cats, "_dividends", lambda t: [])
    out = ticker_catalysts("AAPL")
    assert out["next_earnings"] is None and out["next_dividend"] is None


def test_watchlist_catalysts_sorted(monkeypatch):
    def fake(t):
        return {
            "NVDA": {"ticker": "NVDA", "next_earnings": {"date": "2026-08-20", "eps_estimate": 1.0, "revenue_estimate": None}, "next_dividend": None},
            "AAPL": {"ticker": "AAPL", "next_earnings": {"date": "2026-07-30", "eps_estimate": 1.88, "revenue_estimate": None}, "next_dividend": None},
        }[t]
    monkeypatch.setattr(cats, "ticker_catalysts", fake)
    out = watchlist_catalysts(["NVDA", "AAPL"])
    assert [e["ticker"] for e in out] == ["AAPL", "NVDA"]  # soonest first


def test_macro_disabled_without_key(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    macro._CACHE.clear()
    out = macro.get_macro()
    assert out == {"enabled": False, "series": []}


def test_macro_with_key(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "k")
    macro._CACHE.clear()
    monkeypatch.setattr(macro, "_fred_series", lambda sid, key:
                        {"value": 4.25, "date": "2026-06-01", "prev": 4.5, "yoy_base": 4.0})
    out = macro.get_macro()
    assert out["enabled"] is True
    assert len(out["series"]) == len(macro._SERIES)
    assert out["series"][0]["value"] == 4.25
