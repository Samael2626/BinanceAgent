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

    def log_decision(self, reason: str, logger_func):
        """Standardized logging for strategy decisions."""
        logger_func(f"[Strategy: {self.name}] Decision: {reason}")
