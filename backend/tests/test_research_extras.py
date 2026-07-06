import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.research_service import extract_extras


VALID_EXTRAS = {
    "scorecard": {
        "growth": {"score": 8, "reason": "Revenue up 39% YoY"},
        "profitability": {"score": 9, "reason": "Net margin 55%"},
        "moat": {"score": 9, "reason": "CUDA ecosystem lock-in"},
        "management": {"score": 8, "reason": "Consistent execution"},
        "valuation": {"score": 4, "reason": "P/E 55 vs sector 28"},
        "risk": {"score": 5, "reason": "Customer concentration"},
        "overall_grade": "A-",
    },
    "bull_bear": {
        "bull": [{"point": "Datacenter demand", "evidence": "Backlog $50B"}],
        "bear": [{"point": "Valuation stretched", "evidence": "P/E 2x sector"}],
        "verdict": "Bull case more credible near-term.",
    },
}


def _report_with_block(extras=VALID_EXTRAS, json_text=None):
    body = json_text if json_text is not None else json.dumps(extras)
    return (
        "# PHASE 1\n\nSome analysis text.\n\n## Verdict\n\nBuy.\n\n"
        f"```prism-json\n{body}\n```\n"
    )


def test_parses_and_strips_block():
    report = _report_with_block()
    clean, extras = extract_extras(report)
    assert "prism-json" not in clean
    assert "Some analysis text." in clean
    assert extras["scorecard"]["growth"]["score"] == 8
    assert extras["bull_bear"]["verdict"].startswith("Bull")


def test_no_block_returns_none():
    report = "# PHASE 1\n\nJust a plain old report.\n"
    clean, extras = extract_extras(report)
    assert clean == report
    assert extras is None


def test_malformed_json_returns_original_and_none():
    report = _report_with_block(json_text="{not valid json!!")
    clean, extras = extract_extras(report)
    assert clean == report  # untouched — don't silently delete content we can't parse
    assert extras is None


def test_missing_required_keys_returns_none():
    report = _report_with_block(extras={"scorecard": {}})  # no bull_bear
    clean, extras = extract_extras(report)
    assert extras is None
    assert clean == report


def test_block_mid_text_tolerated():
    report = _report_with_block() + "\nTrailing analyst note.\n"
    clean, extras = extract_extras(report)
    assert extras is not None
    assert "Trailing analyst note." in clean
    assert "prism-json" not in clean


def test_none_and_empty_input():
    clean, extras = extract_extras("")
    assert clean == "" and extras is None
