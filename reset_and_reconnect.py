"""
Script para RESETEAR COMPLETAMENTE las credenciales y empezar desde cero
"""
import sqlite3

DB_PATH = "backend/bot_data.db"

print("🧹 LIMPIEZA COMPLETA DE CREDENCIALES")
print("=" * 50)

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Delete ALL credentials from state table
    cursor.execute("DELETE FROM state WHERE key = 'credentials'")
    creds_deleted = cursor.rowcount

    # Also clear session tokens from users table (if exists)
    try:
        cursor.execute("UPDATE users SET session_token = NULL")
        users_cleared = cursor.rowcount
    except:
        users_cleared = 0

    conn.commit()
    conn.close()

    print(f"\n✅ LIMPIEZA EXITOSA!")
    print(f"   - Credenciales eliminadas: {creds_deleted}")
    print(f"   - Sesiones limpiadas: {users_cleared}")

    print("\n" + "=" * 50)
    print("📌 AHORA DEBES HACER ESTO:")
    print("=" * 50)

    print("\n1️⃣  IMPORTANTE: Abre tu navegador y ve a:")
    print("    👉 http://localhost:3000")

    print("\n2️⃣  Haz clic en el botón:")
    print("    👉 'Logout / API 🔧' (arriba a la derecha)")

    print("\n3️⃣  En la pantalla de login:")
    print("    📝 Campo 'API Key': Pega tu API Key de BINANCE REAL")
    print("    📝 Campo 'API Secret': Pega tu API Secret de BINANCE REAL")
    print("    🔴 Selecciona: 'LIVE' (NO Testnet)")
    print("    ✅ Haz clic en: 'Conectar'")

    print("\n⚠️  CRÍTICO: Asegúrate de que tus credenciales sean de:")
    print("    👉 https://www.binance.com (NO testnet.binance.vision)")
    print("    👉 Sin espacios al inicio o final")
    print("    👉 Copiadas exactamente como aparecen")

    print("\n4️⃣  Verifica que en la UI veas:")
    print("    ✅ Mode: 'REAL' (no TESTNET)")
    print("    ✅ Tu balance real de USDT/BTC")
    print("    ✅ Sin errores en la consola del backend")

    print("\n" + "=" * 50)
    print("🚀 Ahora ve a la UI y conéctate!")
    print("=" * 50 + "\n")

except Exception as e:
    print(f"\n❌ Error durante la limpieza: {e}")
