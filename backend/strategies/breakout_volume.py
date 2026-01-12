from .base_strategy import BaseStrategy
from typing import Dict, Any


class BreakoutVolumeStrategy(BaseStrategy):
    """
    Breakout Volume Strategy:
    - Buy: Price breaks above Bollinger Upper Band + Volume > 1.5x average.
    - Sell: Price drops below Bollinger middle band OR specific SL/TP.
    """

    def __init__(self):
        super().__init__("Breakout Volume")

    def get_required_indicators(self) -> list:
        return ["bb_upper", "bb_middle", "current_vol", "vol_sma"]

    def check_buy_signal(self, indicators: Dict[str, Any], settings: Dict[str, Any], state: Dict[str, Any]) -> bool:
        current_price = state.get('current_price', 0)
        bb_upper = indicators.get('bb_upper', 0)
        current_vol = indicators.get('current_vol', 0)
        vol_sma = indicators.get('vol_sma', 0)

        if bb_upper == 0 or vol_sma == 0:
            return False

        # Breakout condition: Price > BB Upper + High Volume
        if current_price > bb_upper and current_vol > vol_sma * 1.5:
            return True
        return False

    def check_sell_signal(self, indicators: Dict[str, Any], settings: Dict[str, Any], state: Dict[str, Any]) -> bool:
        current_price = state.get('current_price', 0)
        bb_middle = indicators.get('bb_middle', 0)
        entry_price = state.get('entry_price', 0)

        if entry_price <= 0:
            return False

        # 1. Trailing-like Stop: Drop below middle band
        if current_price < bb_middle:
            return True

        # 2. Risk Management
        tp_pct = settings.get('take_profit_pct', 0)
        if tp_pct > 0:
            # Breakouts often have tighter targets or different risk
            tp_price = entry_price * (1 + tp_pct / 200)
            if current_price >= tp_price:
                return True

        return False
