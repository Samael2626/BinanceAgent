"""Offline historical data loader for the validation harness.

Downloads 5m klines from Binance PUBLIC endpoints (no API keys needed),
caches them as parquet, and is resumable: re-running only fetches what's
missing. After the first download everything else in the harness is offline.
"""
from __future__ import annotations

import os
import sys
import datetime as dt

import pandas as pd
from binance.client import Client

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
    "XRPUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT",
]

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TIMEFRAME = "5m"
START = "2024-06-01"
END = "2026-06-29"

COLS = ["open_time", "open", "high", "low", "close", "volume"]


def _path(symbol: str, tf: str = TIMEFRAME) -> str:
    return os.path.join(DATA_DIR, f"{symbol}_{tf}.pkl")


def download_symbol(client: Client, symbol: str, tf: str = TIMEFRAME,
                    start: str = START, end: str = END) -> pd.DataFrame:
    """Fetch klines for one symbol via python-binance paginated helper."""
    raw = client.get_historical_klines(symbol, tf, start, end)
    if not raw:
        raise RuntimeError(f"no klines for {symbol}")
    df = pd.DataFrame(raw, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "qav", "trades", "tbb", "tbq", "ignore",
    ])
    df = df[COLS].copy()
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.drop_duplicates("open_time").reset_index(drop=True)
    return df


def load(symbol: str, tf: str = TIMEFRAME) -> pd.DataFrame:
    """Load a cached symbol from parquet (offline)."""
    p = _path(symbol, tf)
    if not os.path.exists(p):
        raise FileNotFoundError(f"missing cache: {p} (run data_loader first)")
    df = pd.read_pickle(p)
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    return df


def load_all(tf: str = TIMEFRAME) -> dict[str, pd.DataFrame]:
    return {s: load(s, tf) for s in SYMBOLS}


def main() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    client = Client()  # public
    for s in SYMBOLS:
        p = _path(s)
        if os.path.exists(p):
            df = pd.read_pickle(p)
            print(f"[cache] {s:9s} {len(df):>7,} rows  {df['open_time'].iloc[0]} -> {df['open_time'].iloc[-1]}")
            continue
        t0 = dt.datetime.now()
        df = download_symbol(client, s)
        df.to_pickle(p)
        dur = (dt.datetime.now() - t0).total_seconds()
        print(f"[dl]    {s:9s} {len(df):>7,} rows  {df['open_time'].iloc[0]} -> {df['open_time'].iloc[-1]}  ({dur:.0f}s)")
        sys.stdout.flush()
    print("Download complete.")


if __name__ == "__main__":
    main()
