"""Experimento predefinido de ruptura spot con una sola cartera."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from harness import metrics
from harness.costs import CostModel
from harness.gate import assess_backtest
from harness.spot_data import SpotBar, iter_bars, months_between, monthly_name


SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT")
TRAIN_END = datetime(2026, 7, 1, tzinfo=timezone.utc)
HOLDOUT_END = datetime(2026, 10, 1, tzinfo=timezone.utc)


@dataclass(frozen=True)
class BreakoutConfig:
    initial_cash: float = 47.0
    min_order_quote: float = 10.0
    max_position_pct: float = 25.0
    risk_per_trade_pct: float = 0.75
    stop_atr_multiple: float = 2.0
    max_drawdown_pct: float = 8.0


@dataclass
class Position:
    symbol: str
    quantity: float
    entry_price: float
    entry_basis: float
    entry_time: datetime
    highest: float
    stop: float


def load_bars(data_dir: Path, symbol: str, start: str, end: str) -> list[SpotBar]:
    bars: list[SpotBar] = []
    for year, month in months_between(start, end):
        path = data_dir / symbol / "4h" / monthly_name(symbol, "4h", year, month)
        if not path.is_file():
            raise FileNotFoundError(path)
        bars.extend(iter_bars(path))
    step = timedelta(hours=4)
    for previous, current in zip(bars, bars[1:]):
        if current.open_time - previous.open_time != step:
            raise ValueError(f"hueco 4h en {symbol}: {previous.open_time} -> {current.open_time}")
    return bars


def indicators(bars: list[SpotBar]) -> pd.DataFrame:
    frame = pd.DataFrame({
        "time": [bar.open_time for bar in bars],
        "open": [bar.open for bar in bars],
        "high": [bar.high for bar in bars],
        "low": [bar.low for bar in bars],
        "close": [bar.close for bar in bars],
    }).set_index("time")
    close = frame["close"]
    previous_close = close.shift(1)
    true_range = pd.concat([
        frame["high"] - frame["low"],
        (frame["high"] - previous_close).abs(),
        (frame["low"] - previous_close).abs(),
    ], axis=1).max(axis=1)
    frame["atr14"] = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    frame["ema50"] = close.ewm(span=50, adjust=False, min_periods=50).mean()
    frame["ema200"] = close.ewm(span=200, adjust=False, min_periods=200).mean()
    frame["prior_high20"] = frame["high"].shift(1).rolling(20, min_periods=20).max()
    return frame


class BreakoutPortfolio:
    def __init__(self, config: BreakoutConfig, costs: CostModel):
        self.config = config
        self.costs = costs
        self.cash = config.initial_cash
        self.position: Position | None = None
        self.pending_buy: str | None = None
        self.pending_sell = False
        self.peak = config.initial_cash
        self.halted = False
        self.trades: list[dict] = []
        self.curve: list[dict] = []

    def _sell(self, bar: SpotBar, exit_mid: float, reason: str) -> None:
        position = self.position
        if position is None:
            raise RuntimeError("venta sin posicion")
        fill = self.costs.fill_price(position.symbol, exit_mid, "SELL", position.quantity * exit_mid)
        proceeds = position.quantity * fill
        fee = self.costs.fee(proceeds)
        net = proceeds - fee - position.entry_basis
        self.cash += proceeds - fee
        self.trades.append({
            "symbol": position.symbol,
            "entry_time": position.entry_time,
            "exit_time": bar.open_time,
            "entry_price": position.entry_price,
            "exit_price": fill,
            "net_pnl": net,
            "net_return_pct": net / position.entry_basis * 100,
            "reason": reason,
        })
        self.position = None

    def _buy(self, symbol: str, bar: SpotBar, prior_atr: float) -> None:
        stop_distance = self.config.stop_atr_multiple * prior_atr
        if not 0 < stop_distance < bar.open:
            return
        max_stake = min(
            self.cash / (1 + self.costs.fee_pct / 100),
            self.cash * self.config.max_position_pct / 100,
            self.cash * self.config.risk_per_trade_pct / 100 * bar.open / stop_distance,
        )
        if max_stake < self.config.min_order_quote:
            return
        fill = self.costs.fill_price(symbol, bar.open, "BUY", max_stake)
        basis = max_stake + self.costs.fee(max_stake)
        self.cash -= basis
        self.position = Position(symbol, max_stake / fill, fill, basis, bar.open_time,
                                 fill, fill - stop_distance)

    def run(self, frames: dict[str, pd.DataFrame], start: datetime, end: datetime) -> tuple[list[dict], list[dict]]:
        if not frames or set(frames) != set(SYMBOLS):
            raise ValueError("se requieren los cuatro simbolos predefinidos")
        timestamps = frames[SYMBOLS[0]].index
        if any(not timestamps.equals(frames[symbol].index) for symbol in SYMBOLS[1:]):
            raise ValueError("velas no alineadas entre simbolos")
        for index in range(200, len(timestamps)):
            now = timestamps[index].to_pydatetime()
            if now >= end:
                break
            if now < start:
                continue
            bars = {
                symbol: SpotBar(now, *[float(frames[symbol].iloc[index][field])
                                          for field in ("open", "high", "low", "close")], 0.0)
                for symbol in SYMBOLS
            }
            if self.position and self.pending_sell:
                self._sell(bars[self.position.symbol], bars[self.position.symbol].open, "EMA50")
            self.pending_sell = False
            if self.position is None and self.pending_buy and not self.halted:
                prior_atr = float(frames[self.pending_buy].iloc[index - 1]["atr14"])
                self._buy(self.pending_buy, bars[self.pending_buy], prior_atr)
            self.pending_buy = None
            if self.position:
                bar = bars[self.position.symbol]
                if bar.low <= self.position.stop:
                    self._sell(bar, min(bar.open, self.position.stop), "STOP")
                else:
                    atr = float(frames[self.position.symbol].iloc[index]["atr14"])
                    self.position.highest = max(self.position.highest, bar.high)
                    self.position.stop = max(
                        self.position.stop,
                        self.position.highest - self.config.stop_atr_multiple * atr,
                    )
                    row = frames[self.position.symbol].iloc[index]
                    if row["close"] < row["ema50"]:
                        self.pending_sell = True
            equity = self.cash + (self.position.quantity * bars[self.position.symbol].close
                                  if self.position else 0.0)
            self.peak = max(self.peak, equity)
            if equity <= self.peak * (1 - self.config.max_drawdown_pct / 100):
                self.halted = True
            self.curve.append({"time": now, "equity": equity})
            if self.position is None and not self.halted:
                candidates = []
                for symbol in SYMBOLS:
                    row = frames[symbol].iloc[index]
                    if (pd.notna(row["prior_high20"]) and pd.notna(row["ema200"])
                            and row["close"] > row["prior_high20"]
                            and row["close"] > row["ema200"]):
                        candidates.append((row["close"] / row["prior_high20"], symbol))
                if candidates:
                    self.pending_buy = sorted(candidates, key=lambda item: (-item[0], item[1]))[0][1]
        if self.position and self.curve:
            symbol = self.position.symbol
            last = frames[symbol].loc[self.curve[-1]["time"]]
            bar = SpotBar(self.curve[-1]["time"], float(last["open"]), float(last["high"]),
                          float(last["low"]), float(last["close"]), 0.0)
            self._sell(bar, bar.close, "END")
            self.curve[-1]["equity"] = self.cash
        return self.trades, self.curve


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--end-month", default="2026-09")
    args = parser.parse_args()
    frames = {symbol: indicators(load_bars(args.data_dir, symbol, "2024-06", args.end_month))
              for symbol in SYMBOLS}
    for label, start, end in (("TRAIN", datetime(2024, 6, 1, tzinfo=timezone.utc), TRAIN_END),
                              ("HOLDOUT", TRAIN_END, HOLDOUT_END)):
        portfolio = BreakoutPortfolio(BreakoutConfig(), CostModel.stress())
        trades, curve = portfolio.run(frames, start, end)
        result = metrics.compute(trades, curve, portfolio.config.initial_cash)
        print(f"{label}: {result.row()}")
        if label == "HOLDOUT":
            gate = assess_backtest(result, random_p95=None)
            print(f"GATE={'VERDE' if gate.passed else 'ROJO'}: {', '.join(gate.reasons) or 'cumple'}")


if __name__ == "__main__":
    main()
