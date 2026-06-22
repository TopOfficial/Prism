"""Real historical data loaders.

These hit Yahoo Finance via yfinance and require outbound internet access.
Run this on your own machine -- sandboxed CI/dev containers often firewall
off finance data providers, in which case use `goldbot.data.synthetic`
to exercise the rest of the pipeline instead.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache"

# Yahoo Finance tickers used as macro context for gold.
MACRO_TICKERS = {
    "dxy": "DX-Y.NYB",   # US Dollar Index
    "us10y": "^TNX",     # 10-Year Treasury yield (x10)
    "vix": "^VIX",       # CBOE Volatility Index
    "oil": "CL=F",       # WTI Crude futures
    "silver": "SI=F",    # Silver futures
}

GOLD_TICKER = "GC=F"  # COMEX Gold futures continuous contract


def _download(ticker: str, period: str, interval: str) -> pd.DataFrame:
    import yfinance as yf

    df = yf.download(
        ticker, period=period, interval=interval, auto_adjust=False, progress=False
    )
    if df.empty:
        raise RuntimeError(f"No data returned for {ticker} (period={period}, interval={interval})")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    df.index.name = "timestamp"
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    return df


def fetch_gold_ohlcv(
    period: str = "730d", interval: str = "1h", use_cache: bool = True
) -> pd.DataFrame:
    """Fetch gold futures OHLCV from Yahoo Finance, with on-disk caching."""
    cache_path = CACHE_DIR / f"gold_{interval}_{period}.parquet"
    if use_cache and cache_path.exists():
        return pd.read_parquet(cache_path)

    df = _download(GOLD_TICKER, period=period, interval=interval)
    df = df[["open", "high", "low", "close", "volume"]]

    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_path)
    return df


def fetch_macro(
    period: str = "730d", interval: str = "1d", use_cache: bool = True
) -> pd.DataFrame:
    """Fetch macro series (DXY, 10Y yield, VIX, oil, silver), daily by default.

    Daily is intentional even when the gold series is intraday: macro
    releases don't update intrabar, so upsampling happens later in
    `goldbot.features.engineering` via forward-fill alignment.
    """
    cache_path = CACHE_DIR / f"macro_{interval}_{period}.parquet"
    if use_cache and cache_path.exists():
        return pd.read_parquet(cache_path)

    series = {}
    for name, ticker in MACRO_TICKERS.items():
        try:
            raw = _download(ticker, period=period, interval=interval)
            series[name] = raw["close"]
        except Exception as exc:  # pragma: no cover - network dependent
            print(f"warning: failed to fetch {name} ({ticker}): {exc}")
    df = pd.DataFrame(series)

    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_path)
    return df
