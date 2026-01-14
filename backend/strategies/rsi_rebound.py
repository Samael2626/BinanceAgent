from .base_strategy import BaseStrategy
from typing import Dict, Any


class RSIReboundStrategy(BaseStrategy):
    """
    RSI Rebound Strategy:
    - Buy: RSI below 'buy_rsi' threshold + Price Rejection (Bullish candle or cross up).
    - Sell: RSI above 'sell_rsi' threshold OR strategy-defined risk targets.
    """

    def __init__(self):
        super().__init__("RSI Rebound")

    def get_required_indicators(self) -> list:
        return ["rsi", "trend_ema", "vol_sma", "current_vol", "ema_2", "ema_7"]

    def check_buy_signal(self, indicators: Dict[str, Any], settings: Dict[str, Any], state: Dict[str, Any]) -> bool:
        rsi = indicators.get('rsi', 50)
        buy_threshold = settings.get('buy_rsi', 21)
        trend_ema = indicators.get('trend_ema', 0)
        current_price = state.get('current_price', 0)
        vol_sma = indicators.get('vol_sma', 0)
        current_vol = indicators.get('current_vol', 0)

        # 1. RSI Condition (Primary)
        if rsi >= buy_threshold:
            return False

        # 2. Optional Quantitative Filters (Toggleable from Panel)
        if settings.get('enable_trend_filter', True):
            if current_price < trend_ema:
                self.log_decision(
                    f"BUY SKIPPED: Price ({current_price:.2f}) below EMA 200 ({trend_ema:.2f})", print)
                return False

        if settings.get('enable_vol_filter', True):
            if current_vol <= vol_sma:
                self.log_decision(
                    f"BUY SKIPPED: Low volume ({current_vol:.2f} <= SMA {vol_sma:.2f})", print)
                return False

        self.log_decision(
            f"BUY SIGNAL CONFIRMED: RSI({rsi:.1f}) < {buy_threshold} (Filters passed/skipped)", print)
        return True

    def check_sell_signal(self, indicators: Dict[str, Any], settings: Dict[str, Any], state: Dict[str, Any]) -> bool:
        rsi = indicators.get('rsi', 50)
        sell_threshold = settings.get('sell_rsi', 75)  # Default updated to 75
        current_price = state.get('current_price', 0)
        entry_price = state.get('entry_price', 0)

        if entry_price <= 0:
            return False

        # 1. RSI Exit (Oversold exhaustion)
        if rsi > sell_threshold:
            self.log_decision(
                f"SELL SIGNAL: RSI({rsi:.1f}) > {sell_threshold}", print)
            return True

        # 2. Risk Management (SL/TP)
        sl_pct = settings.get('stop_loss_pct', 3.2)  # Default updated to 3.2
        if sl_pct > 0:
            sl_price = entry_price * (1 - sl_pct / 100)
            if current_price <= sl_price:
                self.log_decision(
                    f"SELL SIGNAL: Stop Loss triggered @ {current_price:.2f}", print)
                return True

        tp_pct = settings.get('take_profit_pct', 1.3)  # Default updated to 1.3
        if tp_pct > 0:
            tp_price = entry_price * (1 + tp_pct / 100)
            if current_price >= tp_price:
                self.log_decision(
                    f"SELL SIGNAL: Take Profit triggered @ {current_price:.2f}", print)
                return True

        return False
