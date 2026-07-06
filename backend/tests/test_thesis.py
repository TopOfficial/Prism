import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import services.thesis_service as ts
from services.thesis_service import save_thesis, evaluate_theses_for_earnings, ThesisError


def test_save_rejects_long_thesis():
    with pytest.raises(ThesisError) as e:
        save_thesis("u1", "NVDA", "x" * 2001)
    assert e.value.code == "too_long"


def test_save_rejects_empty():
    with pytest.raises(ThesisError):
        save_thesis("u1", "NVDA", "   ")


def test_evaluate_appends_checkpoints(monkeypatch):
    theses = [
        {"user_id": "u1", "ticker": "NVDA", "thesis": "Datacenter growth + margin expansion",
         "checkpoints": []},
    ]
    monkeypatch.setattr(ts, "_active_theses_for", lambda t: theses)
    monkeypatch.setattr(ts, "_verdict", lambda thesis, summary:
                        {"verdict": "stronger", "note": "Margins expanded again."})
    saved = {}
    monkeypatch.setattr(ts, "_save_checkpoints", lambda uid, t, cps: saved.update({(uid, t): cps}))
    out = evaluate_theses_for_earnings("NVDA", "Revenue beat, margins up.")
    assert len(out) == 1
    uid, cp = out[0]
    assert uid == "u1" and cp["verdict"] == "stronger" and cp["date"]
    assert saved[("u1", "NVDA")][-1]["verdict"] == "stronger"


def test_evaluate_skips_on_model_failure(monkeypatch):
    theses = [{"user_id": "u1", "ticker": "NVDA", "thesis": "t", "checkpoints": []}]
    monkeypatch.setattr(ts, "_active_theses_for", lambda t: theses)
    monkeypatch.setattr(ts, "_verdict", lambda thesis, summary: (_ for _ in ()).throw(RuntimeError("down")))
    saved = {}
    monkeypatch.setattr(ts, "_save_checkpoints", lambda uid, t, cps: saved.update({(uid, t): cps}))
    out = evaluate_theses_for_earnings("NVDA", "summary")
    assert out == [] and saved == {}


def test_verdict_normalization():
    assert ts._normalize_verdict("STRONGER") == "stronger"
    assert ts._normalize_verdict("thesis broken") == "broken"
    assert ts._normalize_verdict("garbage") == "mixed"
