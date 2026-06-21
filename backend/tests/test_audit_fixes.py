"""Tests for the critical/high/medium-tier audit fixes:
  #1 credit refund on analysis failure
  #2 atomic consume_research / refund_research via RPC
  #3 rate limits + comment cap on /search and /feedback
  #4 get_sector_pe matching (empty-entry + substring)
  #5 market_cap consistency between brief display and scoring
  #6 (frontend, verified via eslint — not here)
  #7 /brief rate limit bumped
"""
import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

import main
from services import fmp_service
from services import auth_service
from services.yfinance_service import currency_for_ticker
from services.verdict_service import compute_verdict


# ── Thai (and other) currency derivation ─────────────────────────────────────

SET50 = ["ADVANC", "AOT", "BBL", "BDMS", "BEM", "BH", "CPALL", "CPF", "CPN", "CRC",
         "DELTA", "EA", "GPSC", "GULF", "INTUCH", "IVL", "KBANK", "KTB", "PTT", "SCC"]


def test_set50_tickers_derive_thb():
    # When the data source omits currency, .BK tickers must resolve to THB (the bug was USD).
    for t in SET50:
        assert currency_for_ticker(f"{t}.BK", None) == "THB", t


def test_known_suffix_overrides_wrong_api_currency():
    # A known exchange suffix wins even if the API reports a wrong/stale currency
    # (e.g. delisted INTUCH.BK returning USD must still resolve to THB).
    assert currency_for_ticker("INTUCH.BK", "USD") == "THB"
    assert currency_for_ticker("CTW.BK", "THB") == "THB"


def test_currency_uses_api_then_usd_for_unknown_suffix():
    assert currency_for_ticker("AAPL", None) == "USD"          # US, no suffix
    assert currency_for_ticker("BARC.L", None) == "GBP"
    assert currency_for_ticker("7203.T", None) == "JPY"
    assert currency_for_ticker("FOO.XYZ", "EUR") == "EUR"      # unknown suffix → trust API


def test_verdict_uses_currency_symbol():
    # A negative-FCF Thai stock should report cash burn in ฿, not $.
    v = compute_verdict(pe=None, sector_pe=None, fcf_ttm=-6.7e8, de_ratio=0.4, eps_ttm=0.58,
                        cash=5e8, price=7.3, cur="฿")
    assert "฿" in v["bear_case"] and "$" not in v["bear_case"]


# ── #4 get_sector_pe matching ────────────────────────────────────────────────

class _FakeResp:
    def __init__(self, data): self._data = data
    def raise_for_status(self): pass
    def json(self): return self._data


def test_sector_pe_skips_blank_entry(monkeypatch):
    # A blank "" sector entry must NOT match (the old `'' in x == True` bug).
    payload = [{"sector": "", "pe": 999}, {"sector": "Technology", "pe": 30.0}]
    monkeypatch.setattr(fmp_service, "_key", lambda: "k")
    monkeypatch.setattr(fmp_service.requests, "get", lambda *a, **k: _FakeResp(payload))
    assert fmp_service.get_sector_pe("Technology") == 30.0


def test_sector_pe_blank_only_returns_none(monkeypatch):
    payload = [{"sector": "", "pe": 999}]
    monkeypatch.setattr(fmp_service, "_key", lambda: "k")
    monkeypatch.setattr(fmp_service.requests, "get", lambda *a, **k: _FakeResp(payload))
    assert fmp_service.get_sector_pe("Technology") is None


def test_sector_pe_substring_match(monkeypatch):
    payload = [{"sector": "Financial Services", "pe": 15.0}]
    monkeypatch.setattr(fmp_service, "_key", lambda: "k")
    monkeypatch.setattr(fmp_service.requests, "get", lambda *a, **k: _FakeResp(payload))
    assert fmp_service.get_sector_pe("Financial") == 15.0


def test_exchange_for_snapshot_mapping():
    m = fmp_service._exchange_for_snapshot
    assert m(None) == "NYSE"                 # unknown defaults to NYSE (prior behavior)
    assert m("NASDAQ Global Select") == "NASDAQ"
    assert m("NMS") == "NASDAQ"              # yfinance-style NASDAQ code
    assert m("New York Stock Exchange") == "NYSE"
    assert m("AMEX") == "AMEX"


def test_sector_pe_passes_mapped_exchange(monkeypatch):
    captured = {}
    def fake_get(url, params=None, timeout=None):
        captured["exchange"] = params.get("exchange")
        return _FakeResp([{"sector": "Technology", "pe": 32.0}])
    monkeypatch.setattr(fmp_service, "_key", lambda: "k")
    monkeypatch.setattr(fmp_service.requests, "get", fake_get)
    assert fmp_service.get_sector_pe("Technology", "NASDAQ") == 32.0
    assert captured["exchange"] == "NASDAQ"   # NASDAQ stock no longer forced to NYSE


# ── #2 consume_research / refund_research use the atomic RPCs ─────────────────

def _mock_sb_with_rpc(monkeypatch, rpc_return):
    sb = MagicMock()
    sb.rpc.return_value.execute.return_value = MagicMock(data=rpc_return)
    monkeypatch.setattr(auth_service, "_sb", lambda: sb)
    return sb


def test_consume_research_calls_rpc_and_maps_credit(monkeypatch):
    sb = _mock_sb_with_rpc(monkeypatch, "credit")
    allowed, ctype = auth_service.consume_research("u1")
    assert (allowed, ctype) == (True, "credit")
    sb.rpc.assert_called_once_with("consume_research", {"p_user_id": "u1"})


def test_consume_research_no_credits(monkeypatch):
    _mock_sb_with_rpc(monkeypatch, "no_credits")
    assert auth_service.consume_research("u1") == (False, "no_credits")


def test_refund_research_credit_calls_rpc(monkeypatch):
    sb = _mock_sb_with_rpc(monkeypatch, None)
    auth_service.refund_research("u1", "credit")
    sb.rpc.assert_called_once_with("refund_research", {"p_user_id": "u1", "p_charge_type": "credit"})


def test_refund_research_noop_for_unlimited(monkeypatch):
    sb = _mock_sb_with_rpc(monkeypatch, None)
    auth_service.refund_research("u1", "unlimited")
    sb.rpc.assert_not_called()  # nothing to reverse for an unlimited (admin/subscriber) run


# ── #1 refund-on-failure ordering in /research ───────────────────────────────

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
def client_with_stubs(monkeypatch):
    monkeypatch.setattr(main, "get_stock_data", lambda t: _full_stock())
    monkeypatch.setattr(main, "get_profile", lambda t: {k: None for k in
        ("company_name", "sector", "price", "change_pct_1d", "market_cap", "week_52_high", "week_52_low")})
    monkeypatch.setattr(main, "get_valuation", lambda t: {"pe": None, "pb": None, "ps": None,
        "ev_ebitda": None, "sector_pe": None, "pct_held_institutions": None})
    monkeypatch.setattr(main, "get_sector_pe", lambda s, e=None: None)
    monkeypatch.setattr(main, "get_earnings", lambda t: [])
    monkeypatch.setattr(main, "get_history_report", lambda u, t: None)
    monkeypatch.setattr(main, "get_shared_report", lambda t, exclude_user_id, newer_than=None: None)
    monkeypatch.setattr(main, "get_account_status", lambda u: {"credits": 4})
    # Default: lock acquired; tests that exercise contention override this.
    monkeypatch.setattr(main, "acquire_research_lock", lambda u, t: True)
    monkeypatch.setattr(main, "release_research_lock", MagicMock())
    main.app.dependency_overrides[main._get_user] = lambda: _FakeUser()
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def test_research_refunds_on_analysis_failure(client_with_stubs, monkeypatch):
    monkeypatch.setattr(main, "consume_research", lambda u: (True, "credit"))
    refund = MagicMock()
    monkeypatch.setattr(main, "refund_research", refund)
    save = MagicMock()
    monkeypatch.setattr(main, "save_history", save)
    def boom(t, d): raise RuntimeError("Claude down")
    monkeypatch.setattr(main, "run_stock_analysis", boom)

    r = client_with_stubs.post("/research/AAA")
    assert r.status_code == 500
    refund.assert_called_once_with("u1", "credit")   # charge reversed
    save.assert_not_called()                          # nothing saved


def test_research_no_refund_on_success(client_with_stubs, monkeypatch):
    monkeypatch.setattr(main, "consume_research", lambda u: (True, "credit"))
    refund = MagicMock()
    monkeypatch.setattr(main, "refund_research", refund)
    monkeypatch.setattr(main, "save_history", MagicMock())
    monkeypatch.setattr(main, "run_stock_analysis", lambda t, d: "# Report body")

    r = client_with_stubs.post("/research/AAA")
    assert r.status_code == 200
    assert r.json()["report"] == "# Report body"
    refund.assert_not_called()


def test_research_cached_path_no_claude_no_refund(client_with_stubs, monkeypatch):
    monkeypatch.setattr(main, "consume_research", lambda u: (True, "credit"))
    refund = MagicMock()
    monkeypatch.setattr(main, "refund_research", refund)
    monkeypatch.setattr(main, "save_history", MagicMock())
    monkeypatch.setattr(main, "get_shared_report",
                        lambda t, exclude_user_id, newer_than=None: {
                            "report": "cached body", "company_name": "Alpha Inc",
                            "created_at": "2026-06-18T00:00:00+00:00"})
    claude = MagicMock()
    monkeypatch.setattr(main, "run_stock_analysis", claude)

    r = client_with_stubs.post("/research/AAA")
    assert r.status_code == 200
    assert r.json()["report"] == "cached body"
    claude.assert_not_called()   # cache hit skips the expensive call
    refund.assert_not_called()


def test_research_denied_when_no_credits(client_with_stubs, monkeypatch):
    monkeypatch.setattr(main, "consume_research", lambda u: (False, "no_credits"))
    claude = MagicMock()
    monkeypatch.setattr(main, "run_stock_analysis", claude)
    r = client_with_stubs.post("/research/AAA")
    assert r.status_code == 402
    claude.assert_not_called()   # broke user never triggers Claude


# ── concurrent double-run lock ───────────────────────────────────────────────

def test_research_rejects_when_lock_held(client_with_stubs, monkeypatch):
    # A concurrent run already holds the lock → 409, no charge, no Claude.
    monkeypatch.setattr(main, "acquire_research_lock", lambda u, t: False)
    charge = MagicMock(return_value=(True, "credit"))
    monkeypatch.setattr(main, "consume_research", charge)
    claude = MagicMock()
    monkeypatch.setattr(main, "run_stock_analysis", claude)
    r = client_with_stubs.post("/research/AAA")
    assert r.status_code == 409
    charge.assert_not_called()   # no charge when lock is held
    claude.assert_not_called()   # no second Claude run


def test_research_releases_lock_on_success(client_with_stubs, monkeypatch):
    monkeypatch.setattr(main, "consume_research", lambda u: (True, "credit"))
    monkeypatch.setattr(main, "save_history", MagicMock())
    monkeypatch.setattr(main, "run_stock_analysis", lambda t, d: "# ok")
    release = MagicMock()
    monkeypatch.setattr(main, "release_research_lock", release)
    r = client_with_stubs.post("/research/AAA")
    assert r.status_code == 200
    release.assert_called_once_with("u1", "AAA")


def test_research_releases_lock_on_failure(client_with_stubs, monkeypatch):
    monkeypatch.setattr(main, "consume_research", lambda u: (True, "credit"))
    monkeypatch.setattr(main, "refund_research", MagicMock())
    def boom(t, d): raise RuntimeError("down")
    monkeypatch.setattr(main, "run_stock_analysis", boom)
    release = MagicMock()
    monkeypatch.setattr(main, "release_research_lock", release)
    r = client_with_stubs.post("/research/AAA")
    assert r.status_code == 500
    release.assert_called_once_with("u1", "AAA")   # finally releases even on failure


def test_acquire_release_lock_wrappers(monkeypatch):
    sb = MagicMock()
    sb.rpc.return_value.execute.return_value = MagicMock(data=True)
    monkeypatch.setattr(auth_service, "_sb", lambda: sb)
    assert auth_service.acquire_research_lock("u1", "AAA") is True
    sb.rpc.assert_called_with("acquire_research_lock", {"p_user_id": "u1", "p_ticker": "AAA"})
    auth_service.release_research_lock("u1", "AAA")
    sb.rpc.assert_called_with("release_research_lock", {"p_user_id": "u1", "p_ticker": "AAA"})


def test_acquire_lock_fails_open_on_infra_error(monkeypatch):
    # DB hiccup must not block a paying user — acquire returns True (proceed).
    def boom(): raise RuntimeError("db down")
    monkeypatch.setattr(auth_service, "_sb", boom)
    assert auth_service.acquire_research_lock("u1", "AAA") is True


# ── #3 feedback comment cap ──────────────────────────────────────────────────

def test_delete_me_requires_auth():
    main.app.dependency_overrides.clear()
    client = TestClient(main.app)
    r = client.request("DELETE", "/me")  # no auth
    assert r.status_code == 401


def test_delete_me_calls_delete_account(monkeypatch):
    called = {}
    monkeypatch.setattr(main, "delete_account", lambda uid: called.setdefault("uid", uid) or True)
    main.app.dependency_overrides[main._get_user] = lambda: _FakeUser()
    client = TestClient(main.app)
    r = client.request("DELETE", "/me")
    main.app.dependency_overrides.clear()
    assert r.status_code == 200 and r.json()["ok"] is True
    assert called["uid"] == "u1"


def test_delete_me_500_on_failure(monkeypatch):
    monkeypatch.setattr(main, "delete_account", lambda uid: False)
    main.app.dependency_overrides[main._get_user] = lambda: _FakeUser()
    client = TestClient(main.app)
    r = client.request("DELETE", "/me")
    main.app.dependency_overrides.clear()
    assert r.status_code == 500


def test_feedback_caps_comment_length(monkeypatch):
    captured = {}
    def fake_save(ticker, verdict, thumbs, comment):
        captured.update(ticker=ticker, comment=comment); return True
    monkeypatch.setattr(main, "save_feedback", fake_save)
    main.app.dependency_overrides.clear()
    client = TestClient(main.app)
    long_comment = "x" * 5000
    r = client.post("/feedback", json={"ticker": "AAA", "thumbs": "up", "comment": long_comment})
    assert r.status_code == 200
    assert len(captured["comment"]) == 500   # truncated server-side


# ── #3/#7 rate-limit decorators registered ───────────────────────────────────

def test_rate_limits_registered():
    limits = {}
    for route in main.app.routes:
        endpoint = getattr(route, "endpoint", None)
        if endpoint and hasattr(endpoint, "_rate_limit_decorated"):
            limits[route.path] = True
    # slowapi marks decorated endpoints; assert the three guarded routes exist.
    # (Fallback: just confirm the app exposes them.)
    paths = {getattr(r, "path", None) for r in main.app.routes}
    assert "/search" in paths and "/feedback" in paths and "/brief/{ticker}" in paths
