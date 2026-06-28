from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .indicators import calculate_indicators
from .predictive_modules import PredictiveEngine
from .scanner import parse_rotation_watchlist, score_rotation_candidate


@dataclass(frozen=True)
class ScannerBacktestConfig:
    symbols: list[str]
    initial_equity: float = 1000.0
    window: int = 80
    rotation_interval: int = 15
    min_rotation_score: float = 55.0
    min_market_score_to_buy: float = 45.0
    stop_loss_pct: float = 3.2
    take_profit_pct: float = 1.3
    fee_pct: float = 0.1


@dataclass
class TradeRecord:
    entry_index: int
    exit_index: int
    symbol: str
    entry_price: float
    exit_price: float
    pnl: float
    return_pct: float
    entry_score: float
    exit_reason: str


@dataclass
class ScannerBacktestResult:
    initial_equity: float
    final_equity: float
    trades: list[TradeRecord] = field(default_factory=list)
    equity_curve: list[dict[str, Any]] = field(default_factory=list)
    rotations: list[dict[str, Any]] = field(default_factory=list)

    @property
    def net_pnl(self) -> float:
        return round(self.final_equity - self.initial_equity, 2)

    @property
    def return_pct(self) -> float:
        if self.initial_equity <= 0:
            return 0.0
        return round((self.net_pnl / self.initial_equity) * 100.0, 2)

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if t.pnl > 0)
        return round((wins / len(self.trades)) * 100.0, 2)

    @property
    def profit_factor(self) -> float:
        gross_profit = sum(t.pnl for t in self.trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in self.trades if t.pnl < 0))
        if gross_loss <= 0:
            return round(gross_profit, 2)
        return round(gross_profit / gross_loss, 2)

    @property
    def max_drawdown_pct(self) -> float:
        if not self.equity_curve:
            return 0.0
        peak = self.initial_equity
        max_dd = 0.0
        for point in self.equity_curve:
            equity = float(point.get("equity", peak))
            if equity > peak:
                peak = equity
            drawdown = ((peak - equity) / peak) * 100.0 if peak > 0 else 0.0
            if drawdown > max_dd:
                max_dd = drawdown
        return round(max_dd, 2)


def run_scanner_backtest(
    market_data: dict[str, pd.DataFrame],
    config: ScannerBacktestConfig,
) -> ScannerBacktestResult:
    symbols = parse_rotation_watchlist(config.symbols)
    usable = {
        symbol: df.reset_index(drop=True)
        for symbol, df in market_data.items()
        if symbol in symbols and len(df) > config.window
    }
    if not usable:
        return ScannerBacktestResult(config.initial_equity, config.initial_equity)

    max_steps = min(len(df) for df in usable.values())
    engine = PredictiveEngine()
    equity = float(config.initial_equity)
    active_symbol = symbols[0] if symbols[0] in usable else next(iter(usable))
    position_qty = 0.0
    entry_price = 0.0
    entry_index = 0
    entry_score = 0.0
    highest_price = 0.0
    trades: list[TradeRecord] = []
    curve: list[dict[str, Any]] = []
    rotations: list[dict[str, Any]] = []

    for idx in range(config.window, max_steps):
        current_price = float(usable[active_symbol].iloc[idx]["close"])

        if position_qty > 0:
            highest_price = max(highest_price, current_price)
            stop_price = entry_price * (1 - config.stop_loss_pct / 100.0)
            take_price = entry_price * (1 + config.take_profit_pct / 100.0)
            should_sell = current_price <= stop_price or current_price >= take_price
            if should_sell:
                gross = position_qty * current_price
                fee = gross * (config.fee_pct / 100.0)
                equity = gross - fee
                pnl = equity - config.initial_equity if len(trades) == 0 else equity - trades[-1].equity_after
                return_pct = ((current_price - entry_price) / entry_price) * 100.0 if entry_price > 0 else 0.0
                exit_reason = "SL" if current_price <= stop_price else "TP"
                trades.append(
                    TradeRecord(
                        entry_index=entry_index,
                        exit_index=idx,
                        symbol=active_symbol,
                        entry_price=entry_price,
                        exit_price=current_price,
                        pnl=round(pnl, 2),
                        return_pct=round(return_pct, 2),
                        entry_score=entry_score,
                        exit_reason=exit_reason,
                    )
                )
                position_qty = 0.0
                entry_price = 0.0
                entry_index = 0
                entry_score = 0.0
                highest_price = 0.0

        if position_qty == 0 and idx % max(config.rotation_interval, 1) == 0:
            scored: list[tuple[str, float, float]] = []
            for symbol, df in usable.items():
                frame = df.iloc[idx - config.window : idx].copy()
                indicators = calculate_indicators(frame, {})
                price = float(frame.iloc[-1]["close"])
                prediction = engine.analyze(frame, price)
                score = score_rotation_candidate(prediction, indicators)
                market_score = float(prediction.get("market_score", 50) or 50)
                scored.append((symbol, score, market_score))

            scored.sort(key=lambda item: item[1], reverse=True)
            best_symbol, best_score, best_market_score = scored[0]
            if best_symbol != active_symbol and best_score >= config.min_rotation_score:
                rotations.append(
                    {
                        "index": idx,
                        "from": active_symbol,
                        "to": best_symbol,
                        "score": best_score,
                    }
                )
                active_symbol = best_symbol
                current_price = float(usable[active_symbol].iloc[idx]["close"])

            if best_score >= config.min_rotation_score and best_market_score >= config.min_market_score_to_buy:
                fee = equity * (config.fee_pct / 100.0)
                spend = equity - fee
                position_qty = spend / current_price
                entry_price = current_price
                entry_index = idx
                entry_score = best_score
                highest_price = current_price
                trades.append(
                    {
                        "type": "BUY",
                        "symbol": active_symbol,
                        "index": idx,
                        "price": current_price,
                        "score": best_score,
                        "equity_after": round(equity, 2),
                    }
                )

        mark_to_market = equity if position_qty == 0 else position_qty * current_price
        curve.append(
            {
                "index": idx,
                "symbol": active_symbol,
                "equity": round(mark_to_market, 2),
            }
        )

    closes = {symbol: float(df["close"].iloc[-1]) for symbol, df in usable.items()}
    final_price = closes.get(active_symbol, config.initial_equity)
    final_equity = equity if position_qty == 0 else position_qty * final_price

    return ScannerBacktestResult(
        initial_equity=config.initial_equity,
        final_equity=round(final_equity, 2),
        trades=trades,
        equity_curve=curve,
        rotations=rotations,
    )
