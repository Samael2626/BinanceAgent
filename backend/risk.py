from dataclasses import dataclass
from math import floor
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
    cooldown_minutes: int = 3
    min_market_score_to_buy: float = 32.0


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
    if quote_size < float(min_order_quote or 0):
        return 0.0
    return floor(quote_size * 100) / 100


def calculate_futures_position_size(
    equity: float,
    current_price: float,
    stop_loss_pct: float,
    atr: float,
    risk_per_trade_pct: float,
    atr_stop_mult: float,
    leverage: int = 2,
    min_notional: float = 5.0,
    max_margin_pct: float = 35.0,
    maint_margin_rate: float = 0.005,
) -> float:
    """
    Calculates safe USDⓈ-M Futures notional size (in USDT) for small accounts (< 50 USDT).
    Enforces:
      1. Leverage strictly in 1..3x.
      2. Liquidation distance >= 3x Stop Loss distance (prevents premature isolated liquidation).
      3. Isolated margin required (notional / leverage) <= equity * (max_margin_pct / 100).
      4. Notional >= contract `min_notional` (fails closed returning 0.0 if unreachable).
    """
    if equity <= 0 or current_price <= 0:
        return 0.0
    if int(leverage) < 1 or int(leverage) > 3:
        return 0.0

    lev = float(int(leverage))
    stop_pct = max(float(stop_loss_pct or 0), 0.25)
    if atr > 0:
        atr_pct = (atr / current_price) * 100.0
        stop_pct = max(stop_pct, atr_pct * max(float(atr_stop_mult or 0), 0.1))

    # Isolated liquidation distance (%) ~ (100 / lev) - (maint_margin_rate * 100)
    approx_liq_dist_pct = (100.0 / lev) - (float(maint_margin_rate) * 100.0)
    if stop_pct * 3.0 >= approx_liq_dist_pct:
        return 0.0

    risk_pct = max(float(risk_per_trade_pct or 0), 0.1) / 100.0
    risk_capital = equity * risk_pct
    if risk_capital <= 0:
        return 0.0

    notional_by_risk = risk_capital / max(stop_pct / 100.0, 0.0025)
    max_margin_usdt = min(equity * 0.95, equity * (max(float(max_margin_pct or 0), 1.0) / 100.0))
    max_notional_by_margin = max_margin_usdt * lev

    notional = min(notional_by_risk, max_notional_by_margin)
    if notional < float(min_notional or 5.0):
        return 0.0
    return floor(notional * 100) / 100


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
