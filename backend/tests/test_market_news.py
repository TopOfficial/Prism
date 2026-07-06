import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.market_news_service as mns
from services.market_news_service import get_market_news


CONTENT = {
    "indexes": [{"symbol": "^GSPC", "label": "S&P 500", "price": 6100.0, "change_pct": 0.4}],
    "headlines": [{"title": "Markets rally", "url": "https://x.com/a", "source": "Reuters"}],
    "briefing": "Stocks rose today.",
}


def test_cache_hit_skips_build(monkeypatch):
    monkeypatch.setattr(mns, "_read_cache", lambda d: dict(CONTENT))
    monkeypatch.setattr(mns, "_build_content", lambda: (_ for _ in ()).throw(AssertionError("must not build")))
    out = get_market_news()
    assert out["briefing"] == "Stocks rose today."
    assert out["date"]


def test_cache_miss_builds_and_writes(monkeypatch):
    written = {}
    monkeypatch.setattr(mns, "_read_cache", lambda d: None)
    monkeypatch.setattr(mns, "_build_content", lambda: dict(CONTENT))
    monkeypatch.setattr(mns, "_write_cache", lambda d, c: written.update({"date": d, "content": c}))
    out = get_market_news()
    assert out["indexes"][0]["label"] == "S&P 500"
    assert written["content"]["briefing"] == "Stocks rose today."
    assert written["date"] == out["date"]


def test_briefing_failure_degrades_gracefully(monkeypatch):
    monkeypatch.setattr(mns, "_fetch_indexes", lambda: CONTENT["indexes"])
    monkeypatch.setattr(mns, "_fetch_headlines", lambda: CONTENT["headlines"])
    monkeypatch.setattr(mns, "_write_briefing", lambda idx, hl: (_ for _ in ()).throw(RuntimeError("api down")))
    content = mns._build_content()
    assert content["briefing"] is None
    assert content["indexes"] and content["headlines"]


def test_date_is_isoformat():
    assert len(mns._today_str()) == 10  # YYYY-MM-DD
