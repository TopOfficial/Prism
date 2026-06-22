"""Feature engineering for a close-only monthly price series.

Unlike `goldbot.features.engineering.build_features`, there's no OHLC/volume
and no lower timeframe to build multi-timeframe context from -- monthly is
the base resolution here. Indicator windows are scaled down from the hourly
defaults in `goldbot.features.indicators` to suit ~12 bars/year data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from goldbot.features.indicators import bollinger_bands, ema, macd, rsi, roc, zscore


def build_monthly_features(close: pd.Series) -> pd.DataFrame:
    close = close.astype(float)
    log_return = np.log(close / close.shift(1))

    out = pd.DataFrame(index=close.index)
    out["close"] = close
    out["log_return"] = log_return

    out["rsi_6"] = rsi(close, window=6)
    out["rsi_12"] = rsi(close, window=12)
    out = out.join(macd(close, fast=6, slow=12, signal=4))
    out = out.join(bollinger_bands(close, window=12, n_std=2.0))
    out["roc_3"] = roc(close, window=3)
    out["roc_6"] = roc(close, window=6)
    out["ema_6_dev"] = close / ema(close, window=6) - 1.0
    out["ema_12_dev"] = close / ema(close, window=12) - 1.0
    out["zscore_24"] = zscore(close, window=24)
    out["vol_12"] = log_return.rolling(12).std() * np.sqrt(12)

    return out
