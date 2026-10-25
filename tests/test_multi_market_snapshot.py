import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.multi_market_snapshot import MultiMarketSnapshot, SYMBOLS
from backend.services.multi_market_scanner import MultiMarketScanner
from backend.futures_paper_broker import FuturesPaperBroker
from tests.test_futures_paper_broker import FakeDb, FakeFuturesMarket


class StubScanner:
    def __init__(self, hl=None, poly=None):
        self.hl = hl
        self.poly = poly
        self.hl_calls = 0

    def fetch_hyperliquid_funding_map(self):
        self.hl_calls += 1
        if isinstance(self.hl, Exception):
            raise self.hl
        return self.hl or {}

    def fetch_polymarket_crypto_odds(self, query):
        if isinstance(self.poly, Exception):
            raise self.poly
        return self.poly or []


def test_complete_snapshot_and_cache():
    tick = [0]
    calls = []
    scanner = StubScanner({s.removesuffix("USDT"): 0.02 for s in SYMBOLS},
                          [SimpleNamespace(question="Will BTC rise?", yes_prob_pct=60, no_prob_pct=40,
                                           to_dict=lambda: {"question": "Will BTC rise?", "yes_prob_pct": 60, "no_prob_pct": 40})])
    snapshot = MultiMarketSnapshot(scanner, lambda symbol: calls.append(symbol) or "0.0001", lambda: tick[0])
    result = snapshot.get()
    assert len(result["funding"]) == 6
    assert result["funding"][0]["spread_8h_pct"] == -0.01
    assert result["funding"][0]["annualized_gross_indicative_pct"] == 10.95
    assert result["polymarket"]["status"] == "available"
    assert snapshot.get() is result
    assert scanner.hl_calls == 1 and len(calls) == 6
    tick[0] = 61
    snapshot.get()
    assert scanner.hl_calls == 2


def test_missing_provider_rates_never_create_spread():
    for scanner, fetcher in (
        (StubScanner(RuntimeError("hl")), lambda symbol: 0.0001),
        (StubScanner({s.removesuffix("USDT"): 0.02 for s in SYMBOLS}), lambda symbol: None),
    ):
        result = MultiMarketSnapshot(scanner, fetcher).get()
        assert all(row["spread_8h_pct"] is None and row["annualized_gross_indicative_pct"] is None for row in result["funding"])
    result = MultiMarketSnapshot(StubScanner({}, RuntimeError("poly")), lambda symbol: 0.0001).get()
    assert result["polymarket"] == {"status": "unavailable", "events": []}


def test_hyperliquid_missing_funding_is_absent():
    scanner = MultiMarketScanner(hl_fetcher=lambda: [{"universe": [{"name": "SOL"}]}, [{}]])
    assert scanner.fetch_hyperliquid_funding_map() == {}


def test_report_requires_mark_for_open_position():
    broker = FuturesPaperBroker(FakeDb(), 1, FakeFuturesMarket())
    broker.account["wallet_balance"] = "30"
    broker.account["isolated_margin"] = "17"
    broker.account["position"] = {"symbol": "SOLUSDT", "side": "LONG", "qty": "1", "entry_price": "100", "isolated_margin": "17", "leverage": 2}
    missing = broker.report()
    assert missing["mark_price"] is None
    assert missing["unrealized_pnl_usdt"] is None
    assert missing["total_equity_usdt"] is None
    marked = broker.report(current_mark_price=101)
    assert marked["unrealized_pnl_usdt"] == "1.00000000"
    assert marked["total_equity_usdt"] == "48.00000000"
