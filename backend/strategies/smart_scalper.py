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

    def score_buy_setup(self, indicators: Dict[str, Any], settings: Dict[str, Any], state: Dict[str, Any]) -> tuple[float, list[str]]:
        rsi = float(indicators.get('rsi', 50) or 50)
        buy_threshold = float(settings.get('buy_rsi', 35) or 35)
        macd_hist = float(indicators.get('macd_hist', 0) or 0)
        trend_ema = float(indicators.get('trend_ema', 0) or 0)
        fast_ema = float(indicators.get('fast_ema', 0) or 0)
        current_price = float(state.get('current_price', 0) or 0)

        score = 0.0
        reasons: list[str] = []

        if rsi <= buy_threshold:
            score += 45.0
            reasons.append(f"RSI {rsi:.1f} <= {buy_threshold:.1f}")
        elif rsi <= buy_threshold + 4:
            score += 28.0
            reasons.append(f"RSI near buy zone {rsi:.1f}")

        if macd_hist > 0:
            score += 25.0
            reasons.append("MACD momentum positive")
        elif macd_hist > -0.5:
            score += 10.0
            reasons.append("MACD momentum stabilizing")

        if not settings.get('enable_trend_filter', True):
            score += 10.0
            reasons.append("trend filter disabled")
        elif trend_ema > 0 and current_price >= trend_ema:
            score += 15.0
            reasons.append("price above trend EMA")
        elif trend_ema > 0 and current_price >= trend_ema * 0.995:
            score += 6.0
            reasons.append("price close to trend EMA")

        if not settings.get('enable_fast_ema', True):
            score += 10.0
            reasons.append("fast EMA filter disabled")
        elif fast_ema > 0 and current_price >= fast_ema:
            score += 15.0
            reasons.append("price above fast EMA")
        elif fast_ema > 0 and current_price >= fast_ema * 0.998:
            score += 6.0
            reasons.append("price close to fast EMA")

        return min(score, 100.0), reasons

    def check_buy_signal(self, indicators: Dict[str, Any], settings: Dict[str, Any], state: Dict[str, Any]) -> bool:
        score, reasons = self.score_buy_setup(indicators, settings, state)
        min_score = float(settings.get('smart_scalper_entry_score', 68) or 68)

        if score >= min_score:
            self.log_decision(
                f"BUY score {score:.1f}/{min_score:.1f}: {', '.join(reasons)}",
                print,
            )
            return True

        self.log_decision(
            f"BUY skipped: score {score:.1f}/{min_score:.1f}: {', '.join(reasons) or 'no confluence'}",
            print,
        )
        return False

    def check_sell_signal(self, indicators: Dict[str, Any], settings: Dict[str, Any], state: Dict[str, Any]) -> bool:
        # Smart Scalper also benefits from the new standardized "Glide" and "ATR" logic.
        return self.check_standard_exits(indicators, settings, state)
