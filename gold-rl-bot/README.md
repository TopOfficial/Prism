# gold-rl-bot

A research/backtesting scaffold for a reinforcement-learning gold (XAUUSD)
trading strategy, inspired by a YouTube video claiming "60% OOS returns."

**This is a research tool, not a trading bot.** It does not place trades,
does not connect to a broker, and does not touch real money. Its purpose
is the opposite of the video's pitch: to honestly check whether an
RL-trained strategy has a real, *consistent* edge, or whether a headline
backtest number is one lucky out-of-sample window.

## Why walk-forward + stress tests, not just a backtest

A single train/test split can look great by accident — one favorable test
window, one lucky seed, one overfit policy that memorized noise. This
project is built around three checks that a single backtest skips:

1. **Walk-forward validation** (`goldbot/backtest/walk_forward.py`) — slides
   train/test windows across the full history and reports the
   *distribution* of out-of-sample results across many folds, not one.
2. **Stress tests** (`goldbot/backtest/stress_tests.py`):
   - *Monte Carlo bootstrap* — resamples realized trade PnLs to show how
     much the headline return depends on trade-sequence luck.
   - *Null-distribution test* — runs a swarm of random policies and a
     buy-and-hold baseline on the same OOS data, to see if the trained
     policy actually beats chance.
   - *Seed sensitivity* — retrains from multiple random seeds on identical
     data; a real edge should be roughly stable across seeds, an overfit
     one usually isn't.
3. **Leak-free feature scaling** — the scaler is fit on train data only and
   applied to val/test, and multi-timeframe features are forward-filled
   from already-*closed* higher-timeframe bars (see docstrings in
   `goldbot/features/engineering.py`) so nothing peeks into the future.

## Architecture

```
goldbot/
  data/
    loader.py        # real OHLCV + macro data via yfinance (needs internet)
    synthetic.py      # offline synthetic data generator (no internet needed)
  features/
    indicators.py     # RSI, MACD, Bollinger, ATR, ROC, realized vol, z-score
    engineering.py     # multi-timeframe (1h/4h/1D) + macro feature builder
    scaler.py          # leak-free train-fit / any-split-transform scaler
  env/
    trading_env.py     # Gymnasium env: Discrete(3) {short, flat, long}, cost-aware
  training/
    train.py           # PPO training via stable-baselines3
  backtest/
    metrics.py          # Sharpe, Sortino, max drawdown, Calmar, win rate, profit factor
    backtester.py        # run any policy (trained model / random / buy-hold) through the env
    walk_forward.py      # rolling train/test windows + cross-fold summary
    stress_tests.py      # Monte Carlo bootstrap, null-distribution test, seed sensitivity
scripts/
  download_data.py    # CLI: fetch + cache real gold + macro data (run locally, needs internet)
  run_pipeline.py      # CLI: data -> features -> train -> backtest -> stress test, single config
configs/
  default.yaml         # all tunable parameters in one place
tests/                  # pytest suite, runs entirely offline against synthetic data
```

## Setup

```bash
cd gold-rl-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running

**Synthetic data (no internet needed)** — useful for checking the pipeline
runs, not for evaluating a real strategy:

```bash
python scripts/run_pipeline.py --mode single
python scripts/run_pipeline.py --mode walk_forward
```

**Real data (hourly, full feature set)** — fetches gold futures (`GC=F`) +
macro context (DXY, 10Y yield, VIX, oil, silver) from Yahoo Finance. Run
this on a machine with normal internet access (not a firewalled
CI/sandbox container):

```bash
python scripts/download_data.py --period 730d --interval 1h
python scripts/run_pipeline.py --source real --mode walk_forward
```

Edit `configs/default.yaml` to change training length, window size,
transaction cost assumption, walk-forward fold sizes, etc.

**Real data (monthly, fallback for firewalled environments)** — Yahoo
Finance is unreachable from some sandboxed/CI environments that only allow
GitHub egress. `scripts/run_monthly_pipeline.py` uses the World Bank "Pink
Sheet" monthly gold series instead (hosted on GitHub, no API key, updated
monthly), so it's a genuine real-data result even there. It's a real
tradeoff, not a free upgrade: ~12 bars/year instead of ~8760, so far fewer
trades and weaker statistics:

```bash
python scripts/run_monthly_pipeline.py --split-date 2023-01-01 --out report.json
```

Trains on the real monthly series through the month before `--split-date`
and backtests on `--split-date` onward against the same real prices (default
split is Jan 2023, matching the "since 2023" comparison most people want
against the recent gold rally). Pre-1971 data is the fixed Bretton Woods
peg and is excluded by default (`--start-date 1971-01-01`) since it barely
moves and isn't representative of tradeable gold.

## Reading the output

- `goldbot/backtest/metrics.py` reports CAGR, Sharpe, Sortino, max
  drawdown, Calmar, win rate, and profit factor for a single OOS run.
- Walk-forward mode reports per-fold metrics plus `pct_positive` — the
  share of OOS folds that were actually profitable. If that's well under
  50%, a single good-looking fold elsewhere isn't a real edge.
- The null-distribution stress test reports
  `actual_percentile_vs_random` — where the trained policy's Sharpe ratio
  lands relative to a swarm of random policies on the *same* data. Near
  50% means "indistinguishable from random."
- Seed sensitivity reports `sharpe_std` across retrains — high variance
  across seeds on identical data is a strong overfitting signal.

## What this deliberately does not do

- No live execution / broker integration (MT5 or otherwise) — by design,
  per the brief this was built to (research/backtest only).
- No economic-calendar/news-event features — the source video mentions
  these; they need a paid or rate-limited calendar API and were left out
  to keep the data layer to free, unauthenticated sources.
- No Dreamer/model-based RL — PPO via stable-baselines3 only. Dreamer is a
  much larger implementation lift; PPO is the standard, well-supported
  starting point for this kind of research.
- 140+ engineered features (as claimed in the source material) — this
  ships ~25-30 features (base-timeframe technicals + 4h/1D context +
  macro). More features can be added in `goldbot/features/`, but feature
  count alone doesn't fix the OOS-luck problem this project is about.

## A note on the source video

"60% OOS returns" backtests on retail RL trading bot videos are almost
always either cherry-picked test windows, missing realistic transaction
costs/slippage, or both. Treat any single backtest number — including any
this scaffold produces — as a hypothesis to stress-test, not a result to
trust. If walk-forward and the null-distribution test don't both show a
consistent, above-random edge, the strategy doesn't have one yet.
