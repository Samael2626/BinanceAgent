"""
Binance Trading Bot - Module: bot_logic.py
Version: 1.8.0 Stable (c) 2026
"""
import pandas as pd
import pandas_ta as ta
import time
import threading
from datetime import datetime
from .binance_wrapper import BinanceWrapper
from .config import API_KEY, API_SECRET, TELEGRAM_BOT_TOKEN, TRADING_MODE
from .database import DatabaseManager
from .telegram_notifier import TelegramNotifier
from .indicators import calculate_indicators

# Strategy Imports
from .strategies.rsi_rebound import RSIReboundStrategy
from .strategies.breakout_volume import BreakoutVolumeStrategy
from .strategies.smart_scalper import SmartScalperStrategy
from .strategies.smart_scalper import SmartScalperStrategy
from .predictive_modules import PredictiveEngine
from .services.market_data import MarketDataService


class BinanceBot:
    """
    Main Binance Trading Bot class.
    Handles market data updates, strategy execution, risk management, and trade tracking.
    """

    def __init__(self, user_id: int = 1):
        self.user_id = user_id
        self.db = DatabaseManager()
        self.lock = threading.Lock()
        self.is_running = self.db.get_state(
            "is_running", "False", user_id=user_id) == "True"

        # Core Settings
        self.symbol = self.db.get_setting("symbol", "BTCUSDT", user_id=user_id)
        self.timeframe = self.db.get_setting(
            "timeframe", "15m", user_id=user_id)  # Default updated to 15m
        self.client = None
        self.current_price = 0.0
        self.balance = 0.0
        self.crypto_balance = 0.0

        # Strategy Settings
        self.min_balance_threshold = float(
            self.db.get_setting("min_balance", 0.0, user_id=user_id))
        self.trade_qty = float(self.db.get_setting(
            "trade_qty", 35.0, user_id=user_id))  # Default updated to 35 USDT
        self.buy_rsi = float(self.db.get_setting(
            "buy_rsi", 21.0, user_id=user_id))  # Default updated to 21
        self.sell_rsi = float(self.db.get_setting(
            "sell_rsi", 75.0, user_id=user_id))  # Default updated to 75
        self.ema_length = int(self.db.get_setting(
            "ema_length", 200, user_id=user_id))
        self.macd_fast = int(self.db.get_setting(
            "macd_fast", 12, user_id=user_id))
        self.macd_slow = int(self.db.get_setting(
            "macd_slow", 26, user_id=user_id))
        self.macd_signal_period = int(
            self.db.get_setting("macd_signal", 9, user_id=user_id))
        self.active_strategy = self.db.get_setting(
            "active_strategy", "rsi", user_id=user_id)
        self.trade_qty_type = self.db.get_setting(
            # Default updated to quote (USDT)
            "trade_qty_type", "quote", user_id=user_id)

        # Risk Management Settings
        self.stop_loss_pct = float(self.db.get_setting(
            "stop_loss_pct", 3.2, user_id=user_id))  # Default 3.2%
        self.take_profit_pct = float(self.db.get_setting(
            "take_profit_pct", 1.3, user_id=user_id))  # Default 1.3%
        self.max_dca_orders = int(self.db.get_setting(
            "max_dca_orders", 2, user_id=user_id))  # Default 2
        self.dca_step_pct = float(self.db.get_setting(
            "dca_step_pct", 1.5, user_id=user_id))  # Default 1.5%
        self.trailing_enabled = False  # FORCE DISABLED BY DEFAULT
        self.trailing_stop_pct = float(self.db.get_setting(
            "trailing_stop_pct", 1.0, user_id=user_id))
        self.sniper_mode = False  # FORCE DISABLED BY DEFAULT
        self.dca_enabled = self.db.get_state(
            "dca_enabled", False, user_id=user_id)

        # Initialize Strategies
        self.strategies = {
            "rsi_rebound": RSIReboundStrategy(),
            "breakout_volume": BreakoutVolumeStrategy(),
            "smart_scalper": SmartScalperStrategy(),
            "rsi": RSIReboundStrategy(),  # Backward compatibility
            "ema_rsi": RSIReboundStrategy(),  # Backward compatibility fallback
            "multi": SmartScalperStrategy(),  # Backward compatibility fallback
            "rebound": RSIReboundStrategy(),  # Backward compatibility
            "smart_scalping": SmartScalperStrategy(),  # Backward compatibility
            "scalper_pro": SmartScalperStrategy()  # Backward compatibility
        }

        # Operational Settings
        self.notify_signals = self.db.get_setting(
            "notify_signals", "False", user_id=user_id) == "True"
        self.sell_mode = self.db.get_setting(
            "sell_mode", "full", user_id=user_id)
        self.enable_buying = self.db.get_state(
            "enable_buying", True, user_id=user_id)
        self.enable_selling = self.db.get_state(
            "enable_selling", True, user_id=user_id)

        # New Quantitative Filter Controls
        self.enable_trend_filter = self.db.get_setting(
            "enable_trend_filter", "True", user_id=user_id) == "True"
        self.enable_vol_filter = self.db.get_setting(
            "enable_vol_filter", "True", user_id=user_id) == "True"
        self.enable_mutual_exclusion = self.db.get_setting(
            "enable_mutual_exclusion", "True", user_id=user_id) == "True"

        self.testnet_commission_pct = float(self.db.get_setting(
            "testnet_commission_pct", 0.1, user_id=user_id))
        self.use_real_data = self.db.get_setting(
            "use_real_data", "False", user_id=user_id) == "True"

        # Telegram Notifier
        self.tg_token = TELEGRAM_BOT_TOKEN
        self.tg_chat_id = self.db.get_setting(
            "tg_chat_id", "", user_id=user_id)
        self.telegram_enabled = self.db.get_setting(
            "telegram_enabled", "True", user_id=user_id) == "True"
        self.notifier = TelegramNotifier(
            self.tg_token, self.tg_chat_id, enabled=self.telegram_enabled)

        # RSI Alert Settings & State
        self.enable_rsi_alerts = self.db.get_setting(
            "enable_rsi_alerts", "True", user_id=user_id) == "True"
        self.enable_urgent_alerts = self.db.get_setting(
            "enable_urgent_alerts", "True", user_id=user_id) == "True"

        # Adjustable Alert Thresholds
        self.rsi_alert_buy_urgent = float(self.db.get_setting(
            "rsi_alert_buy_urgent", 21.0, user_id=user_id))
        self.rsi_alert_buy_normal = float(self.db.get_setting(
            "rsi_alert_buy_normal", 31.0, user_id=user_id))
        self.rsi_alert_sell_urgent = float(self.db.get_setting(
            "rsi_alert_sell_urgent", 75.0, user_id=user_id))
        self.rsi_alert_sell_normal = float(self.db.get_setting(
            "rsi_alert_sell_normal", 65.0, user_id=user_id))

        # Anti-spam state per symbol (dict of dicts)
        # Format: {"BTCUSDT": {"buy_normal": False, "buy_urgent": False, ...}, ...}
        self._rsi_alert_states = {}

        # Internal State
        self.last_signal = "none"
        self.crypto_dust = 0.0
        self.partial_traces = []
        self.last_buy_price = 0.0
        self.open_position = False
        self.entry_price = 0.0
        self.accumulated_qty = 0.0
        self.position_orders = 0
        self.highest_price = 0.0

        stored_initial_balance = self.db.get_state(
            "initial_balance", user_id=user_id)
        self.initial_balance = float(
            stored_initial_balance) if stored_initial_balance else 0.0
        self._load_symbol_state()

        self.pnl = 0.0
        self.rsi = 0.0
        self.macd = 0.0
        self.macd_signal = 0.0
        self.macd_hist = 0.0
        self.trend_ema = 0.0
        self.ema_2 = 0.0
        self.ema_7 = 0.0
        self.bb_upper = 0.0
        self.bb_middle = 0.0
        self.bb_lower = 0.0
        self.vol_sma = 0.0
        self.current_vol = 0.0
        self.last_status_time = 0
        self.pnl = 0.0
        self.daily_pnl = 0.0
        self.daily_start_balance = float(self.db.get_state(
            "daily_start_balance", 0.0, user_id=user_id))

        self.history = []
        self.trades = self.db.get_trades(user_id=user_id)
        self.monitor_active = False
        self.data_client = None
        self.market_data_service = None

        # Restore credentials
        creds = self.db.get_state("credentials", is_json=True, user_id=user_id)
        if creds:
            self._init_client(creds.get("api_key"), creds.get(
                "api_secret"), creds.get("is_testnet", True))

        # Predictive Module State
        self.predictive_engine = PredictiveEngine()
        self.prediction = {}

    def _get_scoped_key(self, key: str) -> str:
        """Returns a key scoped to the current symbol for state persistence."""
        return f"{key}_{self.symbol}"

    def _load_symbol_state(self):
        """Loads state variables specific to the current trading pair."""
        user_id = self.user_id
        self.entry_price = float(self.db.get_state(
            self._get_scoped_key("entry_price"), 0.0, user_id=user_id))
        self.position_orders = int(self.db.get_state(
            self._get_scoped_key("position_orders"), 0, user_id=user_id))
        self.accumulated_qty = float(self.db.get_state(
            self._get_scoped_key("accumulated_qty"), 0.0, user_id=user_id))
        self.highest_price = float(self.db.get_state(
            self._get_scoped_key("highest_price"), 0.0, user_id=user_id))
        self._log(
            f"State loaded for {self.symbol}: Pos={self.position_orders}, Entry={self.entry_price}, Qty={self.accumulated_qty}", "DEBUG")

    def _reset_position_state(self):
        """Centralized method to completely clear internal position state (Zero residue principle)."""
        self.highest_price = 0.0
        self.entry_price = 0.0
        self.accumulated_qty = 0.0
        self.position_orders = 0
        self.crypto_dust = 0.0
        self.partial_traces = []
        self.last_buy_price = 0.0
        self.open_position = False

        # Persist the clean state
        state_to_save = {
            "entry_price": 0.0,
            "position_orders": 0,
            "accumulated_qty": 0.0,
            "highest_price": 0.0,
            "open_position": False,
            "last_buy_price": 0.0
        }
        for k, v in state_to_save.items():
            self.db.save_state(self._get_scoped_key(k),
                               v, user_id=self.user_id)

        self._log("🧹 State completely reset (Zero residue principle).", "INFO")

    def set_credentials(self, api_key: str, api_secret: str, is_testnet: bool):
        """Sets or updates Binance credentials and re-initializes client."""
        if self._init_client(api_key, api_secret, is_testnet):
            return {"status": "success", "message": "Conectado exitosamente"}
        return {"status": "error", "message": "Error al conectar con las credenciales proporcionadas"}

    def _init_client(self, api_key: str, api_secret: str, is_testnet: bool) -> bool:
        """Initializes the Binance client and starts background services."""
        try:
            self._log("Validating credentials...", "DEBUG")

            # CRITICAL: Sanitize credentials to prevent APIError -1100 (illegal characters)
            # Remove whitespace, newlines, and other non-alphanumeric characters
            api_key = api_key.strip() if api_key else ""
            api_secret = api_secret.strip() if api_secret else ""

            # Validate format (Binance requires alphanumeric only, 36-64 chars)
            if not api_key or not api_secret:
                raise ValueError("API Key and Secret cannot be empty")

            if not api_key.replace('-', '').isalnum():
                raise ValueError(
                    "API Key contains invalid characters (only alphanumeric allowed)")

            if len(api_key) < 36 or len(api_key) > 64:
                self._log(
                    f"⚠️ API Key length ({len(api_key)}) outside normal range (36-64 chars)", "WARNING")

            self.client = BinanceWrapper(
                api_key, api_secret, testnet=is_testnet)
            self.is_testnet = is_testnet
            self.db.save_state("credentials", {
                               "api_key": api_key, "api_secret": api_secret, "is_testnet": is_testnet}, user_id=self.user_id)

            # Initialize data client (Mainnet) if using real data in testnet
            if is_testnet and self.use_real_data:
                try:
                    # Use None for keys for public access to Mainnet data
                    self.data_client = BinanceWrapper(
                        None, None, testnet=False)
                    self._log(
                        "✅ Real Market Data client initialized (Public Access)")
                except Exception as de:
                    self._log(
                        f"⚠️ Could not init Real Data client: {de}. Falling back to Testnet data.", "WARNING")
                    self.data_client = self.client
            else:
                self.data_client = self.client

            # Initialize Market Data Service with the correct Data Client
            self.market_data_service = MarketDataService(self.data_client)
            self._log(
                "✅ Market Data Service initialized with Smart Caching", "DEBUG")

            threading.Thread(
                target=self._finish_initialization, daemon=True).start()
            self._log(
                f"✅ Credentials validated. Bot calibrated (1000 klines, Vol filter adj). Initializing...", "INFO")
            return True
        except Exception as e:
            self._log(f"❌ Credential validation failed: {e}", "ERROR")
            return False

    def _finish_initialization(self):
        """Background initialization of WebSockets and account data."""
        try:
            # Kline socket always uses data_client (which might be the same as client)
            self.data_client.start_kline_socket(
                self.symbol, self.timeframe, self._on_kline_msg)
            try:
                self.client.start_user_socket(self._on_user_msg)
                self._log("✅ User WebSocket connected", "DEBUG")
            except Exception as ws_error:
                self._log(f"⚠️ User WebSocket failed: {ws_error}", "WARNING")

            if not self.monitor_active:
                self.monitor_active = True
                threading.Thread(target=self._loop, daemon=True).start()

            self._update_account_balances()
            self._log(
                f"✅ Binance Client fully initialized ({'Testnet' if self.is_testnet else 'REAL ACCOUNT'})")
        except Exception as e:
            self._log(f"Error during background initialization: {e}", "ERROR")

    def _update_account_balances(self):
        """Fetches current account balances from Binance."""
        if not self.client:
            return
        try:
            self.balance = self.client.get_account_balance("USDT")
            asset = self.symbol.replace("USDT", "")
            self.crypto_balance = self.client.get_account_balance(asset)
            # Log critical balance info
            self._log(
                f"📊 Balance leído: {self.balance:.2f} USDT | {self.crypto_balance:.6f} {asset}", "DEBUG")
        except Exception as e:
            self._log(f"Balance fetch failed: {e}", "WARNING")

    def _on_kline_msg(self, msg):
        """Handles incoming WebSocket message for candlestick updates."""
        try:
            # Drop messages from other symbols (residual from stopped sockets)
            if msg.get('s') != self.symbol:
                return

            k = msg['k']
            new_price = float(k['c'])

            with self.lock:
                self.current_price = new_price

                # Update history in real-time so chart stays synchronized
                if self.history:
                    # Binance kline start time is in ms
                    current_candle_time = int(k['t']) // 1000

                    if self.history[-1]['time'] == current_candle_time:
                        # Update current candle
                        self.history[-1]['close'] = new_price
                        self.history[-1]['high'] = max(
                            self.history[-1]['high'], float(k['h']))
                        self.history[-1]['low'] = min(self.history[-1]
                                                      ['low'], float(k['l']))
                    elif current_candle_time > self.history[-1]['time']:
                        # New candle started, append it
                        self.history.append({
                            "time": current_candle_time,
                            "open": float(k['o']),
                            "high": float(k['h']),
                            "low": float(k['l']),
                            "close": new_price
                        })
                        if len(self.history) > 100:
                            self.history.pop(0)

            if k['x']:  # Candle closed
                threading.Thread(target=self._update_market_data,
                                 daemon=True).start()
        except Exception as e:
            self._log(f"Error handling kline message: {e}", "ERROR")

    def _on_user_msg(self, msg):
        """Handles incoming WebSocket message for account updates."""
        if msg['e'] == 'outboundAccountPosition':
            for b in msg['B']:
                if b['a'] == 'USDT':
                    with self.lock:
                        self.balance = float(b['f'])
                elif b['a'] == self.symbol.replace("USDT", ""):
                    with self.lock:
                        self.crypto_balance = float(b['f'])

    def _update_market_data(self):
        """Fetches historical data and updates all technical indicators."""
        try:
            # Increase limit for better EMA accuracy (needs warm-up)
            # Use MarketDataService if available, else fallback
            if self.market_data_service:
                df = self.market_data_service.get_historical_data(
                    self.symbol, self.timeframe, limit=1000)
            else:
                df = self.data_client.get_historical_klines(
                    self.symbol, self.timeframe, limit=1000)

            if df.empty:
                return False

            indicators = calculate_indicators(df, self.get_settings())

            # Calculate additional indicators for Frontend Chart (Visualization only)
            # We use append=True to add columns to the dataframe
            try:
                # RSI 14
                df.ta.rsi(length=14, append=True)
                # SMA 50 & 200 (Requested by User for Visuals)
                df.ta.sma(length=50, append=True)
                df.ta.sma(length=200, append=True)
            except Exception as e:
                self._log(
                    f"Error calculating chart indicators: {e}", "WARNING")

            with self.lock:
                for key, val in indicators.items():
                    setattr(self, key, val)

                # Run Predictive Analysis
                if self.current_price > 0:
                    self.prediction = self.predictive_engine.analyze(
                        df, self.current_price)

                # Construct history with all necessary fields for the Pro Chart
                # We take the tail(200) to ensure we have enough data for the chart view
                history_data = []
                for t, r in df.tail(200).iterrows():
                    # Safely get values, handling potential missing columns or NaNs
                    rsi_val = r.get('RSI_14')
                    sma50_val = r.get('SMA_50')
                    sma200_val = r.get('SMA_200')

                    # Convert pandas Timestamp to int timestamp if needed
                    ts = int(t.timestamp()) if hasattr(
                        t, 'timestamp') else int(t)

                    row = {
                        "time": ts,
                        "open": float(r['open']),
                        "high": float(r['high']),
                        "low": float(r['low']),
                        "close": float(r['close']),
                        "volume": float(r['volume']),
                        "rsi": float(rsi_val) if pd.notna(rsi_val) else None,
                        "sma_50": float(sma50_val) if pd.notna(sma50_val) else None,
                        "sma_200": float(sma200_val) if pd.notna(sma200_val) else None,
                    }
                    history_data.append(row)

                self.history = history_data

            return True
        except Exception as e:
            self._log(f"Market update error: {e}", "ERROR")
            return False

    def _loop(self):
        """Main execution loop for checking strategies and risk."""
        self._update_market_data()

        last_rsi_alert_check = 0

        while self.monitor_active:
            now_time = time.time()

            # 1. HEARTBEAT & MARKET SYNC (Every 30s)
            if now_time - self.last_status_time > 30:
                # Refresh market data background
                threading.Thread(
                    target=self._update_market_data, daemon=True).start()
                self._print_status_heartbeat()
                self.last_status_time = now_time

            # 2. ACCOUNT SYNC & SAFETY RESET (Every 10s)
            # We use a secondary timer or just check modulo if loop sleep is small
            if self.client and int(now_time) % 10 == 0:
                try:
                    with self.lock:
                        self._update_account_balances()

                        # Zero Residue Sync: If Binance says crypto_balance is ~0, but we think we have a position, RESET.
                        current_notional = self.crypto_balance * \
                            (self.current_price if self.current_price > 0 else 1)
                        if self.accumulated_qty > 0 and current_notional < 1.0:
                            self._log(
                                f"🔄 Sync Reset: Real balance too low ({current_notional:.2f} USDT). Clearing ghost position.", "DEBUG")
                            self._reset_position_state()

                        if self.current_price > 0:
                            self._update_equity()
                except Exception as e:
                    self._log(f"PnL/Sync Error: {e}", "ERROR")

            # 3. STRATEGY EXECUTION (Only if running)
            if self.is_running and self.client:
                try:
                    with self.lock:
                        if self.current_price > 0:
                            self._run_strategies()
                            if self.notify_signals:
                                self._check_signals_for_alerts()

                    # 4. MULTI-SYMBOL RSI ALERTS (Optimized Check every 60s)
                    if self.enable_rsi_alerts and (now_time - last_rsi_alert_check > 60):
                        threading.Thread(
                            target=self._check_rsi_alerts, daemon=True).start()
                        last_rsi_alert_check = now_time

                except Exception as e:
                    self._log(f"Strategy Loop Error: {e}", "ERROR")

            # Small sleep to prevent CPU spiking, most logic is gated by timers above
            time.sleep(2)

    def _print_status_heartbeat(self):
        """Prints a structured and visual status update to the terminal."""
        import sys
        try:
            now = datetime.now().strftime("%H:%M:%S")
            strat = self.active_strategy.upper()
            icon = "🟢 RUNNING" if self.is_running else "🔴 STOPPED"

            # Use ANSI colors if possible (Windows 10+ supports them)
            # Default to plain text if not
            green = "\033[92m"
            red = "\033[91m"
            blue = "\033[94m"
            yellow = "\033[93m"
            reset = "\033[0m"

            pnl_color = green if self.pnl >= 0 else red
            status_color = green if self.is_running else red

            print(f"\n{blue}┌" + "─" * 60 + f"┐{reset}")
            print(f"{blue}│{reset} {status_color}{icon}{reset} | {now} | {blue}{self.symbol}{reset} @ {yellow}${self.current_price:,.2f}{reset}")
            print(f"{blue}├" + "─" * 60 + f"┤{reset}")
            print(
                f"{blue}│{reset} RSI: {self.rsi:>4.1f} | MACD: {self.macd_hist:>5.2f} | EMA: {self.trend_ema:>8.2f}")
            print(f"{blue}│{reset} Orders: {self.position_orders:>2} | Qty: {self.accumulated_qty:>10.6f} | Entry: {self.entry_price:>8.2f}")
            print(
                f"{blue}│{reset} PnL: {pnl_color}{self.pnl:>8.2f} USDT{reset} | Daily: {self.daily_pnl:>8.2f} | Strategy: {strat}")
            print(f"{blue}└" + "─" * 60 + f"┘{reset}")

            sys.stdout.flush()
        except Exception as e:
            # Fallback if fancy formatting fails
            print(
                f"BOT HEARTBEAT: {self.symbol} ${self.current_price} | RSI: {self.rsi} | PnL: {self.pnl}")

    def _update_equity(self):
        """Calculates current PnL and total account equity (Net of Commissions)."""
        equity = self.balance + (self.crypto_balance * self.current_price)
        if self.initial_balance <= 0:
            self.initial_balance = equity
            self.db.save_state("initial_balance", equity, user_id=self.user_id)

        if self.daily_start_balance <= 0:
            self.daily_start_balance = equity
            self.db.save_state("daily_start_balance",
                               equity, user_id=self.user_id)

        # Calculate Net PnL: Gross PnL - Entry Fee (0.1%) - Exit Fee (0.1%)
        # Note: We calculate net profit based on the movement since the baseline.
        gross_pnl = equity - self.initial_balance
        self.pnl = gross_pnl - (abs(gross_pnl) * 0.002)

        # Daily PnL is strictly Gross Equity change since start of day/reset
        self.daily_pnl = equity - self.daily_start_balance

        self._log(
            f"📊 PNL UPDATE: Total={self.pnl:.2f} | Daily={self.daily_pnl:.2f} | Equity={equity:.2f}", "DEBUG")

    def _print_state_snapshot(self, buy_signal: bool = False, sell_signal: bool = False):
        """Prints a highly visible and structured snapshot of the current bot state."""
        import sys

        # Use simple indicators if we can't find them in strategy (fallback)
        rsi_val = getattr(self, 'rsi', 0.0)

        # ANSI color codes
        yellow = "\033[93m"
        green = "\033[92m"
        red = "\033[91m"
        blue = "\033[94m"
        reset = "\033[0m"
        bold = "\033[1m"

        pnl_color = green if self.pnl >= 0 else red
        buy_sig_color = green if buy_signal else reset
        sell_sig_color = red if sell_signal else reset

        print("\n" + f"{blue}{bold}[STATE SNAPSHOT]{reset}")
        print(f"Symbol: {bold}{self.symbol}{reset}")
        print(f"Active Strategy: {self.active_strategy}")
        print(f"RSI(14): {rsi_val:.1f}")
        print(f"Buy Signal: {buy_sig_color}{str(buy_signal).upper()}{reset}")
        print(
            f"Sell Signal: {sell_sig_color}{str(sell_signal).upper()}{reset}")
        print(
            f"Open Position: {bold}{str(self.accumulated_qty > 0).upper()}{reset}")
        print(f"Last Buy Price: {self.entry_price:.2f}")
        print(f"Net PnL: {pnl_color}{self.pnl:+.4f} USDT{reset}")
        print(f"Sniper Mode: {'ENABLED' if self.sniper_mode else 'DISABLED'}")
        print(
            f"Trailing: {'ENABLED' if self.trailing_enabled else 'DISABLED'}")
        print(f"Balance USDT: {self.balance:.2f}")
        print(f"{blue}-------------------------{reset}\n")
        sys.stdout.flush()

    def _run_strategies(self):
        """Orchestrates strategy execution by delegating to modular strategy instances."""
        if not self.client or not self.strategies:
            return

        strategy_name = self.active_strategy
        strategy = self.strategies.get(strategy_name)

        if not strategy:
            self._log(
                f"⚠️ Estrategia '{strategy_name}' no encontrada. Usando fallback.", "WARNING")
            strategy = self.strategies.get("rsi_rebound")

        # 1. Prepare data for strategy
        indicators = {k: getattr(self, k, 0)
                      for k in strategy.get_required_indicators()}
        # Add extra indicators that might be useful
        indicators['is_lateral'] = getattr(self, 'is_lateral', False)
        indicators['adx'] = getattr(self, 'adx', 0)

        settings = self.get_settings()
        state = {
            "current_price": self.current_price,
            "entry_price": self.entry_price,
            "highest_price": self.highest_price,
            "accumulated_qty": self.accumulated_qty,
            "position_orders": self.position_orders,
            "symbol": self.symbol
        }

        # 2. Check Signals
        buy_sig_checked = False
        sell_sig_checked = False

        if self.accumulated_qty > 0:
            sell_sig_checked = strategy.check_sell_signal(
                indicators, settings, state)
        else:
            # MUTUAL EXCLUSION RULE (Optional): No operar BTC y SOL al mismo tiempo.
            is_blocked_by_exclusion = False
            if self.enable_mutual_exclusion:
                try:
                    asset_to_check = "SOL" if "BTC" in self.symbol else "BTC"
                    other_balance = self.client.get_account_balance(
                        asset_to_check)
                    # If we have more than a tiny amount (dust) in the other asset, block.
                    threshold = 0.0001 if asset_to_check == "BTC" else 0.1
                    if other_balance > threshold:
                        self._log(
                            f"🚫 Mutual Exclusion: Position found in {asset_to_check} ({other_balance}). Clipping BUY signal for {self.symbol}.", "INFO")
                        is_blocked_by_exclusion = True
                except Exception as e:
                    self._log(
                        f"⚠️ Error checking mutual exclusion: {e}", "WARNING")

            if not is_blocked_by_exclusion and not indicators.get('is_lateral', False):
                buy_sig_checked = strategy.check_buy_signal(
                    indicators, settings, state)

        # Requirement: Print block before evaluation (showing what we found)
        self._print_state_snapshot(
            buy_signal=buy_sig_checked, sell_signal=sell_sig_checked)

        # 3. Execution
        if sell_sig_checked:
            self._log(
                f"📉 SEÑAL DE VENTA DETECTADA por {strategy.name}", "INFO")
            qty_to_sell = self._calculate_sell_qty(self.crypto_balance)
            _, _ = self._place_sell_order(
                self.symbol, qty_to_sell, self.current_price, f"{strategy.name}-SELL")

        elif buy_sig_checked:
            self._log(
                f"🚀 SEÑAL DE COMPRA DETECTADA por {strategy.name}", "INFO")
            _, _ = self._place_buy_order(self.symbol, self.trade_qty, self.current_price, f"{strategy.name}-BUY",
                                         is_quote=(self.trade_qty_type == "quote"))

    def _check_dca_allowed(self) -> bool:
        """Determines if a DCA buy order is allowed based on price distance."""
        # Note: This is now largely handled with logging in _run_strategies,
        # but kept for compatibility and manual calls.
        if self.position_orders == 0:
            return True
        if self.sniper_mode:
            return False
        step_price = self.entry_price * (1 - self.dca_step_pct / 100)
        return self.current_price <= step_price

    def _handle_trade_execution(self, trade, side: str, strategy: str, qty: float, price: float):
        """Processes a successful order and updates internal state and database."""
        if not trade:
            return None

        executed_qty = float(trade.get('executedQty', 0))
        quote_qty = float(trade.get('cummulativeQuoteQty', 0))
        actual_price = float(trade.get('price', 0)) or (
            quote_qty / executed_qty if executed_qty > 0 else price)

        commission = 0.0
        final_qty = executed_qty
        if self.is_testnet:
            commission = (
                executed_qty * (self.testnet_commission_pct / 100)) * actual_price
            if side == "BUY":
                final_qty = executed_qty * \
                    (1 - self.testnet_commission_pct / 100)

        pnl = (actual_price - self.entry_price) * \
            executed_qty if side == "SELL" and self.entry_price > 0 else 0.0

        if side == "BUY":
            new_val = (self.accumulated_qty * self.entry_price) + \
                (actual_price * final_qty)
            new_qty = self.accumulated_qty + final_qty
            self.entry_price = new_val / new_qty if new_qty > 0 else actual_price
            self.accumulated_qty = new_qty
            self.position_orders += 1
        else:
            # Update accumulated quantity after a SELL
            self.accumulated_qty = max(
                0.0, self.accumulated_qty - executed_qty)

            # REQUIREMENT: Reset complete internal state after any sale that clears the position
            # Use 1 USDT threshold to handle dust and fees
            current_notional = self.accumulated_qty * actual_price
            if current_notional < 1.0:
                if self.accumulated_qty > 0:
                    self._log(
                        f"🧹 Position cleared: Remaining {self.accumulated_qty:.8f} is Dust/Fees.", "INFO")

                self._reset_position_state()
                # Ensure balance sync
                self._update_account_balances()

        # Persist State
        state_to_save = {
            "entry_price": self.entry_price,
            "position_orders": self.position_orders,
            "accumulated_qty": self.accumulated_qty,
            "highest_price": self.highest_price,
            "open_position": self.open_position,
            "last_buy_price": self.last_buy_price
        }
        for k, v in state_to_save.items():
            self.db.save_state(self._get_scoped_key(k),
                               v, user_id=self.user_id)

        trade_entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": f"{side} ({strategy})", "price": actual_price, "qty": executed_qty,
            "symbol": self.symbol, "pnl": pnl, "rsi": self.rsi, "commission": commission,
            "total": quote_qty or (actual_price * executed_qty)
        }
        self.trades.insert(0, trade_entry)
        self.db.save_trade(trade_entry, user_id=self.user_id)
        self._send_trade_notification(trade_entry)

        # Requirement: Print block after execution
        self._print_state_snapshot()

        return trade

    def _place_buy_order(self, symbol: str, quantity: float, price: float, strategy: str = "AUTO", is_quote: bool = False):
        """Validates and places a BUY order on Binance."""
        try:
            if self.sniper_mode:
                # Calculate All-In amount
                quantity = self.balance * \
                    0.98 if is_quote else (self.balance * 0.98 / price)
                self._log(
                    f"🎯 Sniper Mode Active: Adjusted quantity to {quantity} {'USDT' if is_quote else 'units'}", "DEBUG")

            is_valid, reason = self.client.validate_order(
                symbol, quantity, price, is_quote_qty=is_quote)

            if not is_valid:
                # Try to adjust to min notional if it failed validation
                adj = self.client.adjust_to_min_notional(
                    symbol, quantity, price, is_quote_qty=is_quote)
                if adj:
                    self._log(
                        f"⚠️ Adjusting order from {quantity} to {adj} to meet minimum requirement", "INFO")
                    quantity = adj
                else:
                    self._log(f"❌ Aborting BUY: {reason}", "ERROR")
                    return None, reason

            # Final check: do we actually have the balance for this adjusted quantity?
            total_required = quantity if is_quote else quantity * price
            if total_required > self.balance:
                err_msg = f"Insufficient balance for order: Required {total_required:.2f} USDT, have {self.balance:.2f} USDT"
                self._log(f"❌ {err_msg}", "ERROR")
                return None, err_msg

            trade = self.client.place_order(
                symbol, "BUY", quantity, quote_order_qty=quantity if is_quote else None)

            if not trade:
                err_msg = "Buy order returned None (Check logs for details)"
                self._log(f"❌ {err_msg}", "ERROR")
                return None, err_msg

            return self._handle_trade_execution(trade, "BUY", strategy, quantity, price), None
        except Exception as e:
            err_msg = f"Exception in _place_buy_order: {str(e)}"
            self._log(f"❌ {err_msg}", "ERROR")
            return None, err_msg

    def _place_sell_order(self, symbol: str, quantity: float, price: float, strategy: str = "AUTO"):
        """Validates and places a SELL order on Binance."""
        try:
            # 1. Sanity check: quantity to sell vs balance
            if quantity > self.crypto_balance:
                self._log(
                    f"⚠️ Adjusting sell quantity from {quantity} to available balance {self.crypto_balance}", "DEBUG")
                quantity = self.crypto_balance

            # 2. Log P&L for informational purposes only (no blocking)
            if self.entry_price > 0:
                gross_gain = (price - self.entry_price) * quantity
                commissions = (self.entry_price * quantity *
                               0.001) + (price * quantity * 0.001)
                net_gain = gross_gain - commissions
                position_value = self.entry_price * quantity
                loss_pct = (net_gain / position_value *
                            100) if position_value > 0 else 0

                # Improved logging logic for profit/loss/break-even
                if net_gain > 0.01:
                    label = "✅ Vendiendo con GANANCIA"
                elif net_gain < -0.01:
                    label = "⚠️ Vendiendo con PÉRDIDA"
                else:
                    label = "⚖️ Vendiendo (Empate/Break-even)"

                self._log(
                    f"{label}: {net_gain:.4f} USDT ({loss_pct:.2f}%) - {strategy}", "INFO")

            is_valid, reason = self.client.validate_order(
                symbol, quantity, price)
            if not is_valid:
                adj = self.client.adjust_to_min_notional(
                    symbol, quantity, price, is_quote_qty=False)
                if adj and adj <= self.crypto_balance:
                    self._log(
                        f"⚠️ Adjusting sell qty to {adj} to meet minimum requirement", "INFO")
                    quantity = adj
                else:
                    self._log(f"❌ Aborting SELL: {reason}", "ERROR")
                    return None, reason

            self._log(
                f"📤 Enviando venta: {quantity} {symbol} @ {price} ({strategy})", "INFO")
            trade = self.client.place_order(symbol, "SELL", quantity)

            if not trade:
                err_msg = "Sell order returned None (Check logs for details)"
                self._log(f"❌ {err_msg}", "ERROR")
                return None, err_msg

            return self._handle_trade_execution(trade, "SELL", strategy, quantity, price), None
        except Exception as e:
            err_msg = f"Exception in _place_sell_order: {str(e)}"
            self._log(f"❌ {err_msg}", "ERROR")
            return None, err_msg

    def _calculate_sell_qty(self, balance: float) -> float:
        """Calculates the amount to sell based on the current sell mode."""
        if self.sell_mode == "full":
            return balance
        step = self.trade_qty if self.trade_qty_type == "base" else (
            self.trade_qty / self.current_price if self.current_price > 0 else 0)
        return min(step, balance)

    def _log(self, message: str, level: str = "INFO"):
        """Logs bot messages to console and file, and sends Telegram alerts for errors."""
        import sys
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{level}] {message}"
        print(entry, flush=True)
        with open("backend/logs/bot.log", "a", encoding="utf-8") as f:
            f.write(entry + "\n")
        if level == "ERROR" and self.telegram_enabled:
            self.notifier.send_message(f"🚨 *ERROR BOT*\n{message}")

    def _send_trade_notification(self, t: dict):
        """Sends a formatted trade summary to Telegram."""
        side = "COMPRA" if "BUY" in t['type'].upper() else "VENTA"
        emoji = "🟢" if side == "COMPRA" else "🔴"

        # Determine strategy icon
        strat_icon = "🧠"
        if "MANUAL" in t['type'].upper():
            strat_icon = "🛠"

        msg = (
            f"{emoji} *ZONA DE {side} – {t['symbol']}*\n\n"
            f"💰 *Precio:* ${t['price']:,.2f}\n"
            f"📦 *Cant:* {t['qty']}\n"
            f"📊 *RSI:* {t.get('rsi', 'N/A')}\n"
            f"📜 *Estrategia:* {t['type']}\n"
        )

        if t['pnl'] != 0:
            pnl_emoji = "✅" if t['pnl'] > 0 else "⚠️"
            msg += f"{pnl_emoji} *PnL:* {t['pnl']:.2f} USDT\n"

        msg += f"\n_Última actualización: hace 0 segundos_"

        self.notifier.send_message(msg)

    def _check_rsi_alerts(self):
        """Monitors RSI for ALL coins in the panel and sends alerts based on levels."""
        if not self.client or not self.data_client:
            return

        try:
            from .rsi_snapshot import get_default_symbols, calculate_rsi
            symbols = get_default_symbols()

            # Batch processing would be better, but for now we optimize by not doing it every loop
            for symbol in symbols:
                try:
                    if symbol not in self._rsi_alert_states:
                        self._rsi_alert_states[symbol] = {
                            "buy_normal": False, "buy_urgent": False, "sell_normal": False, "sell_urgent": False}

                    # Fetch klines (Fastest possible fetch)
                    df = self.data_client.get_historical_klines(
                        symbol, self.timeframe, limit=1000)
                    if df is None or df.empty:
                        continue

                    rsi = calculate_rsi(df)
                    if rsi is None or rsi <= 0:
                        continue

                    state = self._rsi_alert_states[symbol]

                    # Logic remains the same but running in background thread now
                    # ... (skipping unchanged alert logic for brevity in this replace call if possible,
                    # but I must provide the full block for replace_file_content)

                    is_buy_urgent = rsi <= self.rsi_alert_buy_urgent
                    is_buy_normal = rsi <= self.rsi_alert_buy_normal and not is_buy_urgent
                    is_sell_urgent = rsi >= self.rsi_alert_sell_urgent
                    is_sell_normal = rsi >= self.rsi_alert_sell_normal and not is_sell_urgent

                    # BUY ALERTS
                    if self.enable_urgent_alerts and is_buy_urgent:
                        if not state["buy_urgent"]:
                            self.notifier.send_message(
                                f"🚨 *URGENT BUY SIGNAL*\n{symbol.replace('USDT', '')}: RSI {rsi:.1f}")
                            state["buy_urgent"], state["buy_normal"] = True, False
                    elif not is_buy_urgent:
                        state["buy_urgent"] = False

                    if is_buy_normal:
                        if not state["buy_normal"]:
                            self.notifier.send_message(
                                f"🟢 *ZONA DE COMPRA – {symbol}*\n📈 *RSI:* {rsi:.1f}")
                            state["buy_normal"] = True
                    elif not is_buy_normal and not is_buy_urgent:
                        state["buy_normal"] = False

                    # SELL ALERTS
                    if self.enable_urgent_alerts and is_sell_urgent:
                        if not state["sell_urgent"]:
                            self.notifier.send_message(
                                f"🔴 *RSI SELL ALERT*\n*{symbol}: RSI {rsi:.1f}*")
                            state["sell_urgent"], state["sell_normal"] = True, False
                    elif not is_sell_urgent:
                        state["sell_urgent"] = False

                    if is_sell_normal:
                        if not state["sell_normal"]:
                            self.notifier.send_message(
                                f"🔴 *RSI SELL ALERT*\n*{symbol}: RSI {rsi:.1f}*")
                            state["sell_normal"] = True
                    elif not is_sell_normal and not is_sell_urgent:
                        state["sell_normal"] = False

                except Exception:
                    continue

        except Exception as e:
            self._log(f"Error in multi-symbol RSI alerts: {e}", "ERROR")

    def manual_buy(self, custom_qty=None, is_quote=None):
        try:
            # Si no se especifica, tomar por defecto segun configuracion
            if is_quote is None:
                is_quote = (self.trade_qty_type == "quote")

            self._log(
                f"🛒 Manual BUY requested: {custom_qty or self.trade_qty} (is_quote={is_quote})", "INFO")

            result, error = self._place_buy_order(
                self.symbol, custom_qty or self.trade_qty, self.current_price, "MANUAL", is_quote=is_quote)

            if result:
                return {"status": "success", "message": f"Orden de compra ejecutada: {result.get('executedQty', '???')} {self.symbol}"}
            else:
                return {"status": "error", "message": f"No se pudo ejecutar la orden: {error}"}
        except Exception as e:
            self._log(f"❌ Error in manual_buy: {str(e)}", "ERROR")
            return {"status": "error", "message": str(e)}

    def manual_sell(self, custom_qty=None):
        try:
            qty_to_sell = custom_qty or self._calculate_sell_qty(
                self.crypto_balance)
            self._log(
                f"🔴 Manual SELL requested: {qty_to_sell} {self.symbol}", "INFO")

            result, error = self._place_sell_order(
                self.symbol, qty_to_sell, self.current_price, "MANUAL")

            if result:
                return {"status": "success", "message": f"Orden de venta ejecutada: {result.get('executedQty', '???')} {self.symbol}"}
            else:
                return {"status": "error", "message": f"No se pudo ejecutar la orden: {error}"}
        except Exception as e:
            self._log(f"❌ Error in manual_sell: {str(e)}", "ERROR")
            return {"status": "error", "message": str(e)}

    def start(self):
        self.is_running = True
        self.db.save_state("is_running", "True", user_id=self.user_id)
        self._log("🚀 Bot iniciado manualmente/auto", "INFO")
        return {"status": "started"}

    def stop(self):
        self.is_running = False
        self._log("🛑 Bot stopped by user.", "INFO")

    def disconnect(self):
        """Cleanly stop all background threads and WebSockets."""
        self.monitor_active = False
        if self.client:
            self.client.stop_all_sockets()
        if self.data_client and self.data_client != self.client:
            self.data_client.stop_all_sockets()
        self._log("🔌 Bot disconnected and WebSockets closed.", "INFO")
        self.db.save_state("is_running", "False", user_id=self.user_id)
        self._log("🛑 Bot detenido manualmente", "INFO")
        return {"status": "stopped"}

    def get_status(self):
        """Returns the current bot status, stats, and settings for the UI."""
        with self.lock:
            wins = len([t for t in self.trades if t.get('pnl', 0) > 0])
            losses = len([t for t in self.trades if t.get('pnl', 0) < 0])
            wr = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0
            net_pnl = sum([t.get('pnl', 0) for t in self.trades])

            return {
                "is_running": self.is_running, "symbol": self.symbol, "mode": "TESTNET" if self.is_testnet else "REAL",
                "price": round(self.current_price, 2), "balance": round(self.balance, 2), "crypto_balance": round(self.crypto_balance, 6),
                "pnl": round(self.pnl, 2), "daily_pnl": round(self.daily_pnl, 2), "rsi": round(self.rsi, 2), "ema_200": round(self.trend_ema, 2),
                "macd": round(self.macd, 2), "macd_signal": round(self.macd_signal, 2), "macd_hist": round(self.macd_hist, 2),
                "bb_upper": round(self.bb_upper, 2), "bb_lower": round(self.bb_lower, 2), "current_vol": round(self.current_vol, 2),
                "history": self.history, "trades": self.trades, "settings": self.get_settings(), "prediction": getattr(self, 'prediction', {}),
                "stats": {"wins": wins, "losses": losses, "win_rate": round(wr, 1), "net_pnl": round(net_pnl, 2), "daily_pnl": round(self.daily_pnl, 2)}
            }

    def get_settings(self):
        """Returns a dictionary of current bot configuration."""
        return {
            "min_balance": self.min_balance_threshold, "trade_qty": self.trade_qty, "buy_rsi": self.buy_rsi,
            "sell_rsi": self.sell_rsi, "active_strategy": self.active_strategy, "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct, "dca_step_pct": self.dca_step_pct, "max_dca_orders": self.max_dca_orders,
            "symbol": self.symbol, "timeframe": self.timeframe, "trade_qty_type": self.trade_qty_type,
            "sell_mode": self.sell_mode, "sniper_mode": self.sniper_mode, "trailing_enabled": self.trailing_enabled,
            "trailing_stop_pct": self.trailing_stop_pct, "enable_buying": self.enable_buying, "enable_selling": self.enable_selling,
            "notify_signals": self.notify_signals, "telegram_enabled": self.telegram_enabled, "tg_chat_id": self.tg_chat_id,
            "testnet_commission_pct": self.testnet_commission_pct, "macd_fast": self.macd_fast, "macd_slow": self.macd_slow,
            "dca_enabled": self.dca_enabled, "enable_rsi_alerts": self.enable_rsi_alerts, "enable_urgent_alerts": self.enable_urgent_alerts,
            "enable_trend_filter": self.enable_trend_filter, "enable_vol_filter": self.enable_vol_filter, "enable_mutual_exclusion": self.enable_mutual_exclusion,
            "rsi_alert_buy_urgent": self.rsi_alert_buy_urgent, "rsi_alert_buy_normal": self.rsi_alert_buy_normal,
            "rsi_alert_sell_urgent": self.rsi_alert_sell_urgent, "rsi_alert_sell_normal": self.rsi_alert_sell_normal
        }

    def update_settings(self, settings: dict):
        """Updates bot settings and persists them to the database."""
        symbol_changed = False
        data_mode_changed = False
        new_symbol = self.symbol
        new_data_mode = self.use_real_data

        mapping = {"min_balance": "min_balance_threshold",
                   "macd_signal": "macd_signal_period"}

        with self.lock:
            if "symbol" in settings and settings["symbol"] != self.symbol:
                symbol_changed = True
                new_symbol = settings["symbol"]

            if "use_real_data" in settings and settings["use_real_data"] != self.use_real_data:
                data_mode_changed = True
                new_data_mode = settings["use_real_data"]

            for k, v in settings.items():
                if isinstance(v, str):
                    if v.replace('.', '', 1).isdigit():
                        v = float(v) if '.' in v else int(v)
                    elif v.lower() == 'true':
                        v = True
                    elif v.lower() == 'false':
                        v = False

                # Apply to standard attributes
                if hasattr(self, k):
                    setattr(self, k, v)

                # Apply to mapped attributes
                if k in mapping:
                    setattr(self, mapping[k], v)

                # Persist to DB (state vs setting)
                state_keys = ["dca_enabled", "sniper_mode", "trailing_enabled",
                              "enable_buying", "enable_selling"]
                if k in state_keys:
                    self.db.save_state(k, v, user_id=self.user_id)
                else:
                    self.db.save_setting(k, v, user_id=self.user_id)

        # TRIGGER ACTIONS OUTSIDE LOCK
        if symbol_changed:
            self._log(f"🔄 Switching symbol to {new_symbol} (Non-blocking)...")
            if self.data_client:
                self.data_client.start_kline_socket(
                    new_symbol, self.timeframe, self._on_kline_msg)

            self._load_symbol_state()
            self._update_account_balances()
            self._update_market_data()
            self._log(f"✅ Symbol switch to {new_symbol} complete.")

        elif data_mode_changed:
            self._log(
                f"🌐 Data mode changed to {'Real' if new_data_mode else 'Testnet'}...")
            if self.data_client:
                self.data_client.stop_all_sockets()

            if self.is_testnet and new_data_mode:
                try:
                    self.data_client = BinanceWrapper(
                        None, None, testnet=False)
                    self._log("✅ Switched to Real Market Data (Mainnet Public)")
                except Exception as de:
                    self._log(f"❌ Error switching to real data: {de}", "ERROR")
                    self.data_client = self.client
            else:
                self.data_client = self.client

            if self.data_client:
                self.data_client.start_kline_socket(
                    self.symbol, self.timeframe, self._on_kline_msg)

            self._update_market_data()

        # Update Telegram notifier if config changed
        if 'tg_chat_id' in settings or 'telegram_enabled' in settings:
            self.notifier.update_config(
                self.tg_token,
                self.tg_chat_id,
                self.telegram_enabled
            )
            self._log(
                f"✅ Telegram config updated: enabled={self.telegram_enabled}, chat_id={'***' if self.tg_chat_id else 'Not set'}")

        return {"status": "success"}

    def disconnect(self):
        """Disconnects the bot and clears credentials."""
        self.stop()

        # Stop all sockets for both clients to ensure clean shutdown
        if self.data_client:
            self.data_client.stop_all_sockets()

        if self.client and self.client != self.data_client:
            self.client.stop_all_sockets()

        self.client = None
        self.data_client = None
        self.is_running = False
        self.db.save_state("credentials", None, user_id=self.user_id)
        return {"status": "disconnected"}

    def reset_position(self):
        """Resets the accumulated position state for the current symbol."""
        with self.lock:
            self.entry_price = self.accumulated_qty = 0.0
            self.position_orders = 0
            for k in ["entry_price", "position_orders", "accumulated_qty"]:
                self.db.save_state(self._get_scoped_key(
                    k), 0.0 if "qty" in k or "price" in k else 0, user_id=self.user_id)
        return {"status": "success"}

    def reset_pnl(self):
        """Resets the total account PnL and trade history."""
        with self.lock:
            # Calculate current actual equity (Real time value of all assets)
            current_equity = self.balance + \
                (self.crypto_balance * self.current_price)

            # Reset calculating markers
            self.initial_balance = current_equity
            self.daily_start_balance = current_equity
            self.pnl = 0.0
            self.daily_pnl = 0.0

            # Persist to local database
            self.db.save_state("initial_balance",
                               current_equity, user_id=self.user_id)
            self.db.save_state("daily_start_balance",
                               current_equity, user_id=self.user_id)
            self.db.clear_trades(user_id=self.user_id)
            self.trades = []

            self._log(
                f"⚠️ PNL RESET: User cleared history at {current_equity:.2f} USDT equity.", "IMPORTANT")
        return {"status": "success"}

    def get_tickers(self):
        """Fetches current prices for major trading pairs."""
        if not self.client:
            return {}
        try:
            # We fetch more targets to improve the converter experience
            tickers = self.client.client.get_all_tickers()
            targets = [
                "BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT",
                "BNBUSDT", "DOTUSDT", "MATICUSDT", "LINKUSDT", "DOGEUSDT",
                "AVAXUSDT"
            ]
            return {t['symbol']: float(t['price']) for t in tickers if t['symbol'] in targets}
        except Exception:
            return {}

    def _check_signals_for_alerts(self):
        """Sends Telegram alerts when buy/sell RSI signals are triggered."""
        sig = "buy" if self.rsi < self.buy_rsi else (
            "sell" if self.rsi > self.sell_rsi else "none")
        if sig != "none" and sig != self.last_signal:
            self.notifier.send_message(
                f"💡 *SEÑAL DE {'COMPRA' if sig == 'buy' else 'VENTA'}*\nSímbolo: {self.symbol}\nPrecio: ${self.current_price}\nRSI: {round(self.rsi, 2)}")
            self.last_signal = sig
        elif sig == "none":
            self.last_signal = "none"
