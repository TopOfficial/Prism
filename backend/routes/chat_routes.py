"""Research chat routes (v1.3)."""
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services.auth_service import verify_jwt, get_account_status
from services.chat_service import chat_turn, chat_state, ChatError
from services.public_service import is_valid_ticker

router = APIRouter()
_security = HTTPBearer(auto_error=False)

_MAX_MESSAGE_CHARS = 1000


def _get_user(creds: HTTPAuthorizationCredentials = Depends(_security)):
    if not creds:
        return None
    return verify_jwt(creds.credentials)


def _auth_ticker(user, ticker: str) -> str:
    if user is None:
        raise HTTPException(status_code=401, detail="not_authenticated")
    ticker = ticker.upper().strip()
    if not is_valid_ticker(ticker):
        raise HTTPException(status_code=422, detail="bad_ticker")
    return ticker


def _is_unlimited(user_id: str) -> bool:
    status = get_account_status(user_id)
    return bool(status.get("is_admin") or status.get("is_subscriber"))


@router.get("/chat/{ticker}")
def get_chat(ticker: str, user=Depends(_get_user)):
    ticker = _auth_ticker(user, ticker)
    return chat_state(user.id, ticker, _is_unlimited(user.id))


@router.post("/chat/{ticker}")
async def post_chat(ticker: str, request: Request, user=Depends(_get_user)):
    ticker = _auth_ticker(user, ticker)
    body = await request.json()
    message = str(body.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=422, detail="empty_message")
    if len(message) > _MAX_MESSAGE_CHARS:
        raise HTTPException(status_code=422, detail="message_too_long")
    try:
        return chat_turn(user.id, ticker, message, _is_unlimited(user.id))
    except ChatError as e:
        status = {"no_report": 404, "chat_limit": 402, "chat_cap": 429}[e.code]
        raise HTTPException(status_code=status, detail=e.code)
    except Exception as e:
        print(f"[CHAT] {ticker} failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="chat_failed")
