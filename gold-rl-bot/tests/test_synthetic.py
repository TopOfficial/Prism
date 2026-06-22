from goldbot.data.synthetic import generate_synthetic_ohlcv, generate_synthetic_macro


def test_ohlcv_shape_and_columns():
    df = generate_synthetic_ohlcv(n_bars=500, seed=1)
    assert len(df) == 500
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert (df["high"] >= df["low"]).all()
    assert (df["close"] > 0).all()


def test_deterministic_with_seed():
    a = generate_synthetic_ohlcv(n_bars=200, seed=42)
    b = generate_synthetic_ohlcv(n_bars=200, seed=42)
    assert a["close"].equals(b["close"])


def test_macro_aligned_to_ohlcv_index():
    df = generate_synthetic_ohlcv(n_bars=300, seed=2)
    macro = generate_synthetic_macro(df.index)
    assert macro.index.equals(df.index)
    assert set(macro.columns) == {"dxy", "us10y", "vix"}
