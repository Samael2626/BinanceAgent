"""
Test script to diagnose Binance API connection issues
"""
from binance.client import Client
from binance import BinanceSocketManager
import asyncio

# Replace with your REAL API credentials
API_KEY = input("Enter your Binance API Key: ")
API_SECRET = input("Enter your Binance API Secret: ")

print("\n🔍 Testing Binance API Connection...\n")

try:
    # Test 1: Basic connection
    print("1️⃣ Testing basic REST API connection...")
    client = Client(API_KEY, API_SECRET, testnet=False)
    server_time = client.get_server_time()
    print(f"   ✅ Connected! Server time: {server_time}")

    # Test 2: Account permissions
    print("\n2️⃣ Testing account access...")
    account = client.get_account()
    print(f"   ✅ Account accessible! Can trade: {account['canTrade']}")

    # Test 3: Get USDT balance
    print("\n3️⃣ Testing balance retrieval...")
    balance = client.get_asset_balance(asset='USDT')
    print(
        f"   ✅ USDT Balance: {balance['free']} (Available) / {balance['locked']} (Locked)")

    # Test 4: User Data Stream (WebSocket)
    print("\n4️⃣ Testing User Data Stream (WebSocket)...")

    async def test_user_socket():
        bsm = BinanceSocketManager(client)
        async with bsm.user_socket() as stream:
            print("   ✅ User WebSocket connected!")
            msg = await asyncio.wait_for(stream.recv(), timeout=5.0)
            print(f"   ✅ Received message from User Stream")
            return True

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(test_user_socket())
    print("   ✅ User WebSocket test PASSED!")

    print("\n" + "="*50)
    print("🎉 ALL TESTS PASSED!")
    print("="*50)
    print("\n✅ Your API configuration is correct.")
    print("✅ All permissions are working properly.")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\n🔍 Possible issues:")
    print("  1. API Key or Secret is incorrect")
    print("  2. API doesn't have required permissions (Enable Spot Trading)")
    print("  3. IP restrictions are blocking your connection")
    print("  4. API Key is for TESTNET but you're using LIVE mode (or vice versa)")
