import os
import requests
from datetime import date

BASE = "https://financialmodelingprep.com/stable"


def _key():
    return os.getenv("FMP_API_KEY")


def get_valuation(ticker: str) -> dict:
    result = {"pe": None, "pb": None, "ps": None, "ev_ebitda": None, "sector_pe": None}
    api_key = _key()
    if not api_key:
        return result
    try:
        r = requests.get(f"{BASE}/key-metrics/?symbol={ticker}&apikey={api_key}", timeout=10)
        r.raise_for_status()
        data = r.json()
        if data and isinstance(data, list):
            m = data[0]
            result["pe"] = m.get("peRatio")
            result["pb"] = m.get("pbRatio")
            result["ps"] = m.get("priceToSalesRatio")
            result["ev_ebitda"] = m.get("enterpriseValueOverEBITDA")
    except Exception:
        pass
    return result


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
            result["change_pct_1d"] = float(p["changes"]) if p.get("changes") is not None else None
            result["market_cap"] = float(p["mktCap"]) if p.get("mktCap") is not None else None
            raw_range = p.get("range", "")
            if raw_range and "-" in str(raw_range):
                parts = str(raw_range).split("-")
                try:
                    result["week_52_low"] = float(parts[0].strip())
                    result["week_52_high"] = float(parts[-1].strip())
                except (ValueError, IndexError):
                    pass
    except Exception:
        pass
    return result


def get_sector_pe(sector: str) -> float | None:
    api_key = _key()
    if not api_key or not sector:
        return None
    try:
        today = date.today().isoformat()
        r = requests.get(
            f"{BASE}/sector_price_earning_ratio",
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
    except Exception:
        pass
    return None
