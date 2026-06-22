from goldbot.backtest.walk_forward import generate_windows


def test_windows_are_contiguous_train_then_test():
    windows = generate_windows(n_rows=1000, train_size=300, test_size=100)
    for tr_s, tr_e, te_s, te_e in windows:
        assert tr_e - tr_s == 300
        assert te_e - te_s == 100
        assert te_s == tr_e  # test immediately follows train, no gap, no overlap

    assert all(w[3] <= 1000 for w in windows)


def test_windows_slide_forward_without_overlap_between_folds():
    windows = generate_windows(n_rows=1000, train_size=300, test_size=100)
    for (a_tr_s, a_tr_e, a_te_s, a_te_e), (b_tr_s, b_tr_e, b_te_s, b_te_e) in zip(
        windows, windows[1:]
    ):
        # Each fold's test window starts where the previous fold's test window ended.
        assert b_te_s >= a_te_e


def test_custom_step_smaller_than_test_size_allows_overlap():
    windows = generate_windows(n_rows=500, train_size=200, test_size=100, step=50)
    assert len(windows) > generate_windows(n_rows=500, train_size=200, test_size=100).__len__()
