"""Lectura y descarga verificable de velas Spot publicas de Binance."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


BASE_URL = "https://data.binance.vision/data/spot/monthly/klines"


@dataclass(frozen=True)
class SpotBar:
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


def parse_timestamp(raw: str) -> datetime:
    value = int(raw)
    divisor = 1_000_000 if value >= 100_000_000_000_000 else 1_000
    return datetime.fromtimestamp(value / divisor, tz=timezone.utc)


def parse_bar(row: list[str]) -> SpotBar:
    if len(row) < 6:
        raise ValueError(f"vela Spot incompleta: {len(row)} columnas")
    opened, high, low, closed = map(float, (row[1], row[2], row[3], row[4]))
    if not (low <= opened <= high and low <= closed <= high and float(row[5]) >= 0):
        raise ValueError("vela Spot OHLCV invalida")
    return SpotBar(parse_timestamp(row[0]), opened, high, low, closed, float(row[5]))


def monthly_name(symbol: str, interval: str, year: int, month: int) -> str:
    if not symbol.isalnum() or not interval.replace("m", "").replace("h", "").isdigit() or not 1 <= month <= 12:
        raise ValueError("simbolo o intervalo invalido")
    return f"{symbol}-{interval}-{year:04d}-{month:02d}.zip"


def _fetch(url: str, timeout: int) -> bytes:
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 3:
                raise
        except (TimeoutError, urllib.error.URLError):
            if attempt == 3:
                raise
        time.sleep(2 ** attempt)
    raise RuntimeError("descarga agotada")


def download_month(symbol: str, interval: str, year: int, month: int, target_dir: Path) -> Path:
    name = monthly_name(symbol, interval, year, month)
    target = target_dir / symbol / interval / name
    url = f"{BASE_URL}/{symbol}/{interval}/{name}"
    expected = _fetch(f"{url}.CHECKSUM", timeout=30).decode("ascii").split()[0].lower()
    if len(expected) != 64:
        raise ValueError(f"checksum invalido: {name}")
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
        return target
    data = _fetch(url, timeout=120)
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"checksum no coincide: {name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(".tmp")
    temp.write_bytes(data)
    temp.replace(target)
    return target


def iter_bars(path: Path) -> Iterator[SpotBar]:
    with zipfile.ZipFile(path) as archive:
        csv_files = [name for name in archive.namelist() if name.endswith(".csv")]
        if len(csv_files) != 1:
            raise ValueError(f"archivo Spot ambiguo: {path}")
        with archive.open(csv_files[0]) as stream:
            rows = csv.reader(io.TextIOWrapper(stream, encoding="utf-8"))
            previous: datetime | None = None
            for row in rows:
                if not row or row[0].lower() == "open_time":
                    continue
                bar = parse_bar(row)
                if previous is not None and bar.open_time <= previous:
                    raise ValueError(f"velas desordenadas o duplicadas: {path}")
                previous = bar.open_time
                yield bar


def months_between(start: str, end: str) -> Iterator[tuple[int, int]]:
    first = datetime.strptime(start, "%Y-%m")
    last = datetime.strptime(end, "%Y-%m")
    index = first.year * 12 + first.month - 1
    final = last.year * 12 + last.month - 1
    if index > final:
        raise ValueError("inicio posterior al fin")
    while index <= final:
        yield index // 12, index % 12 + 1
        index += 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", required=True)
    parser.add_argument("--interval", default="1m")
    parser.add_argument("--start", required=True, help="YYYY-MM")
    parser.add_argument("--end", required=True, help="YYYY-MM")
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    jobs = [(symbol, year, month) for year, month in months_between(args.start, args.end)
            for symbol in args.symbols]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(download_month, symbol, args.interval, year, month,
                               args.data_dir) for symbol, year, month in jobs]
        for future in as_completed(futures):
            path = future.result()
            count = sum(1 for _ in iter_bars(path))
            print(f"{path}: {count} velas verificadas", flush=True)


if __name__ == "__main__":
    main()
