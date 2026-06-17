import os
import requests
import feedparser
from datetime import date, timedelta

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _finnhub_news(ticker: str) -> list:
    key = os.getenv("FINNHUB_API_KEY")
    if not key:
        return []
    try:
        to_date = date.today().isoformat()
        from_date = (date.today() - timedelta(days=30)).isoformat()
        r = requests.get(
            "https://finnhub.io/api/v1/company-news",
            params={"symbol": ticker, "from": from_date, "to": to_date, "token": key},
            timeout=8,
        )
        r.raise_for_status()
        articles = r.json()
        if not isinstance(articles, list):
            return []
        items = []
        for a in articles[:5]:
            ts = a.get("datetime")
            published = date.fromtimestamp(ts).isoformat() if ts else None
            items.append({
                "title": a.get("headline"),
                "url": a.get("url"),
                "published": published,
            })
        return items
    except Exception as e:
        print(f"[news] Finnhub {ticker}: {type(e).__name__}: {e}")
        return []


def _yahoo_rss_news(ticker: str) -> list:
    try:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}"
        feed = feedparser.parse(url, request_headers={"User-Agent": _UA})
        if not feed.entries:
            print(f"[news] {ticker} - Yahoo RSS returned 0 entries (bozo={feed.get('bozo', '?')})")
            return []
        return [
            {"title": e.get("title"), "url": e.get("link"), "published": e.get("published")}
            for e in feed.entries[:5]
        ]
    except Exception as e:
        print(f"[news] Yahoo RSS {ticker}: {type(e).__name__}: {e}")
        return []


def get_news(ticker: str) -> list:
    items = _finnhub_news(ticker)
    if items:
        return items
    return _yahoo_rss_news(ticker)
