"""Daily watchlist alert job — "tell me only when something actually changes".

Triggered by POST /jobs/run-alerts (Render Cron Job with X-Cron-Secret).
Per distinct watched ticker it detects material events vs the stored baseline:
  - earnings released (new quarter key)  → the "earnings copilot" delta summary
  - day-over-day price move >= 5%
Cost scales with distinct tickers, not users. One digest email per affected
user via the Resend HTTP API; no RESEND_API_KEY means we log instead of send.
"""
import os
import hmac
import html as html_mod
import hashlib
import json

PRICE_MOVE_THRESHOLD_PCT = 5.0
SITE_URL = os.environ.get("PUBLIC_SITE_URL", "https://www.prisminv.com")
_ALERT_MODEL_EARNINGS = "claude-sonnet-4-6"      # quality matters for the earnings delta
_ALERT_MODEL_MOVE = "claude-haiku-4-5-20251001"  # one-liner, high volume, cheap


def _sb():
    from services.auth_service import _sb as sb
    return sb()


# ── Event detection (pure) ───────────────────────────────────────────────────

def detect_events(ticker: str, baseline: dict, current_price: float | None,
                  latest_quarter: str | None) -> list:
    """Material events for one ticker vs its baseline. A missing baseline value
    means 'first run' for that signal — seed silently, never alert."""
    events = []
    base_price = (baseline or {}).get("price")
    base_quarter = (baseline or {}).get("earnings_quarter")

    if base_quarter is not None and latest_quarter and latest_quarter != base_quarter:
        events.append({"type": "earnings", "quarter": latest_quarter})

    if base_price and current_price:
        change_pct = (current_price - base_price) / base_price * 100
        if abs(change_pct) >= PRICE_MOVE_THRESHOLD_PCT:
            events.append({"type": "price_move", "change_pct": change_pct,
                           "from": base_price, "to": current_price})
    return events


def group_events_by_user(rows: list, ticker_events: dict) -> dict:
    """{user_id: [(ticker, event), …]} for tickers that actually had events."""
    grouped: dict[str, list] = {}
    for row in rows:
        for ev in ticker_events.get(row["ticker"]) or []:
            grouped.setdefault(row["user_id"], []).append((row["ticker"], ev))
    return grouped


# ── Unsubscribe tokens ───────────────────────────────────────────────────────

def unsub_token(user_id: str) -> str:
    secret = os.environ.get("UNSUB_SECRET", "")
    return hmac.new(secret.encode(), user_id.encode(), hashlib.sha256).hexdigest()


def verify_unsub_token(user_id: str, token: str) -> bool:
    if not os.environ.get("UNSUB_SECRET"):
        return False
    return hmac.compare_digest(unsub_token(user_id), token or "")


def set_alerts_enabled(user_id: str, enabled: bool) -> None:
    _sb().table("users").update({"alerts_enabled": enabled}).eq("id", user_id).execute()


# ── Data access / fetchers (thin, monkeypatchable) ───────────────────────────

def _watch_rows() -> list:
    from services.watchlist_service import all_watch_rows
    return all_watch_rows()


def _update_baseline(ticker: str, baseline: dict) -> None:
    from services.watchlist_service import update_baseline
    update_baseline(ticker, baseline)


def _current_price(ticker: str) -> float | None:
    try:
        import yfinance as yf
        price = yf.Ticker(ticker).fast_info.last_price
        if price:
            return float(price)
    except Exception as e:
        print(f"[ALERTS] yf price {ticker}: {type(e).__name__}: {e}")
    try:
        from services.fmp_service import get_profile
        return get_profile(ticker).get("price")
    except Exception:
        return None


def _latest_quarter(ticker: str) -> tuple[str | None, list]:
    """(newest quarter key, full earnings history) from the existing FMP fetcher."""
    try:
        from services.fmp_service import get_earnings
        earnings = get_earnings(ticker) or []
        newest = earnings[0].get("quarter") if earnings else None
        return newest, earnings
    except Exception as e:
        print(f"[ALERTS] earnings {ticker}: {type(e).__name__}: {e}")
        return None, []


def _user_emails(user_ids: list) -> dict:
    """{user_id: (email, alerts_enabled)} — email from auth.users via admin API is
    overkill; the public.users row already carries email (set at signup)."""
    out = {}
    try:
        res = (
            _sb().table("users")
            .select("id, email, alerts_enabled")
            .in_("id", user_ids)
            .execute()
        )
        for r in res.data or []:
            out[r["id"]] = (r.get("email"), r.get("alerts_enabled", True) is not False)
    except Exception as e:
        print(f"[ALERTS] user_emails failed: {e}")
    return out


# ── Alert copy ───────────────────────────────────────────────────────────────

def _template_text(ticker: str, ev: dict) -> str:
    if ev["type"] == "price_move":
        d = "up" if ev["change_pct"] > 0 else "down"
        return f"{ticker} moved {d} {abs(ev['change_pct']):.1f}% since yesterday ({ev['from']:.2f} → {ev['to']:.2f})."
    return f"{ticker} reported earnings ({ev.get('quarter')}). Check the latest numbers on Prism."


def _event_text(ticker: str, company: str | None, ev: dict, context: dict) -> str:
    """Model-written alert line/paragraph; falls back to a template on any failure."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _template_text(ticker, ev)
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        if ev["type"] == "earnings":
            model = _ALERT_MODEL_EARNINGS
            system = (
                "You write the earnings alert for a stock research app. In <=120 words of plain "
                "prose: what the company just reported vs estimates and the prior quarter, and the "
                "one thing that changed most. Use only the numbers provided. No headers, no hedging."
            )
            payload = {"ticker": ticker, "company": company, "event": ev,
                       "earnings_history": context.get("earnings", [])}
            max_tokens = 300
        else:
            model = _ALERT_MODEL_MOVE
            system = (
                "You write one sentence for a price-move alert in a stock research app. State the "
                "move factually from the data given. Do not speculate about causes you weren't given."
            )
            payload = {"ticker": ticker, "company": company, "event": ev}
            max_tokens = 100
        resp = client.messages.create(
            model=model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": json.dumps(payload, default=str)}],
        )
        text = "".join(b.text for b in resp.content if hasattr(b, "text")).strip()
        return text or _template_text(ticker, ev)
    except Exception as e:
        print(f"[ALERTS] model text {ticker}/{ev['type']}: {type(e).__name__}: {e}")
        return _template_text(ticker, ev)


# ── Email ────────────────────────────────────────────────────────────────────

def _digest_html(items: list, user_id: str) -> str:
    rows = []
    for ticker, ev, text in items:
        tag = "Earnings" if ev["type"] == "earnings" else "Price move"
        rows.append(
            f'<div style="margin-bottom:18px">'
            f'<div style="font-weight:700;color:#111">{html_mod.escape(ticker)} '
            f'<span style="font-size:12px;color:#7C3AED">· {tag}</span></div>'
            f'<div style="color:#444;font-size:14px;line-height:1.6">{html_mod.escape(text)}</div>'
            f'<a href="{SITE_URL}/?t={html_mod.escape(ticker)}" style="font-size:13px;color:#7C3AED">View on Prism →</a>'
            f"</div>"
        )
    unsub = f"{SITE_URL}/unsubscribe?uid={user_id}&token={unsub_token(user_id)}"
    return (
        '<div style="font-family:-apple-system,Segoe UI,sans-serif;max-width:560px;margin:0 auto;padding:24px">'
        f'<div style="letter-spacing:.18em;font-weight:700;color:#7C3AED;margin-bottom:20px">P R I S M</div>'
        + "".join(rows) +
        f'<div style="margin-top:28px;padding-top:14px;border-top:1px solid #eee;font-size:12px;color:#999">'
        f"You get this because these tickers are on your Prism watchlist — we only email when "
        f"something material happens. Not financial advice. "
        f'<a href="{unsub}" style="color:#999">Unsubscribe</a></div></div>'
    )


def _send_email(to: str, subject: str, html: str, user_id: str) -> bool:
    key = os.environ.get("RESEND_API_KEY")
    sender = os.environ.get("ALERT_FROM_EMAIL")
    if not key or not sender:
        print(f"[ALERTS] RESEND_API_KEY/ALERT_FROM_EMAIL not set — would send to {to}: {subject}")
        return False
    try:
        import requests
        unsub = f"{SITE_URL}/unsubscribe?uid={user_id}&token={unsub_token(user_id)}"
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {key}"},
            json={"from": sender, "to": [to], "subject": subject, "html": html,
                  "headers": {"List-Unsubscribe": f"<{unsub}>"}},
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"[ALERTS] send to {to} failed: {type(e).__name__}: {e}")
        return False


# ── The job ──────────────────────────────────────────────────────────────────

def run_alerts() -> dict:
    """One daily pass: detect events per distinct ticker, update baselines,
    email each affected user a digest. Failures skip and continue."""
    rows = _watch_rows()
    by_ticker: dict[str, list] = {}
    for r in rows:
        by_ticker.setdefault(r["ticker"], []).append(r)

    ticker_events: dict[str, list] = {}
    ticker_text: dict[str, dict] = {}   # ticker -> {event_type: text}
    thesis_notes: dict[tuple, dict] = {}  # (user_id, ticker) -> checkpoint
    for ticker, t_rows in by_ticker.items():
        try:
            price = _current_price(ticker)
            quarter, earnings = _latest_quarter(ticker)
            baseline = t_rows[0].get("baseline") or {}
            events = detect_events(ticker, baseline, price, quarter)
            ticker_events[ticker] = events
            company = t_rows[0].get("company_name")
            for ev in events:
                text = _event_text(ticker, company, ev, {"earnings": earnings})
                ticker_text.setdefault(ticker, {})[ev["type"]] = text
                if ev["type"] == "earnings":
                    # Earnings landed → checkpoint every thesis on this ticker (v1.4).
                    from services.thesis_service import evaluate_theses_for_earnings
                    for uid, checkpoint in evaluate_theses_for_earnings(ticker, text):
                        thesis_notes[(uid, ticker)] = checkpoint
            _update_baseline(ticker, {"price": price if price is not None else baseline.get("price"),
                                      "earnings_quarter": quarter or baseline.get("earnings_quarter")})
        except Exception as e:
            print(f"[ALERTS] ticker {ticker} failed: {type(e).__name__}: {e}")
            ticker_events[ticker] = []

    grouped = group_events_by_user(rows, ticker_events)
    emails_sent = 0
    if grouped:
        contact = _user_emails(list(grouped.keys()))
        for user_id, items in grouped.items():
            email, enabled = contact.get(user_id, (None, False))
            if not email or not enabled:
                continue
            digest = []
            for t, ev in items:
                text = ticker_text.get(t, {}).get(ev["type"]) or _template_text(t, ev)
                cp = thesis_notes.get((user_id, t))
                if cp and ev["type"] == "earnings":
                    text += f"\n\nYour thesis: {cp['verdict'].upper()} — {cp['note']}"
                digest.append((t, ev, text))
            tickers = ", ".join(sorted({t for t, _ in items}))
            if _send_email(email, f"Prism watchlist: {tickers}", _digest_html(digest, user_id), user_id):
                emails_sent += 1

    total_events = sum(len(v) for v in ticker_events.values())
    summary = {"tickers_checked": len(by_ticker), "events": total_events, "emails_sent": emails_sent}
    print(f"[ALERTS] run complete: {summary}")
    return summary
