from goldbot.data.synthetic import generate_synthetic_ohlcv, generate_synthetic_macro
from goldbot.features.engineering import build_features


def _sample_features(n_bars=2000):
    df = generate_synthetic_ohlcv(n_bars=n_bars, seed=3)
    macro = generate_synthetic_macro(df.index)
    return build_features(df, macro)


def test_no_nans_after_warmup_dropna():
    feats = _sample_features()
    cleaned = feats.dropna()
    assert cleaned.isna().sum().sum() == 0
    # Warmup is dominated by the "1D" higher-timeframe Bollinger window
    # (20 daily bars = ~480 hourly rows), not the base-timeframe indicators.
    assert len(feats) - len(cleaned) < 500


def test_close_and_log_return_present():
    feats = _sample_features()
    assert "close" in feats.columns
    assert "log_return" in feats.columns


def test_higher_timeframe_features_no_lookahead():
    """An htf feature shouldn't change if we mutate only data *after* the
    current bar -- otherwise it's peeking into the future."""
    df = generate_synthetic_ohlcv(n_bars=1000, seed=4)
    macro = generate_synthetic_macro(df.index)
    feats_a = build_features(df, macro)

    df_mutated = df.copy()
    df_mutated.iloc[500:] = df_mutated.iloc[500:] * 1.5  # blow up the future half
    feats_b = build_features(df_mutated, macro)

    # Bars before the mutation point must be identical -- nothing there
    # should have "seen" the change made to future bars.
    cols = [c for c in feats_a.columns if c.startswith("htf_")]
    before = feats_a.iloc[:480][cols]
    after_mutation = feats_b.iloc[:480][cols]
    assert before.equals(after_mutation)
