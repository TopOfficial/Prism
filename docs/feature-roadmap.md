# Prism — Feature Roadmap (all versions)

Written 2026-07-07. Current state: v1.0 live (Brief free/unlimited, Deep Research 1 credit, History tab, Stripe credits + $14.99/mo sub, Sonnet 4.6 single-call pipeline). **No traction yet.** This roadmap is ordered around that fact: acquisition first, retention second, depth third, portfolio layer fourth, power tools last.

**Rule between versions:** each version has a traction gate. If the gate isn't met, the next version's answer is marketing/distribution work, not more features. Features don't fix distribution.

---

## Versioning overview

| Version | Theme | Features | Gate to proceed |
|---------|-------|----------|-----------------|
| v1.1 | Acquisition | Bull/Bear debate, Investment scorecard, Public report pages, Market-news homepage | 100 organic visits/wk OR 20 signups |
| v1.2 | Retention | AI watchlist + alerts (incl. earnings copilot) | 30% of signups create a watchlist |
| v1.3 | Depth | Comparable companies, Research chat (with memory) | Chat used in >25% of research sessions |
| v1.4 | Portfolio | Portfolio analyzer, Thesis tracker + journal (merged) | First 10 paying users |
| v2.0 | Power research | Catalyst calendar, SEC filing simplifier, Institutional tracker, Scenario modeling, Economic dashboard | Sustained revenue; users asking for these |
| Parked | — | Community research, Backtesting, Historical AI | See revival conditions |

---

## v1.1 — Acquisition (make Prism findable and shareable)

Goal: turn Prism's output into things that travel — screenshots, links, indexed pages. All four features are low-infra; two are prompt-layer only.

### 1. Bull vs Bear debate
Side-by-side bull and bear cases in every Deep Research report.

- **What**: New section in the Deep Research output: 4–6 bull arguments vs 4–6 bear arguments, each tied to a specific metric/fact from the data already fetched, plus a one-line "what would change my mind" per side.
- **How**: Prompt-layer change in `research_service.py` — extend the existing single Sonnet call's output schema. No new API calls, no new data. The `stock-analyst` skill's phase-2 debate structure is the template.
- **Frontend**: Two-column section in `MarkdownReport.jsx` (or a dedicated component); collapses to stacked on mobile.
- **Pricing**: Part of Deep Research (1 credit). No change.
- **Effort**: S (1–2 days).
- **Cost impact**: +~1–2k output tokens/run. Margin stays >85%.

### 2. Investment scorecard
Rate the company 1–10 across Growth, Profitability, Moat, Management, Valuation, Risk — rendered as a visual card.

- **What**: Six scores + one-line justification each + overall grade. Rendered as a shareable graphic card (clean enough to screenshot for TikTok/X).
- **How**: Extend the same Sonnet call's JSON output (scores + rationales). `scoring.py` and `QualityScores.jsx` already exist — extend rather than new files. Add a "download as image" button (html-to-canvas client-side, no backend).
- **Anchor the scores**: prompt must tie each score to fetched metrics (e.g., Valuation score references actual P/E vs sector P/E from FMP sector-pe-snapshot) so scores are defensible, not vibes.
- **Pricing**: Scorecard-lite (overall grade only) on the free Brief as a teaser; full 6-axis card in Deep Research.
- **Effort**: S–M (2–3 days).
- **Marketing note**: this is the content engine — post one scorecard/day on TikTok/X with the Prism URL on the card.

### 3. Public report pages (not on original list — highest leverage)
Every Deep Research report can be published to a public URL: `palprism.com/r/{ticker}`.

- **What**: "Share" button on a report → creates/updates a public, read-only page. One public page per ticker (latest published wins), server-rendered or pre-rendered for SEO. Page shows report + scorecard + "Analyze any stock free →" CTA.
- **Why**: (a) viral loop — users share their research; (b) SEO — Google indexes a page per ticker; people searching "{ticker} stock analysis" land on Prism. For a zero-traction product this is the acquisition machine.
- **How**: New `public_reports` table in Supabase (ticker, report_json, published_at, published_by). `GET /r/{ticker}` endpoint. Frontend route with meta tags/OG image (scorecard as the OG image). Vercel handles pre-render; add sitemap.xml regenerated daily listing all published tickers.
- **Guard**: only reports <7 days old can be published; page shows "Published {date}" + staleness banner, so stale analysis doesn't damage credibility.
- **Pricing**: publishing is free (it's marketing for us).
- **Effort**: M (3–5 days incl. OG images + sitemap).

### 4. Today's Market News homepage (already in backlog)
Daily market briefing shown to everyone on the homepage.

- **How**: as specced in backlog — `GET /market-news`, one cached Supabase row/day, first request after midnight regenerates. Reuse market-briefing logic.
- **Why in v1.1**: gives the homepage a reason to exist before a user searches; daily-fresh content also helps SEO crawl frequency.
- **Effort**: S (1–2 days).

**v1.1 total: ~2 weeks. Gate: 100 organic visits/week or 20 signups before starting v1.2.**

---

## v1.2 — Retention (give users a reason to come back)

### 5. AI watchlist + alerts ("tell me only when something actually changes")
The single retention feature. Absorbs "Earnings copilot" as an alert type.

- **What**: User adds tickers to a watchlist. A daily background job checks each ticker for *material* changes; if (and only if) something material happened, the user gets an email digest. Material = earnings released, price move >5% in a day, analyst-visible news event, valuation crossing a threshold.
- **Earnings copilot lives here**: when earnings drop for a watched ticker, the alert email contains the before/after summary — "what changed vs. last quarter" (revenue, margins, guidance, one-paragraph AI delta). This is the copilot feature, delivered where it's actually useful: in your inbox the morning after earnings.
- **How**:
  - `watchlists` table (user_id, ticker, added_at, last_alerted_at, baseline_snapshot jsonb).
  - Daily cron (Render cron job or GitHub Action hitting an admin endpoint) → for each distinct watched ticker: fetch quote + news (FMP/yfinance, shared across users — cost scales with distinct tickers, not users) → cheap model (Haiku) classifies "material or not" → material ones get a Sonnet summary → email via Resend (free tier: 3k emails/mo, fine for now).
  - Earnings detection: FMP `/stable` earnings endpoint (already integrated for the earnings guard).
- **Pricing**: free tier = 3 tickers; subscribers = unlimited. This becomes the strongest subscription pitch ("your portfolio, monitored").
- **Effort**: L (1.5–2 weeks: cron, email templates, unsubscribe handling, alert-quality tuning).
- **Risk**: alert quality is the whole feature. If it emails noise, users unsubscribe. Start conservative (earnings + >5% moves only), expand triggers later.

**Gate: 30% of active signups create a watchlist; email open rate >40%.**

---

## v1.3 — Depth (make each research session stickier)

### 6. Comparable companies
Auto-compare metrics, valuation, growth vs 3–5 peers.

- **How**: FMP `/stable` has peer lists + the ratios/metrics already fetched per ticker. Fetch peers' key metrics (batch), render comparison table in the Deep Research report; AI adds one paragraph: "vs peers, X trades at a premium because…". Cache peer metrics 24h (same peers requested repeatedly).
- **Pricing**: part of Deep Research.
- **Effort**: M (3–5 days).

### 7. Research chat with memory
Ask follow-up questions about a report; AI remembers prior conversations per ticker.

- **What**: Chat box under a Deep Research report. Context = the saved report + fetched financial data + prior chat history for that (user, ticker). "Why is the moat score only 6?" "What did we discuss about NVDA last month?"
- **How**: `research_chats` table (user_id, ticker, messages jsonb). Each turn = one Sonnet call with report + trimmed history in context. Trim history to last ~20 turns; summarize older.
- **Pricing**: needs its own meter — chat turns are marginal-cost API calls. Proposal: subscribers unlimited (fair-use cap 100 turns/day), free/credit users get 5 free follow-up turns per researched ticker, then it asks for a credit per additional 10 turns. Tune later.
- **Effort**: M–L (~1 week incl. UI).
- **Note**: this is the feature that turns Prism from "report generator" into "research assistant" — likely the long-term core. Design the chat context pipeline cleanly; later features (portfolio chat, filing Q&A) reuse it.

**Gate: chat used in >25% of Deep Research sessions.**

---

## v1.4 — Portfolio layer (requires trust; sell the subscription)

### 8. Portfolio analyzer
Upload holdings → risk, overlap, sector exposure, valuation, AI suggestions.

- **What**: CSV upload (or manual entry) of tickers + quantities → dashboard: sector/geography exposure, concentration risk, weighted valuation multiples, ETF overlap (if two ETFs held, top-holdings overlap %), one AI-written assessment with suggestions.
- **How**: `portfolios` + `holdings` tables. Metrics from data already integrated (FMP profiles/ratios, yfinance). ETF holdings via yfinance. One Sonnet call for the narrative assessment.
- **CSV parsing**: accept a dead-simple format (ticker, shares[, cost_basis]) + paste-in textarea. Do NOT attempt broker-export auto-detection in v1 — that's a swamp.
- **Pricing**: subscriber feature (or 3 credits/analysis for non-subs). This is the anchor of the $14.99 pitch alongside watchlist.
- **Effort**: L (1.5–2 weeks).

### 9. Thesis tracker + portfolio journal (merged — same feature)
Record *why* you bought; Prism tells you when the thesis strengthens/weakens and reviews whether it played out.

- **What**: On any ticker (esp. holdings), user writes a short thesis ("buying for datacenter growth, expecting margin expansion"). Each quarter (post-earnings, reusing v1.2's earnings detection), AI evaluates: thesis stronger / weaker / broken, with evidence. Journal view shows thesis history + outcomes over time.
- **How**: `theses` table (user_id, ticker, thesis_text, created_at, checkpoints jsonb). Piggybacks entirely on v1.2 cron + earnings pipeline — that's why it's after v1.2, and why it's cheap for what it delivers.
- **Pricing**: subscriber feature.
- **Effort**: M (~1 week, given v1.2 infra exists).

**Gate: 10 paying users. Portfolio features to people who won't pay = free work.**

---

## v2.0 — Power research (only with revenue + explicit user demand)

Ordered within v2.0 by value-per-effort. Pick based on what paying users actually request — do not build all five on spec.

### 10. Catalyst calendar
Earnings, dividends, investor days, FDA decisions, lockups.
- Earnings + dividends: easy (FMP has both). Investor days / FDA / lockups: no clean free source — start with earnings+dividends only and call it done; expand only if a data source materializes. **Effort: S–M** for the honest version.

### 11. SEC filing simplifier
Highlight what's new/important in 10-K/10-Q/8-K.
- SEC EDGAR is free. The valuable trick: diff the risk-factors and MD&A sections vs the prior filing, then have the model summarize *only the delta*. 8-Ks summarized on arrival (feeds v1.2 alerts). Parsing EDGAR properly is real work. **Effort: L–XL (2–3 weeks).**

### 12. Institutional tracker
13F holdings changes, insider buying/selling.
- Insider trades: SEC Form 4 via EDGAR (free, parseable) — do this half first, it's the higher-signal half. 13Fs: quarterly, 45-day lag, heavy parsing — later. Feeds v1.2 alerts ("insider bought $2M of your watchlist stock"). **Effort: L** (insiders) + **XL** (13F).

### 13. Scenario modeling
"What if revenue grows 20% instead of 15%?"
- Keep honest: simple driver model (revenue growth, margin, multiple → implied price range), sliders in UI, AI narrates sensitivity. NOT a DCF black box — false precision kills credibility. **Effort: M.**

### 14. Economic dashboard
Rates, inflation, unemployment + effect on your holdings.
- FRED API (free) for macro series; AI paragraph connecting macro to the user's portfolio sectors (needs v1.4). Commodity data, differentiated only by the personalization. **Effort: M.**

---

## Parked — with revival conditions

| Feature | Why parked | Revive when |
|---------|-----------|-------------|
| **Community research** (public theses, comments, upvotes) | Cold-start death: community with no users is an empty restaurant and looks worse than no community. Public report pages (v1.1) capture most of the value solo. | ≥500 MAU and users are already sharing reports organically |
| **Backtesting** | Different product. Crowded (QuantConnect, Composer, Portfolio Visualizer). Huge build: survivorship-bias-free price+fundamentals history is expensive. | Never inside Prism, realistically. Separate product decision. |
| **Historical AI** ("what did people think about NVDA before its breakout?") | No historical-sentiment data source → the model would confabulate history. One confidently wrong answer destroys research credibility. | A real archival news/sentiment dataset is licensed (unlikely at this stage) |

---

## Cross-cutting decisions

- **Model tiering**: Sonnet 4.6 stays the report/chat writer. Use Haiku for classification jobs (alert materiality, news filtering) — high-volume, low-difficulty, 10x cheaper.
- **Cost scaling**: watchlist/cron costs scale with *distinct tickers*, not users — always share fetches and cache per-ticker artifacts in Supabase.
- **Email**: Resend, one integration in v1.2, reused by everything after (thesis checkpoints, filing alerts, insider alerts).
- **Every new heavy feature is subscriber-anchored**: credits monetize casual use; watchlist + portfolio + thesis are the reasons to hold a $14.99 subscription. That split stays consistent across versions.
- **File hygiene**: `main.py` will outgrow 500 lines with v1.2+ — split routes into routers (`routes/research.py`, `routes/watchlist.py`, …) when watchlist lands, not before.

## What NOT to do

- Don't start v1.2 before the v1.1 gate. If public pages + scorecards don't bring visitors, the fix is distribution (posting scorecards, SEO tuning, outreach) — not the watchlist.
- Don't build all of v2.0. Build what paying users ask for by name.
- Don't add a second AI provider, vector DB, or agent framework anywhere in this roadmap. Single-call pipelines + Postgres cover everything here.
