import feedparser


def get_news(ticker: str) -> list:
    try:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}"
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:5]:
            items.append({
                "title": entry.get("title"),
                "url": entry.get("link"),
                "published": entry.get("published"),
            })
        return items
    except Exception:
        return []
