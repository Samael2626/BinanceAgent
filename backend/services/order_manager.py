from typing import Dict, Optional
from backend.utils.logger import logger
from backend.binance_wrapper import BinanceWrapper
import time


class OrderManager:
    """
    The Hands of the System.
    Responsible for:
    1. Validating Orders (Risk Checks, Min Notional)
    2. Executing Trades via Wrapper
    3. Managing Position State (Entry/Exit)
    4. Enforcing 'Zero Residue' cleanup.
    """

    def __init__(self, wrapper: BinanceWrapper):
        self.wrapper = wrapper
        # State tracking: {symbol: {'in_position': bool, 'entry_price': float, 'qty': float}}
        self.positions: Dict[str, dict] = {}

    def validate_buy(self, symbol: str, quantity: float, price: float) -> bool:
        """
        Checks if a BUY order is safe to execute.
        """
        # 1. Check if already in position (Global Rule: 1 Position at a time?)
        # For now, per symbol check
        if self.positions.get(symbol, {}).get('in_position', False):
            logger.warning(f"⛔ Blocked BUY {symbol}: Already in position.")
            return False

        # 2. Min Notional Check
        if not self.wrapper.adjust_to_min_notional(symbol, quantity, price):
            logger.warning(f"⛔ Blocked BUY {symbol}: Below Min Notional.")
            return False

        return True

    def execute_buy(self, symbol: str, quantity: float, price: float, strategy: str = "MANUAL") -> bool:
        """
        Executes a BUY order and updates state.
        """
        if not self.validate_buy(symbol, quantity, price):
            return False

        try:
            logger.info(
                f"🟢 Executing BUY {symbol} | Qty: {quantity} | Price: {price} | Strat: {strategy}")

            # Using basic MARKET order for speed as requested ("Velocidad Extrema")
            # In future we can add LIMIT support
            order = self.wrapper.place_order(
                symbol, "BUY", quantity, order_type="MARKET")

            if order:
                # Use actual fill price later
                self._update_position_entry(symbol, quantity, price)
                return True

        except Exception as e:
            logger.error(f"❌ Failed to execute BUY {symbol}: {e}")

        return False

    def execute_sell(self, symbol: str, quantity: float, strategy: str = "MANUAL") -> bool:
        """
        Executes a SELL order and performs FULL RESET.
        """
        # Check if we have something to sell?
        # For manual override, we might bypass, but generally should track.

        try:
            logger.info(
                f"🔴 Executing SELL {symbol} | Qty: {quantity} | Strat: {strategy}")
            order = self.wrapper.place_order(
                symbol, "SELL", quantity, order_type="MARKET")

            if order:
                self._reset_position_state(symbol)
                return True
        except Exception as e:
            logger.error(f"❌ Failed to execute SELL {symbol}: {e}")

        return False

    def _update_position_entry(self, symbol: str, qty: float, price: float):
        self.positions[symbol] = {
            'in_position': True,
            'entry_price': price,
            'qty': qty,
            'entry_time': time.time()
        }
        logger.info(f"📌 Position Locked: {symbol}")

    def _reset_position_state(self, symbol: str):
        """
        Resets state completely after sale.
        """
        if symbol in self.positions:
            del self.positions[symbol]
        logger.info(f"🧹 State Reset for {symbol} (Zero Residue)")

    def get_position(self, symbol: str) -> Optional[dict]:
        return self.positions.get(symbol)
