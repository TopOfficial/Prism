def _clamp(score):
    return max(1, min(10, score))


def _revenue_growth_pct(fh, period_a, period_b):
    """YoY growth from period_b → period_a (e.g. fy_minus_1 → fy_current)."""
    try:
        rev_a = (fh.get(period_a) or {}).get("revenue")
        rev_b = (fh.get(period_b) or {}).get("revenue")
        if rev_a is not None and rev_b is not None and rev_b != 0:
            return (rev_a - rev_b) / abs(rev_b) * 100
    except Exception:
        pass
    return None


def _score_business_quality(fh):
    score = 5
    signals = []
    skipped = False

    ttm = fh.get("ttm") or {}

    gm = ttm.get("gross_margin_pct")
    om = ttm.get("operating_margin_pct")
    rev_growth = _revenue_growth_pct(fh, "fy_current", "fy_minus_1")

    if gm is not None:
        if gm > 60:
            score += 1
            signals.append((1, f"Gross margin {gm:.1f}% — above 60% threshold"))
        if gm > 40:
            score += 2
            if gm <= 60:
                signals.append((2, f"Gross margin {gm:.1f}% — above 40% threshold"))
    else:
        skipped = True

    if om is not None:
        if om > 15:
            score += 2
            signals.append((2, f"Operating margin {om:.1f}% — above 15% threshold"))
        elif om < 0:
            score -= 2
            signals.append((-2, f"Operating margin {om:.1f}% — negative"))
    else:
        skipped = True

    if rev_growth is not None:
        if rev_growth > 10:
            score += 1
            signals.append((1, f"Revenue growth {rev_growth:.1f}% YoY — above 10%"))
        elif rev_growth < 0:
            score -= 1
            signals.append((-1, f"Revenue declining {abs(rev_growth):.1f}% YoY"))
    else:
        skipped = True

    return _clamp(score), signals, skipped


def _score_financial_health(overview, balance_sheet, fh):
    score = 5
    signals = []
    skipped = False

    total_debt = balance_sheet.get("total_debt")
    cash = balance_sheet.get("cash")
    de_ratio = balance_sheet.get("de_ratio")
    fcf_ttm = overview.get("fcf_ttm")
    roe_ttm = overview.get("roe_ttm")

    ttm = fh.get("ttm") or {}
    ebitda_ttm = ttm.get("ebitda")

    net_debt = None
    if total_debt is not None and cash is not None:
        net_debt = total_debt - cash

    net_debt_ebitda = None
    if net_debt is not None and ebitda_ttm is not None and ebitda_ttm != 0:
        net_debt_ebitda = net_debt / ebitda_ttm

    if net_debt_ebitda is not None:
        if net_debt_ebitda < 0:
            score += 1
            signals.append((1, "Net cash position (negative net debt)"))
        if net_debt_ebitda < 1.5:
            score += 2
            if net_debt_ebitda >= 0:
                signals.append((2, f"Net debt/EBITDA {net_debt_ebitda:.1f}x — below 1.5x"))
        elif net_debt_ebitda > 4:
            score -= 2
            signals.append((-2, f"Net debt/EBITDA {net_debt_ebitda:.1f}x — above 4x (overleveraged)"))
    else:
        skipped = True

    if fcf_ttm is not None:
        if fcf_ttm > 0:
            score += 1
            signals.append((1, f"Positive FCF (TTM {fcf_ttm / 1e9:.2f}B)"))
        else:
            score -= 2
            signals.append((-2, f"Negative FCF (TTM {fcf_ttm / 1e9:.2f}B)"))
    else:
        skipped = True

    if roe_ttm is not None:
        if roe_ttm > 15:
            score += 1
            signals.append((1, f"ROE {roe_ttm:.1f}% — above 15%"))
    else:
        skipped = True

    if de_ratio is not None:
        if de_ratio > 2:
            score -= 1
            signals.append((-1, f"D/E ratio {de_ratio:.1f}x — above 2x"))
    else:
        skipped = True

    return _clamp(score), signals, skipped


def _score_valuation(valuation, overview, market_cap, fh):
    score = 5
    signals = []
    skipped = False

    pe = valuation.get("pe")
    sector_pe = valuation.get("sector_pe")
    fcf_ttm = overview.get("fcf_ttm")

    if pe is not None and sector_pe is not None:
        ratio = pe / sector_pe
        if ratio < 0.8:
            score += 2
            signals.append((2, f"Trading at {ratio:.2f}x sector P/E ({pe:.1f} vs {sector_pe:.1f})"))
        elif ratio < 0.9:
            score += 1
            signals.append((1, f"Trading at {ratio:.2f}x sector P/E ({pe:.1f} vs {sector_pe:.1f})"))
        elif ratio > 1.5:
            score -= 2
            signals.append((-2, f"P/E premium {ratio:.2f}x sector ({pe:.1f} vs {sector_pe:.1f})"))
        elif ratio > 1.2:
            score -= 1
            signals.append((-1, f"P/E at {ratio:.2f}x sector ({pe:.1f} vs {sector_pe:.1f})"))
    elif pe is None:
        skipped = True  # negative earnings — neutral, no adjustment

    p_fcf = None
    if market_cap is not None and fcf_ttm is not None and fcf_ttm > 0:
        p_fcf = market_cap / fcf_ttm

    if p_fcf is not None:
        if p_fcf < 20:
            score += 1
            signals.append((1, f"P/FCF {p_fcf:.1f}x — below 20x"))
        elif p_fcf > 40:
            score -= 1
            signals.append((-1, f"P/FCF {p_fcf:.1f}x — above 40x"))
    else:
        skipped = True

    return _clamp(score), signals, skipped


def _score_growth_outlook(fh, earnings_history):
    score = 5
    signals = []
    skipped = False

    ttm = fh.get("ttm") or {}
    fy_cur = fh.get("fy_current") or {}

    ttm_rev = ttm.get("revenue")
    cur_rev = fy_cur.get("revenue")

    rev_growth_ttm = None
    if ttm_rev is not None and cur_rev is not None and cur_rev != 0:
        rev_growth_ttm = (ttm_rev - cur_rev) / abs(cur_rev) * 100
    else:
        # fall back to fy_current vs fy_minus_1
        rev_growth_ttm = _revenue_growth_pct(fh, "fy_current", "fy_minus_1")

    if rev_growth_ttm is not None:
        if rev_growth_ttm > 15:
            score += 2
            signals.append((2, f"Revenue growth {rev_growth_ttm:.1f}% — above 15%"))
        elif rev_growth_ttm > 5:
            score += 1
            signals.append((1, f"Revenue growth {rev_growth_ttm:.1f}% — above 5%"))
        elif rev_growth_ttm < -10:
            score -= 2
            signals.append((-2, f"Revenue shrinking {abs(rev_growth_ttm):.1f}% — below -10%"))
        elif rev_growth_ttm < 0:
            score -= 1
            signals.append((-1, f"Revenue declining {abs(rev_growth_ttm):.1f}%"))
    else:
        skipped = True

    # Earnings beats — last 2 quarters
    if earnings_history and len(earnings_history) >= 2:
        last2 = earnings_history[:2]
        beats = [q.get("beat") for q in last2 if q.get("beat") is not None]
        if len(beats) == 2:
            if all(beats):
                score += 1
                signals.append((1, "Beat EPS estimates in last 2 quarters"))
            elif not any(beats):
                score -= 1
                signals.append((-1, "Missed EPS estimates in last 2 quarters"))
    else:
        skipped = True

    return _clamp(score), signals, skipped


def compute_quality_scores(data: dict) -> dict:
    fh = data.get("financials_history") or {}
    overview = data.get("overview") or {}
    balance_sheet = data.get("balance_sheet") or {}
    valuation = data.get("valuation") or {}
    earnings_history = data.get("earnings_history") or []
    market_cap = data.get("market_cap")

    bq, bq_signals, bq_skip = _score_business_quality(fh)
    fh_score, fh_signals, fh_skip = _score_financial_health(overview, balance_sheet, fh)
    va, va_signals, va_skip = _score_valuation(valuation, overview, market_cap, fh)
    go, go_signals, go_skip = _score_growth_outlook(fh, earnings_history)

    all_signals = bq_signals + fh_signals + va_signals + go_signals
    all_signals.sort(key=lambda x: abs(x[0]), reverse=True)
    top_signals = [msg for _, msg in all_signals[:3]]

    any_skipped = bq_skip or fh_skip or va_skip or go_skip
    if any_skipped and len(top_signals) < 3:
        top_signals.append("Score based on available data only")
    elif any_skipped and "Score based on available data only" not in top_signals:
        if len(top_signals) >= 3:
            top_signals[2] = "Score based on available data only"

    overall = round((bq + fh_score + va + go) / 4, 1)

    return {
        "business_quality": bq,
        "financial_health": fh_score,
        "valuation_attractiveness": va,
        "growth_outlook": go,
        "overall": overall,
        "signals": top_signals,
    }
