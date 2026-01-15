from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseStrategy(ABC):
    """
    Base class for all trading strategies.
    Each strategy must implement signal logic and define its own indicators.
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def get_required_indicators(self) -> list:
        """Returns a list of indicator names required by this strategy."""
        pass

    @abstractmethod
    def check_buy_signal(self, indicators: Dict[str, Any], settings: Dict[str, Any], state: Dict[str, Any]) -> bool:
        """
        Evaluates conditions for a BUY signal.
        Includes strategy-specific filters and entry logic.
        """
        pass

    @abstractmethod
    def check_sell_signal(self, indicators: Dict[str, Any], settings: Dict[str, Any], state: Dict[str, Any]) -> bool:
        """
        Evaluates conditions for a SELL signal.
        Includes strategy-specific exit logic and risk management (SL/TP/Trailing).
        """
        pass

    def check_standard_exits(self, indicators: Dict[str, Any], settings: Dict[str, Any], state: Dict[str, Any]) -> bool:
        """
        Shared logic for standard exits: SL, TP (Fixed/ATR), and RSI Glide.
        Returns True if an exit signal is triggered.
        """
        current_price = state.get('current_price', 0)
        entry_price = state.get('entry_price', 0)
        highest_price = state.get('highest_price', 0)

        if entry_price <= 0:
            return False

        # 1. STOP LOSS
        sl_pct = settings.get('stop_loss_pct', 3.2)
        if sl_pct > 0:
            sl_price = entry_price * (1 - sl_pct / 100)
            if current_price <= sl_price:
                self.log_decision(
                    f"EXIT: Stop Loss @ {current_price:.2f}", print)
                return True

        # 2. RSI GLIDE (Smart Trailing) & GLOBAL TRAILING
        # We activate trailing if:
        # A) RSI is high (Glide Mode - Standard Strategy behavior)
        # B) "Trailing" is explicitly enabled in global settings (User Request - MANUAL override)
        # C) Profit Step (ALWAYS ACTIVE - User Request): Price went above entry

        rsi = indicators.get('rsi', 50)
        sell_threshold = settings.get('sell_rsi', 70)
        is_global_trail = settings.get('trailing_enabled', False)
        trail_pct = settings.get('rsi_trailing_pct', 0.8)

        # C) Profit Step (ALWAYS ACTIVE):
        # Activate trailing automatically as soon as we are in profit
        # relative to the entry price, regardless of manual settings.
        # This is the "stairs" logic - cada vez que supera el entry, empieza a subir escaleras
        profit_step_reached = (highest_price > entry_price)

        # Trigger Condition: ALWAYS check Profit Step, additionally check RSI or Manual Trailing
        # IMPORTANT: Profit Step is INDEPENDENT of trailing_enabled button
        should_trail = profit_step_reached or (
            rsi > sell_threshold) or is_global_trail

        # If High Price > 0 and we should be trailing
        if highest_price > 0 and should_trail:
            trail_price = highest_price * (1 - trail_pct / 100)

            if current_price < trail_price:
                # Determine reason for logging
                if rsi > sell_threshold:
                    reason_tag = "RSI Glide"
                elif profit_step_reached and not is_global_trail:
                    reason_tag = "Profit Step Trail"
                else:
                    reason_tag = "Manual Trailing"

                self.log_decision(
                    f"EXIT: {reason_tag} Stop @ {current_price:.2f} (High: {highest_price:.2f})", print)
                return True
            else:
                # Optional: log steps status for user reassurance
                if profit_step_reached and not (rsi > sell_threshold) and not is_global_trail:
                    print(
                        f"🧗 PROFIT STEP: In Profit (+{(highest_price/entry_price-1)*100:.2f}%) | Price {current_price:.2f} > Trail {trail_price:.2f} - ASCENDING")
                return False  # Holding

        # 3. DYNAMIC ATR TAKE PROFIT
        if settings.get('enable_atr_tp', False):
            atr = indicators.get('atr', 0)
            atr_mult = settings.get('atr_tp_multiplier', 2.0)
            if atr > 0:
                tp_price = entry_price + (atr * atr_mult)
                # Sanity
                if tp_price <= entry_price:
                    tp_price = entry_price * 1.01

                if current_price >= tp_price:
                    self.log_decision(
                        f"EXIT: ATR Take Profit @ {current_price:.2f} (Target: {tp_price:.2f})", print)
                    return True
            else:
                # Fallback to Fixed
                tp_pct = settings.get('take_profit_pct', 1.5)
                if tp_pct > 0:
                    tp_price = entry_price * (1 + tp_pct / 100)
                    if current_price >= tp_price:
                        self.log_decision(
                            f"EXIT: Fixed TP (ATR Fallback) @ {current_price:.2f}", print)
                        return True
        else:
            # 4. STANDARD FIXED TP
            tp_pct = settings.get('take_profit_pct', 1.5)
            if tp_pct > 0:
                tp_price = entry_price * (1 + tp_pct / 100)
                if current_price >= tp_price:
                    self.log_decision(
                        f"EXIT: Fixed Take Profit @ {current_price:.2f}", print)
                    return True

        return False

    def log_decision(self, reason: str, logger_func):
        """Standardized logging for strategy decisions."""
        logger_func(f"[Strategy: {self.name}] Decision: {reason}")
