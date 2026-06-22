import numpy as np
import pytest

from goldbot.backtest.metrics import compute_metrics


def test_flat_equity_curve_zero_sharpe():
    m = compute_metrics([1.0, 1.0, 1.0, 1.0], bars_per_year=252)
    assert m.sharpe == 0.0
    assert m.total_return_pct == 0.0
    assert m.max_drawdown_pct == 0.0


def test_monotonic_gain_no_drawdown():
    equity = [1.0, 1.02, 1.04, 1.06, 1.08]
    m = compute_metrics(equity, bars_per_year=252)
    assert m.max_drawdown_pct == 0.0
    assert m.total_return_pct == pytest.approx(8.0, abs=0.01)


def test_known_drawdown():
    equity = [1.0, 1.2, 0.9, 1.1]  # peak 1.2 -> trough 0.9 = -25% drawdown
    m = compute_metrics(equity, bars_per_year=252)
    assert m.max_drawdown_pct == pytest.approx(25.0, abs=0.01)


def test_trade_pnl_reconstruction_and_win_rate():
    trade_log = [
        {"to_position": 1.0, "price": 100.0},
        {"to_position": 0.0, "price": 110.0},  # closed long: +10
        {"to_position": -1.0, "price": 110.0},
        {"to_position": 0.0, "price": 100.0},  # closed short: +10
    ]
    equity = [1.0, 1.1, 1.2]
    m = compute_metrics(equity, trade_log=trade_log, bars_per_year=252)
    assert m.n_trades == 2
    assert m.win_rate_pct == 100.0


def test_requires_at_least_two_points():
    with pytest.raises(ValueError):
        compute_metrics([1.0])
