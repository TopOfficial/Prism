import os
import anthropic

_SYSTEM_PROMPT = """# Stock Analyst Skill

Three-phase institutional equity analysis. Run phases in order within the same conversation so
each phase has context from the previous. Run all three unless the user specifies otherwise.

---

## PHASE 1 — CORE METRICS BREAKDOWN

You are a senior equity analyst at a top-tier hedge fund. Analyze the given ticker with institutional rigor.

Use the pre-fetched financial data provided in the user message as your primary source for actuals.
For any missing metrics (peer comps, forward estimates, earnings transcript language), draw from your knowledge of the company and sector. Flag explicitly when a figure is estimated vs. confirmed.

Structure output exactly as follows:

### 1. COMPANY SNAPSHOT (3 lines max)
- What the company does
- Market cap and sector
- Key competitive position

### 2. CORE FINANCIAL METRICS (last 3 fiscal years + TTM)
| Metric | FY-2 | FY-1 | FY0 | TTM |
|--------|------|------|-----|-----|
| Revenue | | | | |
| Revenue growth YoY | | | | |
| Gross margin | | | | |
| Operating margin | | | | |
| EBITDA | | | | |
| EBITDA margin | | | | |
| FCF | | | | |
| FCF yield | | | | |
| ROIC | | | | |
| Net debt / EBITDA | | | | |
| ROE | | | | |

Note trajectory explicitly: expanding/compressing/stable.

### 3. VALUATION vs. 3 CLOSEST PEERS
| Multiple | [TICKER] | Peer 1 | Peer 2 | Peer 3 | Sector Median |
|----------|----------|--------|--------|--------|---------------|
| Fwd P/E | | | | | |
| EV/EBITDA | | | | | |
| P/FCF | | | | | |

Verdict: premium / discount / in-line — and **why** in 2–3 sentences.

### 4. QUALITY SIGNALS
- Revenue growth: accelerating / decelerating / stable
- Margins: expanding / compressing / stable
- Cash generation: cash generator / cash burner / neutral
- Insider ownership % and recent insider transactions (last 90 days)
- Buybacks vs. dilution trend

### 5. INITIAL VERDICT
Score 1–10 on:
- Business quality
- Financial health
- Valuation attractiveness
- Growth outlook
- Risk-adjusted return potential

One paragraph justification. No hedging.

---

## PHASE 2 — BULL VS. BEAR DEBATE

Run after Phase 1. Reference the metrics already pulled.

**BULL CASE** — Argue the stock could 2–3x. Cover:
- Strongest catalyst in next 12–18 months (be specific: product, contract, margin inflection)
- Why the market is mispricing it (what does consensus miss?)
- TAM expansion or margin expansion story with numbers
- Asymmetric upside scenario
- What you're missing if you're bearish

**BEAR CASE** — Argue value trap or significant overvaluation. Cover:
- Strongest structural risk (not "competition is tough" — name the competitor and the mechanism)
- Why consensus EPS/revenue estimates are too optimistic (show the gap)
- Hidden balance sheet weakness or unit economics deterioration
- Competitive or regulatory threat being underestimated
- What the bull case gets wrong

**HONEST WEIGHTING:**
- Which case is more credible right now and why (pick one)
- Single piece of evidence that would flip your view
- What would have to be true for both cases to be partially right

Do not hedge. Pick a side and defend it with data.

---

## PHASE 3 — DOWNSIDE STRESS TEST

Run after Phase 2. Most important phase — do not skip.

### 1. THESIS-BREAKING SCENARIOS
Three specific events that completely invalidate the bull thesis. Be concrete.

### 2. DOWNSIDE SCENARIO — SHOW THE MATH
Build a realistic bear case model:

| Bear Case Assumption | Value |
|----------------------|-------|
| Revenue growth drops to | X% |
| Gross margin compresses to | Y% |
| EBITDA margin | Z% |
| Bear case EBITDA | $Xm |
| Bear multiple assigned | Xx EV/EBITDA |
| Implied enterprise value | $Xm |
| Implied equity value | $Xm |
| Implied stock price | $X |
| Downside from current | -X% |

No vibes. Show the arithmetic.

### 3. WHAT YOU'RE PROBABLY MISSING
- Cyclical / macro factor being ignored
- Competitor or technology that could disrupt (name it)
- Accounting red flags: working capital changes, stock-based comp as % of revenue,
  capitalized vs. expensed costs, related party transactions
- Management alignment: insider sales trend, comp structure, capital allocation track record
- Short interest % of float and options skew (put/call ratio, IV skew)

### 4. THE QUESTION YOU HAVEN'T ASKED
Identify the most important question about this stock the investor hasn't thought to ask.
Answer it directly.

### 5. FINAL RISK VERDICT
- Asymmetry score 1–10 (1 = limited downside, capped upside / 10 = high downside, high upside)
- Position sizing recommendation:
  - **Conviction** (5–10% of portfolio)
  - **Standard** (2–5%)
  - **Starter** (under 2%)
  - **Pass**
- Justify the sizing in 3–5 sentences. No waffling.

---

## TONE AND FORMAT RULES

- No fluff. No "it's worth noting that…" constructions.
- Every claim needs a number or a named source.
- Tables for financial data. Prose for qualitative judgment.
- Verdicts must be directional. "It depends" is not a verdict.
- Phase 3 math must be reproducible — show each step.
"""


def _fmt(val):
    if val is None:
        return "N/A"
    try:
        v = float(val)
        if abs(v) >= 1e9:
            return f"${v / 1e9:.2f}B"
        if abs(v) >= 1e6:
            return f"${v / 1e6:.2f}M"
        return f"{v:.2f}"
    except (TypeError, ValueError):
        return str(val)


def _pct(val):
    if val is None:
        return "N/A"
    try:
        return f"{float(val):.1f}%"
    except (TypeError, ValueError):
        return "N/A"


def _build_context(ticker: str, data: dict) -> str:
    overview = data.get("overview", {})
    balance = data.get("balance_sheet", {})
    valuation = data.get("valuation", {})
    hist = data.get("financials_history", {})
    earnings = data.get("earnings_history", [])
    institutional = data.get("institutional", {})

    lines = [
        f"TICKER: {ticker}",
        f"Company: {data.get('company_name', 'N/A')}",
        f"Sector: {data.get('sector', 'N/A')}",
        f"Market Cap: {_fmt(data.get('market_cap'))}",
        f"Current Price: {_fmt(data.get('price'))} ({data.get('change_pct_1d') or 0:.2f}% today)",
        f"52-week range: {_fmt(data.get('week_52_low'))} – {_fmt(data.get('week_52_high'))}",
        "",
        "=== OVERVIEW (TTM) ===",
        f"Revenue TTM: {_fmt(overview.get('revenue_ttm'))}",
        f"EPS TTM: {overview.get('eps_ttm', 'N/A')}",
        f"Net Margin: {_pct(overview.get('net_margin_pct'))}",
        f"FCF TTM: {_fmt(overview.get('fcf_ttm'))}",
        f"ROIC: {_pct(overview.get('roic_ttm'))}",
        f"ROE: {_pct(overview.get('roe_ttm'))}",
        "",
        "=== BALANCE SHEET ===",
        f"Total Debt: {_fmt(balance.get('total_debt'))}",
        f"Cash: {_fmt(balance.get('cash'))}",
        f"D/E Ratio: {balance.get('de_ratio', 'N/A')}",
        "",
        "=== VALUATION ===",
        f"Trailing P/E: {valuation.get('pe', 'N/A')}",
        f"P/B: {valuation.get('pb', 'N/A')}",
        f"P/S: {valuation.get('ps', 'N/A')}",
        f"EV/EBITDA: {valuation.get('ev_ebitda', 'N/A')}",
        f"Sector P/E: {valuation.get('sector_pe', 'N/A')}",
        "",
        "=== MULTI-YEAR FINANCIALS ===",
    ]

    for period, label in [
        ("fy_minus_2", "FY-2"),
        ("fy_minus_1", "FY-1"),
        ("fy_current", "FY0"),
        ("ttm", "TTM"),
    ]:
        p = hist.get(period) or {}
        lines.append(
            f"{label}: Revenue={_fmt(p.get('revenue'))} | "
            f"Gross Margin={_pct(p.get('gross_margin_pct'))} | "
            f"Op Margin={_pct(p.get('operating_margin_pct'))} | "
            f"EBITDA={_fmt(p.get('ebitda'))} | "
            f"EBITDA Margin={_pct(p.get('ebitda_margin_pct'))} | "
            f"FCF={_fmt(p.get('fcf'))}"
        )

    lines += [
        "",
        "=== EARNINGS HISTORY (last 4 quarters) ===",
    ]
    for e in earnings:
        beat_str = "BEAT" if e.get("beat") is True else ("MISS" if e.get("beat") is False else "N/A")
        lines.append(
            f"{e.get('quarter', 'N/A')}: "
            f"EPS actual={e.get('eps_actual', 'N/A')} "
            f"vs est={e.get('eps_estimate', 'N/A')} ({beat_str})"
        )

    lines += [
        "",
        "=== INSTITUTIONAL / INSIDER ===",
        f"Top institutional holder: {institutional.get('top_holder', 'N/A')}",
        f"Institutional %: {institutional.get('pct_held_institutions', 'N/A')}%",
        f"Short % of float: {institutional.get('short_percent_of_float', 'N/A')}%",
        f"Insider sentiment (90d): {institutional.get('insider_sentiment', 'N/A')}",
        f"Shares trend: {institutional.get('shares_buyback_trend', 'N/A')}",
    ]

    last_5 = institutional.get("last_5_insider_transactions") or []
    if last_5:
        lines.append("Recent insider transactions:")
        for txn in last_5:
            lines.append(
                f"  {txn.get('date', '')} | {txn.get('name', '')} ({txn.get('title', '')}) "
                f"— {txn.get('transaction_type', '')} {txn.get('shares', '')} shares"
            )

    return "\n".join(lines)


def run_stock_analysis(ticker: str, prism_data: dict) -> str:
    """Run a fresh 3-phase institutional equity analysis using the stock-analyst framework."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")

    client = anthropic.Anthropic(api_key=api_key)
    context = _build_context(ticker, prism_data)

    user_message = (
        f"Analyze {ticker} using your three-phase institutional equity analysis framework.\n\n"
        "Pre-fetched financial data is provided below — use it as your primary source for actuals. "
        "For peer comparisons, forward guidance, earnings transcript language, and any gaps, "
        "draw from your training knowledge of this company and sector. "
        "Flag explicitly when a figure is estimated vs. confirmed from the data below.\n\n"
        f"{context}\n\n"
        "Run Phase 1, Phase 2, and Phase 3 in full sequence. Do not skip Phase 3."
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    report = "".join(
        block.text for block in response.content if hasattr(block, "text")
    )
    return report
