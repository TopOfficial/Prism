"""Offline synthetic OHLCV generator.

Used for pipeline development/tests where network access to a real data
provider isn't available. Produces a price series with stochastic
volatility (vol clustering) and mild autocorrelation regimes so the
feature/env/training code has something non-trivial to chew on. This is
NOT a model of real gold price dynamics -- swap in `goldbot.data.loader`
for real history before trusting any backtest result.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def generate_synthetic_ohlcv(
    n_bars: int = 5000,
    freq: str = "1h",
    start: str = "2021-01-01",
    seed: int = 7,
    base_price: float = 1900.0,
    annual_vol: float = 0.14,
    bars_per_year: int = 24 * 365,
) -> pd.DataFrame:
    """Generate a synthetic OHLCV bar series with regime-switching volatility.

    Returns a DataFrame indexed by UTC timestamp with columns
    [open, high, low, close, volume].
    """
    rng = np.random.default_rng(seed)
    dt = 1.0 / bars_per_year
    sigma_bar = annual_vol * np.sqrt(dt)

    # Two-state vol regime (calm / stressed) via a simple Markov chain,
    # giving the kind of vol clustering real markets exhibit.
    regimes = np.zeros(n_bars, dtype=int)
    p_switch = 0.01
    for i in range(1, n_bars):
        if rng.random() < p_switch:
            regimes[i] = 1 - regimes[i - 1]
        else:
            regimes[i] = regimes[i - 1]
    vol_mult = np.where(regimes == 0, 0.7, 2.2)

    # Slow-moving drift regime so there are tradable trends, not pure noise.
    n_drift_states = -(-n_bars // 250)  # ceiling division: enough states to cover n_bars
    drift_state = rng.choice([-1.0, 0.0, 1.0], size=n_drift_states)
    drift_per_bar = np.repeat(drift_state, 250)[:n_bars] * 0.05 * sigma_bar

    shocks = rng.standard_normal(n_bars) * sigma_bar * vol_mult
    log_returns = drift_per_bar + shocks
    close = base_price * np.exp(np.cumsum(log_returns))

    # Synthesize open/high/low around close using intrabar noise.
    intrabar_noise = rng.standard_normal((n_bars, 2)) * sigma_bar * vol_mult[:, None] * 0.5
    open_ = np.empty(n_bars)
    open_[0] = base_price
    open_[1:] = close[:-1]
    high = np.maximum(open_, close) + np.abs(intrabar_noise[:, 0]) * close
    low = np.minimum(open_, close) - np.abs(intrabar_noise[:, 1]) * close
    volume = rng.lognormal(mean=8.0, sigma=0.5, size=n_bars) * (1.0 + vol_mult)

    index = pd.date_range(start=start, periods=n_bars, freq=freq, tz="UTC")
    df = pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=index,
    )
    df.index.name = "timestamp"
    return df


def generate_synthetic_macro(
    ohlcv_index: pd.DatetimeIndex, seed: int = 11
) -> pd.DataFrame:
    """Generate synthetic macro series (DXY, 10Y yield, VIX) aligned to an OHLCV index."""
    rng = np.random.default_rng(seed)
    n = len(ohlcv_index)
    dxy = 100 + np.cumsum(rng.standard_normal(n) * 0.02)
    tnx = 40 + np.cumsum(rng.standard_normal(n) * 0.01)
    vix = np.clip(15 + np.cumsum(rng.standard_normal(n) * 0.05), 8, 80)
    return pd.DataFrame({"dxy": dxy, "us10y": tnx, "vix": vix}, index=ohlcv_index)
