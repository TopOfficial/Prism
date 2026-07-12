"""Deep Research usage log: every successful run (fresh or shared) appends one
research_events row; failures don't log; logging failures never break a run."""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

import main
from services import auth_service


class _FakeUser:
    id = "u1"
    email = "u@example.com"


def _full_stock():
    return {
        "ticker": "AAA", "company_name": "Alpha Inc", "sector": "Technology",
        "currency": "USD", "price": 100.0, "change_pct_1d": 1.0,
        "week_52_high": 120.0, "week_52_low": 80.0, "market_cap": 1e9,
        "shares_outstanding": 1e7,
        "overview": {"revenue_ttm": 5e8, "eps_ttm": 2.0, "net_margin_pct": 10,
                     "fcf_ttm": 1e8, "roic_ttm": 12, "roe_ttm": 15},
        "balance_sheet": {"total_debt": 1e8, "cash": 2e8, "de_ratio": 0.3},
        "valuation_raw": {"pe": 20, "pb": 3, "ps": 4, "ev_ebitda": 12},
        "financials_history": {}, "earnings_history": [],
        "institutional": {"pct_held_institutions": 0.6},
    }


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "get_stock_data", lambda t: _full_stock())
    monkeypatch.setattr(main, "get_profile", lambda t: {k: None for k in
        ("company_name", "sector", "price", "change_pct_1d", "market_cap", "week_52_high", "week_52_low")})
    monkeypatch.setattr(main, "get_valuation", lambda t: {"pe": None, "pb": None, "ps": None,
        "ev_ebitda": None, "sector_pe": None, "pct_held_institutions": None})
    monkeypatch.setattr(main, "get_sector_pe", lambda s, e=None: None)
    monkeypatch.setattr(main, "get_earnings", lambda t: [])
    monkeypatch.setattr(main, "get_history_report", lambda u, t: None)
    monkeypatch.setattr(main, "get_shared_report", lambda t, exclude_user_id, newer_than=None: None)
    monkeypatch.setattr(main, "build_comparables", lambda t, own: None)
    monkeypatch.setattr(main, "get_account_status", lambda u: {"credits": 4})
    monkeypatch.setattr(main, "acquire_research_lock", lambda u, t: True)
    monkeypatch.setattr(main, "release_research_lock", MagicMock())
    monkeypatch.setattr(main, "consume_research", lambda u: (True, "credit"))
    monkeypatch.setattr(main, "refund_research", MagicMock())
    monkeypatch.setattr(main, "save_history", MagicMock())
    main.app.dependency_overrides[main._get_user] = lambda: _FakeUser()
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def test_fresh_run_logs_event(client, monkeypatch):
    log = MagicMock()
    monkeypatch.setattr(main, "log_research_event", log)
    monkeypatch.setattr(main, "run_stock_analysis", lambda t, d, **kw: "# Report")

    r = client.post("/research/AAA")
    assert r.status_code == 200
    log.assert_called_once_with("u1", "u@example.com", "AAA", "credit", source="fresh")


def test_shared_cache_run_logs_event(client, monkeypatch):
    log = MagicMock()
    monkeypatch.setattr(main, "log_research_event", log)
    monkeypatch.setattr(main, "get_shared_report",
                        lambda t, exclude_user_id, newer_than=None: {
                            "report": "cached body", "company_name": "Alpha Inc",
                            "created_at": "2026-07-10T00:00:00+00:00"})
    claude = MagicMock()
    monkeypatch.setattr(main, "run_stock_analysis", claude)

    r = client.post("/research/AAA")
    assert r.status_code == 200
    claude.assert_not_called()
    log.assert_called_once_with("u1", "u@example.com", "AAA", "credit", source="shared")


def test_failed_run_does_not_log(client, monkeypatch):
    log = MagicMock()
    monkeypatch.setattr(main, "log_research_event", log)
    def boom(t, d, **kw): raise RuntimeError("Claude down")
    monkeypatch.setattr(main, "run_stock_analysis", boom)

    r = client.post("/research/AAA")
    assert r.status_code == 500
    log.assert_not_called()


def test_log_research_event_swallows_db_errors(monkeypatch):
    sb = MagicMock()
    sb.table.return_value.insert.return_value.execute.side_effect = RuntimeError("db down")
    monkeypatch.setattr(auth_service, "_sb", lambda: sb)
    # Must not raise — logging is best-effort.
    auth_service.log_research_event("u1", "u@example.com", "AAA", "credit", "fresh")


def test_log_research_event_inserts_row(monkeypatch):
    sb = MagicMock()
    monkeypatch.setattr(auth_service, "_sb", lambda: sb)
    auth_service.log_research_event("u1", "u@example.com", "AAA", "free_weekly", "fresh")
    sb.table.assert_called_once_with("research_events")
    sb.table.return_value.insert.assert_called_once_with({
        "user_id": "u1",
        "email": "u@example.com",
        "ticker": "AAA",
        "charge_type": "free_weekly",
        "source": "fresh",
    })


def test_list_research_events_returns_empty_on_error(monkeypatch):
    sb = MagicMock()
    sb.table.side_effect = RuntimeError("db down")
    monkeypatch.setattr(auth_service, "_sb", lambda: sb)
    assert auth_service.list_research_events() == []


def test_usage_stats_includes_recent_research(monkeypatch):
    sb = MagicMock()
    sb.table.return_value.select.return_value.execute.return_value = MagicMock(data=[])
    monkeypatch.setattr(auth_service, "_sb", lambda: sb)
    events = [{"email": "u@example.com", "ticker": "AAA", "charge_type": "credit",
               "source": "fresh", "created_at": "2026-07-12T00:00:00+00:00"}]
    monkeypatch.setattr(auth_service, "list_research_events", lambda limit=100: events)

    stats = auth_service.get_usage_stats()
    assert stats["recent_research"] == events
