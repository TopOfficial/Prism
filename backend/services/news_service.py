import feedparser

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def get_news(ticker: str) -> list:
    try:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}"
        feed = feedparser.parse(url, request_headers={"User-Agent": _UA})
        if not feed.entries:
            print(f"[news] {ticker} - RSS returned 0 entries (bozo={feed.get('bozo', '?')})")
        items = []
        for entry in feed.entries[:5]:
            items.append({
                "title": entry.get("title"),
                "url": entry.get("link"),
                "published": entry.get("published"),
            })
        return items
    except Exception as e:
        print(f"[news] {ticker}: {type(e).__name__}: {e}")
        return []
