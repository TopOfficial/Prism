"""Comparable companies: real peer metrics (never model-generated) shown with
every Deep Research run and fed into the model's context so its prose cites
actual figures. Peer sets and metrics are cached in-process for 24h — cost is
at most 1 + len(peers) FMP calls per ticker per day across all users."""
import time
import json

_CACHE: dict[str, tuple[float, dict | None]] = {}
_CACHE_TTL_S = 24 * 3600
_MAX_PEERS = 4


def _peers(ticker: str) -> list:
    from services.fmp_service import get_peers
    return get_peers(ticker, limit=_MAX_PEERS)


def _valuation(ticker: str) -> dict:
    from services.fmp_service import get_valuation
    return get_valuation(ticker)


def _round(v, nd=1):
    try:
        return round(float(v), nd)
    except (TypeError, ValueError):
        return None


def build_comparables(ticker: str, own_row: dict) -> dict | None:
    """{"subject": {...}, "peers": [{ticker, name, market_cap, pe, ps, ev_ebitda}]}
    or None when FMP has no peer set (common for small non-US listings)."""
    now = time.time()
    cached = _CACHE.get(ticker)
    if cached and now - cached[0] < _CACHE_TTL_S:
        peers_rows = cached[1]
    else:
        peers = _peers(ticker)
        peers_rows = []
        for p in peers[:_MAX_PEERS]:
            val = _valuation(p["symbol"])
            peers_rows.append({
                "ticker": p["symbol"],
                "name": p.get("name"),
                "market_cap": p.get("market_cap"),
                "pe": _round(val.get("pe")),
                "ps": _round(val.get("ps")),
                "ev_ebitda": _round(val.get("ev_ebitda")),
            })
        _CACHE[ticker] = (now, peers_rows)

    if not peers_rows:
        return None
    return {
        "subject": {
            "ticker": ticker,
            "name": own_row.get("name"),
            "market_cap": own_row.get("market_cap"),
            "pe": _round(own_row.get("pe")),
            "ps": _round(own_row.get("ps")),
            "ev_ebitda": _round(own_row.get("ev_ebitda")),
        },
        "peers": peers_rows,
    }


def attach_comps(report: str, comps: dict | None) -> str:
    """Append the server-generated comparables block to the raw report text so
    saved history / the shared cache carry real peer data (mirrors prism-json)."""
    if not comps:
        return report
    return report.rstrip() + "\n\n```prism-comps\n" + json.dumps(comps) + "\n```\n"


def comps_context_lines(comps: dict | None) -> str:
    """Plain-text peer table for the Claude prompt context."""
    if not comps:
        return ""
    def fmt(row):
        mc = row.get("market_cap")
        mc_s = f"${mc / 1e9:.1f}B" if mc else "N/A"
        return (f"{row['ticker']} ({row.get('name') or 'N/A'}): MktCap={mc_s} | "
                f"P/E={row.get('pe') or 'N/A'} | P/S={row.get('ps') or 'N/A'} | "
                f"EV/EBITDA={row.get('ev_ebitda') or 'N/A'}")
    lines = ["", "=== PEER COMPARISON (real fetched data — use these figures for Phase 1 section 3) ==="]
    lines.append("SUBJECT " + fmt(comps["subject"]))
    lines += [fmt(p) for p in comps["peers"]]
    return "\n".join(lines)
