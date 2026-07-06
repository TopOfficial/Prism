"""Research chat with per-(user, ticker) memory: follow-up questions grounded in
the user's saved Deep Research report. Free users get FREE_TURNS_PER_TICKER
questions per ticker; subscribers/admins are capped only by a fair-use total."""
import os
import json

FREE_TURNS_PER_TICKER = 5      # user questions per ticker for non-subscribers
UNLIMITED_MESSAGE_CAP = 200    # total stored messages/ticker fair-use cap (~100 turns)
_HISTORY_WINDOW = 20           # most recent messages sent to the model
_CHAT_MODEL = "claude-sonnet-4-6"
_MAX_REPLY_TOKENS = 1200


class ChatError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _sb():
    from services.auth_service import _sb as sb
    return sb()


# ── Thin accessors (monkeypatchable) ─────────────────────────────────────────

def _get_report(user_id: str, ticker: str) -> dict | None:
    from services.auth_service import get_history_report
    return get_history_report(user_id, ticker)


def _get_messages(user_id: str, ticker: str) -> list:
    try:
        res = (
            _sb().table("research_chats")
            .select("messages")
            .eq("user_id", user_id).eq("ticker", ticker)
            .single().execute()
        )
        return (res.data or {}).get("messages") or []
    except Exception:
        return []


def _save_messages(user_id: str, ticker: str, messages: list) -> None:
    from datetime import datetime, timezone
    _sb().table("research_chats").upsert({
        "user_id": user_id,
        "ticker": ticker,
        "messages": messages,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="user_id,ticker").execute()


def _model_reply(system: str, messages: list) -> str:
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=_CHAT_MODEL, max_tokens=_MAX_REPLY_TOKENS,
        system=system, messages=messages,
    )
    return "".join(b.text for b in resp.content if hasattr(b, "text")).strip()


# ── Public API ───────────────────────────────────────────────────────────────

def count_user_turns(messages: list) -> int:
    return sum(1 for m in messages if m.get("role") == "user")


def chat_turn(user_id: str, ticker: str, message: str, is_unlimited: bool) -> dict:
    """One question → one grounded answer, persisted to the per-ticker thread.
    Raises ChatError('no_report' | 'chat_limit' | 'chat_cap')."""
    report_row = _get_report(user_id, ticker)
    if not report_row:
        raise ChatError("no_report")

    history = _get_messages(user_id, ticker)
    turns_used = count_user_turns(history)

    if not is_unlimited and turns_used >= FREE_TURNS_PER_TICKER:
        raise ChatError("chat_limit")
    if len(history) >= UNLIMITED_MESSAGE_CAP:
        raise ChatError("chat_cap")

    from services.research_service import split_report
    report_md, extras, comps = split_report(report_row.get("report") or "")

    system = (
        f"You are Prism's research analyst, answering follow-up questions about {ticker} "
        f"for the user who ran this Deep Research report. The full report is below — treat it "
        f"as the primary source. You may add general knowledge of the company/sector, but say "
        f"so when you do. If asked something the report and your knowledge can't answer, say so "
        f"plainly. Be direct and concise (under 200 words unless the question demands more). "
        f"Never give personalized financial advice; frame everything as analysis.\n\n"
        f"=== REPORT (generated {report_row.get('created_at', 'unknown')}) ===\n{report_md}"
    )
    if comps:
        system += f"\n\n=== PEER DATA ===\n{json.dumps(comps)}"

    window = history[-_HISTORY_WINDOW:] if len(history) > _HISTORY_WINDOW else history
    model_messages = window + [{"role": "user", "content": message}]

    reply = _model_reply(system, model_messages)

    new_history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply},
    ]
    _save_messages(user_id, ticker, new_history)

    return {
        "reply": reply,
        "turns_used": turns_used + 1,
        "turn_limit": None if is_unlimited else FREE_TURNS_PER_TICKER,
    }


def chat_state(user_id: str, ticker: str, is_unlimited: bool) -> dict:
    """Thread + metering state so the UI can restore a conversation."""
    messages = _get_messages(user_id, ticker)
    return {
        "messages": messages,
        "turns_used": count_user_turns(messages),
        "turn_limit": None if is_unlimited else FREE_TURNS_PER_TICKER,
    }
