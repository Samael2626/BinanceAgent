import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from the backend directory explicitly
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
TRADING_MODE = os.getenv("TRADING_MODE", "PAPER")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not API_KEY or not API_SECRET:
    print("WARNING: API Key or Secret not found in environment variables.")
