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


def compute_verdict(pe, sector_pe, fcf_ttm, de_ratio, eps_ttm):
    if pe is None or sector_pe is None:
        label = "FAIR VALUE"
        reason = "Insufficient valuation data to determine verdict."
    elif pe < sector_pe * 0.8 and fcf_ttm is not None and fcf_ttm > 0:
        label = "UNDERVALUED"
        reason = f"P/E of {pe:.1f} is below 80% of sector P/E ({sector_pe:.1f}) and FCF is positive."
    elif pe > sector_pe * 1.3:
        label = "OVERVALUED"
        reason = f"P/E of {pe:.1f} exceeds 130% of sector P/E ({sector_pe:.1f})."
    else:
        label = "FAIR VALUE"
        reason = f"P/E of {pe:.1f} is within normal range of sector P/E ({sector_pe:.1f})."

    return {
        "label": label,
        "reason": reason,
        "bull_case": _best_metric(pe, sector_pe, fcf_ttm, eps_ttm),
        "bear_case": _worst_metric(de_ratio, pe, sector_pe),
    }
