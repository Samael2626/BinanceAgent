"""Replay conservador de la configuracion Spot con cartera unica."""

from __future__ import annotations

import argparse
import io
import json
from collections import deque
from contextlib import redirect_stdout
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from itertools import zip_longest
from pathlib import Path
from typing import Iterator

import pandas as pd

from backend.indicators import calculate_indicators
from backend.predictive_modules import PredictiveEngine
from backend.risk import calculate_position_quote_size
from backend.scanner import (
    RotationCandidate, parse_rotation_watchlist, score_rotation_candidate,
    should_switch_rotation_candidate,
)
from backend.strategies.smart_scalper import SmartScalperStrategy
from harness import metrics
from harness.costs import CostModel
from harness.spot_data import SpotBar, iter_bars, months_between, monthly_name


def _enabled(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "on"}


BOOL_KEYS = {
    "auto_asset_rotation", "enable_buying", "enable_selling", "enable_trend_filter",
    "enable_fast_ema", "enable_vol_filter", "auto_position_sizing",
    "adaptive_trailing_enabled", "dca_enabled", "trailing_enabled",
}
NUMBER_KEYS = {
    "rotation_interval_minutes", "min_rotation_score", "buy_rsi", "sell_rsi",
    "smart_scalper_entry_score", "ema_length", "fast_ema_len", "macd_fast",
    "macd_slow", "macd_signal", "stop_loss_pct", "take_profit_pct",
    "rsi_trailing_pct", "adaptive_trailing_atr_mult", "adaptive_trailing_min_pct",
    "adaptive_trailing_max_pct", "trade_qty", "risk_per_trade_pct",
    "max_daily_loss_pct", "max_consecutive_losses", "atr_stop_mult",
    "min_market_score_to_buy", "cooldown_minutes", "portfolio_max_drawdown_pct",
}


def normalize_settings(snapshot: dict) -> dict:
    values = {**snapshot["settings"], **snapshot["state"]}
    for key in BOOL_KEYS & values.keys():
        values[key] = _enabled(values[key])
    for key in NUMBER_KEYS & values.keys():
        values[key] = float(values[key])
    return values


def _frames(bars: deque[SpotBar]) -> pd.DataFrame:
    return pd.DataFrame({
        "open": [bar.open for bar in bars],
        "high": [bar.high for bar in bars],
        "low": [bar.low for bar in bars],
        "close": [bar.close for bar in bars],
        "volume": [bar.volume for bar in bars],
    })


def _active_prediction_frame(bars: deque[SpotBar], settings: dict) -> pd.DataFrame:
    frame = _frames(bars)
    frame.ta.rsi(length=14, append=True)
    frame.ta.ema(length=int(settings.get("ema_length", 200)), append=True)
    frame.ta.ema(length=int(settings.get("fast_ema_len", 7)), append=True)
    return frame


def stream_symbol(data_dir: Path, symbol: str, start: str, end: str) -> Iterator[SpotBar]:
    previous: datetime | None = None
    for year, month in months_between(start, end):
        path = data_dir / symbol / "1m" / monthly_name(symbol, "1m", year, month)
        if not path.is_file():
            raise FileNotFoundError(path)
        for bar in iter_bars(path):
            if previous is not None and bar.open_time - previous != timedelta(minutes=1):
                raise ValueError(f"hueco 1m en {symbol}: {previous} -> {bar.open_time}")
            previous = bar.open_time
            yield bar


def stream_market(data_dir: Path, symbols: list[str], start: str, end: str) -> Iterator[dict[str, SpotBar]]:
    streams = [stream_symbol(data_dir, symbol, start, end) for symbol in symbols]
    for grouped in zip_longest(*streams):
        if any(bar is None for bar in grouped):
            raise ValueError("cantidad de velas distinta entre simbolos")
        times = {bar.open_time for bar in grouped}
        if len(times) != 1:
            raise ValueError(f"velas no alineadas: {times}")
        yield dict(zip(symbols, grouped))


@dataclass
class ReplayPosition:
    symbol: str
    quantity: float
    entry_price: float
    basis: float
    entry_time: datetime
    highest: float


class SpotReplay:
    def __init__(self, snapshot: dict, initial_cash: float = 47.0,
                 costs: CostModel | None = None):
        settings = normalize_settings(snapshot)
        state = snapshot["state"]
        if settings.get("timeframe") != "1m" or settings.get("active_strategy") not in {
            "smart_scalping", "smart_scalper", "multi", "scalper_pro",
        }:
            raise ValueError("replay solo admite smart_scalping en 1m")
        if _enabled(state.get("dca_enabled", False)):
            raise ValueError("replay no admite DCA activo")
        if not settings.get("enable_selling", True):
            raise ValueError("replay requiere ventas habilitadas")
        self.settings = settings
        self.symbols = parse_rotation_watchlist(settings.get("rotation_watchlist"))
        self.symbol = settings.get("symbol", self.symbols[0])
        if self.symbol not in self.symbols:
            raise ValueError("simbolo inicial fuera de la lista")
        self.cash = initial_cash
        self.initial_cash = initial_cash
        self.costs = costs or CostModel.stress()
        self.history = {symbol: deque(maxlen=999) for symbol in self.symbols}
        self.predictors = {symbol: PredictiveEngine() for symbol in self.symbols}
        self.strategy = SmartScalperStrategy()
        self.strategy.log_decision = lambda *args: None
        self.position: ReplayPosition | None = None
        self.pending_buy: tuple[str, float] | None = None
        self.pending_sell = False
        self.last_scan: datetime | None = None
        self.day_start = initial_cash
        self.day: date | None = None
        self.peak = initial_cash
        self.consecutive_losses = 0
        self.halt_until: datetime | None = None
        self.killed = False
        self.trades: list[dict] = []
        self.curve: list[dict] = []
        self.decisions: list[dict] = []

    def _setting(self, name: str, default: float) -> float:
        return float(self.settings.get(name, default))

    def _indicators(self, symbol: str, count: int = 999) -> dict:
        history = self.history[symbol]
        if len(history) < min(count, 250):
            return {}
        return calculate_indicators(_frames(deque(list(history)[-count:])), self.settings)

    def _scan(self, now: datetime) -> None:
        if not _enabled(self.settings.get("auto_asset_rotation", False)) or self.position:
            return
        interval = timedelta(minutes=self._setting("rotation_interval_minutes", 15))
        if self.last_scan and now - self.last_scan < interval:
            return
        self.last_scan = now
        candidates = []
        for symbol in self.symbols:
            if len(self.history[symbol]) < 299:
                continue
            recent = deque(list(self.history[symbol])[-299:])
            frame = _frames(recent)
            indicators = calculate_indicators(frame, self.settings)
            prediction = self.predictors[symbol].analyze(frame, recent[-1].close)
            score = score_rotation_candidate(prediction, indicators)
            candidates.append(RotationCandidate(
                symbol, score, float(prediction.get("market_score", 50)),
                float(prediction.get("breakout_prob", 0)),
                float((prediction.get("trend_strength") or {}).get("score", 50)),
                float(indicators.get("rsi", 50)), bool(indicators.get("is_lateral", False)),
            ))
        if not candidates:
            return
        candidates.sort(key=lambda item: item.score, reverse=True)
        current = next((item.score for item in candidates if item.symbol == self.symbol), 0.0)
        if should_switch_rotation_candidate(
            self.symbol, current, candidates[0], self._setting("min_rotation_score", 55),
        ):
            self.symbol = candidates[0].symbol
            self.decisions.append({"time": now, "event": "ROTATE", "symbol": self.symbol})

    def _sell(self, now: datetime, price: float, reason: str) -> None:
        position = self.position
        if position is None:
            raise RuntimeError("venta sin posicion")
        fill = self.costs.fill_price(position.symbol, price, "SELL", position.quantity * price)
        proceeds = position.quantity * fill
        net = proceeds - self.costs.fee(proceeds) - position.basis
        self.cash += proceeds - self.costs.fee(proceeds)
        self.trades.append({
            "symbol": position.symbol, "entry_time": position.entry_time,
            "exit_time": now, "entry_price": position.entry_price,
            "exit_price": fill, "net_pnl": net,
            "net_return_pct": net / position.basis * 100, "reason": reason,
        })
        self.consecutive_losses = self.consecutive_losses + 1 if net < 0 else 0
        if self.consecutive_losses >= int(self._setting("max_consecutive_losses", 3)):
            self.halt_until = now + timedelta(minutes=self._setting("cooldown_minutes", 3))
        self.position = None

    def _buy(self, now: datetime, symbol: str, price: float, atr: float,
             market_score: float) -> None:
        if self.killed or self.cash <= 0 or market_score < self._setting("min_market_score_to_buy", 32):
            return
        if self.halt_until and now < self.halt_until:
            return
        if self.cash < self.day_start * (1 - self._setting("max_daily_loss_pct", 5) / 100):
            return
        if _enabled(self.settings.get("auto_position_sizing", True)):
            stake = calculate_position_quote_size(
                self.cash, price, self._setting("stop_loss_pct", 1.5), atr,
                self._setting("risk_per_trade_pct", 0.75),
                self._setting("atr_stop_mult", 1.5), min_order_quote=10.0,
                max_position_pct=25.0,
            )
        else:
            stake = self._setting("trade_qty", 12)
            if self.settings.get("trade_qty_type") == "base":
                stake *= price
        if stake < 10 or stake + self.costs.fee(stake) > self.cash:
            return
        fill = self.costs.fill_price(symbol, price, "BUY", stake)
        basis = stake + self.costs.fee(stake)
        self.cash -= basis
        self.position = ReplayPosition(symbol, stake / fill, fill, basis, now, fill)

    def run(self, market: Iterator[dict[str, SpotBar]], start: datetime,
            end: datetime) -> tuple[list[dict], list[dict]]:
        previous: dict[str, SpotBar] | None = None
        for bars in market:
            now = next(iter(bars.values())).open_time
            if now >= end:
                break
            if now < start:
                for symbol, bar in bars.items():
                    self.history[symbol].append(bar)
                continue
            if self.day != now.date():
                self.day = now.date()
                self.day_start = self.cash + (self.position.quantity * bars[self.position.symbol].open
                                              if self.position else 0.0)
            if self.position and self.pending_sell:
                self._sell(now, bars[self.position.symbol].open, "SIGNAL")
            self.pending_sell = False
            if self.position is None and self.pending_buy:
                symbol, market_score = self.pending_buy
                previous_atr = self._indicators(symbol).get("atr", 0)
                self._buy(now, symbol, bars[symbol].open, float(previous_atr), market_score)
            self.pending_buy = None
            if self.position:
                position = self.position
                bar = bars[position.symbol]
                stop = position.entry_price * (1 - self._setting("stop_loss_pct", 1.5) / 100)
                atr = float(self._indicators(position.symbol).get("atr", 0))
                trail_pct = self._setting("rsi_trailing_pct", 0.8)
                if _enabled(self.settings.get("adaptive_trailing_enabled", False)) and atr > 0:
                    trail_pct = max(self._setting("adaptive_trailing_min_pct", 0.35), min(
                        self._setting("adaptive_trailing_max_pct", 1.8),
                        atr / bar.open * 100 * self._setting("adaptive_trailing_atr_mult", 1.25),
                    ))
                bar_highest = max(position.highest, bar.high)
                trail = bar_highest * (1 - trail_pct / 100)
                take_profit = position.entry_price * (1 + self._setting("take_profit_pct", 1.5) / 100)
                if bar.low <= stop:
                    self._sell(now, min(bar.open, stop), "STOP")
                elif bar_highest > position.entry_price and bar.low <= trail:
                    self._sell(now, min(bar.open, trail), "TRAIL")
                elif bar.high >= take_profit:
                    self._sell(now, take_profit, "TP")
                elif self.position:
                    position.highest = bar_highest
            for symbol, bar in bars.items():
                self.history[symbol].append(bar)
            equity = self.cash + (self.position.quantity * bars[self.position.symbol].close
                                  if self.position else 0.0)
            self.peak = max(self.peak, equity)
            if equity <= self.initial_cash * (1 - self._setting("portfolio_max_drawdown_pct", 8) / 100):
                self.killed = True
                if self.position:
                    self.pending_sell = True
            self.curve.append({"time": now, "equity": equity})
            self._scan(now)
            if self.position:
                indicators = self._indicators(self.position.symbol)
                state = {"current_price": bars[self.position.symbol].close,
                         "entry_price": self.position.entry_price,
                         "highest_price": self.position.highest}
                with redirect_stdout(io.StringIO()):
                    should_sell = self.strategy.check_sell_signal(indicators, self.settings, state)
                if should_sell:
                    self.pending_sell = True
            elif not self.killed and len(self.history[self.symbol]) >= 999:
                indicators = self._indicators(self.symbol)
                if not indicators.get("is_lateral", False):
                    prediction = self.predictors[self.symbol].analyze(
                        _active_prediction_frame(self.history[self.symbol], self.settings),
                        bars[self.symbol].close)
                    market_score = float(prediction.get("market_score", 50))
                    state = {"current_price": bars[self.symbol].close}
                    score, _ = self.strategy.score_buy_setup(indicators, self.settings, state)
                    if (_enabled(self.settings.get("enable_buying", True))
                            and score >= self._setting("smart_scalper_entry_score", 55)
                            and market_score >= self._setting("min_market_score_to_buy", 32)):
                        self.pending_buy = self.symbol, market_score
                        self.decisions.append({"time": now, "event": "BUY_SIGNAL",
                                               "symbol": self.symbol, "score": score})
            previous = bars
        if self.position and previous:
            bar = previous[self.position.symbol]
            self._sell(bar.open_time, bar.close, "END")
            self.curve[-1]["equity"] = self.cash
        return self.trades, self.curve


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--start-month", required=True)
    parser.add_argument("--end-month", required=True)
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()
    snapshot = json.loads(args.config.read_text(encoding="utf-8"))
    replay = SpotReplay(snapshot)
    market = stream_market(args.data_dir, replay.symbols, args.start_month, args.end_month)
    start = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)
    trades, curve = replay.run(market, start, end)
    print(metrics.compute(trades, curve, replay.initial_cash).row())
    print(f"decisions={len(replay.decisions)} killed={replay.killed}")


if __name__ == "__main__":
    main()
