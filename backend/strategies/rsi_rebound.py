try:
    from .base_strategy import BaseStrategy
except ImportError:
    from strategies.base_strategy import BaseStrategy
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
        return ["rsi", "trend_ema", "vol_sma", "current_vol", "fast_ema", "atr"]

    def check_buy_signal(self, indicators: Dict[str, Any], settings: Dict[str, Any], state: Dict[str, Any]) -> bool:
        rsi = indicators.get('rsi', 50)
        buy_threshold = settings.get('buy_rsi', 21)
        trend_ema = indicators.get('trend_ema', 0)
        fast_ema = indicators.get('fast_ema', 0)
        current_price = state.get('current_price', 0)
        vol_sma = indicators.get('vol_sma', 0)
        current_vol = indicators.get('current_vol', 0)

        # ========== ENHANCED PRE-EVALUATION LOGGING ==========
        self.log_decision(
            f"[EVAL BUY] Price=${current_price:.2f} | RSI={rsi:.1f} | "
            f"Fast EMA={fast_ema:.2f} | Trend EMA={trend_ema:.2f} | Vol={current_vol:.0f}/{vol_sma:.0f}",
            print
        )

        # ========== INDICATOR VALIDATION (CRITICAL FIX) ==========
        # Si los indicadores son inválidos (0 o negativos), rechazar por seguridad
        if settings.get('enable_trend_filter', True):
            if trend_ema <= 0:
                self.log_decision(
                    f"🚫 BUY BLOCKED: Invalid or uninitialized Trend EMA ({trend_ema:.2f})", print)
                return False

        if settings.get('enable_fast_ema', True):
            if fast_ema <= 0:
                self.log_decision(
                    f"🚫 BUY BLOCKED: Invalid or uninitialized Fast EMA ({fast_ema:.2f})", print)
                return False

        # ========== ORIGINAL FILTERS ==========
        # 1. RSI Condition (Primary)
        if rsi >= buy_threshold:
            return False

        # 2. Fast EMA Confirmation (Price Rejection/Momentum)
        if settings.get('enable_fast_ema', True):
            if current_price < fast_ema:
                self.log_decision(
                    f"❌ BUY SKIPPED: Price ({current_price:.2f}) below Fast EMA ({fast_ema:.2f}) - No confirmation.", print)
                return False

        # 3. Trend Filter (EMA 200)
        if settings.get('enable_trend_filter', True):
            if current_price < trend_ema:
                self.log_decision(
                    f"❌ BUY SKIPPED: Price ({current_price:.2f}) below EMA 200 ({trend_ema:.2f}) - Bearish trend.", print)
                return False

        # 4. Volume Filter
        if settings.get('enable_vol_filter', True):
            if current_vol <= vol_sma:
                self.log_decision(
                    f"❌ BUY SKIPPED: Low volume ({current_vol:.2f} <= SMA {vol_sma:.2f})", print)
                return False

        self.log_decision(
            f"✅ BUY SIGNAL CONFIRMED: RSI({rsi:.1f}) < {buy_threshold} | All filters PASSED", print)
        return True

    def check_sell_signal(self, indicators: Dict[str, Any], settings: Dict[str, Any], state: Dict[str, Any]) -> bool:
        """
        Standardized Sell Signal using BaseStrategy's exit logic.
        (SL, TP, RSI Glide Trailing)
        """
        # We rely 100% on the standardized exit logic for this strategy
        return self.check_standard_exits(indicators, settings, state)
