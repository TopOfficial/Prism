"""Fetch and cache real gold + macro data from Yahoo Finance.

Requires outbound internet access to finance.yahoo.com -- run this on your
own machine, not in a sandboxed/firewalled container. Run from the
gold-rl-bot/ directory:

    python scripts/download_data.py --period 730d --interval 1h
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from goldbot.data.loader import fetch_gold_ohlcv, fetch_macro


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", default="730d", help="yfinance period string, e.g. 730d, 5y")
    parser.add_argument("--interval", default="1h", help="bar interval, e.g. 1h, 1d")
    parser.add_argument("--no-cache", action="store_true", help="bypass on-disk cache")
    args = parser.parse_args()

    print(f"Fetching gold OHLCV (period={args.period}, interval={args.interval})...")
    gold = fetch_gold_ohlcv(period=args.period, interval=args.interval, use_cache=not args.no_cache)
    print(f"  {len(gold)} bars, {gold.index.min()} -> {gold.index.max()}")

    print("Fetching macro series (DXY, 10Y yield, VIX, oil, silver)...")
    macro = fetch_macro(period=args.period, interval="1d", use_cache=not args.no_cache)
    print(f"  {len(macro)} daily rows, columns: {list(macro.columns)}")

    print("Done. Cached under data/cache/.")


if __name__ == "__main__":
    main()
