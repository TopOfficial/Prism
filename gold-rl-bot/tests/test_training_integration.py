"""Slow-ish integration smoke test: trains a tiny PPO agent and backtests it.

Not a strategy-quality test (timesteps are far too low for that) -- just
confirms the env/SB3/backtester wiring doesn't break.
"""
from goldbot.data.synthetic import generate_synthetic_ohlcv, generate_synthetic_macro
from goldbot.features.engineering import build_features
from goldbot.features.scaler import FeatureScaler, scalable_columns
from goldbot.training.train import train_ppo
from goldbot.backtest.backtester import run_backtest, sb3_policy


def test_train_and_backtest_smoke():
    df = generate_synthetic_ohlcv(n_bars=2500, seed=99)
    macro = generate_synthetic_macro(df.index)
    feats = build_features(df, macro).dropna()
    cols = scalable_columns(feats)

    train_df, test_df = feats.iloc[:1800], feats.iloc[1800:]
    scaler = FeatureScaler(cols).fit(train_df)
    train_scaled, test_scaled = scaler.transform(train_df), scaler.transform(test_df)

    model = train_ppo(train_scaled, window_size=24, total_timesteps=2048, seed=0)
    result = run_backtest(test_scaled, sb3_policy(model), window_size=24, cost_bps=2.0)

    assert len(result.equity_curve) > 0
    assert result.metrics.n_trades >= 0
    assert result.equity_curve[0] == 1.0
