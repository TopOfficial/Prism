import sys
import os
import json
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import services.public_service as ps
from services.public_service import (
    is_valid_ticker, render_page_html, sitemap_xml_from, publish_report, PublishError,
)


def _row(report="# NVDA\n\nGreat company.", days_old=0, ticker="NVDA", company="NVIDIA Corp"):
    ts = (datetime.now(timezone.utc) - timedelta(days=days_old)).isoformat()
    return {"ticker": ticker, "company_name": company, "report": report,
            "published_at": ts, "created_at": ts}


def test_ticker_validation():
    for good in ("NVDA", "BRK.B", "RKLB", "PTT.BK", "A", "ABC-D"):
        assert is_valid_ticker(good), good
    for bad in ("", "nvda", "NV DA", "<script>", "A" * 13, "NV/DA", "../etc"):
        assert not is_valid_ticker(bad), bad


def test_render_page_contains_report_and_meta():
    html = render_page_html(_row())
    assert "Great company." in html
    assert "<title>" in html and "NVDA" in html
    assert 'property="og:title"' in html
    assert 'rel="canonical"' in html
    assert "not financial advice" in html.lower()


def test_render_page_escapes_html_in_report():
    html = render_page_html(_row(report="Hello <script>alert(1)</script> world"))
    assert "<script>alert(1)</script>" not in html
    assert "alert(1)" in html  # content kept, tag neutralized


def test_render_page_stale_banner():
    fresh = render_page_html(_row(days_old=1))
    stale = render_page_html(_row(days_old=30))
    assert "days old" not in fresh
    assert "days old" in stale


def test_render_page_shows_scorecard_when_extras_present():
    extras = {
        "scorecard": {
            "growth": {"score": 8, "reason": "r"}, "profitability": {"score": 9, "reason": "r"},
            "moat": {"score": 9, "reason": "r"}, "management": {"score": 8, "reason": "r"},
            "valuation": {"score": 4, "reason": "r"}, "risk": {"score": 5, "reason": "r"},
            "overall_grade": "A-",
        },
        "bull_bear": {"bull": [{"point": "p", "evidence": "e"}],
                      "bear": [{"point": "p", "evidence": "e"}], "verdict": "v"},
    }
    report = f"# NVDA\n\nBody.\n\n```prism-json\n{json.dumps(extras)}\n```\n"
    html = render_page_html(_row(report=report))
    assert "A-" in html
    assert "prism-json" not in html  # raw block never leaks into the page


def test_sitemap_shape():
    xml = sitemap_xml_from([("NVDA", "2026-07-01T00:00:00+00:00"), ("AAPL", "2026-07-02T00:00:00+00:00")])
    assert xml.startswith("<?xml")
    assert "/r/NVDA" in xml and "/r/AAPL" in xml
    assert "<lastmod>2026-07-01</lastmod>" in xml


def test_publish_rejects_missing_report(monkeypatch):
    monkeypatch.setattr(ps, "_own_history_report", lambda uid, t: None)
    with pytest.raises(PublishError) as e:
        publish_report("user-1", "NVDA")
    assert e.value.code == "no_report"


def test_publish_rejects_stale_report(monkeypatch):
    old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    monkeypatch.setattr(ps, "_own_history_report",
                        lambda uid, t: {"ticker": "NVDA", "report": "x", "created_at": old})
    with pytest.raises(PublishError) as e:
        publish_report("user-1", "NVDA")
    assert e.value.code == "stale_report"


def test_publish_upserts_fresh_report(monkeypatch):
    now = datetime.now(timezone.utc).isoformat()
    monkeypatch.setattr(ps, "_own_history_report",
                        lambda uid, t: {"ticker": "NVDA", "company_name": "NVIDIA",
                                        "report": "body", "created_at": now})
    saved = {}
    monkeypatch.setattr(ps, "_upsert_public_report", lambda row: saved.update(row))
    result = publish_report("user-1", "NVDA")
    assert result["url_path"] == "/r/NVDA"
    assert saved["ticker"] == "NVDA"
    assert saved["published_by"] == "user-1"
