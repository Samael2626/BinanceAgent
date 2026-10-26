"""Ejecuta el holdout cronologico; cualquier dato historico faltante deja gate rojo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from backend.services.kronos_adapter import KronosAdapter
from harness.futures_data import load_futures_klines, load_funding_rates
from harness.futures_replay import (
    ContractFilter, HOLDOUT_END, HOLDOUT_START, assess_live_gate, replay,
)
from harness.futures_signals import build_signals
from harness.prepare_futures_holdout import SYMBOLS, WARMUP_START


def load_snapshots(path: Path) -> dict[tuple[pd.Timestamp, str], dict]:
    if not path.exists():
        raise FileNotFoundError(f"faltan snapshots historicos: {path}")
    snapshots = {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            key = (pd.Timestamp(item["close_time"]).tz_convert("UTC"), item["symbol"])
            observed = pd.Timestamp(item["observed_at"]).tz_convert("UTC")
            if observed > key[0] or observed < key[0] - pd.Timedelta(minutes=2):
                raise ValueError(f"snapshot Futures fuera de tiempo: {key}")
            if not item.get("source"):
                raise ValueError(f"snapshot Futures sin procedencia: {key}")
            if key in snapshots:
                raise ValueError(f"snapshot duplicado: {key}")
            snapshots[key] = item
    return snapshots


def load_contracts(path: Path) -> dict[str, ContractFilter]:
    if not path.exists():
        raise FileNotFoundError(f"faltan filtros Futures historicos: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if set(raw) != set(SYMBOLS):
        raise ValueError("filtros Futures incompletos")
    result = {}
    for symbol, item in raw.items():
        if (
            pd.Timestamp(item["valid_from"]).tz_convert("UTC") > HOLDOUT_START
            or pd.Timestamp(item["valid_until"]).tz_convert("UTC") < HOLDOUT_END
            or not item.get("source")
        ):
            raise ValueError(f"filtro Futures sin procedencia o cobertura: {symbol}")
        result[symbol] = ContractFilter(
            item["step_size"], item["min_qty"], item["min_notional"], item["tick_size"]
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("harness/data"))
    parser.add_argument("--snapshots", type=Path, default=Path("harness/data/futures_um/microstructure.jsonl"))
    parser.add_argument("--filters", type=Path, default=Path("harness/data/futures_um/historical_filters.json"))
    args = parser.parse_args()
    try:
        manifest_path = args.data_dir / "futures_um" / "holdout_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError("falta manifiesto verificado del holdout")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("holdout_start") != "2026-07-01" or manifest.get("holdout_end_exclusive") != "2026-10-25":
            raise ValueError("manifiesto de otro holdout")
        snapshots = load_snapshots(args.snapshots)
        contracts = load_contracts(args.filters)
        hourly = {}
        minute = {}
        funding = {}
        for symbol in SYMBOLS:
            hourly[symbol], hour_files = load_futures_klines(symbol, "1h", WARMUP_START, "2026-10-25", args.data_dir)
            minute[symbol], minute_files = load_futures_klines(symbol, "1m", "2026-07-01", "2026-10-25", args.data_dir)
            funding[symbol], funding_file = load_funding_rates(symbol, "2026-07-01", "2026-10-25", args.data_dir)
            if (
                hour_files != manifest["series"][f"{symbol}_1h"]["files"]
                or minute_files != manifest["series"][f"{symbol}_1m"]["files"]
                or funding_file["sha256"] != manifest["funding"][symbol]["sha256"]
            ):
                raise ValueError(f"procedencia Futures cambio tras validar: {symbol}")
        signals = build_signals(hourly, snapshots, KronosAdapter())
        trades, curve, result = replay(minute, funding, contracts, signals)
        decision = assess_live_gate(result)
        print(f"OOS stress taker: {result.row()}")
        print(f"Gate REAL: {'VERDE' if decision.passed else 'ROJO'} {decision.reasons}")
        print(f"Cierres: {len(trades)}; puntos de curva: {len(curve)}")
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        raise SystemExit(f"Gate REAL ROJO: {exc}; winrate OOS indefinido") from exc


if __name__ == "__main__":
    main()
