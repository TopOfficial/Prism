"""v2.0 insight routes: catalyst calendar + economic dashboard."""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services.auth_service import verify_jwt
from services.catalysts_service import ticker_catalysts, watchlist_catalysts
from services.macro_service import get_macro
from services.watchlist_service import list_watchlist
from services.public_service import is_valid_ticker

router = APIRouter()
_security = HTTPBearer(auto_error=False)


def _get_user(creds: HTTPAuthorizationCredentials = Depends(_security)):
    if not creds:
        return None
    return verify_jwt(creds.credentials)


@router.get("/catalysts")
def get_watchlist_catalysts(user=Depends(_get_user)):
    """Upcoming earnings + dividends across the caller's watchlist, soonest first."""
    if user is None:
        raise HTTPException(status_code=401, detail="not_authenticated")
    tickers = [w["ticker"] for w in list_watchlist(user.id)]
    return {"items": watchlist_catalysts(tickers)}


@router.get("/catalysts/{ticker}")
def get_ticker_catalysts(ticker: str):
    ticker = ticker.upper().strip()
    if not is_valid_ticker(ticker):
        raise HTTPException(status_code=422, detail="bad_ticker")
    return ticker_catalysts(ticker)


@router.get("/macro")
def macro():
    """Key macro series (FRED). {enabled: false} until FRED_API_KEY is set."""
    return get_macro()
