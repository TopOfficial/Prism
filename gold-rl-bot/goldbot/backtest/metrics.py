"""Performance metrics computed from an equity curve and/or trade log."""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd


@dataclass
class PerformanceMetrics:
    total_return_pct: float
    cagr_pct: float
    sharpe: float
    sortino: float
    max_drawdown_pct: float
    calmar: float
    win_rate_pct: float
    profit_factor: float
    n_trades: int

    def to_dict(self) -> dict:
        return asdict(self)


def _drawdown_series(equity: np.ndarray) -> np.ndarray:
    running_max = np.maximum.accumulate(equity)
    return (equity - running_max) / running_max


def compute_metrics(
    equity_curve: list[float] | np.ndarray,
    trade_log: list[dict] | None = None,
    bars_per_year: float = 24 * 365,
    risk_free_rate: float = 0.0,
) -> PerformanceMetrics:
    equity = np.asarray(equity_curve, dtype=np.float64)
    if len(equity) < 2:
        raise ValueError("equity_curve needs at least 2 points")

    bar_returns = np.diff(np.log(equity))
    n_bars = len(bar_returns)
    total_return_pct = (equity[-1] / equity[0] - 1.0) * 100

    years = n_bars / bars_per_year
    cagr_pct = ((equity[-1] / equity[0]) ** (1 / years) - 1) * 100 if years > 0 else 0.0

    rf_per_bar = risk_free_rate / bars_per_year
    excess = bar_returns - rf_per_bar
    sharpe = (
        (excess.mean() / excess.std()) * np.sqrt(bars_per_year)
        if excess.std() > 1e-12
        else 0.0
    )

    downside = excess[excess < 0]
    sortino = (
        (excess.mean() / downside.std()) * np.sqrt(bars_per_year)
        if len(downside) > 1 and downside.std() > 1e-12
        else 0.0
    )

    dd = _drawdown_series(equity)
    max_drawdown_pct = abs(dd.min()) * 100

    calmar = (cagr_pct / max_drawdown_pct) if max_drawdown_pct > 1e-9 else 0.0

    win_rate_pct = 0.0
    profit_factor = 0.0
    n_trades = 0
    if trade_log:
        trade_pnls = _trade_pnls_from_log(trade_log)
        n_trades = len(trade_pnls)
        if n_trades > 0:
            wins = [p for p in trade_pnls if p > 0]
            losses = [-p for p in trade_pnls if p < 0]
            win_rate_pct = 100 * len(wins) / n_trades
            profit_factor = (sum(wins) / sum(losses)) if sum(losses) > 1e-12 else float("inf")

    return PerformanceMetrics(
        total_return_pct=round(total_return_pct, 3),
        cagr_pct=round(cagr_pct, 3),
        sharpe=round(sharpe, 3),
        sortino=round(sortino, 3),
        max_drawdown_pct=round(max_drawdown_pct, 3),
        calmar=round(calmar, 3),
        win_rate_pct=round(win_rate_pct, 3),
        profit_factor=round(profit_factor, 3) if np.isfinite(profit_factor) else profit_factor,
        n_trades=n_trades,
    )


def _trade_pnls_from_log(trade_log: list[dict]) -> list[float]:
    """Reconstruct per-position-flip PnL (in price terms) from a trade log.

    `trade_log` entries are produced by GoldTradingEnv: each is a position
    *change* with the price at which it occurred. We pair consecutive
    entries to estimate realized PnL for the position that was just closed.
    """
    pnls = []
    open_position = None
    open_price = None
    for entry in trade_log:
        if open_position is not None and open_position != 0:
            pnl = open_position * (entry["price"] - open_price)
            pnls.append(pnl)
        open_position = entry["to_position"]
        open_price = entry["price"]
    return pnls
