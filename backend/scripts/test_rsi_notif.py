from backend.bot_logic import BinanceBot
import sys
import os
import time
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../..')))


def test_rsi_alerts():
    print("🧪 Starting RSI Alerts Verification...")

    # Mock bot
    bot = BinanceBot(user_id=1)
    bot.notifier = MagicMock()
    bot.symbol = "SOLUSDT"
    bot.enable_rsi_alerts = True
    bot.enable_urgent_alerts = True

    # List of RSI values to simulate
    # 50 (Stable) -> 38 (Normal Buy) -> 28 (Urgent Buy) -> 35 (Normal Buy - should not re-trigger?)
    # -> 45 (Out of range) -> 39 (Normal Buy - should trigger again)
    rsi_sequence = [50, 38, 28, 35, 45, 39, 62, 75, 65, 50, 61]

    for val in rsi_sequence:
        bot.rsi = val
        print(f"--- Simulating RSI: {val} ---")
        bot._check_rsi_alerts()

    print("\n✅ Verification finished.")
    print(f"Total Telegram calls: {bot.notifier.send_message.call_count}")

    for i, call in enumerate(bot.notifier.send_message.call_args_list):
        print(f"Message {i+1}: {call.args[0]}")


if __name__ == "__main__":
    test_rsi_alerts()
