"""Economic dashboard data (v2.0): key FRED series, cached in-process for 12h.
Disabled (returns enabled=False) until FRED_API_KEY is set — a free key from
https://fred.stlouisfed.org/docs/api/api_key.html activates it, no deploy needed."""
import os
import time

_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL_S = 12 * 3600

# (series_id, label, unit, transform) — yoy turns an index into a % change.
_SERIES = [
    ("FEDFUNDS", "Fed Funds Rate", "%", None),
    ("DGS10", "10Y Treasury", "%", None),
    ("CPIAUCSL", "Inflation (CPI YoY)", "%", "yoy"),
    ("UNRATE", "Unemployment", "%", None),
]


def _fred_series(series_id: str, key: str) -> dict | None:
    """{value, date, prev} for the latest observation (13 back for YoY math)."""
    import requests
    try:
        r = requests.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={"series_id": series_id, "api_key": key, "file_type": "json",
                    "sort_order": "desc", "limit": 14},
            timeout=10,
        )
        r.raise_for_status()
        obs = [o for o in r.json().get("observations", []) if o.get("value") not in (None, ".")]
        if not obs:
            return None
        latest = obs[0]
        return {
            "value": float(latest["value"]),
            "date": latest.get("date"),
            "prev": float(obs[1]["value"]) if len(obs) > 1 else None,
            "yoy_base": float(obs[12]["value"]) if len(obs) > 12 else None,
        }
    except Exception as e:
        print(f"[MACRO] {series_id}: {type(e).__name__}: {e}")
        return None


def get_macro() -> dict:
    key = os.environ.get("FRED_API_KEY")
    if not key:
        return {"enabled": False, "series": []}

    now = time.time()
    cached = _CACHE.get("macro")
    if cached and now - cached[0] < _CACHE_TTL_S:
        return cached[1]

    series = []
    for sid, label, unit, transform in _SERIES:
        data = _fred_series(sid, key)
        if not data:
            continue
        value = data["value"]
        if transform == "yoy":
            base = data.get("yoy_base")
            if not base:
                continue
            value = round((data["value"] - base) / base * 100, 1)
        series.append({
            "id": sid, "label": label, "unit": unit,
            "value": round(value, 2), "as_of": data.get("date"),
        })

    result = {"enabled": True, "series": series}
    _CACHE["macro"] = (now, result)
    return result
