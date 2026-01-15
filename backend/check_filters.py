"""
Script para verificar estado de filtros en la base de datos
"""
import sqlite3

db_path = "backend/bot_data.db"


def check_filters():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n" + "="*60)
    print("VERIFICACIÓN DE FILTROS - RSI REBOUND STRATEGY")
    print("="*60 + "\n")

    # Consultar filtros críticos
    filters = [
        'enable_trend_filter',
        'enable_fast_ema',
        'enable_vol_filter',
        'buy_rsi',
        'sell_rsi',
        'active_strategy',
        'ema_length',
        'fast_ema_len'
    ]

    print("📊 CONFIGURACIÓN ACTUAL (user_id=1):\n")

    for filter_key in filters:
        cursor.execute(
            'SELECT value FROM settings WHERE user_id = 1 AND key = ?',
            (filter_key,)
        )
        result = cursor.fetchone()
        value = result[0] if result else "❌ NO CONFIGURADO"

        # Resaltar valores críticos
        if filter_key.startswith('enable') and value == "False":
            print(f"  🔴 {filter_key}: {value} (FILTRO DESHABILITADO)")
        elif filter_key.startswith('enable') and value == "True":
            print(f"  ✅ {filter_key}: {value}")
        else:
            print(f"  ⚙️  {filter_key}: {value}")

    # Verificar últimas operaciones
    print("\n" + "-"*60)
    print("📝 ÚLTIMAS 5 OPERACIONES:\n")

    cursor.execute('''
        SELECT time, type, price, qty, rsi, symbol 
        FROM trades 
        WHERE user_id = 1 
        ORDER BY id DESC 
        LIMIT 5
    ''')

    trades = cursor.fetchall()
    for trade in trades:
        time, type_, price, qty, rsi, symbol = trade
        print(
            f"  {time} | {type_:4s} | {symbol} @ ${price:,.2f} | Qty: {qty:.6f} | RSI: {rsi:.1f}")

    conn.close()

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    try:
        check_filters()
    except Exception as e:
        print(f"❌ Error: {e}")
