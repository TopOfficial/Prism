import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import services.watchlist_service as ws
from services.watchlist_service import add_to_watchlist, WatchlistError, FREE_TICKER_LIMIT


def test_free_user_limit(monkeypatch):
    monkeypatch.setattr(ws, "_count_watchlist", lambda uid: FREE_TICKER_LIMIT)
    with pytest.raises(WatchlistError) as e:
        add_to_watchlist("u1", "NVDA", "NVIDIA", is_unlimited=False)
    assert e.value.code == "limit_reached"


def test_unlimited_user_bypasses_limit(monkeypatch):
    monkeypatch.setattr(ws, "_count_watchlist", lambda uid: 50)
    saved = {}
    monkeypatch.setattr(ws, "_upsert_watch", lambda row: saved.update(row))
    out = add_to_watchlist("u1", "NVDA", "NVIDIA", is_unlimited=True)
    assert saved["ticker"] == "NVDA"
    assert out["ticker"] == "NVDA"


def test_add_under_limit(monkeypatch):
    monkeypatch.setattr(ws, "_count_watchlist", lambda uid: FREE_TICKER_LIMIT - 1)
    saved = {}
    monkeypatch.setattr(ws, "_upsert_watch", lambda row: saved.update(row))
    add_to_watchlist("u1", "AAPL", "Apple", is_unlimited=False)
    assert saved["user_id"] == "u1"
    assert saved["baseline"] == {"price": None, "earnings_quarter": None}


def test_readd_existing_ticker_not_counted_against_limit(monkeypatch):
    # Re-watching an already-watched ticker must not raise even at the limit.
    monkeypatch.setattr(ws, "_count_watchlist", lambda uid: FREE_TICKER_LIMIT)
    monkeypatch.setattr(ws, "_is_watched", lambda uid, t: True)
    saved = {}
    monkeypatch.setattr(ws, "_upsert_watch", lambda row: saved.update(row))
    add_to_watchlist("u1", "NVDA", "NVIDIA", is_unlimited=False)
    assert saved["ticker"] == "NVDA"
