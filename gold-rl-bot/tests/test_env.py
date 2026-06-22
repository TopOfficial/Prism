import numpy as np
from gymnasium.utils.env_checker import check_env

from goldbot.data.synthetic import generate_synthetic_ohlcv, generate_synthetic_macro
from goldbot.features.engineering import build_features
from goldbot.features.scaler import FeatureScaler, scalable_columns
from goldbot.env.trading_env import GoldTradingEnv


def _features():
    df = generate_synthetic_ohlcv(n_bars=2000, seed=8)
    macro = generate_synthetic_macro(df.index)
    feats = build_features(df, macro).dropna()
    cols = scalable_columns(feats)
    return FeatureScaler(cols).fit_transform(feats)


def test_gymnasium_check_env():
    env = GoldTradingEnv(_features(), window_size=24, cost_bps=2.0)
    check_env(env, skip_render_check=True)


def test_buy_and_hold_matches_price_return():
    feats = _features()
    env = GoldTradingEnv(feats, window_size=24, cost_bps=0.0)
    obs, _ = env.reset()
    terminated = False
    while not terminated:
        obs, reward, terminated, _, info = env.step(2)  # always "long"

    start_price = feats["close"].iloc[env.window_size]
    end_price = feats["close"].iloc[-1]
    expected_return = end_price / start_price
    assert np.isclose(env.equity, expected_return, rtol=0.02)


def test_flat_position_has_zero_pnl():
    feats = _features()
    env = GoldTradingEnv(feats, window_size=24, cost_bps=2.0)
    env.reset()
    obs, reward, terminated, _, info = env.step(1)  # flat
    assert reward == 0.0


def test_position_change_incurs_cost():
    feats = _features()
    env = GoldTradingEnv(feats, window_size=24, cost_bps=50.0)  # large cost for visibility
    env.reset()
    _, reward_flat_to_long, _, _, _ = env.step(2)
    _, reward_long_to_short, _, _, _ = env.step(0)
    # Reversing a position costs roughly double a single position open.
    assert env.trade_log[-1]["cost"] > env.trade_log[-2]["cost"]
