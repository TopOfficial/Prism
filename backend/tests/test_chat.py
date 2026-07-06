import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import services.chat_service as chat
from services.chat_service import chat_turn, ChatError, FREE_TURNS_PER_TICKER, UNLIMITED_MESSAGE_CAP


def _msgs(n_user):
    out = []
    for i in range(n_user):
        out.append({"role": "user", "content": f"q{i}"})
        out.append({"role": "assistant", "content": f"a{i}"})
    return out


def _setup(monkeypatch, n_user_turns=0, has_report=True):
    monkeypatch.setattr(chat, "_get_report", lambda uid, t: {"report": "# NVDA report", "created_at": "2026-07-01"} if has_report else None)
    monkeypatch.setattr(chat, "_get_messages", lambda uid, t: _msgs(n_user_turns))
    saved = {}
    monkeypatch.setattr(chat, "_save_messages", lambda uid, t, msgs: saved.update({"msgs": msgs}))
    monkeypatch.setattr(chat, "_model_reply", lambda system, messages: "The moat score reflects CUDA lock-in.")
    return saved


def test_chat_requires_report(monkeypatch):
    _setup(monkeypatch, has_report=False)
    with pytest.raises(ChatError) as e:
        chat_turn("u1", "NVDA", "why?", is_unlimited=False)
    assert e.value.code == "no_report"


def test_free_user_turn_ok_and_saved(monkeypatch):
    saved = _setup(monkeypatch, n_user_turns=0)
    out = chat_turn("u1", "NVDA", "why moat 9?", is_unlimited=False)
    assert out["reply"].startswith("The moat")
    assert out["turns_used"] == 1
    assert out["turn_limit"] == FREE_TURNS_PER_TICKER
    assert saved["msgs"][-1]["role"] == "assistant"
    assert saved["msgs"][-2] == {"role": "user", "content": "why moat 9?"}


def test_free_user_hits_limit(monkeypatch):
    _setup(monkeypatch, n_user_turns=FREE_TURNS_PER_TICKER)
    with pytest.raises(ChatError) as e:
        chat_turn("u1", "NVDA", "one more", is_unlimited=False)
    assert e.value.code == "chat_limit"


def test_unlimited_user_bypasses_free_limit(monkeypatch):
    _setup(monkeypatch, n_user_turns=FREE_TURNS_PER_TICKER + 5)
    out = chat_turn("u1", "NVDA", "more", is_unlimited=True)
    assert out["turn_limit"] is None


def test_unlimited_user_fair_use_cap(monkeypatch):
    _setup(monkeypatch, n_user_turns=UNLIMITED_MESSAGE_CAP // 2)  # msgs = cap
    with pytest.raises(ChatError) as e:
        chat_turn("u1", "NVDA", "more", is_unlimited=True)
    assert e.value.code == "chat_cap"


def test_history_trimmed_for_model(monkeypatch):
    _setup(monkeypatch, n_user_turns=4)
    captured = {}
    monkeypatch.setattr(chat, "_model_reply",
                        lambda system, messages: captured.update({"n": len(messages)}) or "ok")
    chat_turn("u1", "NVDA", "q", is_unlimited=True)
    # 8 history messages + 1 new user message, under the 20-message window
    assert captured["n"] == 9
