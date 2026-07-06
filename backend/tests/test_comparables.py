import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.comparables_service as cs
from services.comparables_service import build_comparables, attach_comps
from services.research_service import split_report


OWN = {"ticker": "AAPL", "name": "Apple Inc", "market_cap": 3.0e12, "pe": 33.0, "ps": 8.1, "ev_ebitda": 24.0}
PEERS = [{"symbol": "MSFT", "name": "Microsoft", "market_cap": 2.8e12, "price": 400.0}]
PEER_VAL = {"pe": 35.0, "pb": 12.0, "ps": 12.5, "ev_ebitda": 25.0, "sector_pe": None, "pct_held_institutions": None}


def test_build_comparables(monkeypatch):
    cs._CACHE.clear()
    monkeypatch.setattr(cs, "_peers", lambda t: PEERS)
    monkeypatch.setattr(cs, "_valuation", lambda t: dict(PEER_VAL))
    out = build_comparables("AAPL", OWN)
    assert out["subject"]["ticker"] == "AAPL"
    assert out["peers"][0]["ticker"] == "MSFT"
    assert out["peers"][0]["pe"] == 35.0


def test_build_comparables_cached(monkeypatch):
    cs._CACHE.clear()
    calls = {"n": 0}
    def fake_peers(t):
        calls["n"] += 1
        return PEERS
    monkeypatch.setattr(cs, "_peers", fake_peers)
    monkeypatch.setattr(cs, "_valuation", lambda t: dict(PEER_VAL))
    build_comparables("AAPL", OWN)
    build_comparables("AAPL", OWN)
    assert calls["n"] == 1  # second call served from cache


def test_no_peers_returns_none(monkeypatch):
    cs._CACHE.clear()
    monkeypatch.setattr(cs, "_peers", lambda t: [])
    assert build_comparables("XXXX.BK", OWN) is None


def test_attach_and_split_roundtrip():
    comps = {"subject": OWN, "peers": [{"ticker": "MSFT", "name": "Microsoft",
                                        "market_cap": 2.8e12, "pe": 35.0, "ps": 12.5, "ev_ebitda": 25.0}]}
    extras = {
        "scorecard": {k: {"score": 7, "reason": "r"} for k in
                      ("growth", "profitability", "moat", "management", "valuation", "risk")}
        | {"overall_grade": "B"},
        "bull_bear": {"bull": [{"point": "p", "evidence": "e"}],
                      "bear": [{"point": "p", "evidence": "e"}], "verdict": "v"},
    }
    raw = f"# Report\n\nBody text.\n\n```prism-json\n{json.dumps(extras)}\n```\n"
    raw = attach_comps(raw, comps)
    md, got_extras, got_comps = split_report(raw)
    assert "Body text." in md
    assert "prism-json" not in md and "prism-comps" not in md
    assert got_extras["scorecard"]["overall_grade"] == "B"
    assert got_comps["peers"][0]["ticker"] == "MSFT"


def test_split_report_handles_absent_blocks():
    md, extras, comps = split_report("plain old report")
    assert md == "plain old report"
    assert extras is None and comps is None
