"""Thesis tracker + journal (merged): record why you bought; after each earnings
event the alert cron asks whether the thesis got stronger or weaker and appends
a checkpoint to the journal. One active thesis per (user, ticker)."""
import os
import json
from datetime import datetime, timezone

MAX_THESIS_CHARS = 2000
_VERDICTS = ("stronger", "weaker", "broken", "mixed")
_VERDICT_MODEL = "claude-sonnet-4-6"


class ThesisError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _sb():
    from services.auth_service import _sb as sb
    return sb()


# ── CRUD ─────────────────────────────────────────────────────────────────────

def save_thesis(user_id: str, ticker: str, text: str) -> dict:
    text = (text or "").strip()
    if not text:
        raise ThesisError("empty")
    if len(text) > MAX_THESIS_CHARS:
        raise ThesisError("too_long")
    row = {
        "user_id": user_id,
        "ticker": ticker,
        "thesis": text,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "checkpoints": [],
    }
    _sb().table("theses").upsert(row, on_conflict="user_id,ticker").execute()
    return {"ticker": ticker, "thesis": text, "checkpoints": []}


def get_theses(user_id: str) -> list:
    try:
        res = (
            _sb().table("theses")
            .select("ticker, thesis, created_at, checkpoints")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def get_thesis(user_id: str, ticker: str) -> dict | None:
    try:
        res = (
            _sb().table("theses")
            .select("ticker, thesis, created_at, checkpoints")
            .eq("user_id", user_id).eq("ticker", ticker)
            .single().execute()
        )
        return res.data
    except Exception:
        return None


def delete_thesis(user_id: str, ticker: str) -> None:
    try:
        _sb().table("theses").delete().eq("user_id", user_id).eq("ticker", ticker).execute()
    except Exception as e:
        print(f"[THESIS] delete {ticker} failed: {e}")


# ── Earnings-time evaluation (called from the alert cron) ────────────────────

def _active_theses_for(ticker: str) -> list:
    try:
        res = (
            _sb().table("theses")
            .select("user_id, ticker, thesis, checkpoints")
            .eq("ticker", ticker)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[THESIS] fetch for {ticker} failed: {e}")
        return []


def _save_checkpoints(user_id: str, ticker: str, checkpoints: list) -> None:
    _sb().table("theses").update({"checkpoints": checkpoints}) \
        .eq("user_id", user_id).eq("ticker", ticker).execute()


def _normalize_verdict(raw: str) -> str:
    raw = (raw or "").lower()
    for v in _VERDICTS:
        if v in raw:
            return v
    return "mixed"


def _verdict(thesis: str, earnings_summary: str) -> dict:
    """{'verdict': stronger|weaker|broken|mixed, 'note': str} via Sonnet."""
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=_VERDICT_MODEL, max_tokens=250,
        system=(
            "An investor recorded a thesis for owning a stock. Earnings just came out. "
            "Judge STRICTLY whether this earnings evidence made the thesis stronger, weaker, "
            "broken, or mixed. Reply as JSON only: "
            '{"verdict": "stronger|weaker|broken|mixed", "note": "<=40 words citing the evidence"}'
        ),
        messages=[{"role": "user", "content": json.dumps(
            {"thesis": thesis, "earnings_summary": earnings_summary})}],
    )
    text = "".join(b.text for b in resp.content if hasattr(b, "text")).strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(text)
    return {"verdict": _normalize_verdict(data.get("verdict")), "note": str(data.get("note", ""))[:400]}


def evaluate_theses_for_earnings(ticker: str, earnings_summary: str) -> list:
    """Checkpoint every thesis on this ticker against fresh earnings.
    Returns [(user_id, checkpoint)] for digest inclusion; failures skip silently
    (they'll be retried at the next earnings event)."""
    results = []
    for row in _active_theses_for(ticker):
        try:
            v = _verdict(row["thesis"], earnings_summary)
        except Exception as e:
            print(f"[THESIS] verdict {ticker}/{row['user_id']}: {type(e).__name__}: {e}")
            continue
        checkpoint = {
            "date": datetime.now(timezone.utc).date().isoformat(),
            "verdict": v["verdict"],
            "note": v["note"],
        }
        checkpoints = (row.get("checkpoints") or []) + [checkpoint]
        try:
            _save_checkpoints(row["user_id"], ticker, checkpoints)
        except Exception as e:
            print(f"[THESIS] save checkpoint {ticker}/{row['user_id']}: {e}")
            continue
        results.append((row["user_id"], checkpoint))
    return results
