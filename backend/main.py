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
from services.scoring import compute_quality_scores
from services.research_service import run_stock_analysis
from services.auth_service import (
    verify_jwt, get_account_status, consume_research,
    save_history, list_history, get_history_report,
)
from services.stripe_service import create_checkout_session, handle_webhook

security = HTTPBearer(auto_error=False)
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Prism API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    if not creds:
        return None
    return verify_jwt(creds.credentials)


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok"}


@app.get("/search")
def search(q: str = ""):
    q = q.strip()
    if len(q) < 1:
        return []
    return search_tickers(q)


@app.get("/me")
def get_me(user=Depends(_get_user)):
    if not user:
        return {"is_admin": False, "is_subscriber": False, "credits": 0, "free_research_available": False}
    return get_account_status(user.id)


@app.post("/feedback")
async def post_feedback(request: Request):
    body = await request.json()
    ticker  = str(body.get("ticker") or "").strip()
    verdict = str(body.get("verdict") or "").strip()
    thumbs  = str(body.get("thumbs") or "").strip()
    comment = str(body.get("comment") or "").strip()
    if not ticker or not thumbs:
        raise HTTPException(status_code=422, detail="ticker and thumbs are required")
    print(f"[FEEDBACK] {ticker} | {verdict} | {thumbs}" + (f" | {comment}" if comment else ""))
    return {"ok": True}


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


@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    try:
        result = handle_webhook(payload, sig)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


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
    return {
        "ticker": row["ticker"],
        "company_name": row.get("company_name"),
        "report": row["report"],
        "created_at": row.get("created_at"),
    }


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

    # Charge only after we know the ticker is valid
    allowed, charge_type = consume_research(user.id)
    if not allowed:
        raise HTTPException(status_code=402, detail="no_credits")

    valuation_raw = stock.get("valuation_raw", {})
    valuation = {
        "pe":        _fill(valuation_raw.get("pe"),        fmp_val.get("pe")),
        "pb":        _fill(valuation_raw.get("pb"),        fmp_val.get("pb")),
        "ps":        _fill(valuation_raw.get("ps"),        fmp_val.get("ps")),
        "ev_ebitda": _fill(valuation_raw.get("ev_ebitda"), fmp_val.get("ev_ebitda")),
        "sector_pe": get_sector_pe(sector),
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
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    save_history(user.id, ticker, company_name, report)
    status = get_account_status(user.id)
    return {
        "ticker": ticker,
        "company_name": company_name,
        "report": report,
        "charge_type": charge_type,
        "account": status,
    }


@app.get("/brief/{ticker}")
@limiter.limit("10/hour")
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

    sector_pe = get_sector_pe(sector)
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
        "market_cap": stock["market_cap"],
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
    }
