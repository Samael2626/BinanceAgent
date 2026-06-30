"""Offline historical data loader for the validation harness.

Downloads klines from Binance PUBLIC endpoints (no API keys needed),
caches them as pickle, and is resumable: re-running only fetches what's
missing. After the first download everything else in the harness is offline.

Supports multiple timeframes (5m default, 1h for maker variant).
Call: python -m harness.data_loader           # downloads 5m (original)
      python -m harness.data_loader --tf 1h   # downloads 1h for maker variant
"""
from __future__ import annotations

import argparse
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
# 1h variant: 24 months (2024-06 -> 2026-06), same window as 5m
START_1H = "2024-06-01"
END_1H   = "2026-06-29"
START = "2024-06-01"
END = "2026-06-29"

COLS = ["open_time", "open", "high", "low", "close", "volume"]


def _path(symbol: str, tf: str = TIMEFRAME) -> str:
    return os.path.join(DATA_DIR, f"{symbol}_{tf}.pkl")


def download_symbol(client: Client, symbol: str, tf: str = TIMEFRAME,
                    start: str = START, end: str = END) -> pd.DataFrame:
    """Fetch klines for one symbol via python-binance paginated helper.

    python-binance get_historical_klines() IS paginated internally (unlike
    binance_wrapper.get_historical_klines which is a single shot). Safe for
    long date ranges.
    """
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
    """Load a cached symbol from pickle (offline)."""
    p = _path(symbol, tf)
    if not os.path.exists(p):
        raise FileNotFoundError(f"missing cache: {p} (run data_loader --tf {tf} first)")
    df = pd.read_pickle(p)
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    return df


def load_all(tf: str = TIMEFRAME) -> dict[str, pd.DataFrame]:
    return {s: load(s, tf) for s in SYMBOLS}


def main(tf: str = TIMEFRAME, start: str = START, end: str = END) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    client = Client()  # public endpoints, no API key needed
    for s in SYMBOLS:
        p = _path(s, tf)
        if os.path.exists(p):
            df = pd.read_pickle(p)
            print(f"[cache] {s:9s} {len(df):>7,} rows  {df['open_time'].iloc[0]} -> {df['open_time'].iloc[-1]}  tf={tf}")
            continue
        t0 = dt.datetime.now()
        df = download_symbol(client, s, tf, start, end)
        df.to_pickle(p)
        dur = (dt.datetime.now() - t0).total_seconds()
        print(f"[dl]    {s:9s} {len(df):>7,} rows  {df['open_time'].iloc[0]} -> {df['open_time'].iloc[-1]}  tf={tf}  ({dur:.0f}s)")
        sys.stdout.flush()
    print(f"Download complete (tf={tf}).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default=TIMEFRAME,
                    help="Timeframe to download (e.g. 5m, 1h). Default: 5m")
    ap.add_argument("--start", default=None, help="Start date YYYY-MM-DD (default by tf)")
    ap.add_argument("--end",   default=None, help="End date   YYYY-MM-DD (default by tf)")
    args = ap.parse_args()

    # Default date range per timeframe
    if args.tf == "1h":
        s, e = START_1H, END_1H
    else:
        s, e = START, END
    if args.start:
        s = args.start
    if args.end:
        e = args.end

    main(args.tf, s, e)
