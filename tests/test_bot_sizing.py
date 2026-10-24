import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.bot_logic import BinanceBot


def test_auto_sizing_does_not_fallback_to_fixed_trade_when_risk_rejects():
    bot = BinanceBot.__new__(BinanceBot)
    bot.auto_position_sizing = True
    bot.trade_qty = 12.0
    bot.trade_qty_type = "quote"
    bot.current_price = 100.0
    bot.atr = 10.0
    bot.stop_loss_pct = 1.5
    bot.risk_per_trade_pct = 0.75
    bot.atr_stop_mult = 1.5
    bot._baseline_equity = lambda: 47.0
    assert bot._resolve_auto_buy_qty() == 0.0


if __name__ == "__main__":
    test_auto_sizing_does_not_fallback_to_fixed_trade_when_risk_rejects()
    print("bot sizing tests ok")
