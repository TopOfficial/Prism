import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from services.yfinance_service import get_stock_data
from services.fmp_service import get_sector_pe
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
    ticker  = body.get("ticker", "")
    verdict = body.get("verdict", "")
    thumbs  = body.get("thumbs", "")
    comment = body.get("comment", "").strip()
    print(f"[FEEDBACK] {ticker} | {verdict} | {thumbs}" + (f" | {comment}" if comment else ""))
    return {"ok": True}


@app.get("/brief/{ticker}")
@limiter.limit("10/hour")
def get_brief(ticker: str, request: Request):
    ticker = ticker.upper().strip()

    stock = get_stock_data(ticker)
    valuation_raw = stock.get("valuation_raw", {})
    sector_pe = get_sector_pe(stock.get("sector"))
    news = get_news(ticker)

    pe = valuation_raw.get("pe")
    fcf_ttm = stock["overview"].get("fcf_ttm")
    de_ratio = stock["balance_sheet"].get("de_ratio")
    eps_ttm = stock["overview"].get("eps_ttm")
    verdict = compute_verdict(pe, sector_pe, fcf_ttm, de_ratio, eps_ttm)

    valuation = {
        "pe": pe,
        "pb": valuation_raw.get("pb"),
        "ps": valuation_raw.get("ps"),
        "ev_ebitda": valuation_raw.get("ev_ebitda"),
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
        "company_name": stock["company_name"],
        "sector": stock["sector"],
        "currency": stock["currency"],
        "price": stock["price"],
        "change_pct_1d": stock["change_pct_1d"],
        "week_52_high": stock["week_52_high"],
        "week_52_low": stock["week_52_low"],
        "market_cap": stock["market_cap"],
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
