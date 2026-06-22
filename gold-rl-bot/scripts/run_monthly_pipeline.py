"""Real-data backtest at monthly resolution, using the World Bank gold series.

This exists alongside `run_pipeline.py` (which uses Yahoo Finance hourly
data) because Yahoo Finance is unreachable from some sandboxed/firewalled
environments. The World Bank "Pink Sheet" monthly series is hosted on GitHub
and reachable wherever `raw.githubusercontent.com` is, so this script is the
fallback that can produce a genuine real-data (not synthetic) result even
there. Monthly resolution is a real tradeoff: far fewer bars, so weaker
statistics and slower-reacting features than the hourly pipeline -- this is
not a substitute for `run_pipeline.py --source real`, just the option that
works when Yahoo Finance doesn't.

Usage:
    python scripts/run_monthly_pipeline.py
    python scripts/run_monthly_pipeline.py --split-date 2023-01-01 --out report.json
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from goldbot.data.loader import fetch_gold_monthly_worldbank
from goldbot.features.monthly import build_monthly_features
from goldbot.features.scaler import FeatureScaler, scalable_columns
from goldbot.training.train import train_ppo
from goldbot.backtest.backtester import run_backtest, sb3_policy, buy_and_hold_policy
from goldbot.backtest.stress_tests import monte_carlo_bootstrap, null_distribution_test, seed_sensitivity

BARS_PER_YEAR = 12


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", default="1971-01-01", help="drop the fixed-peg pre-float era")
    parser.add_argument("--split-date", default="2023-01-01", help="train < this date, test >= this date")
    parser.add_argument("--window-size", type=int, default=12)
    parser.add_argument("--cost-bps", type=float, default=2.0)
    parser.add_argument("--total-timesteps", type=int, default=50_000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--n-random-policies", type=int, default=200)
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    gold = fetch_gold_monthly_worldbank(use_cache=not args.no_cache)
    gold = gold.loc[args.start_date:]
    print(f"Loaded {len(gold)} real monthly gold prices, {gold.index.min().date()} -> {gold.index.max().date()}")

    features = build_monthly_features(gold["close"]).dropna()
    train_df = features.loc[: pd.Timestamp(args.split_date) - pd.Timedelta(days=1)]
    test_df = features.loc[args.split_date :]
    print(
        f"Train: {len(train_df)} months ({train_df.index.min().date()} -> {train_df.index.max().date()})\n"
        f"Test:  {len(test_df)} months ({test_df.index.min().date()} -> {test_df.index.max().date()})"
    )

    cols = scalable_columns(features)
    scaler = FeatureScaler(cols).fit(train_df)
    train_scaled, test_scaled = scaler.transform(train_df), scaler.transform(test_df)

    def train_fn(train_features, seed):
        return train_ppo(
            train_features,
            window_size=args.window_size,
            cost_bps=args.cost_bps,
            total_timesteps=args.total_timesteps,
            seed=seed,
        )

    model = train_fn(train_scaled, args.seed)

    rl_result = run_backtest(
        test_scaled, sb3_policy(model),
        window_size=args.window_size, cost_bps=args.cost_bps, bars_per_year=BARS_PER_YEAR,
    )
    bh_result = run_backtest(
        test_scaled, buy_and_hold_policy(),
        window_size=args.window_size, cost_bps=args.cost_bps, bars_per_year=BARS_PER_YEAR,
    )
    real_bh_pct = (gold["close"].loc[args.split_date:].iloc[-1] / gold["close"].loc[args.split_date:].iloc[0] - 1) * 100

    print(f"\n=== RL policy, real OOS monthly backtest ({args.split_date} onward) ===")
    print(json.dumps(rl_result.metrics.to_dict(), indent=2))

    print("\n=== Buy-and-hold, same OOS window (env-modeled, includes cost_bps) ===")
    print(json.dumps(bh_result.metrics.to_dict(), indent=2))
    print(f"\nRaw price buy-and-hold (no costs, no window warmup loss): {real_bh_pct:.2f}%")

    print("\n=== Stress test: Monte Carlo bootstrap of realized trades ===")
    mc = monte_carlo_bootstrap(rl_result.trade_log, n_sims=2000)
    print(json.dumps(mc, indent=2))

    print("\n=== Stress test: vs random-policy / buy-and-hold null distribution ===")
    null = null_distribution_test(
        test_scaled, rl_result.metrics.sharpe,
        window_size=args.window_size, cost_bps=args.cost_bps, bars_per_year=BARS_PER_YEAR,
        n_random=args.n_random_policies,
    )
    print(json.dumps(null, indent=2))

    print("\n=== Stress test: seed sensitivity (retrain, same data) ===")
    ss = seed_sensitivity(
        train_fn, sb3_policy, train_scaled, test_scaled,
        window_size=args.window_size, cost_bps=args.cost_bps, bars_per_year=BARS_PER_YEAR,
        seeds=tuple(args.seeds),
    )
    print(json.dumps(ss, indent=2))

    report = {
        "data_source": "World Bank monthly gold price (real)",
        "train_range": [str(train_df.index.min().date()), str(train_df.index.max().date())],
        "test_range": [str(test_df.index.min().date()), str(test_df.index.max().date())],
        "rl_policy": rl_result.metrics.to_dict(),
        "buy_and_hold_env_modeled": bh_result.metrics.to_dict(),
        "buy_and_hold_raw_price_pct": round(real_bh_pct, 2),
        "monte_carlo": mc,
        "null_distribution": null,
        "seed_sensitivity": ss,
    }
    if args.out:
        with open(args.out, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nWrote report to {args.out}")


if __name__ == "__main__":
    main()
