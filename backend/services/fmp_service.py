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
