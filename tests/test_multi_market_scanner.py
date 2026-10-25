import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.multi_market_scanner import MultiMarketScanner


def test_hyperliquid_vs_binance_funding_arb_and_bias():
    fake_hl_payload = [
        {"universe": [{"name": "SOL"}, {"name": "BTC"}]},
        [
            {"funding": "0.00005"},    # 0.005%/h -> +0.04% per 8h on Hyperliquid
            {"funding": "-0.000025"},  # -0.0025%/h -> -0.02% per 8h on Hyperliquid
        ],
    ]
    scanner = MultiMarketScanner(hl_fetcher=lambda: fake_hl_payload)
    hl_map = scanner.fetch_hyperliquid_funding_map()
    assert abs(hl_map["SOL"] - 0.04) < 1e-5
    assert abs(hl_map["BTC"] - (-0.02)) < 1e-5

    # Case 1: Binance SOL funding is +0.005% (0.00005), while Hyperliquid is +0.04%
    # Spread = 0.005% - 0.04% = -0.035% -> LONG_BINANCE_SHORT_HL & positive directional bias
    sig_sol = scanner.compute_cross_venue_signal("SOLUSDT", binance_funding_decimal=0.00005, hl_funding_8h_map=hl_map)
    assert sig_sol.recommended_arb == "LONG_BINANCE_SHORT_HL"
    assert sig_sol.directional_bias_bps > 0
    assert sig_sol.annualized_carry_apy_pct > 30.0

    # Case 2: Binance BTC funding is +0.02% (0.0002), while Hyperliquid is -0.02%
    # Spread = +0.04% -> SHORT_BINANCE_LONG_HL & negative directional bias on Binance
    sig_btc = scanner.compute_cross_venue_signal("BTCUSDT", binance_funding_decimal=0.0002, hl_funding_8h_map=hl_map)
    assert sig_btc.recommended_arb == "SHORT_BINANCE_LONG_HL"
    assert sig_btc.directional_bias_bps < 0


def test_polymarket_crypto_odds_parsing():
    fake_poly_response = {
        "events": [
            {
                "title": "Bitcoin Price Target 2026",
                "markets": [
                    {
                        "question": "Will Bitcoin reach $120,000 in 2026?",
                        "outcomePrices": '["0.68", "0.32"]',
                        "volumeNum": 1450000.0,
                    }
                ],
            }
        ]
    }
    scanner = MultiMarketScanner(poly_fetcher=lambda q: fake_poly_response)
    odds = scanner.fetch_polymarket_crypto_odds("Bitcoin", limit=2)
    assert len(odds) == 1
    assert odds[0].yes_prob_pct == 68.0
    assert odds[0].no_prob_pct == 32.0
    assert odds[0].volume_usd == 1450000.0


if __name__ == "__main__":
    test_hyperliquid_vs_binance_funding_arb_and_bias()
    test_polymarket_crypto_odds_parsing()
    print("multi market scanner tests ok")
