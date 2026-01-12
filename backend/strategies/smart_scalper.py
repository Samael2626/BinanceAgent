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
        return ["rsi", "macd_hist", "macd_signal"]

    def check_buy_signal(self, indicators: Dict[str, Any], settings: Dict[str, Any], state: Dict[str, Any]) -> bool:
        rsi = indicators.get('rsi', 50)
        # Scalpers usually have higher buy thresholds
        buy_threshold = settings.get('buy_rsi', 40)
        macd_hist = indicators.get('macd_hist', 0)

        # Momentum: RSI low + MACD histogram turning positive
        if rsi < buy_threshold and macd_hist > 0:
            return True
        return False

    def check_sell_signal(self, indicators: Dict[str, Any], settings: Dict[str, Any], state: Dict[str, Any]) -> bool:
        current_price = state.get('current_price', 0)
        highest_price = state.get('highest_price', 0)
        entry_price = state.get('entry_price', 0)
        trailing_pct = settings.get('trailing_stop_pct', 0)

        if entry_price <= 0:
            return False

        # 1. Trailing Stop (Mandatory for this scalper)
        if trailing_pct > 0 and highest_price > 0:
            if current_price <= highest_price * (1 - trailing_pct / 100):
                return True

        # 2. RSI Exit
        rsi = indicators.get('rsi', 50)
        sell_threshold = settings.get('sell_rsi', 60)
        if rsi > sell_threshold:
            return True

        return False
