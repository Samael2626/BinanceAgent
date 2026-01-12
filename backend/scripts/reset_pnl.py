import requests
# Script rápido para SOLO resetear PnL
print("⏳ Reseteando SOLO PnL y Historial...")
try:
    resp = requests.post("http://localhost:8000/api/reset_pnl")
    if resp.status_code == 200:
        print("✅ PnL reseteado a 0.")
    else:
        print(f"❌ Error: {resp.text}")
except Exception as e:
    print(f"❌ Error: {e}")
