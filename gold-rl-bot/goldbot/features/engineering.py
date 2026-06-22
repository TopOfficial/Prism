"""Multi-timeframe + macro feature builder.

Combines base-timeframe technical indicators with higher-timeframe context
(resampled OHLCV) and macro series (DXY, yields, VIX, ...), all aligned to
the base index without lookahead leakage:

- Higher-timeframe bars are resampled with `label="right"` so a bar's
  timestamp is its *close* time, then forward-filled onto the base index.
  A bar's indicator value only becomes visible once that bar has closed.
- Macro series (daily) are shifted by one full day before forward-filling,
  since same-day macro closes aren't known intrabar in real time.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import indicators as ind

DEFAULT_HIGHER_TIMEFRAMES = ("4h", "1D")


def _resample_ohlcv(ohlcv: pd.DataFrame, rule: str) -> pd.DataFrame:
    agg = ohlcv.resample(rule, label="right", closed="right").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    return agg.dropna(subset=["close"])


def _htf_features(ohlcv: pd.DataFrame, rule: str, base_index: pd.DatetimeIndex) -> pd.DataFrame:
    htf = _resample_ohlcv(ohlcv, rule)
    close = htf["close"]
    feats = pd.DataFrame(index=htf.index)
    feats["rsi"] = ind.rsi(close, 14)
    feats["macd_hist"] = ind.macd(close)["macd_hist"]
    feats["bb_pct_b"] = ind.bollinger_bands(close)["bb_pct_b"]
    feats["roc"] = ind.roc(close, 5)
    feats = feats.add_prefix(f"htf_{rule}_")
    # Forward-fill the closed higher-timeframe bar onto every base bar that
    # falls within it; nothing here looks ahead of what's already closed.
    return feats.reindex(base_index, method="ffill")


def _macro_features(macro: pd.DataFrame, base_index: pd.DatetimeIndex) -> pd.DataFrame:
    macro = macro.shift(1)  # yesterday's close only, to avoid same-day leakage
    feats = pd.DataFrame(index=macro.index)
    for col in macro.columns:
        series = macro[col]
        feats[f"{col}_ret"] = series.pct_change()
        feats[f"{col}_z"] = ind.zscore(series, 50)
    return feats.reindex(base_index, method="ffill")


def build_features(
    ohlcv: pd.DataFrame,
    macro: pd.DataFrame | None = None,
    higher_timeframes: tuple[str, ...] = DEFAULT_HIGHER_TIMEFRAMES,
) -> pd.DataFrame:
    """Build the full feature matrix for `ohlcv`, returned aligned to its index.

    The first ~50-60 rows (longest rolling window) will contain NaNs from
    warmup and should be dropped by the caller via `.dropna()`.
    """
    close, high, low = ohlcv["close"], ohlcv["high"], ohlcv["low"]

    feats = pd.DataFrame(index=ohlcv.index)
    feats["log_return"] = np.log(close / close.shift(1))
    feats["rsi"] = ind.rsi(close, 14)
    feats = feats.join(ind.macd(close))
    feats = feats.join(ind.bollinger_bands(close))
    feats["atr_pct"] = ind.atr(high, low, close, 14) / close
    feats["roc_10"] = ind.roc(close, 10)
    feats["realized_vol_24"] = ind.realized_vol(close, 24)
    feats["sma_50_z"] = ind.zscore(close, 50)
    feats["ema_12_dist"] = (close - ind.ema(close, 12)) / close
    feats["volume_z"] = ind.zscore(ohlcv["volume"], 50)

    for rule in higher_timeframes:
        feats = feats.join(_htf_features(ohlcv, rule, ohlcv.index))

    if macro is not None and not macro.empty:
        feats = feats.join(_macro_features(macro, ohlcv.index))

    feats["close"] = close
    return feats
