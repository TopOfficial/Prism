import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.scoring import compute_quality_scores


def _make_data(
    gross_margin=None, operating_margin=None, fy_cur_rev=None, fy_m1_rev=None,
    ttm_rev=None, ebitda_ttm=None, fcf_ttm=None, total_debt=None, cash=None,
    de_ratio=None, roe_ttm=None, roic_ttm=None, pe=None, sector_pe=None,
    market_cap=None, earnings_history=None,
):
    fh = {
        "ttm": {
            "revenue": ttm_rev,
            "gross_margin_pct": gross_margin,
            "operating_margin_pct": operating_margin,
            "ebitda": ebitda_ttm,
            "fcf": fcf_ttm,
        },
        "fy_current": {"revenue": fy_cur_rev, "gross_margin_pct": None, "operating_margin_pct": None},
        "fy_minus_1": {"revenue": fy_m1_rev, "gross_margin_pct": None, "operating_margin_pct": None},
        "fy_minus_2": {"revenue": None},
    }
    return {
        "financials_history": fh,
        "overview": {
            "fcf_ttm": fcf_ttm,
            "roe_ttm": roe_ttm,
            "roic_ttm": roic_ttm,
        },
        "balance_sheet": {
            "total_debt": total_debt,
            "cash": cash,
            "de_ratio": de_ratio,
        },
        "valuation": {"pe": pe, "sector_pe": sector_pe},
        "earnings_history": earnings_history or [],
        "market_cap": market_cap,
    }


def test_business_quality_high_margins():
    data = _make_data(gross_margin=68, operating_margin=20, fy_cur_rev=110e9, fy_m1_rev=100e9)
    result = compute_quality_scores(data)
    assert result["business_quality"] >= 9


def test_business_quality_negative_margins():
    data = _make_data(gross_margin=15, operating_margin=-5, fy_cur_rev=90e9, fy_m1_rev=100e9)
    result = compute_quality_scores(data)
    assert result["business_quality"] <= 4


def test_financial_health_net_cash():
    data = _make_data(
        total_debt=5e9, cash=20e9, de_ratio=0.2,
        ebitda_ttm=10e9, fcf_ttm=3e9, roe_ttm=20,
    )
    result = compute_quality_scores(data)
    assert result["financial_health"] >= 8


def test_financial_health_overleveraged():
    data = _make_data(
        total_debt=50e9, cash=2e9, de_ratio=3.0,
        ebitda_ttm=8e9, fcf_ttm=-2e9, roe_ttm=None,
    )
    result = compute_quality_scores(data)
    assert result["financial_health"] <= 2


def test_valuation_discount():
    data = _make_data(pe=15, sector_pe=25, market_cap=100e9, fcf_ttm=6e9)
    result = compute_quality_scores(data)
    assert result["valuation_attractiveness"] >= 7


def test_valuation_premium():
    data = _make_data(pe=60, sector_pe=25, market_cap=500e9, fcf_ttm=5e9)
    result = compute_quality_scores(data)
    assert result["valuation_attractiveness"] <= 3


def test_growth_strong():
    earnings = [
        {"quarter": "2024-09-30", "eps_actual": 1.5, "eps_estimate": 1.2, "beat": True},
        {"quarter": "2024-06-30", "eps_actual": 1.3, "eps_estimate": 1.1, "beat": True},
    ]
    data = _make_data(ttm_rev=120e9, fy_cur_rev=100e9, earnings_history=earnings)
    result = compute_quality_scores(data)
    assert result["growth_outlook"] >= 8


def test_growth_declining_misses():
    earnings = [
        {"quarter": "2024-09-30", "eps_actual": 0.8, "eps_estimate": 1.2, "beat": False},
        {"quarter": "2024-06-30", "eps_actual": 0.7, "eps_estimate": 1.1, "beat": False},
    ]
    data = _make_data(ttm_rev=80e9, fy_cur_rev=100e9, earnings_history=earnings)
    result = compute_quality_scores(data)
    assert result["growth_outlook"] <= 3


def test_null_safety():
    data = _make_data()  # all None
    result = compute_quality_scores(data)
    assert isinstance(result, dict)
    assert result["business_quality"] == 5
    assert result["financial_health"] == 5
    assert result["valuation_attractiveness"] == 5
    assert result["growth_outlook"] == 5
    assert result["overall"] == 5.0
    assert isinstance(result["signals"], list)


def test_signals_count():
    data = _make_data(
        gross_margin=65, operating_margin=22, fy_cur_rev=110e9, fy_m1_rev=100e9,
        total_debt=5e9, cash=20e9, ebitda_ttm=10e9, fcf_ttm=3e9, roe_ttm=18,
        de_ratio=0.3, pe=14, sector_pe=25, market_cap=150e9, ttm_rev=120e9,
    )
    result = compute_quality_scores(data)
    assert len(result["signals"]) <= 3


def test_overall_is_average():
    data = _make_data()
    result = compute_quality_scores(data)
    expected = round((
        result["business_quality"] +
        result["financial_health"] +
        result["valuation_attractiveness"] +
        result["growth_outlook"]
    ) / 4, 1)
    assert result["overall"] == expected


def test_scores_clamped_to_1_10():
    # Maximally bad scenario
    data = _make_data(
        gross_margin=5, operating_margin=-30, fy_cur_rev=50e9, fy_m1_rev=100e9,
        total_debt=100e9, cash=1e9, ebitda_ttm=5e9, fcf_ttm=-10e9, roe_ttm=-50,
        de_ratio=5.0, pe=200, sector_pe=20, market_cap=50e9, ttm_rev=40e9,
        earnings_history=[
            {"quarter": "2024-09-30", "eps_actual": -1.0, "eps_estimate": 0.5, "beat": False},
            {"quarter": "2024-06-30", "eps_actual": -0.5, "eps_estimate": 0.3, "beat": False},
        ],
    )
    result = compute_quality_scores(data)
    for key in ("business_quality", "financial_health", "valuation_attractiveness", "growth_outlook"):
        assert 1 <= result[key] <= 10


def test_null_pe_skipped_not_penalized():
    # pe=None (negative earnings) should not penalize valuation score
    data_null_pe = _make_data(pe=None, sector_pe=25, market_cap=100e9, fcf_ttm=10e9)
    data_high_pe = _make_data(pe=50, sector_pe=25, market_cap=100e9, fcf_ttm=10e9)
    result_null = compute_quality_scores(data_null_pe)
    result_high = compute_quality_scores(data_high_pe)
    # null pe should score better than overvalued pe
    assert result_null["valuation_attractiveness"] >= result_high["valuation_attractiveness"]


# --- Competitive moat ---------------------------------------------------------

from services.scoring import compute_moat


def _moat_data(roic=None, roe=None, gm=(None, None, None), om_cur=None):
    return {
        "overview": {"roic_ttm": roic, "roe_ttm": roe},
        "financials_history": {
            "fy_minus_2": {"gross_margin_pct": gm[0]},
            "fy_minus_1": {"gross_margin_pct": gm[1]},
            "fy_current": {"gross_margin_pct": gm[2], "operating_margin_pct": om_cur},
        },
    }


def test_moat_wide_high_roic_stable_margins():
    m = compute_moat(_moat_data(roic=28, gm=(60, 61, 62), om_cur=30))
    assert m["rating"] == "Wide"
    assert m["score"] >= 7
    assert any("ROIC" in s for s in m["signals"])


def test_moat_none_low_roic_commodity_margins():
    m = compute_moat(_moat_data(roic=4, gm=(18, 16, 14)))
    assert m["rating"] == "None"
    assert m["score"] < 4


def test_moat_narrow_middle():
    # Neutral ROIC, moderate but stable margins → middling moat.
    m = compute_moat(_moat_data(roic=7, gm=(28, 28, 28)))
    assert m["rating"] == "Narrow"


def test_moat_insufficient_data():
    m = compute_moat(_moat_data())
    assert m["rating"] in ("Wide", "Narrow", "None")
    assert m["signals"]
