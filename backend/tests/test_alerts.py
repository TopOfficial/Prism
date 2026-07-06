import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.alerts_service as als
from services.alerts_service import (
    detect_events, unsub_token, verify_unsub_token, group_events_by_user, run_alerts,
)


def test_detect_price_move_event():
    baseline = {"price": 100.0, "earnings_quarter": "2026Q1"}
    events = detect_events("NVDA", baseline, current_price=106.0, latest_quarter="2026Q1")
    assert len(events) == 1
    assert events[0]["type"] == "price_move"
    assert round(events[0]["change_pct"], 1) == 6.0


def test_small_move_no_event():
    baseline = {"price": 100.0, "earnings_quarter": "2026Q1"}
    assert detect_events("NVDA", baseline, current_price=103.0, latest_quarter="2026Q1") == []


def test_detect_earnings_event():
    baseline = {"price": 100.0, "earnings_quarter": "2026Q1"}
    events = detect_events("NVDA", baseline, current_price=101.0, latest_quarter="2026Q2")
    assert [e["type"] for e in events] == ["earnings"]


def test_first_run_seeds_baseline_without_events():
    # No baseline yet (fresh watch): never alert, just seed.
    baseline = {"price": None, "earnings_quarter": None}
    events = detect_events("NVDA", baseline, current_price=100.0, latest_quarter="2026Q2")
    assert events == []


def test_unsub_token_roundtrip(monkeypatch):
    monkeypatch.setenv("UNSUB_SECRET", "test-secret")
    t = unsub_token("user-123")
    assert verify_unsub_token("user-123", t)
    assert not verify_unsub_token("user-456", t)
    assert not verify_unsub_token("user-123", "deadbeef")


def test_group_events_by_user():
    rows = [
        {"user_id": "u1", "ticker": "NVDA"},
        {"user_id": "u2", "ticker": "NVDA"},
        {"user_id": "u1", "ticker": "AAPL"},
    ]
    ticker_events = {"NVDA": [{"type": "price_move", "text": "up"}], "AAPL": []}
    grouped = group_events_by_user(rows, ticker_events)
    assert set(grouped.keys()) == {"u1", "u2"}
    assert len(grouped["u1"]) == 1  # AAPL had no events


def test_run_alerts_end_to_end_mocked(monkeypatch):
    rows = [
        {"user_id": "u1", "ticker": "NVDA", "company_name": "NVIDIA",
         "baseline": {"price": 100.0, "earnings_quarter": "2026Q1"}},
        {"user_id": "u2", "ticker": "NVDA", "company_name": "NVIDIA",
         "baseline": {"price": 100.0, "earnings_quarter": "2026Q1"}},
    ]
    monkeypatch.setattr(als, "_watch_rows", lambda: rows)
    monkeypatch.setattr(als, "_current_price", lambda t: 108.0)
    monkeypatch.setattr(als, "_latest_quarter", lambda t: ("2026Q1", []))
    monkeypatch.setattr(als, "_event_text", lambda ticker, company, ev, ctx: "NVDA moved 8%.")
    monkeypatch.setattr(als, "_update_baseline", lambda t, b: None)
    monkeypatch.setattr(als, "_user_emails", lambda uids: {"u1": ("a@x.com", True), "u2": ("b@x.com", False)})
    sent = []
    monkeypatch.setattr(als, "_send_email", lambda to, subject, html, uid: sent.append(to) or True)
    out = run_alerts()
    assert out["tickers_checked"] == 1
    assert out["events"] == 1
    assert sent == ["a@x.com"]  # u2 has alerts_enabled=False
    assert out["emails_sent"] == 1
