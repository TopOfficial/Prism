"""Watchlist + alerts routes (v1.2). Kept out of main.py so it stays readable."""
import os
import hmac

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services.auth_service import verify_jwt, get_account_status
from services.watchlist_service import (
    add_to_watchlist, remove_from_watchlist, list_watchlist, WatchlistError,
    FREE_TICKER_LIMIT,
)
from services.alerts_service import run_alerts, verify_unsub_token, set_alerts_enabled
from services.public_service import is_valid_ticker, SITE_URL

router = APIRouter()
_security = HTTPBearer(auto_error=False)


def _get_user(creds: HTTPAuthorizationCredentials = Depends(_security)):
    if not creds:
        return None
    return verify_jwt(creds.credentials)


def _require_user(user):
    if user is None:
        raise HTTPException(status_code=401, detail="not_authenticated")
    return user


@router.get("/watchlist")
def get_watchlist(user=Depends(_get_user)):
    user = _require_user(user)
    status = get_account_status(user.id)
    unlimited = status.get("is_admin") or status.get("is_subscriber")
    return {
        "items": list_watchlist(user.id),
        "limit": None if unlimited else FREE_TICKER_LIMIT,
    }


@router.post("/watchlist/{ticker}")
async def watch_ticker(ticker: str, request: Request, user=Depends(_get_user)):
    user = _require_user(user)
    ticker = ticker.upper().strip()
    if not is_valid_ticker(ticker):
        raise HTTPException(status_code=422, detail="bad_ticker")
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    status = get_account_status(user.id)
    unlimited = status.get("is_admin") or status.get("is_subscriber")
    try:
        return add_to_watchlist(user.id, ticker, (body.get("company_name") or None), unlimited)
    except WatchlistError as e:
        raise HTTPException(status_code=402, detail=e.code)
    except Exception as e:
        print(f"[WATCH] add {ticker} failed: {e}")
        raise HTTPException(status_code=500, detail="watch_failed")


@router.delete("/watchlist/{ticker}")
def unwatch_ticker(ticker: str, user=Depends(_get_user)):
    user = _require_user(user)
    remove_from_watchlist(user.id, ticker.upper().strip())
    return {"ticker": ticker.upper().strip(), "watching": False}


@router.post("/jobs/run-alerts")
def run_alerts_job(request: Request):
    """Daily cron entrypoint (Render Cron Job). Gated by X-Cron-Secret."""
    secret = os.environ.get("CRON_SECRET")
    provided = request.headers.get("x-cron-secret", "")
    if not secret or not hmac.compare_digest(secret, provided):
        raise HTTPException(status_code=403, detail="forbidden")
    return run_alerts()


@router.get("/unsubscribe")
def unsubscribe(uid: str = "", token: str = ""):
    """One-click alert unsubscribe from email links (HMAC-signed, no login needed)."""
    if not uid or not verify_unsub_token(uid, token):
        raise HTTPException(status_code=403, detail="bad_token")
    try:
        set_alerts_enabled(uid, False)
    except Exception as e:
        print(f"[ALERTS] unsubscribe failed for {uid}: {e}")
        raise HTTPException(status_code=500, detail="unsubscribe_failed")
    return HTMLResponse(
        f"""<!doctype html><html><head><meta charset="utf-8"><title>Unsubscribed — Prism</title></head>
<body style="background:#070B14;color:#94A3B8;font-family:-apple-system,'Segoe UI',sans-serif;
display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
<div style="text-align:center"><div style="letter-spacing:.18em;font-weight:700;color:#A855F7;margin-bottom:14px">P R I S M</div>
<p>You're unsubscribed from watchlist alerts.<br>Your watchlist itself is unchanged.</p>
<a href="{SITE_URL}" style="color:#A855F7">Back to Prism →</a></div></body></html>"""
    )
