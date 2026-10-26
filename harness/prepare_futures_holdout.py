"""Descarga y verifica el holdout Futures; no ejecuta operaciones."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path

from harness.futures_data import load_futures_klines, load_funding_rates

SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "LINKUSDT", "AVAXUSDT", "BNBUSDT")
HOLDOUT_START = "2026-07-01"
HOLDOUT_END = "2026-10-25"
WARMUP_START = "2026-06-01"


def prepare(data_dir: Path, *, download: bool = False) -> dict:
    jobs = [(symbol, "1h", WARMUP_START, HOLDOUT_END) for symbol in SYMBOLS]
    jobs += [(symbol, "1m", HOLDOUT_START, HOLDOUT_END) for symbol in SYMBOLS]
    manifest = {
        "market": "BINANCE_USDM_FUTURES", "holdout_start": HOLDOUT_START,
        "holdout_end_exclusive": HOLDOUT_END, "warmup_start": WARMUP_START,
        "symbols": list(SYMBOLS), "series": {}, "funding": {},
    }
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(load_futures_klines, symbol, interval, start, end, data_dir, download=download): (symbol, interval)
            for symbol, interval, start, end in jobs
        }
        for future in as_completed(futures):
            symbol, interval = futures[future]
            frame, provenance = future.result()
            manifest["series"][f"{symbol}_{interval}"] = {
                "rows": len(frame), "first": str(frame["open_time"].iloc[0]),
                "last": str(frame["open_time"].iloc[-1]), "files": provenance,
            }
            print(f"{symbol} {interval}: {len(frame)} velas verificadas", flush=True)
    for symbol in SYMBOLS:
        funding, provenance = load_funding_rates(symbol, HOLDOUT_START, HOLDOUT_END, data_dir, download=download)
        manifest["funding"][symbol] = {"rows": len(funding), **provenance}
        print(f"{symbol} funding: {len(funding)} liquidaciones verificadas", flush=True)
    target = data_dir / "futures_um" / "holdout_manifest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("harness/data"))
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    prepare(args.data_dir, download=args.download)


if __name__ == "__main__":
    main()
