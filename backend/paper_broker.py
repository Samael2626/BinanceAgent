"""Cartera virtual sobre datos publicos de Binance Spot."""

from __future__ import annotations

import threading
import time
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from uuid import uuid4

from .binance_wrapper import BinanceWrapper


ATOMIC_UNIT = Decimal("0.00000001")


def _decimal(value) -> Decimal:
    return Decimal(str(value))


def _floor(value: Decimal) -> Decimal:
    return value.quantize(ATOMIC_UNIT, rounding=ROUND_DOWN)


def _ceil(value: Decimal) -> Decimal:
    return value.quantize(ATOMIC_UNIT, rounding=ROUND_UP)


def fill_from_book(book: dict, side: str, quantity: Decimal | None,
                   quote_budget: Decimal | None, latency_bps: Decimal) -> tuple[Decimal, Decimal, list[dict]]:
    levels = book.get("asks" if side == "BUY" else "bids") or []
    if not levels or side not in {"BUY", "SELL"}:
        raise ValueError("libro de ordenes no disponible")
    if (quantity is None) == (quote_budget is None):
        raise ValueError("indicar cantidad base o presupuesto quote")
    remaining = quantity if quantity is not None else quote_budget
    filled = Decimal("0")
    notional = Decimal("0")
    fills = []
    multiplier = Decimal("1") + (latency_bps / Decimal("10000")) * (1 if side == "BUY" else -1)
    for raw_price, raw_qty in levels:
        price = _decimal(raw_price) * multiplier
        available = _floor(_decimal(raw_qty))
        if price <= 0 or available <= 0:
            continue
        take = min(available, remaining if quantity is not None else remaining / price)
        take = _floor(take)
        if take <= 0:
            continue
        cost = take * price
        filled += take
        notional += cost
        fills.append({"price": str(price), "qty": str(take)})
        remaining -= take if quantity is not None else cost
        if remaining <= (Decimal("0") if quantity is not None else price * ATOMIC_UNIT):
            break
    if filled <= 0 or (quantity is not None and filled < quantity) or (quote_budget is not None and remaining > price * ATOMIC_UNIT):
        raise ValueError("profundidad insuficiente para llenar la orden")
    return filled, notional, fills


class PaperBroker:
    def __init__(self, db, user_id: int, market: BinanceWrapper | None = None):
        self.db = db
        self.user_id = user_id
        self.market = market or BinanceWrapper(None, None, testnet=False)
        self.testnet = True
        self.client = self.market.client
        self._lock = threading.RLock()
        saved = db.get_state("paper_account", None, is_json=True, user_id=user_id)
        if saved is None:
            initial = _decimal(db.get_setting("paper_initial_usdt", "47", user_id=user_id))
            if initial <= 0:
                raise ValueError("capital PAPER inicial invalido")
            saved = {"quote": str(initial), "assets": {}, "orders": {}}
            db.save_state("paper_account", saved, user_id=user_id)
        self.account = saved
        self._refresh_costs()

    def _refresh_costs(self) -> None:
        self.fee_pct = _decimal(self.db.get_setting("paper_fee_pct", "0.1", user_id=self.user_id))
        self.latency_bps = _decimal(self.db.get_setting("paper_latency_bps", "2", user_id=self.user_id))
        if not Decimal("0") <= self.fee_pct <= Decimal("1") or not Decimal("0") <= self.latency_bps <= Decimal("100"):
            raise ValueError("costes PAPER fuera de rango")

    def __getattr__(self, name):
        return getattr(self.market, name)

    def get_account_balance(self, asset: str) -> float:
        with self._lock:
            if asset == "USDT":
                return float(self.account["quote"])
            return float(self.account["assets"].get(asset, "0"))

    def get_order_by_client_id(self, symbol: str, client_order_id: str) -> dict:
        with self._lock:
            order = self.account["orders"].get(client_order_id)
            if order is None or order["symbol"] != symbol:
                raise KeyError(client_order_id)
            return order

    def report(self) -> dict:
        with self._lock:
            orders = list(self.account["orders"].values())
            fees = Decimal("0")
            for order in orders:
                average = _decimal(order["cummulativeQuoteQty"]) / _decimal(order["executedQty"])
                for fill in order["fills"]:
                    amount = _decimal(fill["commission"])
                    fees += amount if fill["commissionAsset"] == "USDT" else amount * average
            return {
                "mode": "PAPER", "virtual_usdt": self.account["quote"],
                "virtual_assets": dict(self.account["assets"]),
                "fees_paid_usdt": str(fees), "order_count": len(orders),
                "orders": orders,
            }

    def place_order(self, symbol: str, side: str, quantity: float,
                    order_type: str = "MARKET", quote_order_qty: float | None = None,
                    client_order_id: str | None = None) -> dict:
        if order_type != "MARKET" or side not in {"BUY", "SELL"} or not symbol.endswith("USDT"):
            raise ValueError("PAPER solo admite ordenes MARKET en pares USDT")
        if side == "SELL" and quote_order_qty is not None:
            raise ValueError("venta PAPER requiere cantidad base")
        client_order_id = client_order_id or f"pa{uuid4().hex}"
        with self._lock:
            existing = self.account["orders"].get(client_order_id)
            if existing:
                requested_quote = str(_decimal(quote_order_qty)) if quote_order_qty is not None else None
                requested_base = str(_decimal(quantity)) if quote_order_qty is None else "0"
                if (existing["symbol"] != symbol or existing["side"] != side
                        or existing["origQty"] != requested_base
                        or existing.get("origQuoteOrderQty") != requested_quote):
                    raise ValueError("identificador de orden reutilizado")
                return existing
            self._refresh_costs()
            info = self.market.get_symbol_info(symbol)
            if info is None or info.get("status", "TRADING") != "TRADING":
                raise ValueError("filtros del simbolo no disponibles")
            book_start = time.monotonic()
            book = self.client.get_order_book(symbol=symbol, limit=20)
            book_fetch_ms = round((time.monotonic() - book_start) * 1000, 2)
            if book_fetch_ms > 2000:
                raise TimeoutError("libro de ordenes demasiado lento")
            if not book.get("asks") or not book.get("bids"):
                raise ValueError("libro de ordenes incompleto")
            best_bid = _decimal(book["bids"][0][0])
            best_ask = _decimal(book["asks"][0][0])
            if best_bid <= 0 or best_ask <= best_bid:
                raise ValueError("spread del libro invalido")
            is_quote = side == "BUY" and quote_order_qty is not None
            requested = _decimal(quote_order_qty if is_quote else quantity)
            if requested <= 0:
                raise ValueError("cantidad PAPER invalida")
            asset = symbol[:-4]
            base_qty, notional, fills = fill_from_book(
                book, side, None if is_quote else requested,
                requested if is_quote else None, self.latency_bps)
            average_price = notional / base_qty
            valid, reason = self.market.validate_order(
                symbol, float(requested), float(average_price), is_quote_qty=is_quote)
            if not valid:
                raise ValueError(reason)
            quote = _decimal(self.account["quote"])
            base = _decimal(self.account["assets"].get(asset, "0"))
            fee_rate = self.fee_pct / Decimal("100")
            if side == "BUY":
                if notional > quote:
                    raise ValueError("saldo PAPER insuficiente")
                fee = _ceil(base_qty * fee_rate)
                quote -= notional
                base += base_qty - fee
                fee_asset = asset
            else:
                if base_qty > base:
                    raise ValueError("activo PAPER insuficiente")
                fee = _ceil(notional * fee_rate)
                quote += notional - fee
                base -= base_qty
                fee_asset = "USDT"
            remaining_fee = fee
            for index, fill in enumerate(fills):
                if index == len(fills) - 1:
                    part = remaining_fee
                else:
                    basis = _decimal(fill["qty"])
                    if side == "SELL":
                        basis *= _decimal(fill["price"])
                    part = min(remaining_fee, _floor(basis * fee_rate))
                fill["commission"] = str(part)
                fill["commissionAsset"] = fee_asset
                remaining_fee -= part
            order = {
                "symbol": symbol, "side": side, "orderId": len(self.account["orders"]) + 1,
                "clientOrderId": client_order_id, "transactTime": int(time.time() * 1000),
                "status": "FILLED", "price": "0", "origQty": str(requested if not is_quote else 0),
                "origQuoteOrderQty": str(requested) if is_quote else None,
                "executedQty": str(base_qty), "cummulativeQuoteQty": str(notional),
                "fills": fills, "paper": True, "feePct": str(self.fee_pct),
                "latencyBps": str(self.latency_bps), "bookUpdateId": book.get("lastUpdateId"),
                "bestBid": str(best_bid), "bestAsk": str(best_ask),
                "bookFetchMs": book_fetch_ms,
            }
            updated = {
                "quote": str(quote),
                "assets": {**self.account["assets"], asset: str(base)},
                "orders": {**self.account["orders"], client_order_id: order},
            }
            self.db.save_state("paper_account", updated, user_id=self.user_id)
            self.account = updated
            return order
