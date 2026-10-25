"""Lectura y descarga verificable de velas de Futuros USDⓈ-M públicas de Binance (`data.binance.vision`)."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from dataclasses import dataclass
from datetime import datetime
import hashlib
import io
from pathlib import Path
from typing import Iterator
import zipfile

from harness.spot_data import _fetch, months_between, monthly_name, parse_timestamp


FUTURES_UM_BASE_URL = "https://data.binance.vision/data/futures/um/monthly/klines"


@dataclass(frozen=True)
class FuturesBar:
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float


def parse_futures_bar(row: list[str]) -> FuturesBar:
    if len(row) < 8:
        raise ValueError(f"vela Futures incompleta: {len(row)} columnas")
    opened, high, low, closed = map(float, (row[1], row[2], row[3], row[4]))
    vol = float(row[5])
    qvol = float(row[7])
    if not (low <= opened <= high and low <= closed <= high and vol >= 0 and qvol >= 0):
        raise ValueError("vela Futures OHLCV invalida")
    return FuturesBar(parse_timestamp(row[0]), opened, high, low, closed, vol, qvol)


def download_futures_month(symbol: str, interval: str, year: int, month: int, target_dir: Path) -> Path:
    name = monthly_name(symbol, interval, year, month)
    target = target_dir / "futures_um" / symbol / interval / name
    url = f"{FUTURES_UM_BASE_URL}/{symbol}/{interval}/{name}"
    expected = _fetch(f"{url}.CHECKSUM", timeout=30).decode("ascii").split()[0].lower()
    if len(expected) != 64:
        raise ValueError(f"checksum Futures invalido: {name}")
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
        return target
    data = _fetch(url, timeout=120)
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"checksum Futures no coincide: {name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(".tmp")
    temp.write_bytes(data)
    temp.replace(target)
    return target


def iter_futures_bars(path: Path) -> Iterator[FuturesBar]:
    with zipfile.ZipFile(path) as archive:
        csv_files = [name for name in archive.namelist() if name.endswith(".csv")]
        if len(csv_files) != 1:
            raise ValueError(f"archivo Futures ambiguo: {path}")
        with archive.open(csv_files[0]) as stream:
            rows = csv.reader(io.TextIOWrapper(stream, encoding="utf-8"))
            previous: datetime | None = None
            for row in rows:
                if not row or not row[0][0].isdigit():
                    continue
                bar = parse_futures_bar(row)
                if previous is not None and bar.open_time <= previous:
                    raise ValueError(f"velas Futures desordenadas o duplicadas: {path}")
                previous = bar.open_time
                yield bar


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", required=True)
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--start", required=True, help="YYYY-MM")
    parser.add_argument("--end", required=True, help="YYYY-MM")
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    jobs = [
        (symbol, year, month)
        for year, month in months_between(args.start, args.end)
        for symbol in args.symbols
    ]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [
            pool.submit(download_futures_month, symbol, args.interval, year, month, args.data_dir)
            for symbol, year, month in jobs
        ]
        for future in as_completed(futures):
            path = future.result()
            count = sum(1 for _ in iter_futures_bars(path))
            print(f"{path}: {count} velas Futures verificadas", flush=True)


if __name__ == "__main__":
    main()
