"""Rolling walk-forward validation.

A single lucky out-of-sample window is the classic way these "60% OOS
returns" trading-bot videos mislead: one favorable test slice gets
reported, and the strategy never gets re-trained-and-re-tested across
multiple, non-overlapping windows. This module does the latter: it slides
a fixed-size train/test window across the full history and reports the
*distribution* of OOS results, not a single number.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from goldbot.features.scaler import FeatureScaler, scalable_columns
from goldbot.backtest.backtester import BacktestResult, run_backtest
from goldbot.backtest.metrics import PerformanceMetrics


@dataclass
class FoldResult:
    fold: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    metrics: PerformanceMetrics


def generate_windows(
    n_rows: int, train_size: int, test_size: int, step: int | None = None
) -> list[tuple[int, int, int, int]]:
    step = step or test_size
    windows = []
    train_start = 0
    while train_start + train_size + test_size <= n_rows:
        train_end = train_start + train_size
        test_end = train_end + test_size
        windows.append((train_start, train_end, train_end, test_end))
        train_start += step
    return windows


def run_walk_forward(
    features: pd.DataFrame,
    train_fn: Callable[[pd.DataFrame, int], object],
    act_fn_from_model: Callable[[object], Callable],
    train_size: int,
    test_size: int,
    window_size: int = 24,
    cost_bps: float = 2.0,
    bars_per_year: float = 24 * 365,
    step: int | None = None,
    seed_start: int = 0,
) -> list[FoldResult]:
    """Slide train/test windows across `features`, training + backtesting each fold.

    `train_fn(train_df, seed) -> model` and `act_fn_from_model(model) -> act_fn`
    are injected so this module has no hard dependency on stable-baselines3.
    """
    feature_cols = scalable_columns(features)
    windows = generate_windows(len(features), train_size, test_size, step)

    results = []
    for i, (tr_s, tr_e, te_s, te_e) in enumerate(windows):
        train_df = features.iloc[tr_s:tr_e]
        test_df = features.iloc[te_s:te_e]

        scaler = FeatureScaler(feature_cols).fit(train_df)
        train_scaled = scaler.transform(train_df)
        test_scaled = scaler.transform(test_df)

        model = train_fn(train_scaled, seed_start + i)
        act_fn = act_fn_from_model(model)

        result: BacktestResult = run_backtest(
            test_scaled, act_fn, window_size=window_size, cost_bps=cost_bps, bars_per_year=bars_per_year
        )
        results.append(FoldResult(i, tr_s, tr_e, te_s, te_e, result.metrics))

    return results


def summarize_folds(fold_results: list[FoldResult]) -> dict:
    """Aggregate fold metrics: mean/std tell you if the edge is consistent or one lucky fold."""
    if not fold_results:
        return {}
    fields = ["total_return_pct", "sharpe", "max_drawdown_pct", "win_rate_pct"]
    summary = {}
    for field in fields:
        values = np.array([getattr(fr.metrics, field) for fr in fold_results], dtype=float)
        summary[field] = {
            "mean": round(float(values.mean()), 3),
            "std": round(float(values.std()), 3),
            "min": round(float(values.min()), 3),
            "max": round(float(values.max()), 3),
            "pct_positive": round(100 * float((values > 0).mean()), 1),
        }
    return summary
