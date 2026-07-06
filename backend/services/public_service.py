"""Public shareable report pages (/r/{ticker}) — Prism's SEO + viral surface.

A user can publish their own fresh Deep Research report to a public, read-only
page. One public page per ticker (latest publish wins). Pages are server-rendered
HTML with OG/meta tags so crawlers and link unfurlers see real content; Vercel
rewrites prisminv.com/r/* to these endpoints.
"""
import os
import re
import html as html_mod
from datetime import datetime, timezone, timedelta

import markdown as md_lib

from services.research_service import split_report

SITE_URL = os.environ.get("PUBLIC_SITE_URL", "https://www.prisminv.com")
PUBLISH_MAX_AGE = timedelta(days=7)   # only fresh analysis may be published
STALE_BANNER_DAYS = 7                 # public page warns when older than this

_TICKER_RE = re.compile(r"^[A-Z0-9.\-]{1,12}$")

# Neutralize anything that looks like a raw HTML tag in the (model-generated)
# markdown before conversion, without touching blockquote '>' markers.
_RAW_TAG_RE = re.compile(r"<(?=[a-zA-Z/!])")

_SCORECARD_AXES = (
    ("growth", "Growth"), ("profitability", "Profitability"), ("moat", "Moat"),
    ("management", "Management"), ("valuation", "Valuation"), ("risk", "Risk"),
)


class PublishError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def is_valid_ticker(ticker: str) -> bool:
    return bool(ticker) and bool(_TICKER_RE.match(ticker))


def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


# ── Supabase access (thin, monkeypatchable in tests) ─────────────────────────

def _sb():
    from services.auth_service import _sb as sb
    return sb()


def _own_history_report(user_id: str, ticker: str) -> dict | None:
    from services.auth_service import get_history_report
    return get_history_report(user_id, ticker)


def _upsert_public_report(row: dict) -> None:
    _sb().table("public_reports").upsert(row, on_conflict="ticker").execute()


def get_public_report(ticker: str) -> dict | None:
    try:
        res = (
            _sb().table("public_reports")
            .select("ticker, company_name, report, created_at, published_at")
            .eq("ticker", ticker)
            .single()
            .execute()
        )
        return res.data
    except Exception:
        return None


def list_published() -> list:
    try:
        res = (
            _sb().table("public_reports")
            .select("ticker, published_at")
            .order("published_at", desc=True)
            .limit(5000)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[PUBLIC] list_published failed: {e}")
        return []


# ── Publish flow ─────────────────────────────────────────────────────────────

def publish_report(user_id: str, ticker: str) -> dict:
    """Publish the caller's own saved report for this ticker. Raises PublishError
    with code 'no_report' (nothing saved) or 'stale_report' (>7 days old)."""
    row = _own_history_report(user_id, ticker)
    if not row:
        raise PublishError("no_report")
    created = _parse_ts(row.get("created_at"))
    if created is None or datetime.now(timezone.utc) - created > PUBLISH_MAX_AGE:
        raise PublishError("stale_report")

    published_at = datetime.now(timezone.utc).isoformat()
    _upsert_public_report({
        "ticker": ticker,
        "company_name": row.get("company_name"),
        "report": row["report"],
        "created_at": row.get("created_at"),
        "published_at": published_at,
        "published_by": user_id,
    })
    return {"url_path": f"/r/{ticker}", "published_at": published_at}


# ── Page rendering ───────────────────────────────────────────────────────────

def _meta_description(report_md: str, ticker: str, company: str) -> str:
    text = re.sub(r"[#|*`>\[\]_-]", " ", report_md)
    text = re.sub(r"\s+", " ", text).strip()
    base = f"AI investment analysis of {company or ticker}: "
    return html_mod.escape((base + text)[:160])


def _scorecard_strip(extras: dict | None) -> str:
    if not extras or "scorecard" not in extras:
        return ""
    sc = extras["scorecard"]
    cells = []
    for key, label in _SCORECARD_AXES:
        score = (sc.get(key) or {}).get("score")
        if score is None:
            continue
        cells.append(
            f'<div class="sc-cell"><div class="sc-label">{label}</div>'
            f'<div class="sc-score">{int(score)}/10</div></div>'
        )
    grade = html_mod.escape(str(sc.get("overall_grade", "")))
    return (
        '<div class="scorecard">'
        f'<div class="sc-cell sc-grade"><div class="sc-label">Overall</div>'
        f'<div class="sc-score">{grade}</div></div>' + "".join(cells) + "</div>"
    )


def _comps_table(comps: dict | None) -> str:
    if not comps:
        return ""
    def cell(v):
        return html_mod.escape(str(v)) if v is not None else "—"
    def mc(v):
        return f"${v / 1e9:,.0f}B" if v else "—"
    rows = []
    for r in [comps["subject"]] + comps["peers"]:
        bold = ' style="color:#E2E8F0;font-weight:700"' if r["ticker"] == comps["subject"]["ticker"] else ""
        rows.append(
            f"<tr><td{bold}>{cell(r.get('ticker'))}</td><td>{cell(r.get('name'))}</td>"
            f"<td>{mc(r.get('market_cap'))}</td><td>{cell(r.get('pe'))}</td>"
            f"<td>{cell(r.get('ps'))}</td><td>{cell(r.get('ev_ebitda'))}</td></tr>"
        )
    return (
        "<h3>Comparable companies</h3>"
        "<table><thead><tr><th>Ticker</th><th>Company</th><th>Mkt cap</th>"
        "<th>P/E</th><th>P/S</th><th>EV/EBITDA</th></tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody></table>"
    )


def render_page_html(row: dict) -> str:
    """Full HTML document for a published report row."""
    ticker = html_mod.escape(row["ticker"])
    company = html_mod.escape(row.get("company_name") or "")
    display_name = company or ticker

    report_md, extras, comps = split_report(row.get("report") or "")
    safe_md = _RAW_TAG_RE.sub("&lt;", report_md)
    body_html = md_lib.markdown(safe_md, extensions=["tables"])

    created = _parse_ts(row.get("created_at")) or _parse_ts(row.get("published_at"))
    age_days = (datetime.now(timezone.utc) - created).days if created else None
    date_str = created.strftime("%b %d, %Y") if created else ""

    stale_banner = ""
    if age_days is not None and age_days >= STALE_BANNER_DAYS:
        stale_banner = (
            f'<div class="banner">⚠️ This analysis is {age_days} days old. '
            f'Market conditions may have changed — '
            f'<a href="{SITE_URL}">run a fresh analysis on Prism</a>.</div>'
        )

    title = f"{ticker} Stock Analysis — {display_name} | Prism"
    desc = _meta_description(report_md, ticker, company)
    canonical = f"{SITE_URL}/r/{ticker}"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{SITE_URL}/prism-logo.png">
<meta name="twitter:card" content="summary">
<style>
  body {{ margin:0; background:#070B14; color:#94A3B8; font:15px/1.7 -apple-system,'Segoe UI',sans-serif; }}
  .wrap {{ max-width:820px; margin:0 auto; padding:32px 20px 60px; }}
  a {{ color:#A855F7; }}
  h1,h2 {{ color:#A855F7; }} h3,h4 {{ color:#CBD5E1; }}
  strong {{ color:#E2E8F0; }}
  table {{ border-collapse:collapse; width:100%; font-size:13px; margin:14px 0; display:block; overflow-x:auto; }}
  th {{ text-align:left; color:#A855F7; padding:7px 10px; border-bottom:1px solid rgba(168,85,247,.3); }}
  td {{ padding:6px 10px; border-bottom:1px solid rgba(255,255,255,.05); }}
  .top {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:22px; }}
  .brand {{ font-weight:700; letter-spacing:.18em; color:#A855F7; text-decoration:none; }}
  .cta {{ background:#A855F7; color:#fff; text-decoration:none; padding:9px 16px; border-radius:10px; font-size:13px; font-weight:600; }}
  .meta {{ color:#3D5068; font-size:12px; margin-bottom:14px; }}
  .banner {{ background:rgba(251,191,36,.08); border:1px solid rgba(251,191,36,.25); color:#FCD34D; padding:10px 14px; border-radius:12px; font-size:13px; margin-bottom:16px; }}
  .scorecard {{ display:flex; flex-wrap:wrap; gap:10px; margin:0 0 20px; }}
  .sc-cell {{ background:rgba(255,255,255,.03); border:1px solid rgba(168,85,247,.2); border-radius:12px; padding:10px 14px; min-width:86px; }}
  .sc-grade {{ border-color:#A855F7; }}
  .sc-label {{ font-size:11px; text-transform:uppercase; letter-spacing:.08em; color:#4E6278; }}
  .sc-score {{ font-size:18px; font-weight:700; color:#E2E8F0; }}
  .foot {{ margin-top:40px; border-top:1px solid rgba(168,85,247,.15); padding-top:16px; color:#3D5068; font-size:12px; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <a class="brand" href="{SITE_URL}">P R I S M</a>
    <a class="cta" href="{SITE_URL}">Analyze any stock free →</a>
  </div>
  <div class="meta">Published {date_str} · AI-generated Deep Research report</div>
  {stale_banner}
  {_scorecard_strip(extras)}
  {body_html}
  {_comps_table(comps)}
  <div class="foot">
    Prism is for informational purposes only, not financial advice. Investing involves
    risk, including loss of principal. Verify independently before making any investment
    decision. · <a href="{SITE_URL}">prisminv.com</a>
  </div>
</div>
</body>
</html>"""


def render_public_page(ticker: str) -> str | None:
    row = get_public_report(ticker)
    if not row:
        return None
    return render_page_html(row)


# ── Sitemap ──────────────────────────────────────────────────────────────────

def sitemap_xml_from(entries: list[tuple[str, str]]) -> str:
    """entries: [(ticker, published_at_iso)]"""
    urls = [
        f"  <url><loc>{SITE_URL}/</loc><changefreq>daily</changefreq></url>"
    ]
    for ticker, published_at in entries:
        lastmod = (published_at or "")[:10]
        urls.append(
            f"  <url><loc>{SITE_URL}/r/{html_mod.escape(ticker)}</loc>"
            f"<lastmod>{lastmod}</lastmod></url>"
        )
    body = "\n".join(urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n</urlset>"
    )


def sitemap_xml() -> str:
    rows = list_published()
    return sitemap_xml_from([(r["ticker"], r.get("published_at") or "") for r in rows])
