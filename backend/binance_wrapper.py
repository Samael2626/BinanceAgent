"""
Binance Trading Bot - Module: binance_wrapper.py
Version: 1.8.0 Stable (c) 2026
"""
from binance.client import Client
from binance.exceptions import BinanceAPIException
from binance import BinanceSocketManager
import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Callable, Any
from math import floor, ceil
from decimal import Decimal, ROUND_DOWN, ROUND_UP, InvalidOperation
import asyncio
import threading
import time
from uuid import uuid4

from requests.exceptions import ConnectionError as RequestConnectionError
from requests.exceptions import Timeout as RequestTimeout


logger = logging.getLogger(__name__)


class OrderStatusUnknown(RuntimeError):
    def __init__(self, symbol: str, client_order_id: str):
        self.symbol = symbol
        self.client_order_id = client_order_id
        super().__init__(f"Order status unknown: {symbol} {client_order_id}")


def _reject_order(code: str, detail: str) -> tuple[bool, str]:
    logger.info("ORDER_VALIDATION_REJECT reason=%s detail=%s", code, detail)
    return False, f"{code}: {detail}"


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
        self._futures_symbol_info_cache = {}  # Cache for USDS-M Futures contract filters

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
            for col in numeric_cols + ['quote_asset_volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms', utc=True)

            # Set index but KEEP timestamp as a column for easier access if needed
            df.set_index('timestamp', inplace=True, drop=False)

            return df[numeric_cols + ['quote_asset_volume', 'timestamp', 'close_time']]

        except BinanceAPIException as e:
            print(f"Binance API Exception in get_historical_klines: {e}")
            return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching data: {e}")
            return pd.DataFrame()

    def get_futures_klines(self, symbol: str, interval: str, limit: int = 100) -> pd.DataFrame:
        """Fetches USDⓈ-M Perpetual Futures klines via fapi."""
        try:
            klines = self.client.futures_klines(
                symbol=symbol, interval=interval, limit=limit)
            if not klines:
                return pd.DataFrame()

            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms', utc=True)
            df.set_index('timestamp', inplace=True, drop=False)
            return df[numeric_cols + ['timestamp', 'close_time']]
        except Exception as e:
            logger.error("Error fetching futures klines for %s: %s", symbol, e)
            return pd.DataFrame()

    def get_futures_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Fetches USDⓈ-M Futures contract info with 5-minute caching."""
        now = time.time()
        cache = getattr(self, "_futures_symbol_info_cache", None)
        if cache is None:
            self._futures_symbol_info_cache = {}
            cache = self._futures_symbol_info_cache

        if symbol in cache:
            info, expiry = cache[symbol]
            if now < expiry:
                return info

        try:
            ex_info = self.client.futures_exchange_info()
            symbols = ex_info.get("symbols", []) if ex_info else []
            for item in symbols:
                sym = item.get("symbol")
                if sym:
                    cache[sym] = (item, now + 300)
            return cache.get(symbol, (None, 0))[0]
        except Exception as e:
            logger.error("Error getting futures symbol info for %s: %s", symbol, e)
            return None

    def get_futures_order_book(self, symbol: str, limit: int = 20) -> Dict:
        """Fetches L2 order book for USDⓈ-M Futures."""
        return self.client.futures_order_book(symbol=symbol, limit=limit)

    def get_futures_mark_price_and_funding(self, symbol: str) -> Dict[str, Any]:
        """Fetches markPrice, indexPrice, and lastFundingRate from fapi premiumIndex."""
        try:
            raw = self.client.futures_mark_price(symbol=symbol)
            return {
                "symbol": symbol,
                "markPrice": float(raw.get("markPrice", 0.0) or 0.0),
                "indexPrice": float(raw.get("indexPrice", 0.0) or 0.0),
                "lastFundingRate": float(raw.get("lastFundingRate", 0.0) or 0.0),
                "nextFundingTime": int(raw.get("nextFundingTime", 0) or 0),
            }
        except Exception as e:
            logger.error("Error fetching futures mark price for %s: %s", symbol, e)
            return {
                "symbol": symbol,
                "markPrice": 0.0,
                "indexPrice": 0.0,
                "lastFundingRate": 0.0,
                "nextFundingTime": 0,
            }

    def get_futures_open_interest_hist(self, symbol: str, period: str = "15m", limit: int = 10) -> Dict[str, float]:
        """Returns latest open interest and percentage change over recent bars."""
        try:
            rows = self.client.futures_open_interest_hist(
                symbol=symbol, period=period, limit=max(2, int(limit))
            )
            if not rows or len(rows) < 2:
                return {"open_interest": 0.0, "oi_change_pct": 0.0}
            first_oi = float(rows[0].get("sumOpenInterestValue", rows[0].get("sumOpenInterest", 0.0)) or 0.0)
            last_oi = float(rows[-1].get("sumOpenInterestValue", rows[-1].get("sumOpenInterest", 0.0)) or 0.0)
            oi_change_pct = ((last_oi - first_oi) / first_oi) * 100.0 if first_oi > 0 else 0.0
            return {
                "open_interest": round(last_oi, 4),
                "oi_change_pct": round(oi_change_pct, 4),
            }
        except Exception as e:
            logger.debug("Futures open interest history unavailable for %s: %s", symbol, e)
            return {"open_interest": 0.0, "oi_change_pct": 0.0}

    def validate_futures_order(
        self, symbol: str, quantity: float, price: float
    ) -> tuple[bool, str]:
        """Validates LOT_SIZE, MARKET_LOT_SIZE, and MIN_NOTIONAL on USDⓈ-M Futures."""
        if quantity <= 0:
            return _reject_order("quantity_validation_failed", "quantity must be greater than zero")
        if price <= 0:
            return _reject_order("price_validation_failed", "price must be greater than zero")

        info = self.get_futures_symbol_info(symbol)
        if not info:
            return _reject_order("symbol_info_unavailable", f"futures filters unavailable for {symbol}")
        if info.get("status", "TRADING") != "TRADING":
            return _reject_order("symbol_not_trading", f"symbol {symbol} status is {info.get('status')}")

        filters = {f["filterType"]: f for f in info.get("filters", [])}
        lot_filter = filters.get("LOT_SIZE") or filters.get("MARKET_LOT_SIZE")
        if lot_filter:
            min_qty = float(lot_filter.get("minQty", 0) or 0)
            max_qty = float(lot_filter.get("maxQty", 0) or 0)
            step_size = float(lot_filter.get("stepSize", 0) or 0)
            if min_qty > 0 and quantity < min_qty:
                return _reject_order("min_qty_failed", f"quantity {quantity} < minQty {min_qty}")
            if max_qty > 0 and quantity > max_qty:
                return _reject_order("max_qty_failed", f"quantity {quantity} > maxQty {max_qty}")
            if step_size > 0:
                quantized = self._quantize_to_step(quantity, step_size, ROUND_DOWN)
                if abs(float(quantized) - float(quantity)) > max(step_size / 10.0, 1e-12):
                    return _reject_order("step_size_failed", f"quantity {quantity} does not match stepSize {step_size}")

        min_notional = 5.0
        if "MIN_NOTIONAL" in filters:
            raw_mn = filters["MIN_NOTIONAL"].get("notional") or filters["MIN_NOTIONAL"].get("minNotional")
            if raw_mn is not None:
                min_notional = float(raw_mn)
        elif "NOTIONAL" in filters:
            raw_mn = filters["NOTIONAL"].get("minNotional") or filters["NOTIONAL"].get("notional")
            if raw_mn is not None:
                min_notional = float(raw_mn)

        notional = quantity * price
        if notional < min_notional:
            return _reject_order(
                "min_notional_failed",
                f"Futures notional {notional:.2f} USDT below minNotional {min_notional:.2f} USDT",
            )
        return True, "OK"

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
                return self._quantize_to_step(quantity, f['stepSize'], ROUND_DOWN)
        return quantity

    @staticmethod
    def _quantize_to_step(value: float, step_size: str | float, rounding=ROUND_DOWN) -> float:
        try:
            step = Decimal(str(step_size))
            val = Decimal(str(value))
            if step <= 0:
                return float(value)
            units = (val / step).to_integral_value(rounding=rounding)
            return float(units * step)
        except (InvalidOperation, ValueError, TypeError):
            return float(value)

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

        required_qty = target_notional / price
        adjusted_qty = self._quantize_to_step(
            required_qty, lot_filter['stepSize'], ROUND_UP)

        # double check
        if adjusted_qty * price < min_notional:
            adjusted_qty += float(lot_filter['stepSize'])

        return adjusted_qty

    def validate_order(self, symbol: str, quantity: float, price: float, is_quote_qty: bool = False) -> tuple[bool, str]:
        """Validates if an order meets Binance filters."""
        info = self.get_symbol_info(symbol)
        if not info:
            return True, "OK"

        filters = {f['filterType']: f for f in info['filters']}

        if quantity <= 0:
            return _reject_order("quantity_validation_failed", "quantity must be greater than zero")
        if price <= 0:
            return _reject_order("price_validation_failed", "price must be greater than zero")

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

                normalized = self.normalize_quantity(symbol, quantity)
                step_size = float(lot_filter['stepSize'])
                if normalized is not None and abs(float(normalized) - float(quantity)) > max(step_size / 10.0, 1e-12):
                    return _reject_order("step_size_failed", f"quantity {quantity} does not match stepSize {step_size}")

        if is_quote_qty:
            market_lot = filters.get('MARKET_LOT_SIZE')
            if market_lot and price > 0:
                min_qty = float(market_lot.get('minQty', 0) or 0)
                max_qty = float(market_lot.get('maxQty', 0) or 0)
                approx_qty = quantity / price
                if min_qty > 0 and approx_qty < min_qty:
                    return _reject_order("market_lot_size_failed", f"quote amount {quantity:.2f} buys less than MARKET_LOT_SIZE minQty {min_qty}")
                if max_qty > 0 and approx_qty > max_qty:
                    return _reject_order("market_lot_size_failed", f"quote amount {quantity:.2f} exceeds MARKET_LOT_SIZE maxQty {max_qty}")

        # 2. NOTIONAL check
        min_notional = 5.0
        if 'NOTIONAL' in filters:
            min_notional = float(filters['NOTIONAL']['minNotional'])
        elif 'MIN_NOTIONAL' in filters:
            min_notional = float(filters['MIN_NOTIONAL']['minNotional'])

        notional = quantity if is_quote_qty else quantity * price
        if notional < min_notional:
            type_str = "Monto" if is_quote_qty else f"Valor ({quantity} * {price})"
            return _reject_order("min_notional_failed", f"{type_str} {notional:.2f} USDT below minNotional {min_notional} USDT")

        return True, "OK"

    def place_order(self, symbol: str, side: str, quantity: float, order_type: str = 'MARKET', quote_order_qty: float = None, client_order_id: str | None = None):
        if side == "BUY" and not self.testnet:
            raise RuntimeError("Compras REAL bloqueadas: validacion y auditoria pendientes")
        client_order_id = client_order_id or f"ba{uuid4().hex}"
        try:
            params = {"symbol": symbol, "side": side, "type": order_type,
                      "newClientOrderId": client_order_id, "newOrderRespType": "FULL"}
            if quote_order_qty:
                params["quoteOrderQty"] = "{:.8f}".format(
                    float(quote_order_qty)).rstrip('0').rstrip('.')
            else:
                final_qty = self.normalize_quantity(symbol, quantity)
                params["quantity"] = "{:.8f}".format(
                    float(final_qty)).rstrip('0').rstrip('.')

            order = self.client.create_order(**params)
            return order
        except BinanceAPIException as e:
            if getattr(e, "code", None) == -1007:
                return self._recover_order(symbol, client_order_id)
            logger.error(
                "ORDER_API_ERROR code=%s message=%s",
                getattr(e, "code", None),
                getattr(e, "message", e),
            )
            print(f"Error placing order: {e}")
            raise e
        except (RequestTimeout, RequestConnectionError):
            return self._recover_order(symbol, client_order_id)
        except Exception as e:
            logger.error("ORDER_API_ERROR detail=%s", e)
            print(f"Error placing order: {e}")
            raise e

    def _recover_order(self, symbol: str, client_order_id: str) -> dict:
        try:
            order = self.get_order_by_client_id(symbol, client_order_id)
            if order.get("status") in {"FILLED", "CANCELED", "EXPIRED", "EXPIRED_IN_MATCH"}:
                return order
        except Exception as exc:
            logger.error(
                "ORDER_RECONCILE_ERROR symbol=%s client_order_id=%s error_type=%s code=%s",
                symbol, client_order_id, type(exc).__name__, getattr(exc, "code", None),
            )
        logger.error("ORDER_STATUS_UNKNOWN symbol=%s client_order_id=%s", symbol, client_order_id)
        raise OrderStatusUnknown(symbol, client_order_id)

    def get_order_by_client_id(self, symbol: str, client_order_id: str) -> dict:
        return self.client.get_order(
            symbol=symbol, origClientOrderId=client_order_id)

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

    def get_futures_best_bid_ask(self, symbol: str) -> tuple[float, float, float]:
        """
        Returns `(best_bid, best_ask, tick_size)` for a USDⓈ-M Futures contract
        to support Post-Only Maker (`GTX`) order pegging.
        """
        book = self.get_futures_order_book(symbol=symbol, limit=5)
        bids = (book or {}).get("bids") or []
        asks = (book or {}).get("asks") or []
        best_bid = float(bids[0][0]) if bids else 0.0
        best_ask = float(asks[0][0]) if asks else 0.0
        tick_size = 0.0001
        info = self.get_futures_symbol_info(symbol)
        if info:
            for f in info.get("filters", []):
                if f.get("filterType") == "PRICE_FILTER" and f.get("tickSize"):
                    try:
                        tick_size = float(f["tickSize"])
                    except (ValueError, TypeError):
                        pass
                    break
        return best_bid, best_ask, tick_size

    def start_futures_force_order_socket(self, callback: Callable):
        """
        Starts a lightweight daemon stream for Binance Futures `!forceOrder@arr`
        (all-market forced liquidation orders) with automatic reconnection.
        Consumes < 0.3% CPU and < 10 MB RAM when paired with `ForceOrderWindowTracker`.
        """
        name = "futures_force_orders"
        self.stop_socket(name)

        stop_event = threading.Event()
        self._stop_events[name] = stop_event

        def run_socket():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                while not stop_event.is_set():
                    try:
                        async def main():
                            client = Client(self.api_key, self.api_secret, testnet=False)
                            client.https_proxy = None
                            bsm = BinanceSocketManager(client)
                            # Use futures multiplex / custom socket for !forceOrder@arr
                            async with bsm.futures_multiplex_socket(["!forceOrder@arr"]) as stream:
                                while not stop_event.is_set():
                                    try:
                                        msg = await asyncio.wait_for(stream.recv(), timeout=2.0)
                                        if not msg:
                                            continue
                                        payload = msg.get("data", msg) if isinstance(msg, dict) else msg
                                        if isinstance(payload, list):
                                            for item in payload:
                                                callback(item)
                                        elif isinstance(payload, dict):
                                            callback(payload)
                                    except asyncio.TimeoutError:
                                        continue

                        loop.run_until_complete(main())
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        if stop_event.is_set():
                            break
                        if "cannot schedule new futures after shutdown" in str(e):
                            break
                        stop_event.wait(5)
            finally:
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
