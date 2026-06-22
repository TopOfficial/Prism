import numpy as np

from goldbot.data.synthetic import generate_synthetic_ohlcv, generate_synthetic_macro
from goldbot.features.engineering import build_features
from goldbot.features.scaler import FeatureScaler, scalable_columns, RAW_COLUMNS


def test_raw_columns_excluded():
    feats = build_features(
        generate_synthetic_ohlcv(n_bars=500, seed=5), None
    ).dropna()
    cols = scalable_columns(feats)
    for raw in RAW_COLUMNS:
        assert raw not in cols


def test_fit_transform_train_stats():
    feats = build_features(
        generate_synthetic_ohlcv(n_bars=2000, seed=6), None
    ).dropna()
    cols = scalable_columns(feats)
    scaler = FeatureScaler(cols).fit(feats)
    scaled = scaler.transform(feats)

    assert np.allclose(scaled[cols].mean(), 0, atol=0.3)
    # close/log_return must pass through completely untouched.
    assert scaled["close"].equals(feats["close"])
    assert scaled["log_return"].equals(feats["log_return"])


def test_transform_on_unseen_split_uses_train_stats():
    feats = build_features(
        generate_synthetic_ohlcv(n_bars=2000, seed=7), None
    ).dropna()
    cols = scalable_columns(feats)
    train, test = feats.iloc[:1000], feats.iloc[1000:]
    scaler = FeatureScaler(cols).fit(train)

    scaled_test = scaler.transform(test)
    # Test-split mean need not be ~0 (it's scaled with train stats), but it
    # must use exactly train's mean/std, not its own.
    expected = (test[cols] - train[cols].mean()) / train[cols].std().replace(0, 1.0)
    expected = expected.clip(-10, 10)
    assert np.allclose(scaled_test[cols].to_numpy(), expected.to_numpy(), equal_nan=True)
