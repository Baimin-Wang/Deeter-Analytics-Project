"""Download and cache daily OHLCV data from Yahoo's public chart endpoint."""

from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd
import numpy as np


def validate_bars(frame: pd.DataFrame) -> pd.DataFrame:
    """Reject malformed bars instead of silently treating missing sessions as a pause."""
    frame = frame.copy()
    frame.index = pd.DatetimeIndex(frame.index).tz_localize(None).normalize()
    frame = frame.sort_index()
    values = frame[["open", "high", "low", "close", "volume"]]
    if frame.index.has_duplicates or values.isna().any().any():
        raise ValueError("Duplicate dates or missing OHLCV")
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError("Non-finite OHLCV")
    if (values[["open", "high", "low", "close"]] <= 0).any().any() or (frame["volume"] < 0).any():
        raise ValueError("Invalid prices or negative volume")
    if ((frame["high"] < frame[["open", "close", "low"]].max(axis=1)) |
        (frame["low"] > frame[["open", "close", "high"]].min(axis=1))).any():
        raise ValueError("Inconsistent OHLC bounds")
    return frame


def _unix(ts: pd.Timestamp) -> int:
    return int(ts.tz_localize("UTC").timestamp())


def download_symbol(
    ticker: str,
    start: str,
    end: str,
    cache_dir: str | Path = "data/cache",
    pause_seconds: float = 0.15,
    offline: bool = False,
) -> pd.DataFrame:
    """Return a cached or downloaded daily OHLCV frame indexed by date."""
    cache_path = Path(cache_dir) / f"{ticker.replace('/', '_')}.csv"
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists():
        cached = pd.read_csv(cache_path, parse_dates=["date"], index_col="date")
        cached = validate_bars(cached)
        if offline or (not cached.empty and cached.index.max() >= pd.Timestamp(end) - pd.Timedelta(days=3)):
            return cached.loc[pd.Timestamp(start):pd.Timestamp(end)].copy()

    if offline:
        raise FileNotFoundError(f"Offline cache missing: {cache_path}")

    period1 = _unix(pd.Timestamp(start))
    period2 = _unix(pd.Timestamp(end) + pd.Timedelta(days=2))
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(ticker)}"
        f"?period1={period1}&period2={period2}&interval=1d&events=history"
    )
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    result = (payload.get("chart", {}).get("result") or [None])[0]
    if result is None:
        raise RuntimeError(f"No Yahoo Finance data returned for {ticker}")

    timestamps = result.get("timestamp", [])
    quote_data = result.get("indicators", {}).get("quote", [{}])[0]
    frame = pd.DataFrame(
        {
            "open": quote_data.get("open", []),
            "high": quote_data.get("high", []),
            "low": quote_data.get("low", []),
            "close": quote_data.get("close", []),
            "volume": quote_data.get("volume", []),
        },
        index=pd.to_datetime(timestamps, unit="s", utc=True).tz_convert(None),
    )
    frame.index.name = "date"
    # Exclude today's UTC date conservatively: never use a still-forming daily bar.
    frame = frame.loc[frame.index.normalize() < pd.Timestamp.utcnow().tz_localize(None).normalize()]
    frame = validate_bars(frame)
    frame.to_csv(cache_path, date_format="%Y-%m-%d")
    time.sleep(pause_seconds)
    return frame.loc[pd.Timestamp(start):pd.Timestamp(end)].copy()


def load_universe(
    universe_path: str | Path,
    start: str,
    end: str,
    cache_dir: str | Path = "data/cache",
    symbols: list[str] | None = None,
    offline: bool = False,
) -> dict[str, pd.DataFrame]:
    universe = pd.read_csv(universe_path)
    if "ticker" not in universe.columns:
        raise ValueError(f"Universe must contain a ticker column: {universe_path}")
    tickers = universe["ticker"].astype(str).str.strip().tolist()
    if not tickers or any(not ticker for ticker in tickers):
        raise ValueError(f"Universe contains an empty ticker: {universe_path}")
    if len(set(tickers)) != len(tickers):
        raise ValueError(f"Universe contains duplicate tickers: {universe_path}")
    if symbols:
        requested = set(symbols)
        tickers = [ticker for ticker in tickers if ticker in requested]
        tickers += [ticker for ticker in symbols if ticker not in tickers]

    output: dict[str, pd.DataFrame] = {}
    failures: list[str] = []
    for ticker in tickers:
        try:
            frame = download_symbol(ticker, start, end, cache_dir=cache_dir, offline=offline)
            # The screen needs enough history for the 60-session volume and
            # 20-session ATR baselines, plus the impulse/pause window.
            if len(frame) >= 80:
                output[ticker] = frame
            else:
                failures.append(f"{ticker}: only {len(frame)} rows")
        except Exception as exc:  # keep a single bad symbol from stopping the universe
            failures.append(f"{ticker}: {exc}")
    if not output:
        raise RuntimeError(f"No symbols downloaded. Failures: {failures}")
    if failures:
        preview = failures[:20]
        print(f"Skipped symbols: {len(failures)} (showing up to 20)")
        print("\n".join(f"  {item}" for item in preview))
        if len(failures) > len(preview):
            print(f"  ... {len(failures) - len(preview)} more")
    return output
