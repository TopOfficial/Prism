import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.portfolio_service as ps
from services.portfolio_service import parse_holdings_text, analyze


def test_parse_csv_and_whitespace_lines():
    text = "AAPL, 10, 150.5\nMSFT 5\n\nnvda,2\n"
    rows, errors = parse_holdings_text(text)
    assert errors == []
    assert rows == [
        {"ticker": "AAPL", "shares": 10.0, "cost_basis": 150.5},
        {"ticker": "MSFT", "shares": 5.0, "cost_basis": None},
        {"ticker": "NVDA", "shares": 2.0, "cost_basis": None},
    ]


def test_parse_reports_bad_lines():
    rows, errors = parse_holdings_text("AAPL, ten\n<bad>, 5\nMSFT, 3")
    assert len(rows) == 1 and rows[0]["ticker"] == "MSFT"
    assert len(errors) == 2


def test_parse_rejects_too_many_holdings():
    text = "\n".join(f"T{i}, 1" for i in range(60))
    rows, errors = parse_holdings_text(text)
    assert rows == []
    assert any("50" in e for e in errors)


def _fake_quote(ticker):
    quotes = {
        "AAPL": {"price": 200.0, "name": "Apple", "sector": "Technology", "pe": 30.0},
        "KO":   {"price": 60.0, "name": "Coca-Cola", "sector": "Consumer Defensive", "pe": 25.0},
        "XXX":  {"price": None, "name": None, "sector": None, "pe": None},
    }
    return quotes[ticker]


def test_analyze_weights_sectors_concentration(monkeypatch):
    monkeypatch.setattr(ps, "_holdings", lambda uid: [
        {"ticker": "AAPL", "shares": 10, "cost_basis": 100.0},  # value 2000
        {"ticker": "KO", "shares": 50, "cost_basis": None},     # value 3000
        {"ticker": "XXX", "shares": 1, "cost_basis": None},     # unpriced
    ])
    monkeypatch.setattr(ps, "_quote", _fake_quote)
    out = analyze("u1")
    assert out["totals"]["value"] == 5000.0
    aapl = next(h for h in out["holdings"] if h["ticker"] == "AAPL")
    assert aapl["weight_pct"] == 40.0
    assert aapl["gain_pct"] == 100.0  # 100 -> 200
    assert out["unpriced"] == ["XXX"]
    sectors = {s["sector"]: s["weight_pct"] for s in out["sectors"]}
    assert sectors["Consumer Defensive"] == 60.0
    assert out["totals"]["top_weight_pct"] == 60.0
    # HHI on weights 0.4/0.6 = 0.16+0.36 = 0.52
    assert abs(out["totals"]["hhi"] - 0.52) < 1e-9


def test_analyze_empty_portfolio(monkeypatch):
    monkeypatch.setattr(ps, "_holdings", lambda uid: [])
    out = analyze("u1")
    assert out["holdings"] == [] and out["totals"]["value"] == 0
