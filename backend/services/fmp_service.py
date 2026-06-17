import os
import requests
from datetime import date

BASE = "https://financialmodelingprep.com/stable"


def _key():
    return os.getenv("FMP_API_KEY")


def get_valuation(ticker: str) -> dict:
    result = {"pe": None, "pb": None, "ps": None, "ev_ebitda": None, "sector_pe": None, "pct_held_institutions": None}
    api_key = _key()
    if not api_key:
        return result
    try:
        r = requests.get(f"{BASE}/ratios-ttm", params={"symbol": ticker, "apikey": api_key}, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data and isinstance(data, list):
            m = data[0]
            result["pe"] = m.get("priceToEarningsRatioTTM")
            result["pb"] = m.get("priceToBookRatioTTM")
            result["ps"] = m.get("priceToSalesRatioTTM")
            result["ev_ebitda"] = m.get("enterpriseValueMultipleTTM")
            # The stable ratios-ttm endpoint no longer returns institutional ownership;
            # pct_held_institutions stays None here and yfinance remains its source.
    except Exception as e:
        print(f"[FMP] get_valuation {ticker}: {type(e).__name__}: {e}")
    return result


def get_earnings(ticker: str) -> list:
    api_key = _key()
    if not api_key:
        return []
    try:
        r = requests.get(f"{BASE}/earnings", params={"symbol": ticker, "apikey": api_key}, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            return []
        # The stable /earnings endpoint returns a calendar including future quarters whose
        # actuals are null. Keep only reported quarters, newest first, max 4.
        reported = [d for d in data if d.get("epsActual") is not None]
        reported.sort(key=lambda d: str(d.get("date", "")), reverse=True)
        results = []
        for item in reported[:4]:
            actual = item.get("epsActual")
            estimated = item.get("epsEstimated")
            beat = None
            if actual is not None and estimated is not None:
                try:
                    beat = float(actual) >= float(estimated)
                except (TypeError, ValueError):
                    pass
            results.append({
                "quarter": str(item.get("date", ""))[:10],
                "eps_actual": float(actual) if actual is not None else None,
                "eps_estimate": float(estimated) if estimated is not None else None,
                "beat": beat,
            })
        return results
    except Exception as e:
        print(f"[FMP] get_earnings {ticker}: {type(e).__name__}: {e}")
        return []


def get_profile(ticker: str) -> dict:
    result = {"company_name": None, "sector": None, "price": None,
              "change_pct_1d": None, "market_cap": None,
              "week_52_high": None, "week_52_low": None}
    api_key = _key()
    if not api_key:
        return result
    try:
        r = requests.get(f"{BASE}/profile?symbol={ticker}&apikey={api_key}", timeout=10)
        r.raise_for_status()
        data = r.json()
        if data and isinstance(data, list):
            p = data[0]
            result["company_name"] = p.get("companyName")
            result["sector"] = p.get("sector")
            result["price"] = float(p["price"]) if p.get("price") is not None else None
            # changesPercentage is the actual % change; "changes" is dollar change
            pct = p.get("changesPercentage")
            result["change_pct_1d"] = float(pct) if pct is not None else None
            result["market_cap"] = float(p["mktCap"]) if p.get("mktCap") is not None else None
            raw_range = p.get("range", "")
            if raw_range and "-" in str(raw_range):
                parts = str(raw_range).split("-")
                try:
                    result["week_52_low"] = float(parts[0].strip())
                    result["week_52_high"] = float(parts[-1].strip())
                except (ValueError, IndexError):
                    pass
    except Exception as e:
        print(f"[FMP] get_profile {ticker}: {type(e).__name__}: {e}")
    return result


def search_tickers(query: str, limit: int = 8) -> list:
    api_key = _key()
    if not api_key or not query:
        return []
    try:
        r = requests.get(
            f"{BASE}/search-symbol",
            params={"query": query, "limit": limit, "apikey": api_key},
            timeout=5,
        )
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            return []
        return [
            {"symbol": d["symbol"], "name": d.get("name", ""), "exchange": d.get("exchange", "")}
            for d in data if d.get("symbol")
        ]
    except Exception as e:
        print(f"[FMP] search_tickers {query}: {type(e).__name__}: {e}")
        return []


def get_sector_pe(sector: str) -> float | None:
    api_key = _key()
    if not api_key or not sector:
        return None
    try:
        today = date.today().isoformat()
        r = requests.get(
            f"{BASE}/sector-pe-snapshot",
            params={"date": today, "exchange": "NYSE", "apikey": api_key},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            return None
        sector_lower = sector.lower()
        for entry in data:
            if entry.get("sector", "").lower() in sector_lower or sector_lower in entry.get("sector", "").lower():
                val = entry.get("pe")
                return float(val) if val is not None else None
    except Exception as e:
        print(f"[FMP] get_sector_pe {sector}: {type(e).__name__}: {e}")
    return None
