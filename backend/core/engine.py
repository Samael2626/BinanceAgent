import time
import threading
import traceback
from typing import Dict, Optional
from backend.utils.logger import logger
# Future imports
# from backend.services.market_data import MarketDataService
# from backend.services.order_manager import OrderManager


class TradingEngine:
    """
    The Core Brain of the Trading System.
    Orchestrates data flow, strategy execution, and risk checks.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one Engine runs per bot instance."""
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(TradingEngine, cls).__new__(cls)
        return cls._instance

    def __init__(self, user_id: int):
        if hasattr(self, 'initialized'):
            return

        self.user_id = user_id
        self.running = False
        self.paused = False
        self.shutdown_event = threading.Event()
        self.main_thread: Optional[threading.Thread] = None

        # Components (Service Injection)
        self.market_data = None  # Will be MarketDataService()
        self.order_manager = None  # Will be OrderManager()
        self.notifiers = []

        self.initialized = True
        logger.info(f"🚀 TradingEngine initialized for User {user_id}")

    def start(self):
        """Starts the main event loop and services."""
        if self.running:
            logger.warning("Engine already running.")
            return

        logger.info("Starting Trading Engine...")
        self.running = True
        self.shutdown_event.clear()

        # Start Services (Placeholder for now)
        # self.market_data.start()

        # Start Main Loop
        self.main_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.main_thread.start()
        logger.info("✅ Engine Started Successfully")

    def stop(self):
        """Gracefully shuts down the engine."""
        logger.info("Stopping Trading Engine...")
        self.running = False
        self.shutdown_event.set()

        if self.main_thread:
            self.main_thread.join(timeout=5)

        logger.info("🛑 Engine Halted")

    def _run_loop(self):
        """Main heartbeat loop."""
        logger.info("💓 Heartbeat Loop Active")
        while self.running and not self.shutdown_event.is_set():
            try:
                if self.paused:
                    time.sleep(1)
                    continue

                # 1. Tick Market Data
                # self.market_data.tick()

                # 2. Check Strategies
                # self._check_strategies()

                # 3. Health Check
                # self._health_check()

                time.sleep(1)  # Main tick rate (adaptive later)

            except Exception as e:
                logger.error(f"Critical Error in Engine Loop: {e}")
                logger.error(traceback.format_exc())
                # Safe-Boot or Auto-Restart logic could go here
                time.sleep(5)

    def pause(self):
        self.paused = True
        logger.info("⏸️ Engine Paused")

    def resume(self):
        self.paused = False
        logger.info("▶️ Engine Resumed")
