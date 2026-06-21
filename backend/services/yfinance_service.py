import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


# yfinance ticker suffix → trading currency. Used as a fallback when the API doesn't
# return a currency (common on cloud IPs), so e.g. CTW.BK shows THB instead of USD.
_CCY_BY_SUFFIX = {
    "BK": "THB", "L": "GBP", "T": "JPY", "HK": "HKD", "SS": "CNY", "SZ": "CNY",
    "NS": "INR", "BO": "INR", "DE": "EUR", "PA": "EUR", "AS": "EUR", "MI": "EUR",
    "MC": "EUR", "BR": "EUR", "HE": "EUR", "VI": "EUR", "LS": "EUR", "IR": "EUR",
    "TO": "CAD", "V": "CAD", "AX": "AUD", "NZ": "NZD", "KS": "KRW", "KQ": "KRW",
    "TW": "TWD", "TWO": "TWD", "SI": "SGD", "SW": "CHF", "ST": "SEK", "OL": "NOK",
    "CO": "DKK", "SA": "BRL", "MX": "MXN", "JK": "IDR", "KL": "MYR", "PS": "PHP",
    "JO": "ZAR", "TA": "ILS", "IS": "TRY", "ME": "RUB",
}


def currency_for_ticker(ticker: str, info_currency: str | None) -> str:
    """Trust the API's currency when present; otherwise derive from the ticker suffix
    (e.g. '.BK' → THB), defaulting to USD for US/suffixless tickers."""
    if info_currency:
        return info_currency
    suffix = ticker.rsplit(".", 1)[-1].upper() if "." in ticker else ""
    return _CCY_BY_SUFFIX.get(suffix, "USD")


def _safe(fn):
    try:
        return fn()
    except Exception:
        return None


def _row(df, *keys):
    if df is None or df.empty:
        return None
    for key in keys:
        if key in df.index:
            try:
                val = df.loc[key].iloc[0]
                return None if pd.isna(val) else float(val)
            except Exception:
                pass
    return None


def _col_val(df, col_idx, *keys):
    if df is None or df.empty or col_idx >= len(df.columns):
        return None
    for key in keys:
        if key in df.index:
            try:
                val = df.loc[key].iloc[col_idx]
                return None if pd.isna(val) else float(val)
            except Exception:
                pass
    return None


def _ttm_sum(qdf, *keys):
    if qdf is None or qdf.empty:
        return None
    for key in keys:
        if key in qdf.index:
            try:
                vals = qdf.loc[key].iloc[:4]
                if vals.isna().all():
                    continue
                return float(vals.fillna(0).sum())
            except Exception:
                pass
    return None


def _safe_pct(numerator, denominator):
    if numerator is None or denominator is None or denominator == 0:
        return None
    return (numerator / denominator) * 100


def _period_financials(fin, cf, col_idx):
    revenue = _col_val(fin, col_idx, "Total Revenue")
    gross_profit = _col_val(fin, col_idx, "Gross Profit")
    operating_income = _col_val(fin, col_idx, "Operating Income", "EBIT")
    ebitda = _col_val(fin, col_idx, "EBITDA", "Normalized EBITDA")
    if ebitda is None and operating_income is not None:
        da = _col_val(fin, col_idx, "Reconciled Depreciation",
                      "Depreciation And Amortization In Income Statement",
                      "Depreciation Amortization Depletion")
        if da is not None:
            ebitda = operating_income + da

    fcf = _col_val(cf, col_idx, "Free Cash Flow")
    if fcf is None:
        op = _col_val(cf, col_idx, "Operating Cash Flow",
                      "Total Cash From Operating Activities",
                      "Cash Flow From Continuing Operating Activities")
        capex = _col_val(cf, col_idx, "Capital Expenditure",
                         "Capital Expenditures",
                         "Purchase Of Property Plant And Equipment")
        if op is not None and capex is not None:
            fcf = op + capex  # capex is negative in yfinance

    return {
        "revenue": revenue,
        "gross_margin_pct": _safe_pct(gross_profit, revenue),
        "operating_margin_pct": _safe_pct(operating_income, revenue),
        "ebitda": ebitda,
        "ebitda_margin_pct": _safe_pct(ebitda, revenue),
        "fcf": fcf,
    }


def _ttm_financials(qfin, qcf):
    revenue = _ttm_sum(qfin, "Total Revenue")
    gross_profit = _ttm_sum(qfin, "Gross Profit")
    operating_income = _ttm_sum(qfin, "Operating Income", "EBIT")
    ebitda = _ttm_sum(qfin, "EBITDA", "Normalized EBITDA")
    if ebitda is None and operating_income is not None:
        da = _ttm_sum(qfin, "Reconciled Depreciation",
                      "Depreciation And Amortization In Income Statement",
                      "Depreciation Amortization Depletion")
        if da is not None:
            ebitda = operating_income + da

    fcf = _ttm_sum(qcf, "Free Cash Flow")
    if fcf is None:
        op = _ttm_sum(qcf, "Operating Cash Flow",
                      "Total Cash From Operating Activities",
                      "Cash Flow From Continuing Operating Activities")
        capex = _ttm_sum(qcf, "Capital Expenditure",
                         "Capital Expenditures",
                         "Purchase Of Property Plant And Equipment")
        if op is not None and capex is not None:
            fcf = op + capex

    return {
        "revenue": revenue,
        "gross_margin_pct": _safe_pct(gross_profit, revenue),
        "operating_margin_pct": _safe_pct(operating_income, revenue),
        "ebitda": ebitda,
        "ebitda_margin_pct": _safe_pct(ebitda, revenue),
        "fcf": fcf,
    }


def _get_shares_trend(t):
    shares_history = None
    shares_trend = None
    try:
        shares_full = t.get_shares_full(start="2021-01-01")
        if shares_full is not None and not shares_full.empty:
            yearly = shares_full.resample("YE").last().dropna().tail(3)
            if not yearly.empty:
                shares_history = {str(idx.year): int(val) for idx, val in yearly.items()}
                if len(yearly) >= 2:
                    oldest = float(yearly.iloc[0])
                    newest = float(yearly.iloc[-1])
                    if oldest > 0:
                        change_pct = (newest - oldest) / oldest * 100
                        if change_pct < -2:
                            shares_trend = "buyback"
                        elif change_pct > 2:
                            shares_trend = "diluting"
                        else:
                            shares_trend = "stable"
    except Exception as e:
        print(f"[yfinance] _get_shares_trend: {type(e).__name__}: {e}")
    return shares_history, shares_trend


def _get_insider_transactions(t):
    last_5 = None
    insider_sentiment = None
    try:
        it = t.insider_transactions
        if it is not None and not it.empty:
            date_col = next((c for c in it.columns if "date" in c.lower() or "start" in c.lower()), None)
            name_col = next((c for c in it.columns if c.lower() in ("insider", "name")), None)
            title_col = next((c for c in it.columns if "title" in c.lower()), None)
            txn_col = next((c for c in it.columns if c.lower() in ("transaction", "action", "text")), None)
            shares_col = next((c for c in it.columns if "share" in c.lower()), None)
            value_col = next((c for c in it.columns if "value" in c.lower()), None)

            if date_col:
                it = it.sort_values(date_col, ascending=False)

            last_5 = []
            for _, row in it.head(5).iterrows():
                entry = {
                    "date": str(row[date_col])[:10] if date_col and pd.notna(row.get(date_col)) else None,
                    "name": str(row[name_col]) if name_col and pd.notna(row.get(name_col)) else None,
                    "title": str(row[title_col]) if title_col and pd.notna(row.get(title_col)) else None,
                    "transaction_type": str(row[txn_col]) if txn_col and pd.notna(row.get(txn_col)) else None,
                    "shares": int(row[shares_col]) if shares_col and pd.notna(row.get(shares_col)) else None,
                    "value": float(row[value_col]) if value_col and pd.notna(row.get(value_col)) else None,
                }
                last_5.append(entry)

            # Sentiment from last 90 days
            cutoff = datetime.now() - timedelta(days=90)
            recent = it.copy()
            if date_col:
                try:
                    recent[date_col] = pd.to_datetime(recent[date_col], errors="coerce", utc=True)
                    cutoff_ts = pd.Timestamp(cutoff, tz="UTC")
                    recent = recent[recent[date_col] >= cutoff_ts]
                except Exception:
                    recent = it

            buys = sells = 0
            if txn_col:
                for _, row in recent.iterrows():
                    txn = str(row.get(txn_col, "")).lower()
                    if any(k in txn for k in ("purchase", "buy", "acquisition", "acquired")):
                        buys += 1
                    elif any(k in txn for k in ("sale", "sell", "sold", "disposition")):
                        sells += 1

            if buys == 0 and sells == 0:
                insider_sentiment = "none"
            elif buys > 0 and sells == 0:
                insider_sentiment = "buying"
            elif sells > 0 and buys == 0:
                insider_sentiment = "selling"
            else:
                insider_sentiment = "mixed"
    except Exception as e:
        print(f"[yfinance] _get_insider_transactions: {type(e).__name__}: {e}")
    return last_5, insider_sentiment


def get_stock_data(ticker: str) -> dict:
    t = yf.Ticker(ticker)

    info = _safe(lambda: t.info) or {}
    if not info:
        print(f"[yfinance] {ticker} - t.info empty (cloud IP likely blocked by Yahoo Finance)")

    # fast_info uses a lighter endpoint that works reliably on cloud hosts
    fi = _safe(lambda: t.fast_info) or {}
    def _fi(key):
        try:
            v = getattr(fi, key, None)
            return float(v) if v is not None else None
        except Exception:
            return None

    price = (info.get("currentPrice") or info.get("regularMarketPrice")
             or _fi("last_price"))
    prev_close = (info.get("previousClose") or info.get("regularMarketPreviousClose")
                  or _fi("previous_close"))
    if price is not None and prev_close is not None and prev_close != 0:
        change_pct = ((float(price) - float(prev_close)) / float(prev_close)) * 100
    else:
        change_pct = None

    # Annual financials
    fin = _safe(lambda: t.financials)
    revenue = _row(fin, "Total Revenue")
    net_income = _row(fin, "Net Income")
    net_margin = None
    if revenue and net_income and revenue != 0:
        net_margin = (net_income / revenue) * 100

    eps_ttm = None  # computed below after qfin is available

    # Free cash flow (TTM from annual)
    cf = _safe(lambda: t.cashflow)
    fcf = _row(cf, "Free Cash Flow")
    if fcf is None:
        op = _row(cf, "Operating Cash Flow", "Total Cash From Operating Activities")
        capex = _row(cf, "Capital Expenditure", "Capital Expenditures")
        if op is not None and capex is not None:
            fcf = op + capex

    # Balance sheet
    bs = _safe(lambda: t.balance_sheet)
    total_debt = _row(bs, "Total Debt", "Long Term Debt")
    cash = _row(bs, "Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments")
    equity = _row(bs, "Stockholders Equity", "Total Stockholders Equity", "Common Stock Equity")
    de_ratio = None
    if total_debt is not None and equity is not None and equity != 0:
        de_ratio = total_debt / equity

    # ROIC and ROE
    roic_ttm = None
    roe_ttm = None
    if net_income is not None and total_debt is not None and equity is not None:
        denom = equity + total_debt
        if denom > 0:
            roic_ttm = (net_income / denom) * 100
    if net_income is not None and equity is not None and equity > 0:
        roe_ttm = (net_income / equity) * 100

    # Multi-year financials
    qfin = _safe(lambda: t.quarterly_financials)
    qcf = _safe(lambda: t.quarterly_cashflow)

    # EPS TTM — compute from quarterly net income / shares (works without t.info)
    net_income_ttm_raw = _ttm_sum(qfin, "Net Income")
    shares_out = _fi("shares")
    if net_income_ttm_raw is not None and shares_out and shares_out > 0:
        eps_ttm = round(net_income_ttm_raw / shares_out, 4)
    else:
        eps_ttm = info.get("trailingEps")

    financials_history = {
        "fy_minus_2": _period_financials(fin, cf, 2),
        "fy_minus_1": _period_financials(fin, cf, 1),
        "fy_current": _period_financials(fin, cf, 0),
        "ttm": _ttm_financials(qfin, qcf),
    }

    # Short interest
    short_pct = info.get("shortPercentOfFloat")
    if short_pct is not None and short_pct < 1.0:
        short_pct = round(short_pct * 100, 4)
    short_ratio = info.get("shortRatio")

    # Shares buyback/dilution trend
    shares_history, shares_trend = _get_shares_trend(t)

    # Earnings history — last 4 quarters
    earnings_history = []
    try:
        eh = t.earnings_history
        if eh is not None and not eh.empty:
            eh = eh.sort_index(ascending=False).head(4)
            for idx, row in eh.iterrows():
                eps_actual = row.get("epsActual")
                eps_est = row.get("epsEstimate")
                beat = None
                if eps_actual is not None and eps_est is not None:
                    beat = float(eps_actual) >= float(eps_est)
                quarter = str(idx)[:10] if idx else None
                earnings_history.append({
                    "quarter": quarter,
                    "eps_actual": float(eps_actual) if eps_actual is not None and not pd.isna(eps_actual) else None,
                    "eps_estimate": float(eps_est) if eps_est is not None and not pd.isna(eps_est) else None,
                    "beat": beat,
                })
    except Exception as e:
        print(f"[yfinance] {ticker} - earnings_history: {type(e).__name__}: {e}")

    # Institutional holders
    top_holder = None
    pct_held = info.get("heldPercentInstitutions")
    if pct_held is not None:
        pct_held = round(pct_held * 100, 2)
    try:
        ih = t.institutional_holders
        if ih is not None and not ih.empty:
            top_holder = str(ih.iloc[0].get("Holder") or ih.iloc[0].iloc[0])
    except Exception as e:
        print(f"[yfinance] {ticker} - institutional_holders: {type(e).__name__}: {e}")

    # Legacy insider action string (backward compat)
    recent_insider_action = None
    try:
        it = t.insider_transactions
        if it is not None and not it.empty:
            date_col = next((c for c in it.columns if "date" in c.lower() or "start" in c.lower()), None)
            sorted_it = it.sort_values(date_col, ascending=False) if date_col else it
            row = sorted_it.iloc[0]
            action = row.get("Transaction") or row.get("Action")
            name = row.get("Insider") or row.get("Name") or ""
            if action:
                recent_insider_action = f"{name} — {action}".strip(" —")
    except Exception as e:
        print(f"[yfinance] {ticker} - insider_transactions: {type(e).__name__}: {e}")

    last_5_insiders, insider_sentiment = _get_insider_transactions(t)

    def _float(key):
        v = info.get(key)
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    return {
        "ticker": ticker.upper(),
        "company_name": info.get("longName") or info.get("shortName"),
        "sector": info.get("sector"),
        "currency": currency_for_ticker(ticker, info.get("currency") or _fi("currency")),
        "price": float(price) if price is not None else None,
        "change_pct_1d": float(change_pct) if change_pct is not None else None,
        "week_52_high": info.get("fiftyTwoWeekHigh") or _fi("year_high"),
        "week_52_low": info.get("fiftyTwoWeekLow") or _fi("year_low"),
        "market_cap": info.get("marketCap") or _fi("market_cap"),
        "shares_outstanding": info.get("sharesOutstanding") or _fi("shares"),
        "overview": {
            "revenue_ttm": revenue,
            "eps_ttm": eps_ttm,
            "net_margin_pct": net_margin,
            "fcf_ttm": fcf,
            "roic_ttm": roic_ttm,
            "roe_ttm": roe_ttm,
        },
        "balance_sheet": {
            "total_debt": total_debt,
            "cash": cash,
            "de_ratio": de_ratio,
        },
        "valuation_raw": {
            "pe": _float("trailingPE"),
            "pb": _float("priceToBook"),
            "ps": _float("priceToSalesTrailing12Months"),
            "ev_ebitda": _float("enterpriseToEbitda"),
        },
        "financials_history": financials_history,
        "earnings_history": earnings_history,
        "institutional": {
            "top_holder": top_holder,
            "pct_held_institutions": pct_held,
            "recent_insider_action": recent_insider_action,
            "short_percent_of_float": short_pct,
            "short_ratio": short_ratio,
            "shares_outstanding_history": shares_history,
            "shares_buyback_trend": shares_trend,
            "last_5_insider_transactions": last_5_insiders,
            "insider_sentiment": insider_sentiment,
        },
    }
