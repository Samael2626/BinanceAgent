import os
import requests
import sys
# Script rápido para SOLO resetear posición (útil para cuando vendes manual)
print("⏳ Reseteando SOLO Posición...")
try:
    resp = requests.post("http://localhost:8000/api/reset")
    if resp.status_code == 200:
        print("✅ Posición borrada. El bot ahora piensa que tiene 0 monedas.")
    else:
        print(f"❌ Error: {resp.text}")
except Exception as e:
    print(f"❌ Error: {e}")
