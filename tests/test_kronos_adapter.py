import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.kronos_adapter import (
    DEFAULT_KRONOS_MODEL,
    KronosAdapter,
    compute_first_passage_probabilities,
    prepare_kronos_dataframe,
)


def _sample_uptrend_df(n: int = 120) -> pd.DataFrame:
    ts = pd.date_range("2026-01-01", periods=n, freq="15min", tz="UTC")
    base = 100.0 * np.exp(np.linspace(0, 0.12, n))
    df = pd.DataFrame({
        "timestamp": ts,
        "open": base * 0.998,
        "high": base * 1.004,
        "low": base * 0.995,
        "close": base,
        "volume": np.linspace(1000, 2500, n),
        "quote_asset_volume": base * np.linspace(1000, 2500, n),
    })
    return df


def test_prepare_kronos_dataframe_and_first_passage():
    df = _sample_uptrend_df(80)
    work = prepare_kronos_dataframe(df, max_lookback=60)
    assert len(work) == 60
    assert list(work.columns) == ["open", "high", "low", "close", "volume", "amount", "timestamps"]

    # Path that hits +2% on bar 2 before touching -1%
    high_paths = np.array([[100.5, 102.5, 103.0], [100.2, 100.4, 100.8]])
    low_paths = np.array([[99.5, 100.1, 101.0], [98.5, 98.0, 97.5]])
    close_paths = np.array([[100.2, 102.2, 102.8], [98.8, 98.2, 97.8]])
    p_up, p_dn = compute_first_passage_probabilities(
        high_paths, low_paths, close_paths, entry_price=100.0, tp_pct=2.0, sl_pct=1.0
    )
    assert abs(p_up - 0.5) < 1e-6
    assert abs(p_dn - 0.5) < 1e-6


def test_kronos_adapter_forecast_and_caching():
    df = _sample_uptrend_df(120)
    adapter = KronosAdapter(model_id=DEFAULT_KRONOS_MODEL, prefer_neural=False)
    f1 = adapter.forecast(df, symbol="SOLUSDT", timeframe="15m", horizon_bars=12, sample_count=16)
    f2 = adapter.forecast(df, symbol="SOLUSDT", timeframe="15m", horizon_bars=12, sample_count=16)

    assert f1 == f2  # Cached by closed candle timestamp
    assert f1.symbol == "SOLUSDT"
    assert f1.model_id == "NeoQuasar/Kronos-small"
    assert 0.0 <= f1.prob_up_net <= 1.0
    assert 0.0 <= f1.prob_down_net <= 1.0
    assert 0.0 <= f1.rank_score <= 100.0
    assert f1.expected_return_pct > 0.0


def test_kronos_custom_neural_predictor_injection():
    df = _sample_uptrend_df(60)

    class FakeKronosPredictor:
        def __init__(self):
            self.calls = 0

        def predict(self, df, x_timestamp, y_timestamp, pred_len, T, top_p, sample_count, verbose):
            self.calls += 1
            last_c = float(df["close"].iloc[-1])
            steps = np.linspace(last_c * 1.005, last_c * 1.03, pred_len)
            return pd.DataFrame({
                "open": steps * 0.999,
                "high": steps * 1.005,
                "low": steps * 0.997,
                "close": steps,
                "volume": np.full(pred_len, 1000.0),
                "amount": steps * 1000.0,
            })

    fake_pred = FakeKronosPredictor()
    adapter = KronosAdapter(
        model_id="NeoQuasar/Kronos-small",
        prefer_neural=True,
        predictor_factory=lambda model_id, tok_id, ctx: fake_pred,
    )
    res = adapter.forecast(df, symbol="XRPUSDT", timeframe="1h", horizon_bars=6, sample_count=4, tp_pct=2.0, sl_pct=1.0)
    assert res.backend_mode == "kronos_hf"
    assert fake_pred.calls == 4
    assert res.prob_up_net > 0.8


if __name__ == "__main__":
    test_prepare_kronos_dataframe_and_first_passage()
    test_kronos_adapter_forecast_and_caching()
    test_kronos_custom_neural_predictor_injection()
    print("kronos adapter tests ok")
