"""Replay cronologico Futures; nunca emite autorizacion para REAL por si solo."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Mapping

import pandas as pd

from backend.risk import calculate_native_futures_stop
from backend.strategies.kronos_quant import KronosQuantStrategy
from harness.gate import GateResult, assess_backtest
from harness.metrics import compute, Metrics

HOLDOUT_START = pd.Timestamp("2026-07-01", tz="UTC")
HOLDOUT_END = pd.Timestamp("2026-10-25", tz="UTC")
INITIAL_EQUITY = 47.0
MAX_NOTIONAL = 20.0
LEVERAGE = 2
TAKER_FEE = 0.0005
STRESS_SLIPPAGE = 0.0004
RESERVE_USDT = 0.10


@dataclass(frozen=True)
class Signal:
    symbol: str
    side: str
    ev_bps: float
    atr: float
    tp_pct: float
    sl_pct: float
    indicators: dict
    settings: dict


@dataclass(frozen=True)
class ContractFilter:
    step_size: str
    min_qty: str
    min_notional: str
    tick_size: str = "0.01"


@dataclass
class Position:
    signal: Signal
    entry_time: pd.Timestamp
    entry_price: float
    qty: float
    margin: float
    entry_fee: float
    stop_price: float
    tp_price: float
    high: float
    low: float
    funding: float = 0.0


def _fill(price: float, side: str) -> float:
    return price * (1.0 + STRESS_SLIPPAGE * (1 if side == "BUY" else -1))


def _quantity(notional: float, price: float, contract: ContractFilter) -> float:
    step = Decimal(contract.step_size)
    raw = Decimal(str(notional)) / Decimal(str(price))
    qty = (raw / step).to_integral_value(rounding=ROUND_DOWN) * step
    if qty < Decimal(contract.min_qty) or qty * Decimal(str(price)) < Decimal(contract.min_notional):
        return 0.0
    return float(qty)


def choose_signal(signals: list[Signal]) -> Signal | None:
    valid = [s for s in signals if s.side in {"LONG", "SHORT"} and s.ev_bps > 0]
    return sorted(valid, key=lambda s: (-s.ev_bps, s.symbol))[0] if valid else None


def assess_live_gate(
    result: Metrics,
    *,
    random_p95: float | None = None,
    historical_microstructure_verified: bool = False,
    historical_filters_verified: bool = False,
    production_parity_verified: bool = False,
    auditor_approved: bool = False,
) -> GateResult:
    statistical = assess_backtest(result, random_p95)
    reasons = list(statistical.reasons)
    for verified, reason in (
        (historical_microstructure_verified, "faltan snapshots historicos de microestructura"),
        (historical_filters_verified, "faltan filtros Futures historicos"),
        (production_parity_verified, "paridad bot-replay sin verificar"),
        (auditor_approved, "OK auditor pendiente"),
    ):
        if not verified:
            reasons.append(reason)
    return GateResult(not reasons, tuple(reasons))


def replay(
    minute_bars: Mapping[str, pd.DataFrame],
    funding_rates: Mapping[str, pd.DataFrame],
    contracts: Mapping[str, ContractFilter],
    signals_by_close: Mapping[pd.Timestamp, list[Signal]],
    *,
    start: pd.Timestamp = HOLDOUT_START,
    end: pd.Timestamp = HOLDOUT_END,
) -> tuple[list[dict], list[dict], Metrics]:
    """Una billetera y posicion. Senal al cierre; entrada al primer minuto siguiente."""
    if not contracts or set(minute_bars) != set(contracts) or set(funding_rates) != set(contracts):
        raise ValueError("universo Futures incompleto")
    bars = {}
    funding = {}
    for symbol in sorted(contracts):
        frame = minute_bars[symbol].copy()
        times = pd.DatetimeIndex(pd.to_datetime(frame["open_time"], utc=True))
        expected = pd.date_range(start, end, freq="1min", inclusive="left")
        if not times.equals(expected):
            raise ValueError(f"velas 1m incompletas o desordenadas: {symbol}")
        bars[symbol] = frame.set_index("open_time")
        rates = funding_rates[symbol]
        funding[symbol] = {
            pd.Timestamp(row.time): (float(row.rate), float(row.mark_price))
            for row in rates.itertuples()
        }
    wallet = INITIAL_EQUITY
    position: Position | None = None
    loss_streak = 0
    halted = False
    trades: list[dict] = []
    curve: list[dict] = []
    strategy = KronosQuantStrategy()
    for timestamp in pd.date_range(start, end, freq="1min", inclusive="left"):
        if position is None and timestamp.minute == 0 and not halted:
            signal = choose_signal(signals_by_close.get(timestamp, []))
            if signal is not None:
                if signal.symbol not in contracts:
                    raise ValueError(f"simbolo sin filtro Futures: {signal.symbol}")
                row = bars[signal.symbol].loc[timestamp]
                entry_side = "BUY" if signal.side == "LONG" else "SELL"
                fill = _fill(float(row.open), entry_side)
                notional = min(MAX_NOTIONAL, wallet * LEVERAGE * 0.35)
                qty = _quantity(notional, fill, contracts[signal.symbol])
                actual_notional = qty * fill
                margin = actual_notional / LEVERAGE
                fee = actual_notional * TAKER_FEE
                if qty > 0 and margin + fee + RESERVE_USDT <= wallet:
                    stop = calculate_native_futures_stop(
                        fill, signal.atr,
                        float(signal.settings.get("stop_loss_pct", 1.5)),
                        float(signal.settings.get("atr_stop_mult", 1.6)), signal.side,
                    )
                    tick = Decimal(contracts[signal.symbol].tick_size)
                    stop = float((Decimal(str(stop)) / tick).to_integral_value(rounding=ROUND_DOWN) * tick)
                    tp = fill * (1 + signal.tp_pct / 100 * (1 if signal.side == "LONG" else -1))
                    wallet -= margin + fee
                    position = Position(signal, timestamp, fill, qty, margin, fee, stop, tp, fill, fill)
        if position is not None:
            p = position
            row = bars[p.signal.symbol].loc[timestamp]
            close_side = "SELL" if p.signal.side == "LONG" else "BUY"
            is_long = p.signal.side == "LONG"
            rate = funding[p.signal.symbol].get(timestamp)
            if rate is not None:
                funding_rate, mark_price = rate
                cashflow = p.qty * mark_price * funding_rate * (-1 if is_long else 1)
                p.funding += cashflow
                wallet += cashflow
            stop_hit = float(row.low) <= p.stop_price if is_long else float(row.high) >= p.stop_price
            tp_hit = float(row.high) >= p.tp_price if is_long else float(row.low) <= p.tp_price
            reason = ""
            exit_mid = 0.0
            if stop_hit:
                exit_mid = min(float(row.open), p.stop_price) if is_long else max(float(row.open), p.stop_price)
                reason = "NATIVE_STOP"
            elif tp_hit:
                exit_mid = p.tp_price
                reason = "TAKE_PROFIT"
            else:
                p.high = max(p.high, float(row.high))
                p.low = min(p.low, float(row.low))
                bars_held = int((timestamp - p.entry_time).total_seconds() // 3600)
                state = {
                    "position_side": p.signal.side, "current_price": float(row.close),
                    "entry_price": p.entry_price, "highest_price": p.high,
                    "lowest_price": p.low, "bars_held": bars_held,
                }
                if strategy.check_sell_signal(p.signal.indicators, p.signal.settings, state):
                    exit_mid = float(row.close)
                    reason = "DYNAMIC_EXIT"
            if reason:
                exit_fill = _fill(exit_mid, close_side)
                exit_fee = p.qty * exit_fill * TAKER_FEE
                gross = p.qty * (exit_fill - p.entry_price) * (1 if is_long else -1)
                pnl = gross - p.entry_fee - exit_fee + p.funding
                wallet += p.margin + gross - exit_fee
                trades.append({
                    "symbol": p.signal.symbol, "side": p.signal.side,
                    "entry_time": p.entry_time, "exit_time": timestamp,
                    "entry_price": p.entry_price, "exit_price": exit_fill,
                    "net_pnl": pnl, "net_return_pct": pnl / p.margin * 100,
                    "reason": reason, "funding": p.funding,
                })
                position = None
                loss_streak = loss_streak + 1 if pnl < 0 else 0
                halted = loss_streak >= int(p.signal.settings.get("max_consecutive_losses", 3))
        if timestamp.minute == 59:
            equity = wallet
            if position is not None:
                p = position
                price = float(bars[p.signal.symbol].loc[timestamp].close)
                equity += p.margin + p.qty * (price - p.entry_price) * (1 if p.signal.side == "LONG" else -1)
            curve.append({"time": timestamp, "equity": equity})
    if position is not None:
        raise ValueError(f"posicion abierta al final del holdout: {position.signal.symbol}")
    return trades, curve, compute(trades, curve, INITIAL_EQUITY)
