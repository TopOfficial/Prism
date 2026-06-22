"""Run a policy through GoldTradingEnv once, deterministically, and score it."""
from __future__ import annotations

from typing import Callable, Protocol

import numpy as np
import pandas as pd

from goldbot.env.trading_env import GoldTradingEnv
from goldbot.backtest.metrics import PerformanceMetrics, compute_metrics


class Policy(Protocol):
    def predict(self, obs: np.ndarray, deterministic: bool = True): ...


def sb3_policy(model) -> Callable[[np.ndarray], int]:
    def act(obs: np.ndarray) -> int:
        action, _ = model.predict(obs, deterministic=True)
        return int(action)

    return act


def buy_and_hold_policy() -> Callable[[np.ndarray], int]:
    return lambda obs: 2  # always "long"


def random_policy(seed: int = 0) -> Callable[[np.ndarray], int]:
    rng = np.random.default_rng(seed)
    return lambda obs: int(rng.integers(0, 3))


class BacktestResult:
    def __init__(self, equity_curve: list[float], trade_log: list[dict], metrics: PerformanceMetrics):
        self.equity_curve = equity_curve
        self.trade_log = trade_log
        self.metrics = metrics


def run_backtest(
    features: pd.DataFrame,
    act_fn: Callable[[np.ndarray], int],
    window_size: int = 24,
    cost_bps: float = 2.0,
    bars_per_year: float = 24 * 365,
) -> BacktestResult:
    env = GoldTradingEnv(features, window_size=window_size, cost_bps=cost_bps)
    obs, _ = env.reset()
    terminated = False
    while not terminated:
        action = act_fn(obs)
        obs, _, terminated, _, _ = env.step(action)

    metrics = compute_metrics(env.equity_curve, env.trade_log, bars_per_year=bars_per_year)
    return BacktestResult(env.equity_curve, env.trade_log, metrics)
