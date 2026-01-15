from .base_strategy import BaseStrategy
from typing import Dict, Any


class SmartScalperStrategy(BaseStrategy):
    """
    Smart Scalper Strategy:
    - Buy: RSI < threshold + MACD Hist increasing.
    - Sell: RSI > threshold OR Trailing Stop.
    """

    def __init__(self):
        super().__init__("Smart Scalper")

    def get_required_indicators(self) -> list:
        return ["rsi", "macd_hist", "macd_signal", "trend_ema", "fast_ema"]

    def check_buy_signal(self, indicators: Dict[str, Any], settings: Dict[str, Any], state: Dict[str, Any]) -> bool:
        rsi = indicators.get('rsi', 50)
        # Scalpers use slightly higher RSI
        buy_threshold = settings.get('buy_rsi', 35)
        macd_hist = indicators.get('macd_hist', 0)
        trend_ema = indicators.get('trend_ema', 0)
        fast_ema = indicators.get('fast_ema', 0)
        current_price = state.get('current_price', 0)

        # 1. Trend Filter (Senior Rule: Never buy against the trend)
        if settings.get('enable_trend_filter', True):
            if trend_ema > 0 and current_price < trend_ema:
                # self.log_decision(f"SCALPER SKIPPED: Price ({current_price:.2f}) < EMA 200 ({trend_ema:.2f})", print)
                return False

        # 2. RSI Condition
        if rsi >= buy_threshold:
            return False

        # 3. MACD Momentum (Histogram must be increasing or positive)
        # Scalper needs momentum, not just oversold status
        if macd_hist <= 0:
            return False

        # 4. Fast Confirmation (Optional but recommended)
        if settings.get('enable_fast_ema', True):
            if fast_ema > 0 and current_price < fast_ema:
                return False

        return True

    def check_sell_signal(self, indicators: Dict[str, Any], settings: Dict[str, Any], state: Dict[str, Any]) -> bool:
        # Smart Scalper also benefits from the new standardized "Glide" and "ATR" logic.
        return self.check_standard_exits(indicators, settings, state)
