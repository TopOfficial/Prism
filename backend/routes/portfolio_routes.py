"""Portfolio analyzer + thesis tracker routes (v1.4)."""
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services.auth_service import verify_jwt, get_account_status
from services.portfolio_service import (
    parse_holdings_text, replace_holdings, remove_holding, analyze, ai_assessment,
)
from services.thesis_service import (
    save_thesis, get_theses, get_thesis, delete_thesis, ThesisError,
)
from services.public_service import is_valid_ticker

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


def _is_unlimited(user_id: str) -> bool:
    status = get_account_status(user_id)
    return bool(status.get("is_admin") or status.get("is_subscriber"))


# ── Portfolio ────────────────────────────────────────────────────────────────

@router.get("/portfolio")
def get_portfolio(assess: int = 0, user=Depends(_get_user)):
    user = _require_user(user)
    result = analyze(user.id)
    result["assessment"] = None
    result["can_assess"] = _is_unlimited(user.id)
    if assess and result["holdings"]:
        if not result["can_assess"]:
            raise HTTPException(status_code=402, detail="subscribers_only")
        try:
            result["assessment"] = ai_assessment(
                {k: result[k] for k in ("holdings", "sectors", "totals")})
        except Exception as e:
            print(f"[PORTFOLIO] assessment failed: {type(e).__name__}: {e}")
            # analytics still returned; the UI shows a soft failure for the text
    return result


@router.put("/portfolio")
async def put_portfolio(request: Request, user=Depends(_get_user)):
    user = _require_user(user)
    body = await request.json()
    rows, errors = parse_holdings_text(str(body.get("text") or ""))
    if errors and not rows:
        raise HTTPException(status_code=422, detail={"errors": errors})
    try:
        replace_holdings(user.id, rows)
    except Exception as e:
        print(f"[PORTFOLIO] replace failed: {e}")
        raise HTTPException(status_code=500, detail="save_failed")
    return {"saved": len(rows), "errors": errors}


@router.delete("/portfolio/holdings/{ticker}")
def delete_holding(ticker: str, user=Depends(_get_user)):
    user = _require_user(user)
    remove_holding(user.id, ticker.upper().strip())
    return {"ok": True}


# ── Thesis ───────────────────────────────────────────────────────────────────

@router.get("/theses")
def list_theses(user=Depends(_get_user)):
    user = _require_user(user)
    return {"items": get_theses(user.id)}


@router.get("/thesis/{ticker}")
def get_one_thesis(ticker: str, user=Depends(_get_user)):
    user = _require_user(user)
    row = get_thesis(user.id, ticker.upper().strip())
    if not row:
        raise HTTPException(status_code=404, detail="no_thesis")
    return row


@router.post("/thesis/{ticker}")
async def post_thesis(ticker: str, request: Request, user=Depends(_get_user)):
    user = _require_user(user)
    ticker = ticker.upper().strip()
    if not is_valid_ticker(ticker):
        raise HTTPException(status_code=422, detail="bad_ticker")
    body = await request.json()
    try:
        return save_thesis(user.id, ticker, str(body.get("thesis") or ""))
    except ThesisError as e:
        raise HTTPException(status_code=422, detail=e.code)
    except Exception as e:
        print(f"[THESIS] save {ticker} failed: {e}")
        raise HTTPException(status_code=500, detail="save_failed")


@router.delete("/thesis/{ticker}")
def remove_thesis(ticker: str, user=Depends(_get_user)):
    user = _require_user(user)
    delete_thesis(user.id, ticker.upper().strip())
    return {"ok": True}
