"""Lectura y descarga verificable de velas de Futuros USDⓈ-M públicas de Binance (`data.binance.vision`)."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from dataclasses import dataclass
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
from typing import Iterator
from urllib.parse import urlencode
import zipfile

import pandas as pd

from harness.spot_data import _fetch, months_between, monthly_name, parse_timestamp


FUTURES_UM_BASE_URL = "https://data.binance.vision/data/futures/um/monthly/klines"
FUTURES_UM_DAILY_URL = "https://data.binance.vision/data/futures/um/daily/klines"
FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"


def _verified_cached(path: Path) -> bool:
    checksum_path = path.with_suffix(".sha256")
    return (
        path.exists() and checksum_path.exists()
        and hashlib.sha256(path.read_bytes()).hexdigest()
        == checksum_path.read_text(encoding="ascii").strip().split()[0].lower()
    )


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
    if _verified_cached(target):
        return target
    url = f"{FUTURES_UM_BASE_URL}/{symbol}/{interval}/{name}"
    expected = _fetch(f"{url}.CHECKSUM", timeout=30).decode("ascii").split()[0].lower()
    if len(expected) != 64:
        raise ValueError(f"checksum Futures invalido: {name}")
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
        target.with_suffix(".sha256").write_text(expected, encoding="ascii")
        return target
    data = _fetch(url, timeout=120)
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"checksum Futures no coincide: {name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(".tmp")
    temp.write_bytes(data)
    temp.replace(target)
    target.with_suffix(".sha256").write_text(expected, encoding="ascii")
    return target


def download_futures_day(symbol: str, interval: str, day: datetime, target_dir: Path) -> Path:
    name = f"{symbol}-{interval}-{day:%Y-%m-%d}.zip"
    target = target_dir / "futures_um" / symbol / interval / name
    if _verified_cached(target):
        return target
    url = f"{FUTURES_UM_DAILY_URL}/{symbol}/{interval}/{name}"
    expected = _fetch(f"{url}.CHECKSUM", timeout=30).decode("ascii").split()[0].lower()
    if len(expected) != 64:
        raise ValueError(f"checksum Futures invalido: {name}")
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
        target.with_suffix(".sha256").write_text(expected, encoding="ascii")
        return target
    data = _fetch(url, timeout=120)
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"checksum Futures no coincide: {name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(".tmp")
    temp.write_bytes(data)
    temp.replace(target)
    target.with_suffix(".sha256").write_text(expected, encoding="ascii")
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


def load_futures_klines(
    symbol: str, interval: str, start: str, end: str, data_dir: Path,
    *, download: bool = False,
) -> tuple[pd.DataFrame, list[dict]]:
    """Lee [start, end) UTC y exige una vela Futures por cada intervalo."""
    if interval not in {"1h", "1m"}:
        raise ValueError("intervalo Futures no soportado")
    if not symbol.isalnum() or not symbol.endswith("USDT"):
        raise ValueError("simbolo Futures invalido")
    begin = pd.Timestamp(start, tz="UTC")
    finish = pd.Timestamp(end, tz="UTC")
    frequency = "1min" if interval == "1m" else "1h"
    if finish <= begin or begin != begin.floor(frequency) or finish != finish.floor(frequency):
        raise ValueError("rango UTC invalido")
    paths: list[Path] = []
    for month_start in pd.date_range(begin.normalize().replace(day=1), finish - pd.Timedelta(nanoseconds=1), freq="MS"):
        month_end = month_start + pd.offsets.MonthBegin(1)
        if month_end <= finish:
            path = data_dir / "futures_um" / symbol / interval / monthly_name(symbol, interval, month_start.year, month_start.month)
            if download:
                path = download_futures_month(symbol, interval, month_start.year, month_start.month, data_dir)
            paths.append(path)
        else:
            for day in pd.date_range(max(month_start, begin.normalize()), (finish - pd.Timedelta(nanoseconds=1)).normalize(), freq="D"):
                path = data_dir / "futures_um" / symbol / interval / f"{symbol}-{interval}-{day:%Y-%m-%d}.zip"
                if download:
                    path = download_futures_day(symbol, interval, day.to_pydatetime(), data_dir)
                paths.append(path)
    rows: list[FuturesBar] = []
    provenance: list[dict] = []
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"faltan velas Futures {path}")
        checksum_path = path.with_suffix(".sha256")
        if not checksum_path.exists():
            raise FileNotFoundError(f"falta checksum Futures {checksum_path}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != checksum_path.read_text(encoding="ascii").strip().split()[0].lower():
            raise ValueError(f"checksum Futures no coincide: {path}")
        provenance.append({"path": str(path), "sha256": digest})
        rows.extend(bar for bar in iter_futures_bars(path) if begin <= bar.open_time < finish)
    expected = pd.date_range(begin, finish, freq=frequency, inclusive="left")
    actual = pd.DatetimeIndex([bar.open_time for bar in rows])
    if not actual.equals(expected):
        mismatch = next((str(a) for a, b in zip(actual, expected) if a != b), "longitud")
        raise ValueError(f"cobertura Futures {symbol} {interval} incompleta o desordenada: {mismatch}; {len(actual)}/{len(expected)}")
    frame = pd.DataFrame([{
        "open_time": bar.open_time, "open": bar.open, "high": bar.high,
        "low": bar.low, "close": bar.close, "volume": bar.volume,
        "quote_asset_volume": bar.quote_volume,
    } for bar in rows])
    return frame, provenance


def load_funding_rates(
    symbol: str, start: str, end: str, data_dir: Path, *, download: bool = False,
) -> tuple[pd.DataFrame, dict]:
    begin = pd.Timestamp(start, tz="UTC")
    finish = pd.Timestamp(end, tz="UTC")
    path = data_dir / "futures_um" / symbol / f"funding-{begin:%Y%m%d}-{finish:%Y%m%d}.json"
    if download:
        if not symbol.isalnum() or not symbol.endswith("USDT"):
            raise ValueError("simbolo Futures invalido")
        cursor = int((begin - pd.Timedelta(hours=8)).timestamp() * 1000)
        final = int(finish.timestamp() * 1000)
        records = []
        while cursor < final:
            query = urlencode({"symbol": symbol, "startTime": cursor, "endTime": final, "limit": 1000})
            batch = json.loads(_fetch(f"{FUNDING_URL}?{query}", timeout=30))
            if not batch:
                break
            records.extend(batch)
            next_cursor = int(batch[-1]["fundingTime"]) + 1
            if next_cursor <= cursor:
                raise ValueError("funding Futures sin progreso")
            cursor = next_cursor
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(records, separators=(",", ":")), encoding="utf-8")
    if not path.exists():
        raise FileNotFoundError(f"falta funding Futures {path}")
    raw = path.read_bytes()
    rows = json.loads(raw)
    frame = pd.DataFrame([{
        "raw_time": pd.to_datetime(int(row["fundingTime"]), unit="ms", utc=True),
        "rate": float(row["fundingRate"]),
        "mark_price": float(row["markPrice"]),
    } for row in rows if row.get("symbol") == symbol])
    if not frame.empty:
        frame["time"] = frame["raw_time"].dt.floor("min")
        if ((frame["raw_time"] - frame["time"]) >= pd.Timedelta(minutes=1)).any():
            raise ValueError(f"funding Futures {symbol} fuera del minuto de liquidacion")
    if frame.empty or not frame["time"].is_monotonic_increasing or frame["time"].duplicated().any():
        raise ValueError(f"funding Futures {symbol} vacio, duplicado o desordenado")
    if frame["time"].iloc[0] > begin or frame["time"].iloc[-1] < finish - pd.Timedelta(hours=8):
        raise ValueError(f"funding Futures {symbol} sin cobertura")
    if (frame["time"].diff().dropna() > pd.Timedelta(hours=8)).any():
        raise ValueError(f"funding Futures {symbol} con huecos")
    return frame[(frame["time"] >= begin) & (frame["time"] < finish)].reset_index(drop=True), {
        "path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "source": FUNDING_URL,
    }


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
