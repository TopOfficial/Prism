"""Today's Market News — one AI-written market briefing per day, shown to all
users on the homepage. Generated on the first request of the (US/Eastern) day
and cached in the `market_news` Supabase table, so every subsequent visitor
reads the same cached row: cost is one Haiku call per day, not per user.
"""
import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

_MARKET_TZ = ZoneInfo("America/New_York")
_BRIEFING_MODEL = os.environ.get("MARKET_NEWS_MODEL", "claude-haiku-4-5-20251001")

_INDEXES = [
    ("^GSPC", "S&P 500"),
    ("^IXIC", "Nasdaq"),
    ("^DJI", "Dow Jones"),
    ("^VIX", "VIX"),
]


def _today_str() -> str:
    return datetime.now(_MARKET_TZ).date().isoformat()


# ── Cache (Supabase) ─────────────────────────────────────────────────────────

def _sb():
    from services.auth_service import _sb as sb
    return sb()


def _read_cache(date_str: str) -> dict | None:
    try:
        res = _sb().table("market_news").select("content").eq("date", date_str).single().execute()
        return res.data["content"] if res.data else None
    except Exception:
        return None


def _write_cache(date_str: str, content: dict) -> None:
    try:
        _sb().table("market_news").upsert(
            {"date": date_str, "content": content}, on_conflict="date"
        ).execute()
    except Exception as e:
        print(f"[MARKET] cache write failed: {e}")


# ── Data fetchers ────────────────────────────────────────────────────────────

def _fetch_indexes() -> list:
    import yfinance as yf
    out = []
    for symbol, label in _INDEXES:
        try:
            info = yf.Ticker(symbol).fast_info
            price = info.last_price
            prev = info.previous_close
            change_pct = round((price - prev) / prev * 100, 2) if price and prev else None
            out.append({"symbol": symbol, "label": label,
                        "price": round(price, 2) if price else None,
                        "change_pct": change_pct})
        except Exception as e:
            print(f"[MARKET] index {symbol}: {type(e).__name__}: {e}")
    return out


def _fetch_headlines() -> list:
    key = os.getenv("FINNHUB_API_KEY")
    if key:
        try:
            r = requests.get(
                "https://finnhub.io/api/v1/news",
                params={"category": "general", "token": key},
                timeout=8,
            )
            r.raise_for_status()
            articles = r.json()
            if isinstance(articles, list) and articles:
                return [
                    {"title": a.get("headline"), "url": a.get("url"), "source": a.get("source")}
                    for a in articles[:6] if a.get("headline")
                ]
        except Exception as e:
            print(f"[MARKET] Finnhub general news: {type(e).__name__}: {e}")
    # Fallback: Yahoo Finance market RSS
    try:
        import feedparser
        feed = feedparser.parse("https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC")
        return [
            {"title": e.get("title"), "url": e.get("link"), "source": "Yahoo Finance"}
            for e in feed.entries[:6]
        ]
    except Exception as e:
        print(f"[MARKET] Yahoo RSS fallback: {type(e).__name__}: {e}")
        return []


def _write_briefing(indexes: list, headlines: list) -> str:
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")

    context = {
        "indexes": indexes,
        "headlines": [h["title"] for h in headlines],
        "date": _today_str(),
    }
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=_BRIEFING_MODEL,
        max_tokens=500,
        system=(
            "You write the daily market briefing for Prism, a stock research app. "
            "Given today's index levels and top headlines, write a ~130-word briefing for "
            "retail investors: what the market is doing, the one or two themes driving it, "
            "and what to watch. Plain prose, no headers, no bullet lists, no hedging filler. "
            "Do not invent numbers not present in the data."
        ),
        messages=[{"role": "user", "content": json.dumps(context)}],
    )
    return "".join(b.text for b in response.content if hasattr(b, "text")).strip()


def _build_content() -> dict:
    indexes = _fetch_indexes()
    headlines = _fetch_headlines()
    try:
        briefing = _write_briefing(indexes, headlines)
    except Exception as e:
        print(f"[MARKET] briefing generation failed: {type(e).__name__}: {e}")
        briefing = None
    return {"indexes": indexes, "headlines": headlines, "briefing": briefing}


def get_market_news() -> dict:
    """Today's cached market briefing, generating and caching it on first request."""
    today = _today_str()
    content = _read_cache(today)
    if content is None:
        content = _build_content()
        _write_cache(today, content)
    return {"date": today, **content}
