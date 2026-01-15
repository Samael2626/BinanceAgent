"""
Binance Trading Bot - Module: binance_wrapper.py
Version: 1.8.0 Stable (c) 2026
"""
from binance.client import Client
from binance.exceptions import BinanceAPIException
from binance import BinanceSocketManager
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Callable
from math import floor, ceil
import asyncio
import threading
import time


class BinanceWrapper:
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        try:
            self.client = Client(api_key, api_secret, testnet=testnet)
            # Patch for python-binance - required for BinanceSocketManager
            self.client.https_proxy = None
            # Test connection by fetching server time
            self.client.get_server_time()
        except BinanceAPIException as e:
            # Handle cases where Binance returns an HTML page (like 502/504)
            if "<html>" in str(e.message).lower():
                error_msg = f"Binance Server Error (502/504 Bad Gateway). The API is currently overloaded or down."
            else:
                error_msg = f"Binance API Error (Code {e.code}): {e.message}"
            raise Exception(error_msg)
        except Exception as e:
            if "502" in str(e) or "504" in str(e):
                raise Exception(
                    f"Binance Server Error (502/504 Bad Gateway). Retrying...")
            raise Exception(f"Error de conexión: {str(e)}")

        self._loop = None
        self._sockets = {}
        self._stop_events = {}
        self._symbol_info_cache = {}  # Cache to avoid redundant API calls

    def get_historical_klines(self, symbol: str, interval: str, limit: int = 100) -> pd.DataFrame:
        try:
            klines = self.client.get_klines(
                symbol=symbol, interval=interval, limit=limit)

            if not klines:
                return pd.DataFrame()

            # data structure: [Open Time, Open, High, Low, Close, Volume, ...]
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])

            # Convert numeric columns
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            # Set index but KEEP timestamp as a column for easier access if needed
            df.set_index('timestamp', inplace=True, drop=False)

            return df[numeric_cols + ['timestamp']]

        except BinanceAPIException as e:
            print(f"Binance API Exception in get_historical_klines: {e}")
            return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching data: {e}")
            return pd.DataFrame()

    def get_account_balance(self, asset: str) -> float:
        try:
            balance = self.client.get_asset_balance(asset=asset)
            if balance:
                return float(balance['free'])
            return 0.0
        except Exception as e:
            print(f"Error getting balance: {e}")
            return 0.0

    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Fetches symbol info with basic caching (5 min)."""
        now = time.time()

        if symbol in self._symbol_info_cache:
            info, expiry = self._symbol_info_cache[symbol]
            if now < expiry:
                return info

        try:
            info = self.client.get_symbol_info(symbol)
            if info:
                # Cache for 5 minutes
                self._symbol_info_cache[symbol] = (info, now + 300)
            return info
        except Exception as e:
            print(f"Error getting symbol info: {e}")
            return None

    def normalize_quantity(self, symbol: str, quantity: float) -> Optional[float]:
        """Rounds quantity to the nearest stepSize for the symbol."""
        info = self.get_symbol_info(symbol)
        if not info:
            return quantity

        for f in info['filters']:
            if f['filterType'] in ['LOT_SIZE', 'MARKET_LOT_SIZE']:
                step_size = float(f['stepSize'])
                precision = int(round(-np.log10(step_size)))
                normalized = floor(
                    quantity * (10**precision)) / (10**precision)
                return normalized
        return quantity

    def adjust_to_min_notional(self, symbol: str, quantity: float, price: float, is_quote_qty: bool = False) -> Optional[float]:
        """Checks if quantity * price < MIN_NOTIONAL and adjusts if needed."""
        info = self.get_symbol_info(symbol)
        if not info:
            return None

        filters = {f['filterType']: f for f in info['filters']}

        # Priority: NOTIONAL (modern) > MIN_NOTIONAL (legacy)
        min_notional = 6.0  # Default conservative minimum
        if 'NOTIONAL' in filters:
            min_notional = float(filters['NOTIONAL']['minNotional'])
        elif 'MIN_NOTIONAL' in filters:
            min_notional = float(filters['MIN_NOTIONAL']['minNotional'])

        notional = quantity if is_quote_qty else quantity * price

        # Buffer: Always aim slightly above the minimum to avoid floating point issues
        target_notional = max(min_notional * 1.05, 6.0)

        if notional >= min_notional:
            return None

        if is_quote_qty:
            return target_notional

        # For base quantity, we must respect LOT_SIZE
        lot_filter = filters.get('LOT_SIZE') or filters.get('MARKET_LOT_SIZE')
        if not lot_filter:
            return None

        step_size = float(lot_filter['stepSize'])
        required_qty = target_notional / price
        precision = int(round(-np.log10(step_size)))
        adjusted_qty = ceil(required_qty * (10**precision)) / (10**precision)

        # double check
        if adjusted_qty * price < min_notional:
            adjusted_qty += step_size

        return adjusted_qty

    def validate_order(self, symbol: str, quantity: float, price: float, is_quote_qty: bool = False) -> tuple[bool, str]:
        """Validates if an order meets Binance filters."""
        info = self.get_symbol_info(symbol)
        if not info:
            return True, "OK"

        filters = {f['filterType']: f for f in info['filters']}

        # 1. LOT_SIZE check (only if not using quote quantity)
        if not is_quote_qty:
            lot_filter = filters.get(
                'LOT_SIZE') or filters.get('MARKET_LOT_SIZE')
            if lot_filter:
                min_qty = float(lot_filter['minQty'])
                max_qty = float(lot_filter['maxQty'])
                if quantity < min_qty:
                    return False, f"Cantidad {quantity} menor al mínimo ({min_qty} {symbol.replace('USDT', '')})"
                if quantity > max_qty:
                    return False, f"Cantidad {quantity} excede el máximo ({max_qty})"

        # 2. NOTIONAL check
        min_notional = 5.0
        if 'NOTIONAL' in filters:
            min_notional = float(filters['NOTIONAL']['minNotional'])
        elif 'MIN_NOTIONAL' in filters:
            min_notional = float(filters['MIN_NOTIONAL']['minNotional'])

        notional = quantity if is_quote_qty else quantity * price
        if notional < min_notional:
            type_str = "Monto" if is_quote_qty else f"Valor ({quantity} * {price})"
            return False, f"{type_str} {notional:.2f} USDT menor al mínimo permitido de {min_notional} USDT"

        return True, "OK"

    def place_order(self, symbol: str, side: str, quantity: float, order_type: str = 'MARKET', quote_order_qty: float = None):
        try:
            params = {"symbol": symbol, "side": side, "type": order_type}
            if quote_order_qty:
                params["quoteOrderQty"] = "{:.8f}".format(
                    float(quote_order_qty)).rstrip('0').rstrip('.')
            else:
                final_qty = self.normalize_quantity(symbol, quantity)
                params["quantity"] = "{:.8f}".format(
                    float(final_qty)).rstrip('0').rstrip('.')

            order = self.client.create_order(**params)
            return order
        except Exception as e:
            print(f"Error placing order: {e}")
            raise e

    def start_kline_socket(self, symbol: str, interval: str, callback: Callable):
        """Starts a kline socket for the given symbol and interval with auto-reconnect."""
        # Ensure only one kline socket is active at a time to prevent "mixed state"
        for name in list(self._stop_events.keys()):
            if name.startswith("kline_"):
                self.stop_socket(name)

        name = f"kline_{symbol}_{interval}"

        stop_event = threading.Event()
        self._stop_events[name] = stop_event

        def run_socket():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                while not stop_event.is_set():  # Outer loop for reconnection
                    try:
                        async def main():
                            client = Client(
                                self.api_key, self.api_secret, testnet=self.testnet)
                            client.https_proxy = None
                            bsm = BinanceSocketManager(client)
                            async with bsm.kline_socket(symbol=symbol, interval=interval) as stream:
                                while not stop_event.is_set():
                                    try:
                                        msg = await asyncio.wait_for(stream.recv(), timeout=2.0)
                                        if msg and 'k' in msg:
                                            callback(msg)
                                    except asyncio.TimeoutError:
                                        continue

                        loop.run_until_complete(main())
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        if stop_event.is_set():
                            break

                        # Log error safely
                        error_msg = str(e)
                        # Suppress reconnection errors if already shutting down
                        if "cannot schedule new futures after shutdown" in error_msg:
                            break

                        print(
                            f"Kline Socket connection failed/closed: {error_msg}. Reconnecting in 5s...", flush=True)

                        # Stop retrying if it's a fatal credential error
                        if "code=-2015" in error_msg or "code=-1100" in error_msg:
                            print(
                                "❌ Fatal API Error detected in Kline Socket. Stopping reconnect loop.", flush=True)
                            break

                        stop_event.wait(5)
            finally:
                # Properly close the loop to prevent "cannot schedule" errors
                try:
                    loop.close()
                except Exception:
                    pass

        t = threading.Thread(target=run_socket, daemon=True)
        t.start()
        self._sockets[name] = t

    def start_user_socket(self, callback: Callable):
        """Starts a user data socket for account updates with auto-reconnect."""
        name = "user"
        self.stop_socket(name)

        stop_event = threading.Event()
        self._stop_events[name] = stop_event

        def run_socket():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                while not stop_event.is_set():  # Outer loop for reconnection
                    try:
                        async def main():
                            client = Client(
                                self.api_key, self.api_secret, testnet=self.testnet)
                            client.https_proxy = None
                            bsm = BinanceSocketManager(client)
                            async with bsm.user_socket() as stream:
                                while not stop_event.is_set():
                                    try:
                                        msg = await asyncio.wait_for(stream.recv(), timeout=2.0)
                                        callback(msg)
                                    except asyncio.TimeoutError:
                                        continue

                        loop.run_until_complete(main())
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        if stop_event.is_set():
                            break

                        # Log error safely
                        error_msg = str(e)
                        # Suppress reconnection errors if already shutting down
                        if "cannot schedule new futures after shutdown" in error_msg:
                            break

                        print(
                            f"User Socket connection failed/closed: {error_msg}. Reconnecting in 5s...", flush=True)

                        # Stop retrying if it's a fatal credential error
                        if "code=-2015" in error_msg or "code=-1100" in error_msg:
                            print(
                                "❌ Fatal API Error detected in User Socket. Stopping reconnect loop.", flush=True)
                            break

                        stop_event.wait(5)
            finally:
                # Properly close the loop to prevent "cannot schedule" errors
                try:
                    loop.close()
                except Exception:
                    pass

        t = threading.Thread(target=run_socket, daemon=True)
        t.start()
        self._sockets[name] = t

    def stop_socket(self, name: str):
        """Stops a specific socket by name."""
        if name in self._stop_events:
            self._stop_events[name].set()
            # Wait for thread to finish if necessary, but daemon threads will die anyway
            del self._stop_events[name]

        if name in self._sockets:
            del self._sockets[name]

    def stop_all_sockets(self):
        """Stops all running sockets."""
        for name in list(self._stop_events.keys()):
            self.stop_socket(name)
