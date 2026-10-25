"""
Cartera virtual de Futuros Perpetuos USDⓈ-M (PAPER) sobre datos públicos de Binance Futures (`fapi`).

Características principales:
  - Contabilidad exacta en `Decimal` con Margen Aislado (`leverage` entero 1x..3x, bloqueado >3x para cuentas < 50 USDT).
  - Soporta posiciones `LONG` y `SHORT` (One-Way Mode, 1 posición activa a la vez).
  - Soporta órdenes `MARKET` (consume niveles del libro L2 `fapi` + `latency_bps`, comisión Taker `0.05%`)
    y `LIMIT_MAKER` (Post-Only `GTX`, comisión Maker `0.02%` = 5x más barato que Spot).
  - Precio de liquidación aislado realista (`maint_margin_rate` configurable, por defecto `0.5%` = `0.005`)
    evaluado contra `markPrice` oficial de Binance.
  - Liquidación periódica de `funding_rate` cada 8h (00:00, 08:00, 16:00 UTC):
      funding_fee = notional_mark * funding_rate
      LONG paga si funding_rate > 0 y cobra si < 0; SHORT cobra si funding_rate > 0 y paga si < 0.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_DOWN, ROUND_UP
import threading
import time
from typing import Any
from uuid import uuid4

from .binance_wrapper import BinanceWrapper
from .paper_broker import ATOMIC_UNIT, _ceil, _decimal, _floor, fill_from_book


MAX_ALLOWED_LEVERAGE = 3
DEFAULT_MAINT_MARGIN_RATE = Decimal("0.005")  # 0.50% maintenance margin


def compute_isolated_liquidation_price(
    side: str,
    entry_price: Decimal,
    quantity: Decimal,
    isolated_margin: Decimal,
    maint_margin_rate: Decimal = DEFAULT_MAINT_MARGIN_RATE,
) -> Decimal:
    """
    Calculates isolated-margin liquidation price for a linear USDⓈ-M perpetual contract.
    For LONG:
      isolated_margin + qty * (P_liq - entry_price) = qty * P_liq * mmr
      => P_liq * qty * (1 - mmr) = qty * entry_price - isolated_margin
    For SHORT:
      isolated_margin + qty * (entry_price - P_liq) = qty * P_liq * mmr
      => P_liq * qty * (1 + mmr) = qty * entry_price + isolated_margin
    """
    if quantity <= 0 or entry_price <= 0:
        return Decimal("0")
    direction = side.upper()
    entry_notional = quantity * entry_price
    if direction in {"LONG", "BUY"}:
        numerator = entry_notional - isolated_margin
        denom = quantity * (Decimal("1") - maint_margin_rate)
        if numerator <= 0 or denom <= 0:
            return Decimal("0")
        return _floor(numerator / denom)
    if direction in {"SHORT", "SELL"}:
        numerator = entry_notional + isolated_margin
        denom = quantity * (Decimal("1") + maint_margin_rate)
        if denom <= 0:
            return Decimal("0")
        return _ceil(numerator / denom)
    raise ValueError(f"invalid position side: {side}")


class FuturesPaperBroker:
    """
    Simulated USDⓈ-M Perpetual Futures broker backed by live Mainnet `fapi` order book & mark price.
    Never sends real orders to Binance.
    """

    def __init__(self, db, user_id: int, market: BinanceWrapper | None = None):
        self.db = db
        self.user_id = user_id
        self.market = market or BinanceWrapper(None, None, testnet=False)
        self.testnet = True
        self.is_futures = True
        self.client = self.market.client
        self._lock = threading.RLock()

        saved = db.get_state("paper_futures_account", None, is_json=True, user_id=user_id)
        if saved is None:
            initial = _decimal(db.get_setting("paper_initial_usdt", "47", user_id=user_id))
            if initial <= 0:
                raise ValueError("capital PAPER Futures inicial invalido")
            saved = {
                "wallet_balance": str(initial),
                "isolated_margin": "0",
                "leverage": int(db.get_setting("futures_leverage", 2, user_id=user_id) or 2),
                "position": None,  # dict when open: {symbol, side, qty, entry_price, isolated_margin, liq_price, last_funding_ts}
                "orders": {},
                "funding_history": [],
                "liquidations": [],
                "realized_pnl": "0",
                "fees_paid_usdt": "0",
                "funding_net_usdt": "0",
            }
            db.save_state("paper_futures_account", saved, user_id=user_id)
        self.account = saved
        self._refresh_config()

    def _refresh_config(self) -> None:
        raw_lev = int(self.db.get_setting("futures_leverage", self.account.get("leverage", 2), user_id=self.user_id) or 2)
        if raw_lev < 1 or raw_lev > MAX_ALLOWED_LEVERAGE:
            raise ValueError(f"apalancamiento Futures fuera de rango permitido (1..{MAX_ALLOWED_LEVERAGE}x)")
        self.leverage = raw_lev
        self.account["leverage"] = raw_lev

        self.maker_fee_pct = _decimal(self.db.get_setting("futures_maker_fee_pct", "0.02", user_id=self.user_id))
        self.taker_fee_pct = _decimal(self.db.get_setting("futures_taker_fee_pct", "0.05", user_id=self.user_id))
        self.latency_bps = _decimal(self.db.get_setting("paper_latency_bps", "2", user_id=self.user_id))
        self.maint_margin_rate = _decimal(self.db.get_setting("futures_maint_margin_rate", "0.005", user_id=self.user_id))

        if not (Decimal("0") <= self.maker_fee_pct <= Decimal("0.5") and Decimal("0") <= self.taker_fee_pct <= Decimal("0.5")):
            raise ValueError("comisiones Futures PAPER fuera de rango")
        if not Decimal("0") <= self.latency_bps <= Decimal("100"):
            raise ValueError("latencia Futures PAPER fuera de rango")

    def _persist(self) -> None:
        self.db.save_state("paper_futures_account", self.account, user_id=self.user_id)

    def __getattr__(self, name: str):
        return getattr(self.market, name)

    def get_account_balance(self, asset: str = "USDT") -> float:
        with self._lock:
            if asset == "USDT":
                return float(_decimal(self.account["wallet_balance"]))
            pos = self.account.get("position")
            if pos and pos["symbol"] == f"{asset}USDT":
                return float(_decimal(pos["qty"]))
            return 0.0

    def get_position(self) -> dict[str, Any] | None:
        with self._lock:
            pos = self.account.get("position")
            return dict(pos) if pos else None

    def get_order_by_client_id(self, symbol: str, client_order_id: str) -> dict:
        with self._lock:
            order = self.account["orders"].get(client_order_id)
            if order is None or order["symbol"] != symbol:
                raise KeyError(client_order_id)
            return order

    def set_leverage(self, leverage: int) -> int:
        with self._lock:
            if self.account.get("position") is not None:
                raise ValueError("no se puede cambiar apalancamiento con posicion abierta")
            if int(leverage) < 1 or int(leverage) > MAX_ALLOWED_LEVERAGE:
                raise ValueError(f"apalancamiento debe estar entre 1 y {MAX_ALLOWED_LEVERAGE}")
            self.leverage = int(leverage)
            self.account["leverage"] = self.leverage
            self.db.save_setting("futures_leverage", str(self.leverage), user_id=self.user_id)
            self._persist()
            return self.leverage

    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float = 0.0,
        order_type: str = "MARKET",
        quote_order_qty: float | None = None,
        client_order_id: str | None = None,
        reduce_only: bool = False,
    ) -> dict[str, Any]:
        """
        Executes a simulated USDⓈ-M Futures order (`BUY` or `SELL`, `MARKET` or `LIMIT_MAKER`).
        - If flat: `BUY` opens a `LONG` position; `SELL` opens a `SHORT` position.
        - If holding an opposite position (or `reduce_only=True`): closes the active position.
        """
        side = side.upper()
        order_type = order_type.upper()
        if side not in {"BUY", "SELL"} or order_type not in {"MARKET", "LIMIT_MAKER"} or not symbol.endswith("USDT"):
            raise ValueError("Futures PAPER solo admite BUY/SELL con MARKET o LIMIT_MAKER en pares USDT")

        client_order_id = client_order_id or f"fp{uuid4().hex}"
        with self._lock:
            existing = self.account["orders"].get(client_order_id)
            if existing is not None:
                if existing["symbol"] != symbol or existing["side"] != side:
                    raise ValueError("clientOrderId reutilizado con parametros distintos")
                return existing

            self._refresh_config()
            info = self.market.get_futures_symbol_info(symbol)
            if info is None or info.get("status", "TRADING") != "TRADING":
                raise ValueError("filtros de contrato Futures no disponibles")

            book_start = time.monotonic()
            book = self.market.get_futures_order_book(symbol=symbol, limit=20)
            book_fetch_ms = round((time.monotonic() - book_start) * 1000, 2)
            if book_fetch_ms > 2000:
                raise TimeoutError("libro de ordenes Futures demasiado lento")
            if not book.get("asks") or not book.get("bids"):
                raise ValueError("libro de ordenes Futures incompleto")

            best_bid = _decimal(book["bids"][0][0])
            best_ask = _decimal(book["asks"][0][0])
            if best_bid <= 0 or best_ask <= best_bid:
                raise ValueError("spread del libro Futures invalido")

            pos = self.account.get("position")
            is_closing = False
            if pos is not None:
                if pos["symbol"] != symbol:
                    raise ValueError(f"ya existe una posicion abierta en {pos['symbol']}")
                if (pos["side"] == "LONG" and side == "SELL") or (pos["side"] == "SHORT" and side == "BUY"):
                    is_closing = True
                elif reduce_only:
                    raise ValueError("reduce_only incompatible con la direccion de la posicion actual")
                else:
                    raise ValueError("una sola entrada por posicion activa en Futures PAPER")
            elif reduce_only:
                raise ValueError("reduce_only sin posicion abierta")

            is_quote = (not is_closing) and (quote_order_qty is not None) and float(quote_order_qty) > 0
            if is_closing:
                pos_qty = _decimal(pos["qty"])
                requested_qty = _decimal(quantity) if quantity and float(quantity) > 0 else pos_qty
                requested_qty = min(requested_qty, pos_qty)
                requested_quote = None
            elif is_quote:
                requested_quote = _decimal(quote_order_qty)
                requested_qty = None
            else:
                requested_qty = _decimal(quantity)
                requested_quote = None
                if requested_qty <= 0:
                    raise ValueError("cantidad Futures PAPER invalida")

            # Execution price & fee calculation
            if order_type == "LIMIT_MAKER":
                # Maker post-only rests at best_bid (for BUY) or best_ask (for SELL) with 0 latency slippage
                maker_price = best_bid if side == "BUY" else best_ask
                if requested_qty is None:
                    lot_filter = next(
                        (f for f in info.get("filters", []) if f["filterType"] in {"LOT_SIZE", "MARKET_LOT_SIZE"}),
                        None,
                    )
                    step_str = lot_filter.get("stepSize", "0.00000001") if lot_filter else "0.00000001"
                    raw_qty = float(requested_quote / maker_price)
                    base_qty = _decimal(self.market._quantize_to_step(raw_qty, step_str, ROUND_DOWN))
                else:
                    base_qty = _floor(requested_qty)
                if base_qty <= 0:
                    raise ValueError("cantidad Maker redondeada a cero")
                notional = _floor(base_qty * maker_price)
                fills = [{"price": str(maker_price), "qty": str(base_qty)}]
                fee_pct = self.maker_fee_pct
            else:
                base_qty, notional, fills = fill_from_book(
                    book,
                    side,
                    requested_qty,
                    requested_quote,
                    self.latency_bps,
                )
                fee_pct = self.taker_fee_pct

            avg_price = notional / base_qty
            valid, reason = self.market.validate_futures_order(symbol, float(base_qty), float(avg_price))
            if not valid:
                raise ValueError(reason)

            fee_rate = fee_pct / Decimal("100")
            fee_usdt = _ceil(notional * fee_rate)
            for idx, f in enumerate(fills):
                f["commission"] = str(fee_usdt if idx == 0 else Decimal("0"))
                f["commissionAsset"] = "USDT"

            wallet = _decimal(self.account["wallet_balance"])
            realized_pnl_delta = Decimal("0")

            if not is_closing:
                pos_side = "LONG" if side == "BUY" else "SHORT"
                lev = Decimal(str(self.leverage))
                required_margin = _ceil(notional / lev)
                total_needed = required_margin + fee_usdt
                if total_needed > wallet:
                    raise ValueError(
                        f"margen Futures PAPER insuficiente: requiere {total_needed:.4f} USDT, libre {wallet:.4f} USDT"
                    )
                wallet -= total_needed
                liq_price = compute_isolated_liquidation_price(
                    pos_side,
                    avg_price,
                    base_qty,
                    required_margin,
                    self.maint_margin_rate,
                )
                self.account["position"] = {
                    "symbol": symbol,
                    "side": pos_side,
                    "qty": str(base_qty),
                    "entry_price": str(avg_price),
                    "notional": str(notional),
                    "isolated_margin": str(required_margin),
                    "leverage": self.leverage,
                    "liquidation_price": str(liq_price),
                    "opened_at_ms": int(time.time() * 1000),
                    "last_funding_time": 0,
                }
                self.account["isolated_margin"] = str(required_margin)
            else:
                pos_side = pos["side"]
                pos_qty = _decimal(pos["qty"])
                entry_price = _decimal(pos["entry_price"])
                iso_margin = _decimal(pos["isolated_margin"])
                close_ratio = base_qty / pos_qty if pos_qty > 0 else Decimal("1")
                released_margin = _floor(iso_margin * close_ratio)

                if pos_side == "LONG":
                    gross_pnl = (avg_price - entry_price) * base_qty
                else:
                    gross_pnl = (entry_price - avg_price) * base_qty

                realized_pnl_delta = gross_pnl - fee_usdt
                wallet += released_margin + gross_pnl - fee_usdt
                remaining_qty = pos_qty - base_qty
                if remaining_qty <= ATOMIC_UNIT:
                    self.account["position"] = None
                    self.account["isolated_margin"] = "0"
                else:
                    rem_margin = iso_margin - released_margin
                    pos["qty"] = str(remaining_qty)
                    pos["isolated_margin"] = str(rem_margin)
                    self.account["isolated_margin"] = str(rem_margin)

            self.account["wallet_balance"] = str(_floor(wallet))
            self.account["realized_pnl"] = str(_decimal(self.account["realized_pnl"]) + realized_pnl_delta)
            self.account["fees_paid_usdt"] = str(_decimal(self.account["fees_paid_usdt"]) + fee_usdt)

            order = {
                "symbol": symbol,
                "side": side,
                "positionSide": self.account["position"]["side"] if self.account.get("position") else pos_side,
                "type": order_type,
                "timeInForce": "GTX" if order_type == "LIMIT_MAKER" else "IOC",
                "postOnly": order_type == "LIMIT_MAKER",
                "orderId": len(self.account["orders"]) + 1,
                "clientOrderId": client_order_id,
                "transactTime": int(time.time() * 1000),
                "status": "FILLED",
                "price": str(_floor(avg_price)),
                "avgPrice": str(_floor(avg_price)),
                "origQty": str(base_qty),
                "executedQty": str(base_qty),
                "cummulativeQuoteQty": str(_floor(notional)),
                "realizedPnl": str(_floor(realized_pnl_delta)),
                "feeUsdt": str(fee_usdt),
                "feePct": str(fee_pct),
                "fills": fills,
                "paper": True,
                "market": "FUTURES_USDSM",
                "leverage": self.leverage,
                "bestBid": str(best_bid),
                "bestAsk": str(best_ask),
                "bookUpdateId": book.get("lastUpdateId"),
                "bookFetchMs": book_fetch_ms,
            }
            self.account["orders"][client_order_id] = order
            self._persist()
            return order

    def place_smart_maker_order(
        self,
        symbol: str,
        side: str,
        quantity: float = 0.0,
        quote_order_qty: float | None = None,
        client_order_id: str | None = None,
        reduce_only: bool = False,
        max_reprice_attempts: int = 3,
    ) -> dict[str, Any]:
        """
        Executes a Smart Post-Only Maker (`GTX`) order pegged to the top of the L2
        order book (`Best Bid` for BUY, `Best Ask` for SELL).
        - Guarantees Maker fee (`0.02%`) and zero spread-crossing slippage.
        - If the L2 book is temporarily inverted or stale, reprices up to
          `max_reprice_attempts` times before rejecting (never falls back to Taker).
        """
        attempts = max(1, int(max_reprice_attempts))
        last_exc: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                order = self.place_order(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    order_type="LIMIT_MAKER",
                    quote_order_qty=quote_order_qty,
                    client_order_id=client_order_id,
                    reduce_only=reduce_only,
                )
                order["repriceAttempts"] = attempt
                order["executionStyle"] = "SMART_GTX_PEG"
                return order
            except (ValueError, TimeoutError) as exc:
                last_exc = exc
                if "spread del libro" in str(exc) or "lento" in str(exc):
                    continue
                raise
        raise ValueError(f"Smart Post-Only GTX fallo tras {attempts} intentos: {last_exc}")

    def apply_funding_if_due(
        self,
        funding_rate: float | Decimal,
        funding_timestamp_ms: int,
        mark_price: float | Decimal | None = None,
    ) -> dict[str, Any] | None:
        """
        Applies 8-hour funding fee to the active position if `funding_timestamp_ms`
        has not been settled yet.
        - `funding_rate > 0`: LONG pays, SHORT receives.
        - `funding_rate < 0`: LONG receives, SHORT pays.
        """
        with self._lock:
            pos = self.account.get("position")
            if pos is None:
                return None
            last_settled = int(pos.get("last_funding_time", 0) or 0)
            if funding_timestamp_ms <= 0 or funding_timestamp_ms <= last_settled:
                return None

            qty = _decimal(pos["qty"])
            ref_price = _decimal(mark_price) if mark_price is not None and float(mark_price) > 0 else _decimal(pos["entry_price"])
            rate = _decimal(funding_rate)
            notional = qty * ref_price
            # Positive cashflow means credited to user; negative means debited
            signed_mult = Decimal("-1") if pos["side"] == "LONG" else Decimal("1")
            cashflow = _floor(notional * rate * signed_mult)

            wallet = _decimal(self.account["wallet_balance"]) + cashflow
            self.account["wallet_balance"] = str(wallet)
            self.account["funding_net_usdt"] = str(_decimal(self.account["funding_net_usdt"]) + cashflow)
            pos["last_funding_time"] = int(funding_timestamp_ms)

            record = {
                "symbol": pos["symbol"],
                "side": pos["side"],
                "fundingTime": int(funding_timestamp_ms),
                "fundingRate": str(rate),
                "markPrice": str(ref_price),
                "cashflowUsdt": str(cashflow),
            }
            self.account["funding_history"].append(record)
            self._persist()
            return record

    def check_mark_and_liquidate(self, mark_price: float | Decimal | None = None) -> dict[str, Any] | None:
        """
        Checks current `markPrice` against the active position's `liquidation_price`.
        If breached, force-liquidates the isolated position and zeroes its isolated margin.
        """
        with self._lock:
            pos = self.account.get("position")
            if pos is None:
                return None

            if mark_price is None or float(mark_price) <= 0:
                mp_info = self.market.get_futures_mark_price_and_funding(pos["symbol"])
                mark = _decimal(mp_info.get("markPrice", 0) or 0)
            else:
                mark = _decimal(mark_price)

            if mark <= 0:
                return None

            liq_price = _decimal(pos["liquidation_price"])
            if liq_price <= 0:
                return None

            breached = (pos["side"] == "LONG" and mark <= liq_price) or (
                pos["side"] == "SHORT" and mark >= liq_price
            )
            if not breached:
                return None

            iso_margin = _decimal(pos["isolated_margin"])
            self.account["realized_pnl"] = str(_decimal(self.account["realized_pnl"]) - iso_margin)
            liq_event = {
                "symbol": pos["symbol"],
                "side": pos["side"],
                "qty": pos["qty"],
                "entry_price": pos["entry_price"],
                "liquidation_price": str(liq_price),
                "mark_price": str(mark),
                "lost_margin_usdt": str(iso_margin),
                "timestamp": int(time.time() * 1000),
            }
            self.account["liquidations"].append(liq_event)
            self.account["position"] = None
            self.account["isolated_margin"] = "0"
            self._persist()
            return liq_event

    def report(self, current_mark_price: float | None = None) -> dict[str, Any]:
        with self._lock:
            pos = self.account.get("position")
            unrealized = Decimal("0")
            valuation_available = pos is None
            if pos is not None:
                valuation_available = current_mark_price is not None and current_mark_price > 0
                if valuation_available:
                    mark = _decimal(current_mark_price)
                    qty = _decimal(pos["qty"])
                    entry = _decimal(pos["entry_price"])
                    unrealized = (mark - entry) * qty if pos["side"] == "LONG" else (entry - mark) * qty

            wallet = _decimal(self.account["wallet_balance"])
            iso = _decimal(self.account["isolated_margin"])
            total_equity = wallet + iso + unrealized
            orders = list(self.account["orders"].values())
            return {
                "mode": "PAPER_FUTURES_USDSM",
                "wallet_balance_usdt": str(wallet),
                "isolated_margin_usdt": str(iso),
                "mark_price": str(_decimal(current_mark_price)) if pos and valuation_available else None,
                "unrealized_pnl_usdt": str(_floor(unrealized)) if valuation_available else None,
                "total_equity_usdt": str(_floor(total_equity)) if valuation_available else None,
                "realized_pnl_usdt": self.account["realized_pnl"],
                "fees_paid_usdt": self.account["fees_paid_usdt"],
                "funding_net_usdt": self.account["funding_net_usdt"],
                "leverage": self.leverage,
                "position": dict(pos) if pos else None,
                "liquidation_count": len(self.account["liquidations"]),
                "liquidations": list(self.account["liquidations"]),
                "funding_history": list(self.account["funding_history"]),
                "order_count": len(orders),
                "orders": orders,
            }
