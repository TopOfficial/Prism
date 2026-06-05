import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from services.yfinance_service import get_stock_data
from services.fmp_service import get_sector_pe, get_valuation, get_profile
from services.news_service import get_news
from services.verdict_service import compute_verdict
from services.scoring import compute_quality_scores

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


@app.get("/health")
def health():
    return {"status": "ok"}


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


@app.get("/brief/{ticker}")
@limiter.limit("10/hour")
def get_brief(ticker: str, request: Request):
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
        "earnings_history": stock["earnings_history"],
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
        "earnings_history": stock["earnings_history"],
        "news": news,
        "institutional": stock["institutional"],
        "verdict": verdict,
        "quality_scores": quality_scores,
    }
