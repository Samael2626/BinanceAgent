import sqlite3
import os


def fix_pnl_base():
    # Configuración
    QTY = 0.000405
    ENTRY_PRICE = 90840.51
    USDT_BALANCE = 0.0  # Asumimos 0 según screenshot "Saldo Total 0.00"

    # El "Initial Balance" debe ser el valor del portafolio en el momento de la compra
    # para que la diferencia (Equity - Initial) sea el PnL Real.
    CORRECT_INITIAL_BALANCE = USDT_BALANCE + (QTY * ENTRY_PRICE)

    print(f"🔧 Reparando Base de Cálculo PnL...")
    print(f"   Cant: {QTY} BTC")
    print(f"   Entrada: ${ENTRY_PRICE}")
    print(f"   Saldo USDT: ${USDT_BALANCE}")
    print(f"   => Base Correcta: ${CORRECT_INITIAL_BALANCE:.8f}")

    # Path DB
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, '..', 'bot_data.db')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        key = "initial_balance"
        USER_ID = 8

        # Check current value
        cursor.execute(
            "SELECT value FROM state WHERE key=? AND user_id=?", (key, USER_ID))
        row = cursor.fetchone()
        current_val = row[0] if row else "Not Set"
        print(f"   Valor Actual en DB: {current_val}")

        # Update
        cursor.execute("INSERT OR REPLACE INTO state (user_id, key, value) VALUES (?, ?, ?)",
                       (USER_ID, key, str(CORRECT_INITIAL_BALANCE)))
        conn.commit()
        print(f"   ✅ ¡Actualizado a {CORRECT_INITIAL_BALANCE}!")
        print("   ➡️  Reinicia el backend para ver el PnL real.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    fix_pnl_base()
