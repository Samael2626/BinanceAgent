"""
Script to clean corrupted API credentials from the database
"""
import sqlite3
import sys

DB_PATH = "backend/bot_data.db"

print("🧹 Limpiando credenciales corruptas de la base de datos...")

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Delete corrupted credentials from state table
    cursor.execute("DELETE FROM state WHERE key = 'credentials'")
    rows_deleted = cursor.rowcount

    conn.commit()
    conn.close()

    print(
        f"✅ Limpieza exitosa! Se eliminaron {rows_deleted} registro(s) de credenciales.")
    print("\n📌 Próximos pasos:")
    print("   1. Ve a la UI del bot")
    print("   2. Haz clic en 'Logout / API 🔧'")
    print("   3. Ingresa tus credenciales de Binance (asegúrate de copiarlas SIN espacios)")
    print("   4. Selecciona 'LIVE' (no Testnet)")
    print("   5. Haz clic en 'Conectar'")
    print("\n⚠️  IMPORTANTE: Al copiar la API Key y Secret, asegúrate de:")
    print("   - NO incluir espacios al inicio o final")
    print("   - NO incluir saltos de línea")
    print("   - Copiar solo los caracteres alfanuméricos")

except Exception as e:
    print(f"❌ Error durante la limpieza: {e}")
    sys.exit(1)
