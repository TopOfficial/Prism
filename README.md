# Prism

A stock investment brief web app. Enter a ticker and get a full data snapshot — valuation, financials, earnings history, recent news, and a rule-based verdict — in seconds.

## What it does

Search any US stock ticker and Prism returns:

- **Price & range** — current price, 1-day change, and a visual 52-week range bar
- **Overview** — Revenue TTM, EPS TTM, Net Margin, Free Cash Flow
- **Balance sheet** — Total Debt, Cash, Debt/Equity ratio
- **Valuation** — P/E, P/B, P/S, EV/EBITDA compared against sector P/E
- **Earnings history** — last 4 quarters with EPS estimate vs actual and beat/miss indicator
- **Institutional** — top institutional holder and % held
- **News** — 5 most recent headlines (Finnhub, falls back to Yahoo Finance RSS)
- **Verdict** — rule-based UNDERVALUED / FAIR VALUE / OVERVALUED label with bull and bear case

### Verdict logic

| Condition | Label |
|---|---|
| P/E < 80% of sector P/E **and** FCF > 0 | UNDERVALUED |
| P/E > 130% of sector P/E | OVERVALUED |
| Everything else | FAIR VALUE |

## Stack

- **Frontend** — React + Vite + Tailwind CSS (dark theme)
- **Backend** — FastAPI + uvicorn
- **Data** — yfinance + FMP (price, financials, earnings, institutional), Finnhub (news)

## Running locally

**Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Optionally add a `.env` file (copy from `.env.example`):
```
FMP_API_KEY=your_key_here        # optional — live sector P/E; falls back to static table
FINNHUB_API_KEY=your_key_here    # optional — company news; falls back to Yahoo Finance RSS
```

Get a free Finnhub key at [finnhub.io](https://finnhub.io).

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

The frontend reads `VITE_API_URL` from `frontend/.env` (defaults to `http://localhost:8000`).

## Deployment

**Backend → Render**

Start command:
```
uvicorn main:app --host 0.0.0.0 --port $PORT
```
Set environment variables in the Render dashboard:
- `FMP_API_KEY` — for live sector P/E
- `FINNHUB_API_KEY` — for company news (get free key at finnhub.io)

**Frontend → Vercel**

Vercel auto-detects Vite. Set one environment variable:
```
VITE_API_URL=https://your-app.onrender.com
```

## API

```
GET /health          → {"status": "ok"}
GET /brief/{ticker}  → full investment brief JSON
```

Rate limit: 10 requests per IP per hour.
