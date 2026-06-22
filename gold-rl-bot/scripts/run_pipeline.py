"""End-to-end pipeline: load data -> features -> train -> backtest -> stress test.

Usage:
    python scripts/run_pipeline.py                       # synthetic data, single split
    python scripts/run_pipeline.py --source real          # real data (needs internet + cache)
    python scripts/run_pipeline.py --mode walk_forward    # rolling walk-forward validation

This prints a plain-text report. It does NOT place any trades or connect to
a broker -- research/backtest only.
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from goldbot.data.synthetic import generate_synthetic_ohlcv, generate_synthetic_macro
from goldbot.features.engineering import build_features
from goldbot.features.scaler import FeatureScaler, scalable_columns
from goldbot.training.train import train_ppo
from goldbot.backtest.backtester import run_backtest, sb3_policy
from goldbot.backtest.walk_forward import run_walk_forward, summarize_folds
from goldbot.backtest.stress_tests import (
    monte_carlo_bootstrap,
    null_distribution_test,
    seed_sensitivity,
)


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_data(cfg: dict, source_override: str | None):
    source = source_override or cfg["data"]["source"]
    if source == "real":
        from goldbot.data.loader import fetch_gold_ohlcv, fetch_macro

        ohlcv = fetch_gold_ohlcv(period=cfg["data"]["period"], interval=cfg["data"]["interval"])
        macro = fetch_macro(period=cfg["data"]["period"])
    else:
        ohlcv = generate_synthetic_ohlcv(n_bars=cfg["data"]["n_bars"], freq=cfg["data"]["interval"])
        macro = generate_synthetic_macro(ohlcv.index)
    return ohlcv, macro


def make_train_fn(cfg: dict):
    def train_fn(train_df, seed):
        return train_ppo(
            train_df,
            window_size=cfg["env"]["window_size"],
            cost_bps=cfg["env"]["cost_bps"],
            total_timesteps=cfg["training"]["total_timesteps"],
            seed=seed,
        )

    return train_fn


def run_single_split(features, cfg: dict) -> dict:
    n = len(features)
    split = int(n * 0.8)
    train_df, test_df = features.iloc[:split], features.iloc[split:]

    cols = scalable_columns(features)
    scaler = FeatureScaler(cols).fit(train_df)
    train_scaled, test_scaled = scaler.transform(train_df), scaler.transform(test_df)

    train_fn = make_train_fn(cfg)
    model = train_fn(train_scaled, cfg["training"]["seed"])

    result = run_backtest(
        test_scaled,
        sb3_policy(model),
        window_size=cfg["env"]["window_size"],
        cost_bps=cfg["env"]["cost_bps"],
        bars_per_year=cfg["bars_per_year"],
    )
    print("\n=== Out-of-sample backtest (single 80/20 split) ===")
    print(json.dumps(result.metrics.to_dict(), indent=2))

    print("\n=== Stress test: Monte Carlo bootstrap of realized trades ===")
    mc = monte_carlo_bootstrap(result.trade_log, n_sims=cfg["stress_tests"]["monte_carlo_sims"])
    print(json.dumps(mc, indent=2))

    print("\n=== Stress test: vs random-policy / buy-and-hold null distribution ===")
    null = null_distribution_test(
        test_scaled,
        result.metrics.sharpe,
        window_size=cfg["env"]["window_size"],
        cost_bps=cfg["env"]["cost_bps"],
        bars_per_year=cfg["bars_per_year"],
        n_random=cfg["stress_tests"]["n_random_policies"],
    )
    print(json.dumps(null, indent=2))

    print("\n=== Stress test: seed sensitivity (retrain, same data) ===")
    seeds = tuple(cfg["stress_tests"]["seeds"])
    ss = seed_sensitivity(
        train_fn,
        sb3_policy,
        train_scaled,
        test_scaled,
        window_size=cfg["env"]["window_size"],
        cost_bps=cfg["env"]["cost_bps"],
        bars_per_year=cfg["bars_per_year"],
        seeds=seeds,
    )
    print(json.dumps(ss, indent=2))

    return {
        "backtest": result.metrics.to_dict(),
        "monte_carlo": mc,
        "null_distribution": null,
        "seed_sensitivity": ss,
    }


def run_walk_forward_mode(features, cfg: dict) -> dict:
    train_fn = make_train_fn(cfg)
    folds = run_walk_forward(
        features,
        train_fn,
        sb3_policy,
        train_size=cfg["walk_forward"]["train_size"],
        test_size=cfg["walk_forward"]["test_size"],
        window_size=cfg["env"]["window_size"],
        cost_bps=cfg["env"]["cost_bps"],
        bars_per_year=cfg["bars_per_year"],
        step=cfg["walk_forward"]["step"],
    )
    print(f"\n=== Walk-forward: {len(folds)} folds ===")
    for f in folds:
        print(f"  fold {f.fold}: {f.metrics.to_dict()}")

    summary = summarize_folds(folds)
    print("\n=== Walk-forward summary (consistency across folds) ===")
    print(json.dumps(summary, indent=2))

    if summary and summary["total_return_pct"]["pct_positive"] < 50:
        print(
            "\nNote: fewer than half the OOS folds were profitable. A single "
            "favorable fold (or a single favorable backtest window) is not "
            "evidence of a real edge -- this is what walk-forward is for."
        )

    return {"folds": [f.metrics.to_dict() for f in folds], "summary": summary}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(Path(__file__).resolve().parents[1] / "configs" / "default.yaml"))
    parser.add_argument("--source", choices=["synthetic", "real"], default=None)
    parser.add_argument("--mode", choices=["single", "walk_forward"], default="single")
    parser.add_argument("--out", default=None, help="optional path to dump JSON report")
    args = parser.parse_args()

    cfg = load_config(args.config)
    ohlcv, macro = load_data(cfg, args.source)
    features = build_features(ohlcv, macro, tuple(cfg["features"]["higher_timeframes"])).dropna()
    print(f"Loaded {len(ohlcv)} bars -> {len(features)} usable feature rows after warmup.")

    if args.mode == "walk_forward":
        report = run_walk_forward_mode(features, cfg)
    else:
        report = run_single_split(features, cfg)

    if args.out:
        with open(args.out, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nWrote report to {args.out}")


if __name__ == "__main__":
    main()
