import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from services.yfinance_service import get_stock_data
from services.fmp_service import get_sector_pe, get_valuation, get_profile, search_tickers, get_earnings
from services.news_service import get_news
from services.verdict_service import compute_verdict
from services.scoring import compute_quality_scores, compute_moat
from services.research_service import run_stock_analysis, extract_extras
from services.auth_service import (
    verify_jwt, get_account_status, consume_research, refund_research,
    save_history, list_history, get_history_report, get_usage_stats, save_feedback,
    get_shared_report, acquire_research_lock, release_research_lock, delete_account,
    get_user_record,
)
from services.stripe_service import create_checkout_session, handle_webhook, create_portal_session
from services.public_service import (
    publish_report, render_public_page, sitemap_xml, is_valid_ticker, PublishError,
)
from services.market_news_service import get_market_news

security = HTTPBearer(auto_error=False)
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Prism API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Restrict CORS to the known frontend origins (override via CORS_ORIGINS env, comma-separated).
# Auth is via Bearer token rather than cookies, so credentials stay off; the regex covers
# Vercel preview deploys. Stripe webhooks are server-to-server and unaffected by CORS.
_ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get(
        "CORS_ORIGINS",
        "https://www.prisminv.com,https://prisminv.com,http://localhost:5173,http://localhost:3000",
    ).split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    if not creds:
        return None
    return verify_jwt(creds.credentials)


_CCY_SYMBOL = {
    "USD": "$", "THB": "฿", "GBP": "£", "EUR": "€", "JPY": "¥", "CNY": "¥",
    "HKD": "HK$", "INR": "₹", "CAD": "C$", "AUD": "A$", "NZD": "NZ$", "KRW": "₩",
    "TWD": "NT$", "SGD": "S$", "CHF": "CHF ", "SEK": "kr", "NOK": "kr", "DKK": "kr",
    "BRL": "R$", "MXN": "MX$", "IDR": "Rp", "MYR": "RM", "PHP": "₱", "ZAR": "R",
}


def _ccy_symbol(currency: str | None) -> str:
    """Display symbol for a currency code; falls back to '<CODE> ' for unmapped ones."""
    if not currency:
        return "$"
    return _CCY_SYMBOL.get(currency.upper(), f"{currency.upper()} ")


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok"}


@app.get("/search")
@limiter.limit("60/minute")
def search(request: Request, q: str = ""):
    q = q.strip()
    if len(q) < 1:
        return []
    return search_tickers(q)


@app.get("/me")
def get_me(user=Depends(_get_user)):
    if not user:
        return {"is_admin": False, "is_subscriber": False, "credits": 0, "free_research_available": False, "next_free_research_at": None}
    return get_account_status(user.id)


@app.delete("/me")
def delete_me(user=Depends(_get_user)):
    """Permanently delete the signed-in user's account and data."""
    if user is None:
        raise HTTPException(status_code=401, detail="not_authenticated")
    if not delete_account(user.id):
        raise HTTPException(status_code=500, detail="delete_failed")
    return {"ok": True}


@app.post("/feedback")
@limiter.limit("20/hour")
async def post_feedback(request: Request):
    body = await request.json()
    ticker  = str(body.get("ticker") or "").strip()[:20]
    verdict = str(body.get("verdict") or "").strip()[:40]
    thumbs  = str(body.get("thumbs") or "").strip()[:10]
    comment = str(body.get("comment") or "").strip()[:500]
    if not ticker or not thumbs:
        raise HTTPException(status_code=422, detail="ticker and thumbs are required")
    saved = save_feedback(ticker, verdict, thumbs, comment)
    return {"ok": saved}


@app.post("/create-checkout-session")
async def checkout_session(request: Request, user=Depends(_get_user)):
    if not user:
        raise HTTPException(status_code=401, detail="not_authenticated")
    body = await request.json()
    plan = str(body.get("plan", "subscription"))
    quantity = int(body.get("quantity", 1) or 1)
    try:
        url = create_checkout_session(user.id, user.email, plan, quantity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {e}")
    return {"checkout_url": url}


@app.post("/create-portal-session")
def portal_session(user=Depends(_get_user)):
    """Stripe Billing Portal so the user can manage/cancel their subscription."""
    if user is None:
        raise HTTPException(status_code=401, detail="not_authenticated")
    record = get_user_record(user.id)
    customer_id = (record or {}).get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(status_code=400, detail="no_customer")
    return_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    try:
        url = create_portal_session(customer_id, return_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {e}")
    return {"portal_url": url}


@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    try:
        result = handle_webhook(payload, sig)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@app.get("/stats")
def get_stats(user=Depends(_get_user)):
    """Admin-only usage dashboard: runs, users, top tickers, peak hours (Bangkok time)."""
    if user is None:
        raise HTTPException(status_code=401, detail="not_authenticated")
    if not get_account_status(user.id).get("is_admin"):
        raise HTTPException(status_code=403, detail="forbidden")
    return get_usage_stats()


@app.get("/history")
def get_history_list(user=Depends(_get_user)):
    """Return the signed-in user's saved Deep Research tickers (newest first)."""
    if user is None:
        raise HTTPException(status_code=401, detail="not_authenticated")
    return {"items": list_history(user.id)}


@app.get("/history/{ticker}")
def get_history_one(ticker: str, user=Depends(_get_user)):
    """Return a previously generated report for this user + ticker. Free, no credit charged."""
    if user is None:
        raise HTTPException(status_code=401, detail="not_authenticated")
    row = get_history_report(user.id, ticker.upper().strip())
    if not row:
        raise HTTPException(status_code=404, detail="no_history")
    report_md, extras = extract_extras(row["report"])
    return {
        "ticker": row["ticker"],
        "company_name": row.get("company_name"),
        "report": report_md,
        "extras": extras,
        "created_at": row.get("created_at"),
    }


@app.get("/market-news")
@limiter.limit("30/hour")
def market_news(request: Request):
    """Today's market briefing — same cached content for every visitor."""
    try:
        return get_market_news()
    except Exception as e:
        print(f"[MARKET] /market-news failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=503, detail="market_news_unavailable")


@app.post("/publish/{ticker}")
@limiter.limit("20/hour")
def publish(ticker: str, request: Request, user=Depends(_get_user)):
    """Publish the caller's own fresh (<7 days) report to the public /r/{ticker} page."""
    if user is None:
        raise HTTPException(status_code=401, detail="not_authenticated")
    ticker = ticker.upper().strip()
    if not is_valid_ticker(ticker):
        raise HTTPException(status_code=422, detail="bad_ticker")
    try:
        result = publish_report(user.id, ticker)
    except PublishError as e:
        raise HTTPException(status_code=409 if e.code == "stale_report" else 404, detail=e.code)
    except Exception as e:
        print(f"[PUBLIC] publish {ticker} failed: {e}")
        raise HTTPException(status_code=500, detail="publish_failed")
    return result


@app.get("/r/{ticker}")
@limiter.limit("120/minute")
def public_report_page(ticker: str, request: Request):
    """Server-rendered public report page (proxied onto prisminv.com via Vercel rewrite)."""
    from fastapi.responses import HTMLResponse
    ticker = ticker.upper().strip()
    if not is_valid_ticker(ticker):
        raise HTTPException(status_code=404, detail="not_found")
    page = render_public_page(ticker)
    if page is None:
        raise HTTPException(status_code=404, detail="not_found")
    return HTMLResponse(page, headers={"Cache-Control": "public, max-age=3600"})


@app.get("/sitemap.xml")
def sitemap():
    from fastapi.responses import Response
    return Response(
        sitemap_xml(), media_type="application/xml",
        headers={"Cache-Control": "public, max-age=21600"},
    )


@app.post("/research/{ticker}")
def run_research(ticker: str, request: Request, user=Depends(_get_user)):
    """Run a fresh 3-phase analysis. Charges a credit (or weekly-free / unlimited) and saves to history."""
    if user is None:
        raise HTTPException(status_code=401, detail="not_authenticated")

    ticker = ticker.upper().strip()

    stock = get_stock_data(ticker)
    fmp_profile = get_profile(ticker)
    fmp_val = get_valuation(ticker)

    def _fill(a, b):
        return a if a is not None else b

    company_name = _fill(stock["company_name"], fmp_profile["company_name"])
    sector       = _fill(stock["sector"],       fmp_profile["sector"])
    price        = _fill(stock["price"],         fmp_profile["price"])
    change_pct   = _fill(stock["change_pct_1d"], fmp_profile["change_pct_1d"])
    market_cap   = _fill(stock["market_cap"],    fmp_profile["market_cap"])
    week_52_high = _fill(stock["week_52_high"],  fmp_profile["week_52_high"])
    week_52_low  = _fill(stock["week_52_low"],   fmp_profile["week_52_low"])

    if stock["overview"].get("revenue_ttm") is None and company_name is None:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found")

    # Per-(user, ticker) lock: reject a second concurrent run for the same ticker before
    # charging or doing any work, so a double-submit can't trigger two Claude calls.
    if not acquire_research_lock(user.id, ticker):
        raise HTTPException(status_code=409, detail="analysis_in_progress")

    try:
        # Charge only after we know the ticker is valid and we hold the run lock
        allowed, charge_type = consume_research(user.id)
        if not allowed:
            raise HTTPException(status_code=402, detail="no_credits")

        # Shared-cache: reuse another user's report for this ticker if it's within the
        # freshness window AND strictly newer than the requester's own existing report.
        # First-time analysis (no own report) reuses any fresh peer; Re-analyze only reuses
        # a peer newer than what the user already has, else it does a fresh Claude run.
        own = get_history_report(user.id, ticker)
        own_created = own.get("created_at") if own else None
        shared = get_shared_report(ticker, exclude_user_id=user.id, newer_than=own_created)
        if shared:
            report = shared["report"]
            company_name = shared.get("company_name") or company_name
            save_history(user.id, ticker, company_name, report,
                         created_at=shared.get("created_at"), source="shared")
            status = get_account_status(user.id)
            report_md, extras = extract_extras(report)
            return {
                "ticker": ticker,
                "company_name": company_name,
                "report": report_md,
                "extras": extras,
                "charge_type": charge_type,
                "account": status,
            }

        valuation_raw = stock.get("valuation_raw", {})
        valuation = {
            "pe":        _fill(valuation_raw.get("pe"),        fmp_val.get("pe")),
            "pb":        _fill(valuation_raw.get("pb"),        fmp_val.get("pb")),
            "ps":        _fill(valuation_raw.get("ps"),        fmp_val.get("ps")),
            "ev_ebitda": _fill(valuation_raw.get("ev_ebitda"), fmp_val.get("ev_ebitda")),
            "sector_pe": get_sector_pe(sector, fmp_profile.get("exchange")),
        }

        # Earnings fallback: yfinance earnings_history fails on cloud IPs
        research_earnings = stock["earnings_history"]
        if not research_earnings:
            research_earnings = get_earnings(ticker)

        # Institutional % fallback from FMP ratios-ttm
        if stock["institutional"].get("pct_held_institutions") is None and fmp_val.get("pct_held_institutions") is not None:
            stock["institutional"]["pct_held_institutions"] = fmp_val["pct_held_institutions"]

        prism_data = {
            "ticker":             ticker,
            "company_name":       company_name,
            "sector":             sector,
            "price":              price,
            "change_pct_1d":      change_pct,
            "market_cap":         market_cap,
            "week_52_high":       week_52_high,
            "week_52_low":        week_52_low,
            "overview":           stock["overview"],
            "balance_sheet":      stock["balance_sheet"],
            "valuation":          valuation,
            "financials_history": stock.get("financials_history"),
            "earnings_history":   research_earnings,
            "institutional":      stock["institutional"],
        }

        try:
            report = run_stock_analysis(ticker, prism_data)
        except ValueError as e:
            # Refund: the user was charged above but gets no report.
            refund_research(user.id, charge_type)
            print(f"[RESEARCH] {ticker} config error: {e}")
            raise HTTPException(status_code=503, detail="analysis_unavailable")
        except HTTPException:
            raise
        except Exception as e:
            refund_research(user.id, charge_type)
            print(f"[RESEARCH] {ticker} failed: {type(e).__name__}: {e}")
            raise HTTPException(status_code=500, detail="analysis_failed")

        save_history(user.id, ticker, company_name, report)
        status = get_account_status(user.id)
        report_md, extras = extract_extras(report)
        return {
            "ticker": ticker,
            "company_name": company_name,
            "report": report_md,
            "extras": extras,
            "charge_type": charge_type,
            "account": status,
        }
    finally:
        release_research_lock(user.id, ticker)


@app.get("/brief/{ticker}")
@limiter.limit("40/hour")
def get_brief(ticker: str, request: Request, user=Depends(_get_user)):
    # Briefs are free and unlimited; the IP rate limiter above guards against abuse.
    ticker = ticker.upper().strip()

    stock = get_stock_data(ticker)

    # FMP fallbacks for fields that fail when Yahoo Finance blocks cloud IPs
    fmp_profile = get_profile(ticker)
    fmp_val = get_valuation(ticker)

    def _fill(stock_val, fmp_val):
        return stock_val if stock_val is not None else fmp_val

    company_name = _fill(stock["company_name"], fmp_profile["company_name"])
    sector       = _fill(stock["sector"],       fmp_profile["sector"])
    price        = _fill(stock["price"],         fmp_profile["price"])
    change_pct   = _fill(stock["change_pct_1d"], fmp_profile["change_pct_1d"])
    market_cap   = _fill(stock["market_cap"],    fmp_profile["market_cap"])
    week_52_high = _fill(stock["week_52_high"],  fmp_profile["week_52_high"])
    week_52_low  = _fill(stock["week_52_low"],   fmp_profile["week_52_low"])

    # Reject unknown tickers: no financial data AND no profile from either source
    revenue_ttm = stock["overview"].get("revenue_ttm")
    if revenue_ttm is None and company_name is None:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found")

    valuation_raw = stock.get("valuation_raw", {})
    pe = _fill(valuation_raw.get("pe"), fmp_val.get("pe"))
    pb = _fill(valuation_raw.get("pb"), fmp_val.get("pb"))
    ps = _fill(valuation_raw.get("ps"), fmp_val.get("ps"))
    ev_ebitda = _fill(valuation_raw.get("ev_ebitda"), fmp_val.get("ev_ebitda"))

    sector_pe = get_sector_pe(sector, fmp_profile.get("exchange"))
    news = get_news(ticker)

    # Earnings fallback: yfinance earnings_history fails on cloud IPs
    earnings_history = stock["earnings_history"]
    if not earnings_history:
        earnings_history = get_earnings(ticker)

    # Institutional % fallback from FMP ratios-ttm
    if stock["institutional"].get("pct_held_institutions") is None and fmp_val.get("pct_held_institutions") is not None:
        stock["institutional"]["pct_held_institutions"] = fmp_val["pct_held_institutions"]

    fcf_ttm = stock["overview"].get("fcf_ttm")
    de_ratio = stock["balance_sheet"].get("de_ratio")
    eps_ttm = stock["overview"].get("eps_ttm")
    shares_outstanding = stock.get("shares_outstanding")
    verdict = compute_verdict(
        pe, sector_pe, fcf_ttm, de_ratio, eps_ttm,
        financials_history=stock.get("financials_history"),
        total_debt=stock["balance_sheet"].get("total_debt"),
        cash=stock["balance_sheet"].get("cash"),
        shares_outstanding=shares_outstanding,
        price=price,
        ps=ps,
        cur=_ccy_symbol(stock["currency"]),
    )

    valuation = {
        "pe": pe,
        "pb": pb,
        "ps": ps,
        "ev_ebitda": ev_ebitda,
        "sector_pe": sector_pe,
    }

    quality_scores = compute_quality_scores({
        "financials_history": stock.get("financials_history"),
        "overview": stock["overview"],
        "balance_sheet": stock["balance_sheet"],
        "valuation": valuation,
        "earnings_history": earnings_history,
        "market_cap": market_cap,  # FMP-filled value, consistent with what the card displays
    })

    competitive_moat = compute_moat({
        "overview": stock["overview"],
        "financials_history": stock.get("financials_history"),
    })

    return {
        "ticker": stock["ticker"],
        "company_name": company_name,
        "sector": sector,
        "currency": stock["currency"],
        "price": price,
        "change_pct_1d": change_pct,
        "week_52_high": week_52_high,
        "week_52_low": week_52_low,
        "market_cap": market_cap,
        "overview": stock["overview"],
        "balance_sheet": stock["balance_sheet"],
        "valuation": valuation,
        "financials_history": stock.get("financials_history"),
        "earnings_history": earnings_history,
        "news": news,
        "institutional": stock["institutional"],
        "verdict": verdict,
        "quality_scores": quality_scores,
        "competitive_moat": competitive_moat,
    }
