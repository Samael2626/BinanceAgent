"""
Script para verificar las credenciales guardadas en la base de datos
"""
import sqlite3
import json

DB_PATH = "backend/bot_data.db"

print("🔍 Verificando credenciales guardadas en la base de datos...\n")

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get credentials from state table
    cursor.execute("SELECT key, value FROM state WHERE key = 'credentials'")
    row = cursor.fetchone()

    if row:
        key, value = row
        try:
            creds = json.loads(value)
            api_key = creds.get('api_key', '')
            api_secret = creds.get('api_secret', '')
            is_testnet = creds.get('is_testnet', True)

            print("📋 Credenciales encontradas:")
            print(
                f"   - API Key: {api_key[:10]}...{api_key[-10:]} (longitud: {len(api_key)})")
            print(
                f"   - API Secret: {api_secret[:10]}...{api_secret[-10:]} (longitud: {len(api_secret)})")
            print(f"   - Modo: {'TESTNET' if is_testnet else 'LIVE'}")
            print(f"\n🔍 Análisis:")

            # Check for whitespace
            if api_key != api_key.strip():
                print(f"   ⚠️ API Key tiene espacios en blanco!")
            else:
                print(f"   ✅ API Key sin espacios")

            # Check for non-alphanumeric
            if not api_key.isalnum():
                print(f"   ⚠️ API Key contiene caracteres no alfanuméricos")
            else:
                print(f"   ✅ API Key solo tiene caracteres alfanuméricos")

            # Check length
            if len(api_key) < 36 or len(api_key) > 64:
                print(
                    f"   ⚠️ API Key longitud anormal ({len(api_key)} caracteres)")
            else:
                print(f"   ✅ API Key longitud correcta")

        except json.JSONDecodeError:
            print("❌ Error: Las credenciales no están en formato JSON válido")
    else:
        print("ℹ️  No hay credenciales guardadas en la base de datos")

    conn.close()

except Exception as e:
    print(f"❌ Error: {e}")
