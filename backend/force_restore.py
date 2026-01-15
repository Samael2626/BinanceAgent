from database import DatabaseManager
from binance_wrapper import BinanceWrapper
import sys
import os

# Ensure backend module can be found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def force_restore():
    print("🚑 INICIANDO RESTAURACIÓN DE ESTADO (STANDALONE) 🚑")

    db = DatabaseManager()

    # 1. Get User Credentials
    users = db.get_all_users()
    if not users:
        print("❌ No hay usuarios en la BD.")
        return

    user = users[0]  # Assume first user
    user_id = user['id']
    api_key = user['api_key']
    api_secret = user['api_secret']
    is_testnet = bool(user['is_testnet'])

    print(f"👤 Usuario encontrado: {user['username']} (ID: {user_id})")

    # 2. Get Real Balance
    wrapper = BinanceWrapper(api_key, api_secret, testnet=is_testnet)

    # Hardcoded for now based on user context
    symbol = "BNBUSDT"
    asset = "BNB"

    print(f"📡 Conectando a Binance para leer balance de {asset}...")
    try:
        real_qty = wrapper.get_account_balance(asset)
    except Exception as e:
        print(f"❌ Error conectando a Binance: {e}")
        return

    if real_qty < 0.001:
        print(f"❌ Error: Balance {real_qty} {asset} insuficiente.")
        return

    print(f"✅ Balance encontrado: {real_qty} {asset}")

    # 3. Values to Restore
    restore_entry = 941.72
    restore_high = 942.19

    # 4. Save to Database (CORRECT KEY FORMAT: key_SYMBOL)
    # Based on _get_scoped_key: return f"{key}_{self.symbol}"

    print(f"📝 Guardando estado en DB para {symbol}...")

    keys_map = {
        f"entry_price_{symbol}": restore_entry,
        f"highest_price_{symbol}": restore_high,
        f"accumulated_qty_{symbol}": real_qty,
        # Text "True" usually handled by save_state checks?
        f"open_position_{symbol}": True,
        # db.save_state converts input?
        # Let's check db implementation or pass raw.
        # Usually sqlite stores text/real.
        f"position_orders_{symbol}": 1
    }

    current_high_key = f"highest_price_{symbol}"

    for k, v in keys_map.items():
        db.save_state(k, v, user_id=user_id)
        print(f"   -> {k}: {v}")

    print("\n✅ RESTAURACIÓN COMPLETADA.")
    print("⚠️  AHORA REINICIA EL BOT.")


if __name__ == "__main__":
    force_restore()
