import numpy as np
import pandas as pd

from goldbot.features.monthly import build_monthly_features


def _sample_close(n=200, seed=5):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2000-01-01", periods=n, freq="MS")
    log_rets = rng.normal(0.003, 0.04, size=n)
    close = 300 * np.exp(np.cumsum(log_rets))
    return pd.Series(close, index=idx)


def test_close_and_log_return_present():
    feats = build_monthly_features(_sample_close())
    assert "close" in feats.columns
    assert "log_return" in feats.columns


def test_no_nans_after_warmup_dropna():
    feats = build_monthly_features(_sample_close())
    cleaned = feats.dropna()
    assert cleaned.isna().sum().sum() == 0
    # Longest window used is the 24-month zscore.
    assert len(feats) - len(cleaned) < 24


def test_no_lookahead():
    close = _sample_close()
    feats_a = build_monthly_features(close)

    mutated = close.copy()
    mutated.iloc[100:] = mutated.iloc[100:] * 1.5
    feats_b = build_monthly_features(mutated)

    before = feats_a.iloc[:80]
    after_mutation = feats_b.iloc[:80]
    assert before.equals(after_mutation)
