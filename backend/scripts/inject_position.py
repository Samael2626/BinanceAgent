import sys
import os
import sqlite3


def inject_position():
    print("💉 Iniciando inyección de posición manual...")

    # Valores del Usuario
    SYMBOL = "BTCUSDT"
    ENTRY_PRICE = 90840.51
    QTY = 0.000405
    USER_ID = 8

    # Path a la DB: backend/bot_data.db
    # Si ejecutamos desde el root, es backend/bot_data.db
    # Si ejecutamos desde backend/scripts, es ../bot_data.db

    # Intentar localizar la DB
    base_dir = os.path.dirname(
        os.path.abspath(__file__))  # .../backend/scripts
    db_path = os.path.join(base_dir, '..', 'bot_data.db')

    print(f"📂 Ruta de Base de Datos: {os.path.abspath(db_path)}")

    if not os.path.exists(db_path):
        print("❌ No se encuentra el archivo de base de datos.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"📊 Configurando para {SYMBOL}:")
    print(f"   - Precio Entrada: ${ENTRY_PRICE}")
    print(f"   - Cantidad: {QTY} BTC")

    try:
        # Helper para guardar estado
        def save_state(key, value):
            scoped_key = f"{key}_{SYMBOL}"
            # Check if exists
            cursor.execute(
                "SELECT 1 FROM state WHERE key=? AND user_id=?", (scoped_key, USER_ID))
            if cursor.fetchone():
                cursor.execute("UPDATE state SET value=? WHERE key=? AND user_id=?", (str(
                    value), scoped_key, USER_ID))
            else:
                cursor.execute(
                    "INSERT INTO state (key, value, user_id) VALUES (?, ?, ?)", (scoped_key, str(value), USER_ID))
            print(f"   ✅ {scoped_key} -> {value}")

        # Helper para guardar setting global
        def save_setting(key, value):
            cursor.execute(
                "SELECT 1 FROM settings WHERE key=? AND user_id=?", (key, USER_ID))
            if cursor.fetchone():
                cursor.execute("UPDATE settings SET value=? WHERE key=? AND user_id=?", (str(
                    value), key, USER_ID))
            else:
                cursor.execute(
                    "INSERT INTO settings (key, value, user_id) VALUES (?, ?, ?)", (key, str(value), USER_ID))
            print(f"   ⚙️ {key} -> {value}")

        # 1. Inyectar Estado de Posición
        save_state("entry_price", ENTRY_PRICE)
        save_state("accumulated_qty", QTY)
        save_state("position_orders", 1)
        save_state("highest_price", 0)

        # 2. Configurar Estrategia Segura
        save_state("sniper_mode", "True")
        save_state("dca_enabled", "False")
        save_state("enable_buying", "False")
        save_state("enable_selling", "True")

        save_setting("stop_loss_pct", 0)
        save_setting("take_profit_pct", 2.4)
        save_setting("sell_mode", "full")
        save_setting("trade_qty", 0.0004)

        conn.commit()
        print("\n✨ ¡Inyección completada exitosamente!")
        print("➡️  Reinicia el backend del bot para ver los cambios.")

    except Exception as e:
        print(f"\n❌ Error SQL: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    inject_position()
