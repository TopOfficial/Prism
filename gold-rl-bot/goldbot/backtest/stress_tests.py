"""Stress tests for "is this edge real, or did it get lucky?"

Three independent angles:
  1. Monte Carlo bootstrap  -- resample the realized trade PnLs to see how
     much the headline return depends on the exact sequence/luck of trades.
  2. Random/buy-and-hold null comparison -- run a swarm of random policies
     (and buy-and-hold) over the *same* OOS data; see where the trained
     policy's Sharpe actually lands in that null distribution.
  3. Seed sensitivity -- retrain from multiple random seeds, same data;
     a real edge should be reasonably stable across seeds, an overfit one
     usually isn't.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from goldbot.backtest.backtester import run_backtest, random_policy, buy_and_hold_policy
from goldbot.backtest.metrics import _trade_pnls_from_log, compute_metrics


def monte_carlo_bootstrap(
    trade_log: list[dict], n_sims: int = 2000, seed: int = 0
) -> dict:
    pnls = np.array(_trade_pnls_from_log(trade_log), dtype=np.float64)
    if len(pnls) < 5:
        return {"warning": "too few trades for a meaningful bootstrap", "n_trades": len(pnls)}

    rng = np.random.default_rng(seed)
    n = len(pnls)
    totals = np.empty(n_sims)
    for i in range(n_sims):
        sample = rng.choice(pnls, size=n, replace=True)
        totals[i] = sample.sum()

    actual_total = pnls.sum()
    percentile = float((totals < actual_total).mean() * 100)
    return {
        "n_trades": n,
        "actual_total_pnl": round(float(actual_total), 5),
        "bootstrap_mean": round(float(totals.mean()), 5),
        "bootstrap_p05": round(float(np.percentile(totals, 5)), 5),
        "bootstrap_p50": round(float(np.percentile(totals, 50)), 5),
        "bootstrap_p95": round(float(np.percentile(totals, 95)), 5),
        "pct_sims_profitable": round(float((totals > 0).mean() * 100), 1),
        "actual_percentile_in_bootstrap": round(percentile, 1),
    }


def null_distribution_test(
    features_test: pd.DataFrame,
    actual_sharpe: float,
    window_size: int = 24,
    cost_bps: float = 2.0,
    bars_per_year: float = 24 * 365,
    n_random: int = 200,
    seed: int = 0,
) -> dict:
    """Compare the trained policy's OOS Sharpe against a swarm of random policies
    and a buy-and-hold baseline, all evaluated on the same test data."""
    random_sharpes = np.empty(n_random)
    for i in range(n_random):
        result = run_backtest(
            features_test, random_policy(seed=seed + i),
            window_size=window_size, cost_bps=cost_bps, bars_per_year=bars_per_year,
        )
        random_sharpes[i] = result.metrics.sharpe

    bh_result = run_backtest(
        features_test, buy_and_hold_policy(),
        window_size=window_size, cost_bps=cost_bps, bars_per_year=bars_per_year,
    )

    percentile_vs_random = float((random_sharpes < actual_sharpe).mean() * 100)
    return {
        "actual_sharpe": round(actual_sharpe, 3),
        "random_policy_sharpe_mean": round(float(random_sharpes.mean()), 3),
        "random_policy_sharpe_std": round(float(random_sharpes.std()), 3),
        "buy_and_hold_sharpe": round(bh_result.metrics.sharpe, 3),
        "buy_and_hold_total_return_pct": bh_result.metrics.total_return_pct,
        "actual_percentile_vs_random": round(percentile_vs_random, 1),
        "beats_random_policies_pct_of_time": round(percentile_vs_random, 1),
    }


def seed_sensitivity(
    train_fn: Callable[[pd.DataFrame, int], object],
    act_fn_from_model: Callable[[object], Callable],
    train_features: pd.DataFrame,
    test_features: pd.DataFrame,
    window_size: int = 24,
    cost_bps: float = 2.0,
    bars_per_year: float = 24 * 365,
    seeds: tuple[int, ...] = (0, 1, 2, 3, 4),
) -> dict:
    sharpes, returns = [], []
    for seed in seeds:
        model = train_fn(train_features, seed)
        act_fn = act_fn_from_model(model)
        result = run_backtest(
            test_features, act_fn, window_size=window_size, cost_bps=cost_bps, bars_per_year=bars_per_year
        )
        sharpes.append(result.metrics.sharpe)
        returns.append(result.metrics.total_return_pct)

    sharpes_arr, returns_arr = np.array(sharpes), np.array(returns)
    return {
        "seeds": list(seeds),
        "sharpe_per_seed": [round(s, 3) for s in sharpes],
        "return_pct_per_seed": [round(r, 3) for r in returns],
        "sharpe_mean": round(float(sharpes_arr.mean()), 3),
        "sharpe_std": round(float(sharpes_arr.std()), 3),
        "return_pct_mean": round(float(returns_arr.mean()), 3),
        "return_pct_std": round(float(returns_arr.std()), 3),
    }
