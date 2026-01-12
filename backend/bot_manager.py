"""
Bot Manager - Handles multiple bot instances for different users
"""
import threading
from typing import Dict, Optional
from .bot_logic import BinanceBot


class BotManager:
    """Manages multiple BinanceBot instances, one per user"""

    def __init__(self):
        self.bots: Dict[int, BinanceBot] = {}
        self.lock = threading.Lock()

    def get_or_create_bot(self, user_id: int, api_key: str, api_secret: str, is_testnet: bool) -> BinanceBot:
        """Get existing bot for user or create new one"""
        with self.lock:
            if user_id not in self.bots:
                # Create new bot instance for this user
                bot = BinanceBot(user_id=user_id)
                # Set credentials
                result = bot.set_credentials(api_key, api_secret, is_testnet)
                if result.get("status") == "error":
                    raise Exception(result.get(
                        "message", "Failed to initialize bot"))
                self.bots[user_id] = bot

            return self.bots[user_id]

    def get_bot(self, user_id: int) -> Optional[BinanceBot]:
        """Get bot instance for user, returns None if not found"""
        with self.lock:
            return self.bots.get(user_id)

    def stop_bot(self, user_id: int):
        """Stop and remove bot instance for user"""
        with self.lock:
            bot = self.bots.get(user_id)
            if bot:
                bot.stop()
                bot.disconnect()
                del self.bots[user_id]

    def cleanup_inactive_bots(self):
        """Remove inactive bots to free resources"""
        with self.lock:
            inactive_users = [
                user_id for user_id, bot in self.bots.items()
                if not bot.is_running
            ]
            for user_id in inactive_users:
                del self.bots[user_id]
