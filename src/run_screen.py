"""CLI for the latest-close screen."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .data import load_universe
from .screen import build_features, screen_asof, load_rules, DEFAULT_RULES_PATH


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="outputs/latest_screen.csv")
    parser.add_argument("--symbols", nargs="*", default=None)
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--offline", action="store_true", help="Read cached data without network or refresh")
    parser.add_argument("--universe", default=str(Path(__file__).resolve().parents[1] / "config/universe.csv"))
    parser.add_argument("--rules", default=str(DEFAULT_RULES_PATH))
    args = parser.parse_args()

    end = args.end or (pd.Timestamp.utcnow() - pd.Timedelta(days=1)).date().isoformat()
    universe_path = Path(args.universe)
    data = load_universe(universe_path, args.start, end, symbols=args.symbols, offline=args.offline)
    rules = load_rules(args.rules)
    features = build_features(data, rules)
    asof = max(frame.index.max() for frame in features.values())
    # Only use symbols that have the common as-of date.
    available = {ticker: frame for ticker, frame in features.items() if asof in frame.index}
    result = screen_asof(features, asof, rules)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    requested_size = len(pd.read_csv(universe_path)) if not args.symbols else len(args.symbols)
    print(f"As of {asof.date()} | requested_symbols={requested_size} | loaded_symbols={len(available)} | setups={len(result)}")
    if result.empty:
        print("No qualifying setups.")
    else:
        print(result[["ticker", "direction", "lean", "continuation_level", "failure_level", "reason"]].to_string(index=False))
        print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
