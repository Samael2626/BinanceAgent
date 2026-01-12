import sqlite3
import os


def debug_pnl_state():
    # Setup paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, '..', 'bot_data.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    USER_ID = 1

    print("🔍 DEBUG PNL STATE")
    print("-" * 30)

    try:
        # 1. Check Initial Balance (Base Cost)
        cursor.execute(
            "SELECT value FROM state WHERE key='initial_balance' AND user_id=?", (USER_ID,))
        row = cursor.fetchone()
        initial_balance = float(row[0]) if row else 0.0
        print(f"💰 Initial Balance (DB): {initial_balance}")

        # 2. Check Holdings
        cursor.execute(
            "SELECT value FROM state WHERE key='accumulated_qty_BTCUSDT' AND user_id=?", (USER_ID,))
        qty = float(cursor.fetchone()[0])
        print(f"📦 Holdings (Qty): {qty} BTC")

        # 3. Check Entry Price
        cursor.execute(
            "SELECT value FROM state WHERE key='entry_price_BTCUSDT' AND user_id=?", (USER_ID,))
        entry = float(cursor.fetchone()[0])
        print(f"🏷️ Entry Price: ${entry}")

        # 4. Simulate PnL at current market price (approx 91358 from screenshot)
        current_price = 91358.01
        equity = 0.0 + (qty * current_price)  # Assuming 0 USDT balance

        # Calculate Gross PnL
        gross_pnl = equity - initial_balance

        # Calculate Net PnL (Logic in bot)
        # self.pnl = equity - self.initial_balance - (self.initial_balance * 0.001) - (equity * 0.001)
        net_pnl = equity - initial_balance - \
            (initial_balance * 0.001) - (equity * 0.001)

        print("-" * 30)
        print(f"📈 Price Sim: ${current_price}")
        print(f"💵 Equity Sim: ${equity:.8f}")
        print(f"----------------")
        print(f"🧮 Gross PnL (Equity - Initial): ${gross_pnl:.4f}")
        print(
            f"📉 Fees (0.2%): -${(initial_balance * 0.001) + (equity * 0.001):.4f}")
        print(f"✅ Net PnL (Calculated): ${net_pnl:.4f}")

        # Validate Match
        if net_pnl < 0 and current_price > entry:
            print("\n⚠️ WARNING: Net PnL is negative despite price rise!")
            print("Possible reasons:")
            print("1. Initial Balance is too high due to previous incorrect set.")
            print("2. Fees are eating the meager profit.")

        # Check if Initial Balance matches Entry * Qty
        expected_initial = qty * entry
        if abs(initial_balance - expected_initial) > 0.01:
            print(f"\n🚫 Mismatch detected in Base Cost!")
            print(f"   Expected (Entry*Qty): {expected_initial}")
            print(f"   Actual (Initial Bal): {initial_balance}")
            print("   -> 'Initial Balance' might include old funds or was overwritten?")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    debug_pnl_state()
