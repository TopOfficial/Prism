"""Portfolio analyzer: paste-in holdings → exposure, concentration, valuation,
and (for subscribers) an AI-written assessment generated strictly from the
computed stats. One portfolio per user in the `holdings` table."""
import os
import re
import json
import time

MAX_HOLDINGS = 50
_TICKER_RE = re.compile(r"^[A-Z0-9.\-]{1,12}$")
_QUOTE_CACHE: dict[str, tuple[float, dict]] = {}
_QUOTE_TTL_S = 3600
_ASSESS_MODEL = "claude-sonnet-4-6"


def _sb():
    from services.auth_service import _sb as sb
    return sb()


# ── Input parsing ────────────────────────────────────────────────────────────

def parse_holdings_text(text: str) -> tuple[list, list]:
    """Parse `TICKER, shares[, cost_basis]` lines (comma or whitespace separated).
    Returns (rows, errors); a line failing validation lands in errors, not rows."""
    rows, errors = [], []
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    if len(lines) > MAX_HOLDINGS:
        return [], [f"Too many holdings ({len(lines)}) — max {MAX_HOLDINGS}."]
    for ln in lines:
        parts = [p.strip() for p in (ln.split(",") if "," in ln else ln.split()) if p.strip()]
        if len(parts) < 2:
            errors.append(f"'{ln}': need at least TICKER and shares")
            continue
        ticker = parts[0].upper()
        if not _TICKER_RE.match(ticker):
            errors.append(f"'{ln}': bad ticker")
            continue
        try:
            shares = float(parts[1])
            if shares <= 0:
                raise ValueError
        except ValueError:
            errors.append(f"'{ln}': bad share count")
            continue
        cost_basis = None
        if len(parts) >= 3:
            try:
                cost_basis = float(parts[2])
            except ValueError:
                errors.append(f"'{ln}': bad cost basis")
                continue
        rows.append({"ticker": ticker, "shares": shares, "cost_basis": cost_basis})
    return rows, errors


# ── Storage ──────────────────────────────────────────────────────────────────

def _holdings(user_id: str) -> list:
    try:
        res = (
            _sb().table("holdings")
            .select("ticker, shares, cost_basis")
            .eq("user_id", user_id)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def replace_holdings(user_id: str, rows: list) -> None:
    """Replace the user's whole portfolio (the paste box is the source of truth)."""
    sb = _sb()
    sb.table("holdings").delete().eq("user_id", user_id).execute()
    if rows:
        sb.table("holdings").insert([{**r, "user_id": user_id} for r in rows]).execute()


def remove_holding(user_id: str, ticker: str) -> None:
    try:
        _sb().table("holdings").delete().eq("user_id", user_id).eq("ticker", ticker).execute()
    except Exception as e:
        print(f"[PORTFOLIO] remove {ticker} failed: {e}")


# ── Quotes (cached) ──────────────────────────────────────────────────────────

def _quote(ticker: str) -> dict:
    """{price, name, sector, pe} from FMP (1h cache per ticker)."""
    now = time.time()
    cached = _QUOTE_CACHE.get(ticker)
    if cached and now - cached[0] < _QUOTE_TTL_S:
        return cached[1]
    from services.fmp_service import get_profile, get_valuation
    prof = get_profile(ticker)
    val = get_valuation(ticker) if prof.get("price") is not None else {}
    q = {
        "price": prof.get("price"),
        "name": prof.get("company_name"),
        "sector": prof.get("sector"),
        "pe": val.get("pe"),
    }
    _QUOTE_CACHE[ticker] = (now, q)
    return q


# ── Analysis ─────────────────────────────────────────────────────────────────

def analyze(user_id: str) -> dict:
    holdings = _holdings(user_id)
    priced, unpriced = [], []
    for h in holdings:
        q = _quote(h["ticker"])
        if q.get("price") is None:
            unpriced.append(h["ticker"])
            continue
        value = q["price"] * float(h["shares"])
        gain_pct = None
        if h.get("cost_basis"):
            gain_pct = round((q["price"] - float(h["cost_basis"])) / float(h["cost_basis"]) * 100, 1)
        priced.append({
            "ticker": h["ticker"], "name": q.get("name"), "sector": q.get("sector") or "Other",
            "price": q["price"], "shares": float(h["shares"]), "value": round(value, 2),
            "weight_pct": None,  # filled below
            "pe": round(q["pe"], 1) if q.get("pe") else None,
            "cost_basis": h.get("cost_basis"), "gain_pct": gain_pct,
        })

    total = sum(h["value"] for h in priced)
    sectors: dict[str, float] = {}
    weighted_pe_num = weighted_pe_den = 0.0
    for h in priced:
        h["weight_pct"] = round(h["value"] / total * 100, 1) if total else 0.0
        sectors[h["sector"]] = sectors.get(h["sector"], 0.0) + h["value"]
        if h["pe"]:
            weighted_pe_num += h["pe"] * h["value"]
            weighted_pe_den += h["value"]

    priced.sort(key=lambda h: h["value"], reverse=True)
    sector_rows = sorted(
        ({"sector": s, "weight_pct": round(v / total * 100, 1)} for s, v in sectors.items()),
        key=lambda r: r["weight_pct"], reverse=True,
    ) if total else []
    hhi = sum((h["value"] / total) ** 2 for h in priced) if total else 0.0

    return {
        "holdings": priced,
        "unpriced": unpriced,
        "sectors": sector_rows,
        "totals": {
            "value": round(total, 2),
            "weighted_pe": round(weighted_pe_num / weighted_pe_den, 1) if weighted_pe_den else None,
            "top_weight_pct": priced[0]["weight_pct"] if priced else 0.0,
            "hhi": round(hhi, 4),
        },
    }


def ai_assessment(analysis: dict) -> str:
    """Sonnet-written portfolio assessment from computed stats only (subscriber feature)."""
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=_ASSESS_MODEL, max_tokens=600,
        system=(
            "You assess a retail investor's portfolio for Prism. Using ONLY the computed stats "
            "provided (weights, sectors, concentration HHI, weighted P/E, gains), write <=180 words: "
            "the portfolio's dominant bets, its biggest structural risk (concentration, sector "
            "correlation, valuation), and one or two concrete rebalancing considerations. Plain "
            "prose. Direct. No invented numbers, no personalized advice framing — analysis only."
        ),
        messages=[{"role": "user", "content": json.dumps(analysis)}],
    )
    return "".join(b.text for b in resp.content if hasattr(b, "text")).strip()
