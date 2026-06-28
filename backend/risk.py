from dataclasses import dataclass
from typing import Tuple
import time


ALLOWED_TIMEFRAMES = {"1m", "5m", "15m", "1h"}


@dataclass(frozen=True)
class RiskConfig:
    auto_position_sizing: bool = True
    risk_per_trade_pct: float = 0.75
    max_daily_loss_pct: float = 5.0
    max_consecutive_losses: int = 3
    atr_stop_mult: float = 1.5
    min_order_quote: float = 10.0
    max_position_pct: float = 25.0
    cooldown_minutes: int = 10
    min_market_score_to_buy: float = 45.0


def sanitize_timeframe(value: str, default: str = "15m") -> str:
    if value in ALLOWED_TIMEFRAMES:
        return value
    return default


def calculate_position_quote_size(
    equity: float,
    current_price: float,
    stop_loss_pct: float,
    atr: float,
    risk_per_trade_pct: float,
    atr_stop_mult: float,
    min_order_quote: float = 10.0,
    max_position_pct: float = 25.0,
) -> float:
    if equity <= 0 or current_price <= 0:
        return 0.0

    spendable_equity = equity * 0.98
    if spendable_equity < float(min_order_quote or 0):
        return 0.0

    stop_pct = max(float(stop_loss_pct or 0), 0.25)
    if atr > 0:
        atr_pct = (atr / current_price) * 100.0
        stop_pct = max(stop_pct, atr_pct * max(atr_stop_mult, 0.1))

    risk_pct = max(float(risk_per_trade_pct or 0), 0.1) / 100.0
    risk_capital = equity * risk_pct
    if risk_capital <= 0:
        return 0.0

    quote_size = risk_capital / max(stop_pct / 100.0, 0.0025)
    hard_cap = equity * max(float(max_position_pct or 0), 1.0) / 100.0
    quote_size = min(quote_size, hard_cap, spendable_equity)
    quote_size = max(float(min_order_quote or 0), quote_size)
    return round(quote_size, 2)


def should_halt_buying(
    *,
    daily_pnl: float,
    baseline_equity: float,
    max_daily_loss_pct: float,
    consecutive_losses: int,
    max_consecutive_losses: int,
    trading_halt_until: float,
    market_score: float,
    min_market_score_to_buy: float,
) -> Tuple[bool, str]:
    now = time.time()

    if trading_halt_until and now < trading_halt_until:
        remaining = int(trading_halt_until - now)
        return True, f"cooldown activo ({remaining}s)"

    if baseline_equity > 0:
        max_daily_loss = baseline_equity * (max_daily_loss_pct / 100.0)
        if daily_pnl <= -max_daily_loss:
            return True, f"limite de perdida diaria alcanzado ({daily_pnl:.2f} USDT)"

    if consecutive_losses >= max_consecutive_losses:
        return True, f"racha de perdidas alcanzada ({consecutive_losses})"

    if market_score < min_market_score_to_buy:
        return True, f"market score bajo ({market_score:.1f})"

    return False, ""


def next_halt_timestamp(cooldown_minutes: int) -> float:
    return time.time() + max(cooldown_minutes, 1) * 60.0


def should_trigger_portfolio_kill_switch(
    *,
    equity: float,
    baseline_equity: float,
    max_drawdown_pct: float,
) -> Tuple[bool, str]:
    if equity <= 0 or baseline_equity <= 0 or max_drawdown_pct <= 0:
        return False, ""

    drawdown_pct = ((baseline_equity - equity) / baseline_equity) * 100.0
    if drawdown_pct >= max_drawdown_pct:
        return True, f"drawdown global {drawdown_pct:.2f}% >= {max_drawdown_pct:.2f}%"
    return False, ""
