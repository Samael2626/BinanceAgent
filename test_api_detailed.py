"""
Test DIRECTO de la API - Identifica el problema exacto
"""
import json
import sqlite3
from binance.client import Client
from binance import BinanceSocketManager
import asyncio
import sys

print("="*60)
print("🔍 TEST DIRECTO DE BINANCE API")
print("="*60)

# Lee credenciales desde la base de datos

try:
    conn = sqlite3.connect("backend/bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM state WHERE key = 'credentials'")
    row = cursor.fetchone()

    if not row:
        print("❌ ERROR: No hay credenciales en la base de datos")
        print("\n👉 Ve a la UI y conéctate primero:")
        print("   http://localhost:3000")
        sys.exit(1)

    creds = json.loads(row[0])
    API_KEY = creds['api_key']
    API_SECRET = creds['api_secret']
    IS_TESTNET = creds['is_testnet']

    conn.close()

    print(f"\n📋 Credenciales encontradas:")
    print(f"   API Key: {API_KEY[:10]}...{API_KEY[-10:]}")
    print(f"   Modo: {'TESTNET' if IS_TESTNET else 'LIVE'}")
    print(f"\n" + "="*60)

except Exception as e:
    print(f"❌ Error leyendo credenciales: {e}")
    sys.exit(1)

# TEST 1: Conexión básica
print("\n1️⃣  TEST: Conexión REST API...")
try:
    client = Client(API_KEY, API_SECRET, testnet=IS_TESTNET)
    server_time = client.get_server_time()
    print("   ✅ PASS - Servidor alcanzable")
except Exception as e:
    print(f"   ❌ FAIL - {e}")
    sys.exit(1)

# TEST 2: Información de cuenta
print("\n2️⃣  TEST: Acceso a cuenta...")
try:
    account = client.get_account()
    can_trade = account.get('canTrade', False)
    print(f"   ✅ PASS - Cuenta accesible")
    print(f"   📊 Puede operar: {can_trade}")
except Exception as e:
    print(f"   ❌ FAIL - {e}")
    print("\n🔍 PROBLEMA IDENTIFICADO:")
    print("   Tu API Key NO tiene permisos para acceder a la cuenta")
    print("\n✅ SOLUCIÓN:")
    print("   1. Ve a: https://www.binance.com/en/my/settings/api-management")
    print("   2. Edita tu API Key")
    print("   3. Asegúrate de habilitar:")
    print("      ✓ Enable Reading")
    print("      ✓ Enable Spot & Margin Trading")
    sys.exit(1)

# TEST 3: Balance
print("\n3️⃣  TEST: Lectura de balance...")
try:
    balance = client.get_asset_balance(asset='USDT')
    print(f"   ✅ PASS - Balance USDT: {balance['free']}")
except Exception as e:
    print(f"   ❌ FAIL - {e}")
    sys.exit(1)

# TEST 4: User Data Stream (el que está fallando)
print("\n4️⃣  TEST: User Data Stream (WebSocket)...")
print("   ⏳ Intentando conectar...")
try:
    async def test_user_stream():
        client_test = Client(API_KEY, API_SECRET, testnet=IS_TESTNET)
        bsm = BinanceSocketManager(client_test)

        try:
            async with bsm.user_socket() as stream:
                print("   ✅ PASS - WebSocket conectado!")
                msg = await asyncio.wait_for(stream.recv(), timeout=3.0)
                print("   ✅ PASS - Mensaje recibido")
                return True
        except Exception as e:
            raise e

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(test_user_stream())

except Exception as e:
    print(f"   ❌ FAIL - {e}")
    print("\n🔍 PROBLEMA IDENTIFICADO:")
    print("   El User Data Stream requiere permisos especiales")
    print("\n✅ SOLUCIÓN:")
    print("   1. Ve a: https://www.binance.com/en/my/settings/api-management")
    print("   2. ELIMINA tu API Key actual")
    print("   3. CREA UNA NUEVA con estos permisos:")
    print("      ✓ Enable Reading")
    print("      ✓ Enable Spot & Margin Trading")
    print("   4. RESTRICCIONES DE IP:")
    print("      Si tienes IP restringida, AGREGA tu IP actual")
    print("      O cambia a 'Unrestricted' (menos seguro pero funciona)")
    print("\n   5. USA LAS NUEVAS CREDENCIALES en la UI")
    sys.exit(1)

print("\n" + "="*60)
print("🎉 TODOS LOS TESTS PASARON!")
print("="*60)
print("\n✅ Tu API está configurada correctamente")
print("✅ El bot debería funcionar sin problemas")
print("\n¿Por qué entonces aparece el error?")
print("Posiblemente las credenciales se están cargando desde otro lugar.")
print("\nReinicia el bot para asegurarte de que use estas credenciales.")
