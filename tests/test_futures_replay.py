import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

import pandas as pd
import pytest

from harness.futures_data import load_futures_klines, load_funding_rates
from harness.futures_replay import ContractFilter, Signal, _quantity, assess_live_gate, choose_signal, replay
from harness.metrics import compute
from backend.strategies.kronos_quant import KronosQuantStrategy


def _bars(start, prices):
    times = pd.date_range(start, periods=len(prices), freq="1min", tz="UTC")
    return pd.DataFrame({
        "open_time": times,
        "open": [p[0] for p in prices], "high": [p[1] for p in prices],
        "low": [p[2] for p in prices], "close": [p[3] for p in prices],
    })


def _signal(symbol="BTCUSDT", ev=20):
    return Signal(symbol, "LONG", ev, 0.1, 2.0, 1.5, {}, {"stop_loss_pct": 1.5, "take_profit_pct": 2.0})


def test_signal_tie_break_by_symbol():
    assert choose_signal([_signal("ETHUSDT"), _signal("BTCUSDT")]).symbol == "BTCUSDT"


def test_live_gate_never_promotes_incomplete_replay():
    result = compute([], [], 47)
    gate = assess_live_gate(result)
    assert not gate.passed
    assert "OK auditor pendiente" in gate.reasons


def test_real_forecast_rejects_fallback_and_stale_candle():
    closed = int(pd.Timestamp("2026-07-01T01:00:00Z").timestamp()) - 1
    forecast = {"backend_mode": "kronos_hf", "symbol": "BTCUSDT", "timeframe": "1h",
                "last_candle_ts": int(pd.Timestamp("2026-07-01T00:00:00Z").timestamp() * 1000)}
    assert KronosQuantStrategy.neural_forecast_ready(forecast, "BTCUSDT", "1h", closed)
    assert not KronosQuantStrategy.neural_forecast_ready({**forecast, "backend_mode": "monte_carlo_kline"}, "BTCUSDT", "1h", closed)
    assert not KronosQuantStrategy.neural_forecast_ready(forecast, "BTCUSDT", "1h", closed + 3600)


def test_single_wallet_stop_first_and_net_costs():
    start = pd.Timestamp("2026-07-01T00:00:00Z")
    end = start + pd.Timedelta(hours=1)
    prices = [(100, 100, 100, 100)] * 60
    prices[0] = (100, 103, 98, 100)
    bars = {symbol: _bars(start, prices) for symbol in ("BTCUSDT", "ETHUSDT")}
    funding = {symbol: pd.DataFrame(columns=["time", "rate", "mark_price"]) for symbol in bars}
    contracts = {symbol: ContractFilter("0.001", "0.001", "5") for symbol in bars}
    trades, curve, result = replay(bars, funding, contracts, {start: [_signal("ETHUSDT"), _signal("BTCUSDT")]}, start=start, end=end)
    assert len(trades) == 1
    assert trades[0]["symbol"] == "BTCUSDT"
    assert trades[0]["reason"] == "NATIVE_STOP"
    assert trades[0]["net_pnl"] < 0
    assert result.n_trades == 1 and result.win_rate == 0
    assert len(curve) == 1


def test_missing_minute_rejected():
    start = pd.Timestamp("2026-07-01T00:00:00Z")
    end = start + pd.Timedelta(hours=1)
    bars = _bars(start, [(100, 100, 100, 100)] * 59)
    with pytest.raises(ValueError, match="incompletas"):
        replay({"BTCUSDT": bars}, {"BTCUSDT": pd.DataFrame()},
               {"BTCUSDT": ContractFilter("0.001", "0.001", "5")}, {}, start=start, end=end)


def test_rounding_never_exceeds_notional_or_ignores_minimum():
    contract = ContractFilter("0.003", "0.003", "5")
    qty = _quantity(20, 101, contract)
    assert qty * 101 <= 20
    assert _quantity(5, 101, ContractFilter("1", "1", "5")) == 0


def test_funding_is_included_in_net_pnl():
    start = pd.Timestamp("2026-07-01T00:00:00Z")
    end = start + pd.Timedelta(hours=1)
    prices = [(100, 100.1, 99.9, 100)] * 60
    prices[2] = (100, 100, 98, 99)
    bars = {"BTCUSDT": _bars(start, prices)}
    contracts = {"BTCUSDT": ContractFilter("0.001", "0.001", "5")}
    base_funding = pd.DataFrame(columns=["time", "rate", "mark_price"])
    with_funding = pd.DataFrame([{"time": start + pd.Timedelta(minutes=1), "rate": 0.001, "mark_price": 100}])
    signal = Signal("BTCUSDT", "LONG", 20, 0.1, 2, 1.5, {}, {})
    baseline, _, _ = replay(bars, {"BTCUSDT": base_funding}, contracts, {start: [signal]}, start=start, end=end)
    funded, _, _ = replay(bars, {"BTCUSDT": with_funding}, contracts, {start: [signal]}, start=start, end=end)
    assert len(baseline) == len(funded) == 1
    assert funded[0]["funding"] < 0
    assert funded[0]["net_pnl"] == pytest.approx(baseline[0]["net_pnl"] + funded[0]["funding"])


def test_loader_rejects_gap_and_funding_gap():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        name = "BTCUSDT-1m-2026-07-01.zip"
        path = root / "futures_um" / "BTCUSDT" / "1m" / name
        path.parent.mkdir(parents=True)
        rows = []
        for minute in (0, 2):
            ms = int(pd.Timestamp("2026-07-01T00:00:00Z").timestamp() * 1000) + minute * 60000
            rows.append(f"{ms},100,101,99,100,1,0,100\n")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(name.replace(".zip", ".csv"), "".join(rows))
        path.with_suffix(".sha256").write_text(hashlib.sha256(path.read_bytes()).hexdigest(), encoding="ascii")
        with pytest.raises(ValueError, match="incompleta"):
            load_futures_klines("BTCUSDT", "1m", "2026-07-01", "2026-07-01 00:03", root)
        funding_path = root / "futures_um" / "BTCUSDT" / "funding-20260701-20260702.json"
        base = int(pd.Timestamp("2026-07-01T00:00:00Z").timestamp() * 1000)
        funding_path.write_text(json.dumps([
            {"symbol": "BTCUSDT", "fundingTime": base, "fundingRate": "0.0001", "markPrice": "100"},
            {"symbol": "BTCUSDT", "fundingTime": base + 16 * 3600000, "fundingRate": "0.0001", "markPrice": "100"},
        ]), encoding="utf-8")
        with pytest.raises(ValueError, match="huecos"):
            load_funding_rates("BTCUSDT", "2026-07-01", "2026-07-02", root)


def test_funding_millisecond_jitter_maps_to_settlement_minute():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        path = root / "futures_um" / "BTCUSDT" / "funding-20260701-20260702.json"
        path.parent.mkdir(parents=True)
        base = int(pd.Timestamp("2026-07-01T00:00:00Z").timestamp() * 1000)
        path.write_text(json.dumps([
            {"symbol": "BTCUSDT", "fundingTime": base + i * 8 * 3600000 + (5 if i % 2 else 0),
             "fundingRate": "0.0001", "markPrice": "100"}
            for i in range(4)
        ]), encoding="utf-8")
        frame, _ = load_funding_rates("BTCUSDT", "2026-07-01", "2026-07-02", root)
        assert len(frame) == 3
        assert frame["time"].iloc[1] == pd.Timestamp("2026-07-01T08:00:00Z")
