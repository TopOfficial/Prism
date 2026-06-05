WACC = 0.09
TERMINAL_GROWTH = 0.025
PROJECTION_YEARS = 5
UNDERVALUED_THRESHOLD = 0.20   # intrinsic > price by > 20%
OVERVALUED_THRESHOLD = -0.20   # intrinsic < price by > 20%


def _estimate_fcf_growth(financials_history: dict | None) -> float:
    """CAGR of FCF from earliest available annual period to TTM. Capped 3–25%."""
    if not financials_history:
        return 0.07

    fcf_vals = []
    for key in ("fy_minus_2", "fy_minus_1", "fy_current", "ttm"):
        period = financials_history.get(key) or {}
        v = period.get("fcf")
        if v is not None:
            fcf_vals.append(float(v))

    # Need at least two positive data points to compute a growth rate
    positives = [v for v in fcf_vals if v > 0]
    if len(positives) < 2:
        return 0.07

    n = len(positives) - 1
    cagr = (positives[-1] / positives[0]) ** (1 / n) - 1
    return max(0.03, min(cagr, 0.25))


def _dcf(fcf_ttm: float, growth: float, total_debt: float, cash: float,
         shares: float, price: float) -> dict:
    """
    Returns intrinsic value per share and margin of safety.
    margin > 0  → undervalued (price < intrinsic)
    margin < 0  → overvalued  (price > intrinsic)
    """
    pv_sum = 0.0
    fcf = fcf_ttm
    for t in range(1, PROJECTION_YEARS + 1):
        fcf *= (1 + growth)
        pv_sum += fcf / (1 + WACC) ** t

    fcf_terminal = fcf * (1 + TERMINAL_GROWTH)
    terminal_value = fcf_terminal / (WACC - TERMINAL_GROWTH)
    pv_terminal = terminal_value / (1 + WACC) ** PROJECTION_YEARS

    enterprise_value = pv_sum + pv_terminal
    equity_value = enterprise_value - total_debt + cash
    if equity_value <= 0 or shares <= 0:
        return {"intrinsic": None, "margin": None}

    intrinsic = equity_value / shares
    margin = (intrinsic - price) / intrinsic
    return {"intrinsic": round(intrinsic, 2), "margin": round(margin, 4)}


def compute_verdict(pe, sector_pe, fcf_ttm, de_ratio, eps_ttm,
                    financials_history=None, total_debt=None, cash=None,
                    shares_outstanding=None, price=None):

    # --- DCF path: requires positive FCF, price, and shares ---
    dcf_result = None
    if (fcf_ttm is not None and fcf_ttm > 0
            and price is not None and price > 0
            and shares_outstanding is not None and shares_outstanding > 0):

        debt = total_debt or 0.0
        cash_ = cash or 0.0
        growth = _estimate_fcf_growth(financials_history)
        dcf_result = _dcf(fcf_ttm, growth, debt, cash_, shares_outstanding, price)

    if dcf_result and dcf_result["intrinsic"] is not None:
        intrinsic = dcf_result["intrinsic"]
        margin = dcf_result["margin"]
        growth_used = _estimate_fcf_growth(financials_history)

        if margin >= UNDERVALUED_THRESHOLD:
            label = "UNDERVALUED"
            reason = (f"DCF intrinsic value ${intrinsic:,.2f} is "
                      f"{margin*100:.1f}% above market price ${price:,.2f} "
                      f"(FCF growth: {growth_used*100:.1f}%, WACC: {WACC*100:.0f}%).")
        elif margin <= OVERVALUED_THRESHOLD:
            label = "OVERVALUED"
            reason = (f"Market price ${price:,.2f} is "
                      f"{abs(margin)*100:.1f}% above DCF intrinsic value ${intrinsic:,.2f} "
                      f"(FCF growth: {growth_used*100:.1f}%, WACC: {WACC*100:.0f}%).")
        else:
            label = "FAIR VALUE"
            reason = (f"Market price ${price:,.2f} is within ±20% of DCF intrinsic value "
                      f"${intrinsic:,.2f} "
                      f"(FCF growth: {growth_used*100:.1f}%, WACC: {WACC*100:.0f}%).")

        bull = _best_metric(pe, sector_pe, fcf_ttm, eps_ttm)
        bear = _worst_metric(de_ratio, pe, sector_pe)
        return {
            "label": label,
            "reason": reason,
            "intrinsic_value": intrinsic,
            "margin_of_safety": round(margin * 100, 1),
            "dcf_inputs": {
                "fcf_ttm": fcf_ttm,
                "growth_rate": round(growth_used * 100, 1),
                "wacc": WACC * 100,
                "terminal_growth": TERMINAL_GROWTH * 100,
            },
            "bull_case": bull,
            "bear_case": bear,
        }

    # --- PE fallback: when FCF is unavailable or negative ---
    if pe is not None and sector_pe is not None:
        if pe < sector_pe * 0.8 and fcf_ttm is not None and fcf_ttm > 0:
            label = "UNDERVALUED"
            reason = f"P/E of {pe:.1f} is below 80% of sector P/E ({sector_pe:.1f}) and FCF is positive."
        elif pe > sector_pe * 1.3:
            label = "OVERVALUED"
            reason = f"P/E of {pe:.1f} exceeds 130% of sector P/E ({sector_pe:.1f})."
        else:
            label = "FAIR VALUE"
            reason = f"P/E of {pe:.1f} is within normal range of sector P/E ({sector_pe:.1f})."
    else:
        label = "FAIR VALUE"
        reason = "Insufficient data for DCF or P/E valuation."

    return {
        "label": label,
        "reason": reason,
        "intrinsic_value": None,
        "margin_of_safety": None,
        "dcf_inputs": None,
        "bull_case": _best_metric(pe, sector_pe, fcf_ttm, eps_ttm),
        "bear_case": _worst_metric(de_ratio, pe, sector_pe),
    }


def _best_metric(pe, sector_pe, fcf_ttm, eps_ttm):
    if pe is not None and sector_pe is not None and pe < sector_pe:
        return f"Trading below sector P/E ({pe:.1f} vs {sector_pe:.1f})"
    if fcf_ttm is not None and fcf_ttm > 0:
        return f"FCF positive at {fcf_ttm / 1e9:.2f}B"
    if eps_ttm is not None and eps_ttm > 0:
        return f"EPS positive at {eps_ttm:.2f}"
    return "Stable financial position"


def _worst_metric(de_ratio, pe, sector_pe):
    if de_ratio is not None and de_ratio > 2.0:
        return f"High D/E ratio of {de_ratio:.1f}"
    if pe is not None and sector_pe is not None and pe > sector_pe * 1.2:
        return f"P/E premium over sector ({pe:.1f} vs {sector_pe:.1f})"
    if de_ratio is not None and de_ratio > 1.0:
        return f"Elevated D/E ratio of {de_ratio:.1f}"
    return "Limited downside indicators from available data"
